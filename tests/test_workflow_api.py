"""Harihar transport/lifecycle tests. Deterministic planner is test-only."""
from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest

from fastapi.testclient import TestClient
from jsonschema import Draft202012Validator
from planner import PlannerService
from planner.provider import RuleBasedStructuredOutputProvider
from registry.contracts import schema
from workflow_api.main import create_app, COOKIE
from workflow_api.service import WorkflowService
from workflow_api.storage import WorkflowStore
from workflow_api.registry_adapter import load_registry_config

ROOT = Path(__file__).resolve().parents[1]


class WorkflowApiTests(unittest.TestCase):
    def setUp(self):
        (ROOT / '.local/tests').mkdir(parents=True, exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(dir=ROOT / '.local/tests')
        self.path = Path(self.temp.name) / 'workflows.sqlite3'
        self.service = WorkflowService(WorkflowStore(self.path), PlannerService(RuleBasedStructuredOutputProvider()))
        self.client = self.session(['builder'])
        self.workflow = json.loads((ROOT / 'shared/contracts/examples/workflows/support-triage.json').read_text())
        self.workflow['agents'] = []
        self.workflow['tools'] = []
        self.workflow['conditions'] = []
        self.workflow['approval_gates'] = []
        self.workflow['nodes'] = [dict(node_id='start', kind='trigger', label='Start'), dict(node_id='finish', kind='output', label='Finish')]
        self.workflow['edges'] = [dict(edge_id='start_finish', source='start', target='finish')]
        self.workflow['status'] = 'draft'
        self.workflow['version'] = 1
        self.workflow['execution_policy']['allow_external_writes'] = False
        self.workflow['metadata'] = {}

    def tearDown(self):
        self.client.close()
        self.temp.cleanup()

    def session(self, roles):
        client = TestClient(create_app(self.service, dev_auth=True, roles=roles))
        result = client.get('/session')
        client.cookies.set(COOKIE, result.cookies[COOKIE], path='/')
        return client

    def mutate(self, path, operation, payload, key='retry_key_12345678', client=None, method='post'):
        result = getattr(client or self.client, method)(path, json=dict(request_id='req_test', operation=operation, idempotency_key=key, payload=payload))
        Draft202012Validator(schema('api')['properties']['response_envelope']).validate(result.json())
        if result.status_code >= 400:
            Draft202012Validator(schema('error')).validate(result.json()['data']['error'])
        return result

    def save(self, workflow=None, base=0, key='save_key_12345678', client=None):
        workflow = workflow or self.workflow
        return self.mutate(f"/workflows/{workflow['workflow_id']}/versions/{workflow['version']}", 'save_workflow_version',
                           dict(workflow_id=workflow['workflow_id'], workflow_version=workflow['version'], workflow=workflow, base_version=base), key, client, 'put')

    def ref(self):
        return dict(workflow_id=self.workflow['workflow_id'], workflow_version=1)

    def test_session_opt_in_cookie_and_scope(self):
        disabled = TestClient(create_app(self.service, dev_auth=False))
        self.assertEqual(disabled.get('/session').status_code, 401)
        unauthenticated = TestClient(create_app(self.service, dev_auth=True))
        self.assertEqual(unauthenticated.get('/workflows').status_code, 401)
        self.assertEqual(self.client.get('/session', headers={'Origin': 'https://evil.example'}).status_code, 403)
        cookie = self.client.get('/session').headers['set-cookie']
        self.assertIn('HttpOnly', cookie)
        self.assertIn('SameSite=strict', cookie)
        self.assertNotIn('workflow.approve', self.client.get('/session').json()['data']['auth']['permissions'])

    def test_planner_to_save_to_restart_read(self):
        result = self.mutate('/workflows/plan', 'plan_workflow', {'objective': 'If a request arrives classify it and email the owner'})
        self.assertEqual(result.status_code, 200, result.json())
        draft = result.json()['data']['workflow']
        self.assertTrue(draft['conditions'])
        self.assertTrue(draft['approval_gates'])
        self.assertEqual(self.save(draft).status_code, 200)
        restarted = WorkflowService(WorkflowStore(self.path), self.service.planner)
        auth = self.client.get('/session').json()['data']['auth']
        read = restarted.handle(dict(request_id='req_read', operation='get_workflow', payload={'workflow_id': draft['workflow_id']}), auth)
        self.assertEqual(read['data']['workflow']['nodes'], draft['nodes'])
        self.assertEqual(read['data']['workflow']['approval_gates'], draft['approval_gates'])

    def test_idempotency_survives_restart_and_revision_conflict(self):
        first = self.save()
        self.assertEqual(first.status_code, 200)
        self.assertEqual(self.save().json(), first.json())
        restarted = WorkflowService(WorkflowStore(self.path))
        request = dict(request_id='req_retry', operation='save_workflow_version', idempotency_key='save_key_12345678',
                       payload=dict(workflow_id=self.workflow['workflow_id'], workflow_version=1, workflow=self.workflow, base_version=0))
        auth = self.client.get('/session').json()['data']['auth']
        self.assertEqual(restarted.handle(request, auth), first.json())
        changed = deepcopy(self.workflow)
        changed['name'] = 'Different'
        self.assertEqual(self.save(changed).status_code, 409)
        changed['version'] = 2
        self.assertEqual(self.save(changed, base=0, key='next_key_12345678').status_code, 409)
        self.assertEqual(self.save(changed, base=1, key='next_key_12345678').status_code, 200)

    def test_viewer_denied_and_payload_cannot_grant_authority(self):
        viewer = self.session(['viewer'])
        self.assertEqual(self.save(client=viewer).status_code, 403)
        response = self.mutate('/workflows/plan', 'plan_workflow', {'objective': 'Review', 'auth_context': {'roles': ['admin']}})
        self.assertEqual(response.status_code, 400)
        elevated = deepcopy(self.workflow)
        elevated['status'] = 'published'
        self.assertEqual(self.save(elevated).status_code, 400)
        viewer.close()

    def test_validation_errors_persist_and_never_echo_values(self):
        invalid = deepcopy(self.workflow)
        invalid['edges'][0]['target'] = 'missing_node'
        self.assertEqual(self.save(invalid).status_code, 200)
        result = self.mutate(f"/workflows/{invalid['workflow_id']}/validate", 'validate_workflow', self.ref())
        self.assertEqual(result.status_code, 400)
        self.assertEqual(result.json()['data']['error']['field'], 'edges[0].target')
        saved = self.client.get(f"/workflows/{invalid['workflow_id']}").json()['data']['workflow']
        self.assertEqual(saved['metadata']['validation_state'], 'validation_failed')

    def test_approve_publish_requires_roles_exact_revision_and_validation(self):
        self.save()
        endpoint = f"/workflows/{self.workflow['workflow_id']}"
        self.assertEqual(self.mutate(endpoint + '/approve', 'approve_workflow', {**self.ref(), 'action': 'approve'}).status_code, 403)
        admin = self.session(['admin'])
        self.assertEqual(self.mutate(endpoint + '/approve', 'approve_workflow', {**self.ref(), 'action': 'publish'}, client=admin).status_code, 409)
        self.assertEqual(self.mutate(endpoint + '/validate', 'validate_workflow', self.ref(), key='validate_key_12345678').status_code, 200)
        self.assertEqual(self.mutate(endpoint + '/approve', 'approve_workflow', {**self.ref(), 'action': 'approve'}, key='approve_key_12345678', client=admin).status_code, 200)
        self.assertEqual(self.mutate(endpoint + '/approve', 'approve_workflow', {**self.ref(), 'action': 'publish'}, key='publish_key_12345678', client=admin).json()['data']['workflow']['status'], 'published')
        admin.close()

    def test_tools_capabilities_cannot_be_published(self):
        result = self.mutate('/workflows/plan', 'plan_workflow', {'objective': 'Read a spreadsheet'})
        draft = result.json()['data']['workflow']
        self.save(draft)
        ref = dict(workflow_id=draft['workflow_id'], workflow_version=1)
        endpoint = f"/workflows/{draft['workflow_id']}"
        self.assertEqual(self.mutate(endpoint + '/validate', 'validate_workflow', ref).status_code, 200)
        admin = self.session(['admin'])
        denied = self.mutate(endpoint + '/approve', 'approve_workflow', {**ref, 'action': 'approve'}, key='approve_tool_key_12345678', client=admin)
        self.assertEqual(denied.json()['data']['error']['error_code'], 'TOOL_ASSIGNMENT_REQUIRED')
        admin.close()

    def test_safe_planner_errors_and_missing_runtime(self):
        invalid = self.mutate('/workflows/plan', 'plan_workflow', {'objective': ''})
        self.assertEqual(invalid.status_code, 400)
        self.assertNotIn('error', {k: v for k, v in invalid.json().items() if k != 'data'})
        secret = self.mutate('/workflows/plan', 'plan_workflow', {'objective': 'password=do_not_echo_this'})
        self.assertNotIn('do_not_echo_this', secret.text)
        result = self.client.get('/runs/run_missing')
        self.assertEqual(result.status_code, 503)
        self.assertEqual(self.client.get('/tools').json()['data']['items'], [])
        self.assertTrue(self.client.get('/agents/capabilities').json()['data']['items'])

    def test_hierarchy_semantics_fail_validation_until_review(self):
        self.workflow['nodes'][0]['configuration'] = {'ui': {'role': 'master'}}
        self.save()
        result = self.mutate(f"/workflows/{self.workflow['workflow_id']}/validate", 'validate_workflow', self.ref())
        self.assertEqual(result.status_code, 400)
        self.assertEqual(result.json()['data']['error']['error_code'], 'UNSUPPORTED_EXECUTION_CONFIGURATION')

    def test_unregistered_agent_cannot_be_approved_even_without_tools(self):
        standalone = json.loads((ROOT / 'shared/contracts/examples/agents/valid-classifier.json').read_text())
        for key in ('name', 'retry_policy', 'guardrails'):
            standalone.pop(key)
        standalone['capabilities'] = []
        standalone['allowed_tool_ids'] = []
        self.workflow['agents'] = [standalone]
        self.save()
        endpoint = f"/workflows/{self.workflow['workflow_id']}"
        self.assertEqual(self.mutate(endpoint + '/validate', 'validate_workflow', self.ref(), key='validate_agent_12345678').status_code, 200)
        admin = self.session(['admin'])
        response = self.mutate(endpoint + '/approve', 'approve_workflow', {**self.ref(), 'action': 'approve'}, key='approve_agent_12345678', client=admin)
        self.assertEqual(response.json()['data']['error']['error_code'], 'AGENT_REGISTRATION_REQUIRED')
        admin.close()

    def test_cross_workspace_read_and_body_path_mismatch(self):
        self.save()
        auth = self.client.get('/session').json()['data']['auth']
        auth['subject']['workspace_id'] = 'another-workspace'
        result = self.service.handle(dict(request_id='req_other', operation='get_workflow', payload=self.ref()), auth)
        self.assertEqual(result['status'], 404)
        mismatch = self.mutate('/workflows/wrong_id/versions/1', 'save_workflow_version', {**self.ref(), 'workflow': self.workflow, 'base_version': 0}, method='put')
        self.assertEqual(mismatch.status_code, 400)

    def registry_configuration(self, **tool_changes):
        agent = json.loads((ROOT / 'shared/contracts/examples/agents/valid-classifier.json').read_text())
        agent.update(capabilities=['read_spreadsheet'], permissions=['data.read'])
        agent['limits'].update(max_tool_calls=4, max_retries=2, max_estimated_cost_usd=1)
        agent['retry_policy']['max_retries'] = 2
        tool = json.loads((ROOT / 'shared/contracts/examples/tools/google-sheets-read.json').read_text())
        tool.update({'availability': 'enabled', **tool_changes})
        embedded = {key: value for key, value in agent.items() if key not in {'name', 'retry_policy', 'guardrails'}}
        self.workflow['agents'] = [embedded]
        self.workflow['tools'] = [dict(tool_id=tool['tool_id'], capability=tool['capability'])]
        self.workflow['nodes'].insert(1, dict(node_id='read_rows', kind='agent', label='Read rows', agent_id=agent['agent_id']))
        self.workflow['edges'] = [dict(edge_id='start_read', source='start', target='read_rows'), dict(edge_id='read_finish', source='read_rows', target='finish')]
        config = dict(policy=dict(workspace_id='local-workspace', agent_permissions=['workflow.read_input', 'data.read'],
                      approved_providers=['google_sheets'], remaining_quota={tool['tool_id']: 10},
                      credential_references={'cred_local_sheets': dict(provider_id='google_sheets', scopes=['data.read', 'spreadsheets.readonly'])}),
                      agents=[agent], tools=[dict(definition=tool, credential_reference='cred_local_sheets')],
                      bindings=[dict(workflow_id=self.workflow['workflow_id'], workflow_version=1, agent_id=agent['agent_id'],
                                     capability=tool['capability'], tool_id=tool['tool_id'], input_schema=tool['input_schema'], output_schema=tool['output_schema'])],
                      subject_permissions=['data.read'], subject_scopes=['data.read', 'spreadsheets.readonly'])
        return config

    def configured_session(self, config, roles=None):
        source = Path(self.temp.name) / 'registry.json'
        source.write_text(json.dumps(config))
        client = TestClient(create_app(dev_auth=True, roles=roles or ['admin'], database=self.path, registry_config=source))
        response = client.get('/session')
        client.cookies.set(COOKIE, response.cookies[COOKIE], path='/')
        self.addCleanup(client.close)
        return client

    def test_configured_registry_allows_exact_revision_publication_and_retry(self):
        config = self.registry_configuration()
        admin = self.configured_session(config)
        saved = self.save(client=admin)
        self.assertEqual(saved.status_code, 200, saved.json())
        review = saved.json()['data']['registry_review']
        self.assertTrue(review['ready'], review)
        self.assertEqual(review['items'][0]['authorization_state'], 'authorized')
        self.assertNotIn('cred_local_sheets', saved.text)
        self.assertNotIn('authorization_reference', saved.text)
        endpoint = f"/workflows/{self.workflow['workflow_id']}"
        self.assertEqual(self.mutate(endpoint + '/validate', 'validate_workflow', self.ref(), key='validate_registry_1234', client=admin).status_code, 200)
        approved = self.mutate(endpoint + '/approve', 'approve_workflow', {**self.ref(), 'action': 'approve'}, key='approve_registry_1234', client=admin)
        self.assertEqual(approved.status_code, 200, approved.json())
        self.assertEqual(approved.json()['data']['workflow']['agents'][0]['allowed_tool_ids'], ['google_sheets_read_rows'])
        published = self.mutate(endpoint + '/approve', 'approve_workflow', {**self.ref(), 'action': 'publish'}, key='publish_registry_1234', client=admin)
        self.assertEqual(published.status_code, 200, published.json())
        restarted = self.configured_session(config)
        self.assertEqual(restarted.get(endpoint).json()['data']['workflow']['status'], 'published')
        retry = self.mutate(endpoint + '/approve', 'approve_workflow', {**self.ref(), 'action': 'publish'}, key='publish_registry_1234', client=restarted)
        self.assertEqual(retry.json(), published.json())
        revision = deepcopy(self.workflow)
        revision['version'] = 2
        result = self.save(revision, base=1, key='save_registry_v2_1234', client=admin)
        self.assertFalse(result.json()['data']['registry_review']['ready'])
        self.assertIn('ASSIGNMENT_CONFIGURATION_REQUIRED', result.json()['data']['registry_review']['reason_codes'])

    def test_registry_unavailable_risky_pending_and_missing_scopes_fail_publication(self):
        for changes, reason in [({'availability': 'disabled'}, 'TOOL_UNAVAILABLE'),
                                ({'risk_level': 'high'}, 'RISK_NOT_AUTHORIZED'),
                                ({'approval_required': True}, 'APPROVAL_REQUIRED'),
                                ({}, 'MISSING_SCOPE')]:
            with self.subTest(reason=reason):
                # Reset the graph after each independent configuration scenario.
                self.workflow['nodes'] = [self.workflow['nodes'][0], self.workflow['nodes'][-1]]
                config = self.registry_configuration(**changes)
                self.workflow['workflow_id'] = 'registry_' + reason.lower()
                config['bindings'][0]['workflow_id'] = self.workflow['workflow_id']
                if reason == 'MISSING_SCOPE':
                    config['subject_scopes'] = []
                client = self.configured_session(config)
                saved = self.save(key='save_' + reason, client=client)
                self.assertEqual(saved.status_code, 200, saved.json())
                review = saved.json()['data']['registry_review']
                self.assertFalse(review['ready'])
                self.assertIn(reason, review['reason_codes'])
                if reason == 'APPROVAL_REQUIRED':
                    self.assertEqual(review['items'][0]['authorization_state'], 'pending_approval')
                endpoint = f"/workflows/{self.workflow['workflow_id']}"
                self.mutate(endpoint + '/validate', 'validate_workflow', self.ref(), key='validate_' + reason, client=client)
                denied = self.mutate(endpoint + '/approve', 'approve_workflow', {**self.ref(), 'action': 'approve'}, key='approve_' + reason, client=client)
                self.assertEqual(denied.status_code, 409, denied.json())

    def test_registry_revalidation_rejects_revocation_and_agent_edits(self):
        config = self.registry_configuration()
        source = Path(self.temp.name) / 'registry.json'
        source.write_text(json.dumps(config))
        adapter, permissions, scopes = load_registry_config(source)
        auth = self.client.get('/session').json()['data']['auth']
        auth['permissions'] += permissions
        auth['scopes'] += scopes
        first = adapter.review(self.workflow, auth)
        self.assertTrue(first['ready'])
        grants = adapter.execution_assignments(self.workflow, auth)
        self.assertEqual(grants[0]['workflow_version'], 1)
        revoked = deepcopy(auth)
        revoked['scopes'] = []
        self.assertIn('MISSING_SCOPE', adapter.review(self.workflow, revoked)['reason_codes'])
        changed = deepcopy(self.workflow)
        changed['agents'][0]['instructions'] = 'Changed instructions need registry acceptance'
        self.assertIn('AGENT_CONFIGURATION_MISMATCH', adapter.review(changed, auth)['reason_codes'])
        viewer = deepcopy(auth)
        viewer['roles'] = ['viewer']
        self.assertFalse(adapter.review(self.workflow, viewer)['ready'])
        config['tools'][0]['definition']['availability'] = 'disabled'
        managing = deepcopy(auth)
        managing['roles'] = ['admin']
        managing['permissions'].append('tools.manage')
        adapter.service.register_tool(config['tools'][0]['definition'], managing, 'cred_local_sheets')
        self.assertIn('STALE_ASSIGNMENT', adapter.review(self.workflow, auth)['reason_codes'])

    def test_registry_config_rejects_client_like_authority_secrets_and_external_paths(self):
        config = self.registry_configuration()
        config['policy']['approval_grants'] = {'invented': {'reference': 'approval_fake'}}
        source = Path(self.temp.name) / 'invalid-registry.json'
        source.write_text(json.dumps(config))
        with self.assertRaisesRegex(ValueError, 'Invalid trusted registry configuration'):
            load_registry_config(source)
        with self.assertRaisesRegex(ValueError, 'Invalid trusted registry configuration'):
            load_registry_config(ROOT.parent / 'unread-external.json')
        source.write_text(json.dumps({'password': 'never_reflect_configuration_contents'}))
        with self.assertRaises(ValueError) as failure:
            load_registry_config(source)
        self.assertNotIn('never_reflect', str(failure.exception))
