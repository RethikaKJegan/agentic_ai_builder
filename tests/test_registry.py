from copy import deepcopy
import json
from pathlib import Path
import time
import unittest
from jsonschema import Draft202012Validator

from planner import PlannerService
from planner.provider import RuleBasedStructuredOutputProvider
from registry import RegistryService, WorkspacePolicy
from registry.contracts import schema
from registry.matching import schema_subset

ROOT = Path(__file__).resolve().parents[1]


def fixture(relative):
    return json.loads((ROOT / relative).read_text())


def auth(roles=None, permissions=None, scopes=None, subject='operator', workspace='workspace-1'):
    return dict(subject=dict(subject_id=subject, workspace_id=workspace), roles=roles or ['admin'],
                permissions=permissions if permissions is not None else ['tools.manage','tools.assign','tools.read',
                    'workflow.approve','workflow.read_input','data.read','communication.send'],
                scopes=scopes if scopes is not None else ['data.read','spreadsheets.readonly','communication.send','email.send',
                    'github.access','slack.access','weather.access','http.access','webhook.access'], decision='allow')


def policy():
    p = WorkspacePolicy('workspace-1', agent_permissions={'workflow.read_input','data.read','communication.send'},
        approved_providers={'smtp','google_sheets','github','slack','weather','http','webhook'},
        allowed_destinations={'https://api.example/read','verified_recipients'})
    for provider in p.approved_providers:
        p.credential_references[f'cred_{provider}'] = {'provider_id': provider, 'scopes': auth()['scopes']}
    p.remaining_quota = dict(google_sheets_read_rows=10,smtp_send_email=10,github_send_notification=10,
        slack_send_notification=10,weather_read_conditions=10,approved_http_request=10,approved_webhook_request=10)
    return p


def agent(capabilities=None, agent_id='reader_agent'):
    value = fixture('shared/contracts/examples/agents/valid-classifier.json')
    value.update(agent_id=agent_id, capabilities=capabilities or ['read_spreadsheet'], permissions=['data.read'])
    value['limits'].update(max_tool_calls=4, max_retries=2, timeout_seconds=60)
    value['retry_policy']['max_retries'] = 2
    return value


def sheets():
    tool=fixture('shared/contracts/examples/tools/google-sheets-read.json')
    tool['availability']='enabled'
    return tool


