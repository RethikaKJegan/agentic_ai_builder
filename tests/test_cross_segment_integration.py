import json
import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

from planner import PlannerService
from planner.provider import RuleBasedStructuredOutputProvider
from workflow_api.main import COOKIE, create_app


ROOT = Path(__file__).resolve().parents[1]


class OfflineConnector:
    external_write = True
    timeout = 30

    @staticmethod
    def reservation(grant):
        return {'tool_calls': 1, 'estimated_cost_usd': 0}

    def invoke(self, grant, inputs, effect_id):
        return {'message_id': effect_id}


def offline_model_factory(definition):
    from runtime.model import BoundedLLM
    return BoundedLLM(definition, lambda messages, cap, duration: ('{}', 0, 0), lambda messages: 1, 0, 0)


class CrossSegmentIntegrationTests(unittest.TestCase):
    def setUp(self):
        (ROOT / '.local').mkdir(exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(dir=ROOT / '.local')
        root = Path(self.temp.name)
        smtp = json.loads((ROOT / 'shared/contracts/examples/tools/smtp-send-email.json').read_text())
        self.registry = {
            'auto_resolve_planner': True,
            'policy': {
                'workspace_id': 'local-workspace',
                'agent_permissions': ['workflow.read_input', 'communication.send'],
                'approved_providers': ['smtp'],
                'allowed_destinations': ['verified_recipients'],
                'remaining_quota': {'smtp_send_email': 10},
                'credential_references': {'cred_test_smtp': {'provider_id': 'smtp', 'scopes': ['communication.send', 'email.send']}},
                'approval_roles': ['approver'],
            },
            'agents': [],
            'tools': [{'definition': smtp, 'credential_reference': 'cred_test_smtp'}],
            'bindings': [],
            'subject_permissions': ['communication.send'],
            'operator_permissions': ['tools.manage'],
            'subject_scopes': ['communication.send', 'email.send'],
        }
        config = root / 'registry.json'
        config.write_text(json.dumps(self.registry))
        self.app = create_app(dev_auth=True, roles=['admin', 'approver'], runtime_enabled=True, database=root / 'workflows.sqlite3', registry_config=config)
        self.app.state.workflow_service.planner = PlannerService(RuleBasedStructuredOutputProvider())
        from runtime import RuntimeService
        from runtime.crew import CrewExecutor
        from runtime.graph import GraphRunner
        service = self.app.state.workflow_service
        service.runtime_runner = GraphRunner(RuntimeService(service), agents=CrewExecutor(service.registry_adapter, offline_model_factory),
                                             connectors={'smtp_send_email': OfflineConnector()})
        self.client = TestClient(self.app)
        session = self.client.get('/session')
        self.client.cookies.set(COOKIE, session.cookies[COOKIE], path='/')

    def tearDown(self):
        self.client.close()
        self.temp.cleanup()

    def request(self, operation, key, payload, path):
        return self.client.post(path, json={'request_id': 'req_' + key, 'operation': operation,
                                            'idempotency_key': key, 'payload': payload})

    def test_prompt_resolves_tool_and_approval_before_publication(self):
        planned = self.request('plan_workflow', 'plan_auto_123456', {'objective': 'Send an email to the owner'}, '/workflows/plan')
        self.assertEqual(planned.status_code, 200, planned.text)
        workflow = planned.json()['data']['workflow']
        self.assertTrue(workflow['agents'][0]['agent_id'].startswith(workflow['workflow_id'] + '_'))
        saved = self.client.put(f"/workflows/{workflow['workflow_id']}/versions/1", json={
            'request_id': 'req_save_auto_123456', 'operation': 'save_workflow_version', 'idempotency_key': 'save_auto_123456',
            'payload': {'workflow_id': workflow['workflow_id'], 'workflow_version': 1, 'base_version': 0, 'workflow': workflow},
        })
        self.assertEqual(saved.status_code, 200, saved.text)
        resolved = saved.json()['data']['workflow']
        self.assertEqual(resolved['tools'], [{'tool_id': 'smtp_send_email', 'capability': 'send_email'}])
        self.assertTrue(any(node['kind'] == 'tool' and node['tool_id'] == 'smtp_send_email' for node in resolved['nodes']))
        self.assertEqual(saved.json()['data']['registry_review']['items'][0]['authorization_state'], 'pending_approval')
        ref = {'workflow_id': workflow['workflow_id'], 'workflow_version': 1}
        validated = self.request('validate_workflow', 'validate_auto_123456', ref, f"/workflows/{workflow['workflow_id']}/validate")
        self.assertEqual(validated.status_code, 200, validated.text)
        approved = self.request('approve_workflow', 'approve_auto_123456', {**ref, 'action': 'approve'}, f"/workflows/{workflow['workflow_id']}/approve")
        self.assertEqual(approved.status_code, 200, approved.text)
        self.assertEqual(approved.json()['data']['workflow']['status'], 'approved')
        self.assertTrue(approved.json()['data']['registry_review']['ready'])

    def test_hierarchical_prompt_resolves_specialist_assignments_before_publication(self):
        planned = self.request('plan_workflow', 'plan_hierarchy_123456', {
            'objective': 'Classify the request and send an email to the owner', 'context': {'generation_mode': 'hierarchy'},
        }, '/workflows/plan')
        self.assertEqual(planned.status_code, 200, planned.text)
        workflow = planned.json()['data']['workflow']
        self.assertEqual(workflow['agents'][0]['hierarchy_role'], 'master')
        saved = self.client.put(f"/workflows/{workflow['workflow_id']}/versions/1", json={
            'request_id': 'req_save_hierarchy_123456', 'operation': 'save_workflow_version', 'idempotency_key': 'save_hierarchy_123456',
            'payload': {'workflow_id': workflow['workflow_id'], 'workflow_version': 1, 'base_version': 0, 'workflow': workflow},
        })
        self.assertEqual(saved.status_code, 200, saved.text)
        # Simulate a draft saved before the Registry learnt that model-only
        # capabilities do not need connector assignments.
        legacy = saved.json()['data']['workflow']
        legacy['metadata']['unresolved_requirements'] = [{'requirement': 'classify_text', 'reason': 'registry_assignment_pending'}]
        with self.app.state.workflow_service.store.transaction() as db:
            self.app.state.workflow_service.store.put(db, 'local-workspace', legacy)
        ref = {'workflow_id': workflow['workflow_id'], 'workflow_version': 1}
        self.assertEqual(self.request('validate_workflow', 'validate_hierarchy_123456', ref, f"/workflows/{workflow['workflow_id']}/validate").status_code, 200)
        approved = self.request('approve_workflow', 'approve_hierarchy_123456', {**ref, 'action': 'approve'}, f"/workflows/{workflow['workflow_id']}/approve")
        self.assertEqual(approved.status_code, 200, approved.text)

    def test_missing_capability_remains_unresolved(self):
        planned = self.request('plan_workflow', 'plan_unknown_123456', {'objective': 'Notify the team through an unknown provider'}, '/workflows/plan')
        self.assertEqual(planned.status_code, 200, planned.text)
        workflow = planned.json()['data']['workflow']
        self.assertTrue(workflow['metadata']['unresolved_requirements'])

    def test_approved_revision_runs_to_exact_action_approval_and_connector(self):
        planned = self.request('plan_workflow', 'plan_run_123456', {'objective': 'Send an email to the owner'}, '/workflows/plan')
        workflow = planned.json()['data']['workflow']
        self.client.put(f"/workflows/{workflow['workflow_id']}/versions/1", json={
            'request_id': 'req_save_run_123456', 'operation': 'save_workflow_version', 'idempotency_key': 'save_run_123456',
            'payload': {'workflow_id': workflow['workflow_id'], 'workflow_version': 1, 'base_version': 0, 'workflow': workflow},
        })
        ref = {'workflow_id': workflow['workflow_id'], 'workflow_version': 1}
        self.request('validate_workflow', 'validate_run_123456', ref, f"/workflows/{workflow['workflow_id']}/validate")
        self.request('approve_workflow', 'approve_run_123456', {**ref, 'action': 'approve'}, f"/workflows/{workflow['workflow_id']}/approve")
        published = self.request('approve_workflow', 'publish_run_123456', {**ref, 'action': 'publish'}, f"/workflows/{workflow['workflow_id']}/approve")
        self.assertEqual(published.status_code, 200, published.text)
        activation = self.client.post(f"/workflows/{workflow['workflow_id']}/releases", json={
            'request_id': 'req_release_run_123456', 'operation': 'activate_release', 'idempotency_key': 'release_run_123456',
            'payload': {'workflow_id': workflow['workflow_id'], 'workflow_version': 1, 'triggers': []},
        })
        self.assertEqual(activation.status_code, 200, activation.text)
        run = self.request('execute_workflow', 'execute_run_123456', {**ref, 'inputs': {
            'email_to': 'owner@example.com', 'email_subject': 'Test', 'email_body': 'Controlled local test',
        }}, f"/workflows/{workflow['workflow_id']}/execute")
        self.assertEqual(run.status_code, 200, run.text)
        with self.app.state.workflow_service.store.transaction() as db:
            detail = self.app.state.workflow_service.runtime_runner.runtime.load(db, run.json()['data']['run']['run_id'], self.client.get('/session').json()['data']['auth'])
        self.assertEqual(run.json()['data']['run']['status'], 'paused_for_approval', detail)
        pending = run.json()['data']['run']['approvals'][0]
        decision = self.request('decide_approval', 'decision_run_123456', {
            'approval_id': pending['approval_id'], **ref, 'decision': 'approved',
        }, f"/approvals/{pending['approval_id']}/decision")
        self.assertEqual(decision.status_code, 200, decision.text)
        completed = self.app.state.workflow_service.runtime_runner.advance(run.json()['data']['run']['run_id'],
                                                                            self.client.get('/session').json()['data']['auth'])
        with self.app.state.workflow_service.store.transaction() as db:
            detail = self.app.state.workflow_service.runtime_runner.runtime.load(db, run.json()['data']['run']['run_id'], self.client.get('/session').json()['data']['auth'])
        self.assertEqual(completed['status'], 'completed', detail)


if __name__ == '__main__':
    unittest.main()