class RegistryTests(unittest.TestCase):
    def setUp(self):
        self.policy=policy()
        self.service=RegistryService(self.policy)
        self.admin=auth()

    def ok(self, response):
        self.assertEqual(response['status'],200,response)
        Draft202012Validator(schema('api')['properties']['response_envelope']).validate(response)
        return response['data']

    def error(self, response, code):
        self.assertGreaterEqual(response['status'],400,response)
        self.assertEqual(response['data']['error']['error_code'],code,response)
        Draft202012Validator(schema('error')).validate(response['data']['error'])
        Draft202012Validator(schema('api')['properties']['response_envelope']).validate(response)

    def ready(self):
        self.ok(self.service.register_agent(agent(),self.admin))
        self.ok(self.service.register_tool(sheets(),self.admin,'cred_google_sheets'))

    def assign(self, **changes):
        params=dict(agent_id='reader_agent',capability='read_spreadsheet',input_schema=sheets()['input_schema'],
            output_schema=sheets()['output_schema'],auth=self.admin,workflow_id='workflow_one',workflow_version=1)
        params.update(changes)
        return self.service.assign(**params)

    def test_agent_contract_negative_fixtures_and_limits(self):
        for name,code in [('incomplete-agent','VALIDATION_FAILED'),('overprivileged-agent','AGENT_NOT_AUTHORIZED'),
                          ('secret-bearing-agent','SENSITIVE_DATA_DETECTED')]:
            with self.subTest(name=name):
                self.error(self.service.register_agent(fixture(f'shared/contracts/examples/agents/{name}.json'),self.admin),code)
        over=agent();over['limits']['max_tokens']=999999
        self.error(self.service.register_agent(over,self.admin),'AGENT_LIMIT_EXCEEDED')
        self.ok(self.service.register_agent(fixture('shared/contracts/examples/agents/valid-classifier.json'),self.admin))

    def test_agent_versions_workspace_ownership_and_copy_isolation(self):
        original=agent()
        first=self.ok(self.service.register_agent(original,self.admin))['agent']
        first['definition']['permissions'].append('admin.all')
        original['instructions']='Updated approved instructions'
        second=self.ok(self.service.register_agent(original,self.admin))['agent']
        self.assertEqual(second['version'],2)
        self.assertEqual(second['workspace_id'],'workspace-1')
        self.assertEqual(second['owner_subject_id'],'operator')
        self.assertEqual(second['definition']['permissions'],['data.read'])
        self.error(self.service.register_agent(original,auth(workspace='other')),'WORKSPACE_NOT_AUTHORIZED')

    def test_planner_adapter_preserves_no_grants_and_unresolved_requirements(self):
        planner_auth={'subject_id':'operator','workspace_id':'workspace-1','roles':['builder'],'permissions':['workflow.plan']}
        response=PlannerService(provider=RuleBasedStructuredOutputProvider()).plan(dict(request_id='planner_req',
            operation='plan_workflow',idempotency_key='planner-registry-123',
            payload={'objective':'If a request is urgent, read a spreadsheet and send an email', 'auth_context':planner_auth}))
        self.ok(self.service.register_tool(sheets(),self.admin,'cred_google_sheets'))
        self.ok(self.service.register_tool(fixture('shared/contracts/examples/tools/smtp-send-email.json'),self.admin,'cred_smtp'))
        before=deepcopy(response)
        adapted=self.ok(self.service.consume_planner(response,self.admin))['requirements']
        self.assertEqual(response,before)
        self.assertEqual(adapted['agents'][0]['allowed_tool_ids'],[])
        self.assertEqual(adapted['agents'][0]['permissions'],['workflow.read_input'])
        self.assertTrue(adapted['approval_gates'])
        self.assertTrue(adapted['execution_policy']['requires_review_before_execution'])
        self.ok(self.service.register_agent(adapted['agents'][0],self.admin))
        # Planner agents cannot inherit connector permissions or tool-call budget.
        self.error(self.service.assign(adapted['agents'][0]['agent_id'],'read_spreadsheet',sheets()['input_schema'],
            sheets()['output_schema'],self.admin,adapted['workflow_id'],adapted['workflow_version']),'NO_ELIGIBLE_TOOL')
        response['data']['workflow']['metadata']['unresolved_requirements']=['unknown_action']
        self.assertIn('unknown_action',self.ok(self.service.consume_planner(response,self.admin))['requirements']['unresolved_requirements'])
        response['data']['workflow']['agents'][0]['allowed_tool_ids']=['smtp_send_email']
        self.error(self.service.consume_planner(response,self.admin),'INVALID_PLANNER_HANDOFF')

    def test_all_approved_connector_fixtures_register(self):
        tools=[sheets(),fixture('shared/contracts/examples/tools/smtp-send-email.json')]
        tools += [fixture(f'tests/fixtures/registry/{name}.json') for name in ('github','slack','weather','http','webhook')]
        for tool in tools:
            with self.subTest(provider=tool['provider_id']):
                result=self.ok(self.service.register_tool(tool,self.admin,f"cred_{tool['provider_id']}"))
                Draft202012Validator(schema('tool')).validate(result['tool']['definition'])
        self.assertEqual(self.ok(self.service.list_tools(self.admin))['total'],7)

    def test_raw_credentials_rejected_before_storage_and_never_reflected(self):
        for extra in ({'password':'raw-password-value'}, {'description':'Bearer raw-token-value'},
                      {'description':'https://user:secret@example.com'}, {'api_key':'raw-key-value'}):
            value=sheets();value.update(extra)
            result=self.service.register_tool(value,self.admin,'cred_google_sheets')
            self.error(result,'SENSITIVE_DATA_DETECTED')
            for secret in ('raw-password-value','raw-token-value','raw-key-value','user:secret'):
                self.assertNotIn(secret,json.dumps(result))
                self.assertNotIn(secret,json.dumps(self.ok(self.service.decision_records(self.admin))))
        self.assertEqual(self.ok(self.service.list_tools(self.admin))['total'],0)
        self.error(self.service.register_tool(sheets(),self.admin,'raw-credential'),'INVALID_CREDENTIAL_REFERENCE')
        self.error(self.service.register_tool(sheets(),self.admin,'cred_smtp'),'CREDENTIAL_NOT_CONFIGURED')

    def test_incomplete_metadata_rejected(self):
        for field in ('availability','risk_level','rate_limits','estimated_cost','timeout_seconds','retry_policy','approval_required'):
            value=sheets();del value[field]
            self.error(self.service.register_tool(value,self.admin),'VALIDATION_FAILED')
        self.error(self.service.register_tool(fixture('shared/contracts/examples/tools/incomplete-tool.json'),self.admin),'VALIDATION_FAILED')

    def test_assignments_are_bound_to_versions_subject_workflow_agent_and_tool(self):
        self.ready()
        grant=self.ok(self.assign())['assignment']
        self.assertEqual(grant['assigned_tool_ids'],['google_sheets_read_rows'])
        self.assertEqual(grant['authorization_state'],'authorized')
        self.assertEqual(grant['credential_reference'],'cred_google_sheets')
        params=dict(reference=grant['authorization_reference'],agent_id='reader_agent',tool_id='google_sheets_read_rows',
            workflow_id='workflow_one',workflow_version=1,auth=self.admin)
        self.ok(self.service.revalidate_assignment(**params))
        for change in (dict(agent_id='other_agent'),dict(tool_id='smtp_send_email'),dict(workflow_version=2),
                       dict(auth=auth(subject='someone_else'))):
            self.error(self.service.revalidate_assignment(**{**params,**change}),'UNASSIGNED_TOOL')
        self.ok(self.service.register_tool(sheets(),self.admin,'cred_google_sheets'))
        self.error(self.service.revalidate_assignment(**params),'STALE_ASSIGNMENT')

    def test_matching_checks_both_schemas_and_does_not_invent_tools(self):
        self.ready()
        self.error(self.assign(input_schema={'type':'string'}),'NO_ELIGIBLE_TOOL')
        self.error(self.assign(output_schema={'type':'object','required':['secret_field']}),'NO_ELIGIBLE_TOOL')
        self.error(self.assign(tool_id='imaginary_connector'),'NO_ELIGIBLE_TOOL')
        self.error(self.assign(capability='send_email'),'UNASSIGNED_CAPABILITY')
        self.assertTrue(schema_subset({'type':'object','required':['a','b']},{'type':'object','required':['a']}))
        self.assertFalse(schema_subset({'type':'object','required':['a']},{'type':'object','required':['a','b']}))
        self.assertFalse(schema_subset({'type':'object'},{'type':'object','properties':{'a':{'type':'string'}}}))

    def test_revoked_scopes_unavailable_provider_quota_risk_and_permissions(self):
        self.ready()
        for changed in (dict(scopes=[]),dict(permissions=['tools.assign']),dict(workspace='elsewhere'),
                        dict(roles=['viewer'])):
            self.assertGreaterEqual(self.assign(auth=auth(**changed))['status'],400)
        for field,value,reason in [('availability','disabled','TOOL_UNAVAILABLE'),('risk_level','critical','RISK_NOT_AUTHORIZED')]:
            tool=sheets();tool[field]=value
            self.ok(self.service.register_tool(tool,self.admin,'cred_google_sheets'))
            denied=self.assign();self.error(denied,'NO_ELIGIBLE_TOOL')
            self.assertEqual(denied['data']['error']['details']['excluded_candidates'][0]['reason_code'],reason)
        self.ok(self.service.register_tool(sheets(),self.admin,'cred_google_sheets'))
        self.policy.version=2;self.policy.remaining_quota['google_sheets_read_rows']=0
        self.ok(self.service.update_policy(self.policy,self.admin))
        denied=self.assign();self.error(denied,'NO_ELIGIBLE_TOOL')
        self.assertEqual(denied['data']['error']['details']['excluded_candidates'][0]['reason_code'],'QUOTA_EXCEEDED')

    def test_credential_revocation_and_policy_revision_invalidate_assignments(self):
        self.ready();grant=self.ok(self.assign())['assignment']
        self.policy.version=2;self.policy.credential_references.clear()
        self.ok(self.service.update_policy(self.policy,self.admin))
        self.error(self.assign(),'NO_ELIGIBLE_TOOL')
        self.error(self.service.revalidate_assignment(grant['authorization_reference'],'reader_agent','google_sheets_read_rows',
            'workflow_one',1,self.admin),'STALE_ASSIGNMENT')

    def test_missing_credentials_excluded_even_when_metadata_enabled(self):
        self.ok(self.service.register_agent(agent(),self.admin))
        self.ok(self.service.register_tool(sheets(),self.admin))
        denied=self.assign();self.error(denied,'NO_ELIGIBLE_TOOL')
        self.assertEqual(denied['data']['error']['details']['excluded_candidates'][0]['reason_code'],'CREDENTIAL_NOT_CONFIGURED')

    def test_http_and_webhook_destinations_require_both_allowlists(self):
        self.ok(self.service.register_agent(agent(['retrieve_records','send_notification']),self.admin))
        for provider,capability in [('http','retrieve_records'),('webhook','send_notification')]:
            tool=fixture(f'tests/fixtures/registry/{provider}.json')
            self.ok(self.service.register_tool(tool,self.admin,f'cred_{provider}'))
            params=dict(capability=capability,input_schema=tool['input_schema'],output_schema=tool['output_schema'],tool_id=tool['tool_id'])
            self.error(self.assign(**params,destination='https://evil.example/write'),'NO_ELIGIBLE_TOOL')
            self.error(self.assign(**params),'NO_ELIGIBLE_TOOL')
            self.ok(self.assign(**params,destination='https://api.example/read'))

    def test_approval_is_pending_until_trusted_bound_unexpired_evidence(self):
        value=agent(['send_email']);value['permissions']=['communication.send']
        self.ok(self.service.register_agent(value,self.admin))
        tool=fixture('shared/contracts/examples/tools/smtp-send-email.json')
        self.ok(self.service.register_tool(tool,self.admin,'cred_smtp'))
        params=dict(capability='send_email',input_schema=tool['input_schema'],output_schema=tool['output_schema'],destination='verified_recipients')
        pending=self.ok(self.assign(**params))['assignment']
        self.assertEqual(pending['authorization_state'],'pending_approval')
        self.assertEqual(pending['assigned_tool_ids'],[])
        self.assertIsNone(pending['authorization_reference'])
        # Approval grants are supplied by trusted server policy, bound to the new policy revision.
        self.policy.version=2
        self.ok(self.service.update_policy(self.policy,self.admin))
        pending=self.ok(self.assign(**params))['assignment']
        self.policy.approval_grants[pending['approval_fingerprint']]=dict(reference='approval_one',expires_at=time.time()+60,
            approver=auth(roles=['approver']))
        # Refresh approval state within this policy version via the trusted policy object.
        self.ok(self.service.update_approval_evidence(self.policy.approval_grants,self.admin))
        grant=self.ok(self.assign(**params))['assignment']
        self.assertEqual(grant['authorization_state'],'authorized')
        check=dict(reference=grant['authorization_reference'],agent_id='reader_agent',tool_id='smtp_send_email',
            workflow_id='workflow_one',workflow_version=1,auth=self.admin)
        self.ok(self.service.revalidate_assignment(**check))
        self.ok(self.service.update_approval_evidence({},self.admin))
        self.error(self.service.revalidate_assignment(**check),'APPROVAL_REQUIRED')

    def test_discovery_envelopes_and_safe_denials(self):
        self.ready()
        request=dict(request_id='req_discovery',operation='list_tools',payload={})
        listed=self.ok(self.service.handle(request,self.admin))
        Draft202012Validator(schema('api')['properties']['collection_response']).validate(
            {k:listed[k] for k in ('items','has_more','next_cursor','total')})
        self.assertNotIn('cred_google_sheets',json.dumps(listed))
        self.assertNotIn('credential_reference',listed['items'][0])
        limited=auth(roles=['viewer'],permissions=['tools.read'],scopes=[])
        self.assertEqual(self.ok(self.service.list_tools(limited))['items'],[])
        self.assertIn('read_spreadsheet',[v['capability'] for v in self.ok(self.service.list_capabilities(self.admin))['items']])
        self.error(self.service.handle({**request,'operation':'execute_workflow'},self.admin),'INVALID_OPERATION')
        self.error(self.service.register_agent(agent(),limited),'OPERATION_NOT_AUTHORIZED')
        self.error(self.service.list_tools(None),'VALIDATION_FAILED')
        self.error(self.service.list_tools(self.admin,request_id='api_key=raw-secret'),'SENSITIVE_DATA_DETECTED')
        decisions=self.ok(self.service.decision_records(self.admin))['items']
        self.assertTrue(all('policy_inputs' in record and 'contract_versions' in record for record in decisions))
        self.assertNotIn('raw-secret',json.dumps(decisions))

    def test_invalid_schema_references_are_not_resolved_over_network(self):
        tool=sheets();tool['input_schema']={'$ref':'https://untrusted.example/schema'}
        self.error(self.service.register_tool(tool,self.admin),'UNSUPPORTED_SCHEMA')
        tool=sheets();tool['input_schema']={'type':'imaginary'}
        self.error(self.service.register_tool(tool,self.admin),'INVALID_SCHEMA')


    def test_policy_limits_disabled_and_configuration_states(self):
        self.ready()
        for field, value, reason in (
            ('availability', 'needs_configuration', 'TOOL_UNAVAILABLE'),
            ('availability', 'unavailable', 'TOOL_UNAVAILABLE'),
            ('availability', 'quota_exceeded', 'TOOL_UNAVAILABLE'),
            ('estimated_cost', {'currency':'USD', 'per_call':5}, 'TOOL_LIMIT_EXCEEDED'),
            ('timeout_seconds', 500, 'TOOL_LIMIT_EXCEEDED'),
            ('retry_policy', {'max_retries':10,'retryable_errors':[]}, 'TOOL_LIMIT_EXCEEDED')):
            tool=sheets();tool[field]=value
            self.ok(self.service.register_tool(tool,self.admin,'cred_google_sheets'))
            denied=self.assign();self.error(denied,'NO_ELIGIBLE_TOOL')
            self.assertEqual(denied['data']['error']['details']['excluded_candidates'][0]['reason_code'],reason)
        self.ok(self.service.register_tool(sheets(),self.admin,'cred_google_sheets'))
        self.policy.version=2;self.policy.approved_providers.remove('google_sheets')
        self.ok(self.service.update_policy(self.policy,self.admin))
        self.error(self.assign(),'NO_ELIGIBLE_TOOL')
        self.error(self.service.register_tool(sheets(),self.admin,'cred_google_sheets'),'PROVIDER_NOT_AUTHORIZED')

    def test_subject_revocation_revalidates_existing_grant(self):
        self.ready();grant=self.ok(self.assign())['assignment']
        params=dict(reference=grant['authorization_reference'],agent_id='reader_agent',tool_id='google_sheets_read_rows',
            workflow_id='workflow_one',workflow_version=1,auth=auth(scopes=[]))
        self.error(self.service.revalidate_assignment(**params),'MISSING_SCOPE')
        denied=auth();denied['decision']='deny'
        self.error(self.assign(auth=denied),'WORKSPACE_NOT_AUTHORIZED')
        anonymous=auth();anonymous['subject']['subject_id']=''
        self.error(self.assign(auth=anonymous),'AUTHENTICATION_REQUIRED')

    def test_cross_agent_isolation_and_agent_revision_invalidation(self):
        self.ready()
        self.ok(self.service.register_agent(agent(agent_id='second_reader'),self.admin))
        first=self.ok(self.assign())['assignment']
        second=self.ok(self.assign(agent_id='second_reader'))['assignment']
        self.assertNotEqual(first['authorization_reference'],second['authorization_reference'])
        self.error(self.service.revalidate_assignment(first['authorization_reference'],'second_reader',
            'google_sheets_read_rows','workflow_one',1,self.admin),'UNASSIGNED_TOOL')
        revised=agent();revised['instructions']='Revised bounded agent'
        self.ok(self.service.register_agent(revised,self.admin))
        self.error(self.service.revalidate_assignment(first['authorization_reference'],'reader_agent',
            'google_sheets_read_rows','workflow_one',1,self.admin),'STALE_ASSIGNMENT')

    def test_malformed_requests_do_not_escape_safe_errors(self):
        self.ready()
        self.error(self.assign(agent_id=[]),'INVALID_REQUEST')
        self.error(self.assign(destination=[]),'INVALID_REQUEST')
        self.error(self.assign(input_schema=None),'INVALID_SCHEMA')
        self.error(self.assign(workflow_version=True),'INVALID_WORKFLOW_REFERENCE')
        self.error(self.service.consume_planner({'status':200,'data':[]},self.admin),'INVALID_PLANNER_HANDOFF')
        self.error(self.service.handle([],self.admin),'INVALID_REQUEST')
        tool=sheets();tool['permission_scopes']=['admin.*']
        self.error(self.service.register_tool(tool,self.admin),'TOOL_NOT_AUTHORIZED')
        self.error(self.service.update_approval_evidence({'not-a-binding':{}},self.admin),'INVALID_APPROVAL_EVIDENCE')

    def test_unapproved_unknown_tool_refs_remain_unresolved(self):
        planner_auth={'subject_id':'operator','workspace_id':'workspace-1','roles':['builder'],'permissions':['workflow.plan']}
        response=PlannerService(provider=RuleBasedStructuredOutputProvider()).plan(dict(request_id='planner_unknown',
            operation='plan_workflow',idempotency_key='planner-unknown-123',
            payload={'objective':'send an email', 'auth_context':planner_auth}))
        adapted=self.ok(self.service.consume_planner(response,self.admin))['requirements']
        self.assertEqual(adapted['tool_requirements'],[])
        self.assertTrue(adapted['unresolved_requirements'])
        self.assertEqual(adapted['agents'][0]['allowed_tool_ids'],[])


    def test_downstream_consumer_examples_match_shared_envelopes(self):
        examples=fixture('docs/contributors/examples/aravind-registry.json')
        for response in examples.values():
            Draft202012Validator(schema('api')['properties']['response_envelope']).validate(response)
            self.assertEqual(response['data']['contract_versions']['tool'],'tool-contract-v1')
            self.assertTrue(response['data']['correlation_id'])
        ui=examples['harihar_discovery']['data']
        self.assertTrue(ui['items'][0]['credential_configured'])
        self.assertNotIn('credential_reference',ui['items'][0])
        grant=examples['rethika_assignment']['data']['assignment']
        self.assertEqual(grant['authorization_state'],'authorized')
        self.assertEqual(grant['assigned_tool_ids'],['google_sheets_read_rows'])
        self.assertTrue(grant['authorization_reference'])
        self.assertEqual(grant['agent_version'],1)
        self.assertEqual(grant['workflow_version'],1)
        Draft202012Validator(schema('error')).validate(examples['denied_assignment']['data']['error'])


if __name__=='__main__':
    unittest.main()
