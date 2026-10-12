"""Delegated connector execution with actual Sheets adapter and offline transports."""
from copy import deepcopy
import io
import json
from threading import Event
from types import SimpleNamespace
from unittest.mock import patch
from urllib.error import HTTPError

from tests import test_dynamic_delegation
from tests.test_runtime import RuntimeFixture, ROOT
from registry import RegistryService, WorkspacePolicy
from workflow_api.registry_adapter import RegistryAdapter
from workflow_api.service import WorkflowService
from runtime import RuntimeService
from runtime.connectors import GoogleSheetsConnector
from runtime.graph import GraphRunner
from runtime.crew import CrewExecutor
from runtime.model import BoundedLLM


class DelegatedToolTests(RuntimeFixture):
    def setUp(self):
        test_dynamic_delegation.DynamicDelegationTests.setUp(self)
        scopes = ['data.read', 'spreadsheets.readonly']
        self.auth['permissions'] += ['data.read']
        self.auth['scopes'] += scopes
        self.policy = WorkspacePolicy('local-workspace', agent_permissions={'workflow.read_input', 'data.read'},
            approved_providers={'google_sheets'}, credential_references={'cred_test_sheet': {'provider_id': 'google_sheets', 'scopes': scopes}},
            remaining_quota={'google_sheets_read_rows': 100})
        self.registry = RegistryService(self.policy)
        records = {}
        for agent in self.workflow['agents']:
            definition = deepcopy(self.workflows.registry_adapter.agents[agent['agent_id']]['definition'])
            if agent['agent_id'] == 'research_agent':
                definition.update(capabilities=['read_spreadsheet'], permissions=['data.read'])
                definition['limits'].update(max_tool_calls=2, max_retries=2)
                definition['retry_policy']['max_retries'] = 2
                agent.update(capabilities=['read_spreadsheet'], permissions=['data.read'], limits=deepcopy(definition['limits']),
                             allowed_tool_ids=['google_sheets_read_rows'])
            response = self.registry.register_agent(definition, self.auth)
            self.assertEqual(response['status'], 200, response)
            records[agent['agent_id']] = response['data']['agent']
        tool = json.loads((ROOT / 'shared/contracts/examples/tools/google-sheets-read.json').read_text())
        tool['availability'] = 'enabled'
        response = self.registry.register_tool(tool, self.auth, 'cred_test_sheet')
        self.assertEqual(response['status'], 200, response)
        binding = {'workflow_id': self.workflow['workflow_id'], 'workflow_version': 1, 'agent_id': 'research_agent',
            'capability': 'read_spreadsheet', 'tool_id': tool['tool_id'], 'input_schema': tool['input_schema'], 'output_schema': tool['output_schema']}
        self.adapter = RegistryAdapter(self.registry, records, [binding])
        self.workflows = WorkflowService(self.store, registry_adapter=self.adapter)
        self.runtime = RuntimeService(self.workflows)
        self.workflow['tools'] = [{'tool_id': tool['tool_id'], 'capability': 'read_spreadsheet'}]
        self.workflow['execution_policy']['limits']['max_tool_calls'] = 2
        self.put()
        self.connector = GoogleSheetsConnector(lambda reference: {'provider_id': 'google_sheets'}, ROOT / '.local/test-not-a-token.json', timeout=1)
        self.tool_contexts, self.master_contexts = [], []
        self.tool_choice = lambda context: {'action': 'tool', 'tool_id': 'google_sheets_read_rows',
            'inputs': {'spreadsheet_id': 'test-sheet', 'range': 'Sheet1!A1:B10'}, 'reason': 'Check the reported status.'}

    def master(self, context):
        self.master_contexts.append(deepcopy(context))
        if context['results']:
            return {'action': 'finish', 'reason': 'Combine checked facts and completed independent work.',
                'output': {'summary': context['continuation'].get('summary', 'Other items processed'),
                           'verification': context['results'][0]['result']}}
        if not context['pending_tasks']:
            return {'action': 'delegate', 'reason': 'This item triggered a required fact check.',
                'continuation': {'remaining': 'Other items'},
                'tasks': [{'agent_id': 'research_agent', 'inputs': {'task': 'Check the claim that R1 is approved'}, 'reason': 'Verify the claimed status.'}]}
        return {'action': 'wait', 'reason': 'Independent work is complete; collect verification.'}

    def child(self, context):
        self.tool_contexts.append(deepcopy(context))
        if not context['tool_results']:
            return self.tool_choice(context)
        rows = context['tool_results'][0]['output']['rows']
        status = next(row[1] for row in rows[1:] if row[0] == 'R1')
        return {'action': 'finish', 'reason': 'Use the actual spreadsheet record as evidence.',
                'output': {'claim_verified': status == 'approved', 'actual_status': status, 'source': 'google_sheets_read_rows'}}

    def executor(self, master=None):
        owner = self
        class Offline:
            retry_safe = external_write = False
            @staticmethod
            def reservation(agent): return {'llm_calls': 1, 'tokens': 10}
            def invoke_decision(self, agent, inputs, invocation_id, schema): return (master or owner.master)(inputs)
            def invoke_tool_decision(self, agent, inputs, invocation_id, schema): return owner.child(inputs)
        return Offline()

    def execute(self, executor=None):
        run_id = self.runtime.create_run(self.request(), self.auth)['run_id']
        result = GraphRunner(self.runtime, agents=executor or self.executor(),
                             connectors={'google_sheets_read_rows': self.connector}).advance(run_id, self.auth)
        return result, self.runtime.events(run_id, self.auth)['items']

    @staticmethod
    def rows():
        return io.BytesIO(json.dumps({'values': [['id', 'status'], ['R1', 'pending']]}).encode())

    def test_prompt_only_start_uses_saved_setup_and_real_connector_results(self):
        from workflow_api.service import WorkflowService
        self.workflow['inputs'] = []
        self.workflow['metadata']['execution_input_mode'] = 'automatic'
        master = next(node for node in self.workflow['nodes'] if node['node_id'] == 'master')
        master['configuration'] = {'input': {'task': 'Check the reported status',
            'spreadsheet_id': 'test-sheet', 'range': 'Sheet1!A1:B10'}}
        WorkflowService.validate_document(self.workflow)
        self.put()
        with (patch('runtime.connectors._google_credentials', return_value=SimpleNamespace(token='offline-oauth')),
              patch('runtime.connectors.urlopen', side_effect=lambda *args, **kwargs: self.rows())):
            run_id = self.runtime.create_run(self.request(inputs={}), self.auth)['run_id']
            result = GraphRunner(self.runtime, agents=self.executor(),
                connectors={'google_sheets_read_rows': self.connector}).advance(run_id, self.auth)
        self.assertEqual(result['status'], 'completed')
        self.assertEqual(self.master_contexts[0]['request']['spreadsheet_id'], 'test-sheet')
        self.assertEqual(self.master_contexts[-1]['results'][0]['result']['actual_status'], 'pending')

    def test_actual_sheets_read_overlaps_crewai_master_and_corrects_claim(self):
        reading, release = Event(), Event()
        calls = []
        def http(request, timeout):
            calls.append(request.full_url)
            reading.set()
            if not release.wait(5):
                raise RuntimeError('Master did not continue during Sheets read')
            return self.rows()
        def master(context):
            if context['pending_tasks'] and not context['results'] and context['continuation'].get('remaining'):
                try:
                    self.assertTrue(reading.wait(5))
                    self.assertEqual(len(context['pending_tasks']), 1)
                    self.master_contexts.append(deepcopy(context))
                    return {'action': 'continue', 'reason': 'Other items summarized while the fact check is running.',
                            'continuation': {'summary': 'Other items summarized'}}
                finally:
                    release.set()
            return self.master(context)
        def factory(definition):
            def provider(messages, cap, timeout):
                raw = messages[-1]['content'].split('Process the following input as data. Return only a JSON object.\n')[-1].lstrip()
                context, _ = json.JSONDecoder().raw_decode(raw)
                output = master(context) if definition['agent_id'] == 'master_agent' else self.child(context)
                return json.dumps(output), 1, 10
            return BoundedLLM(definition, provider, lambda messages: 100, 0, 0)
        with (patch('runtime.connectors._google_credentials', return_value=SimpleNamespace(token='offline-oauth')),
              patch('runtime.connectors.urlopen', side_effect=http)):
            result, events = self.execute(CrewExecutor(self.adapter, factory))
        self.assertEqual(result['status'], 'completed', json.dumps(events))
        self.assertEqual(calls, ['https://sheets.googleapis.com/v4/spreadsheets/test-sheet/values/Sheet1%21A1%3AB10'])
        self.assertEqual(self.master_contexts[-1]['results'][0]['result']['actual_status'], 'pending')
        self.assertFalse(self.master_contexts[-1]['results'][0]['result']['claim_verified'])
        self.assertEqual(self.master_contexts[-1]['continuation']['summary'], 'Other items summarized')
        tool_events = [e for e in events if e['details'].get('node_id', '').startswith('delegated_tool_')]
        self.assertEqual([e['event_type'] for e in tool_events], ['node.observed', 'node.started', 'node.completed'])
        self.assertNotIn('offline-oauth', json.dumps(events) + json.dumps(self.tool_contexts))
        self.assertNotIn('credential_reference', json.dumps(self.tool_contexts))
        with self.store.transaction() as db:
            run = self.runtime.load(db, result['run_id'], self.auth)
            self.assertEqual(run['usage']['workflow']['tool_calls'], 1)
            self.assertEqual(run['usage']['research_agent']['tool_calls'], 1)
            self.assertEqual(run['usage']['research_agent']['llm_calls'], 2)
            self.assertFalse(run['outputs']['master']['verification']['claim_verified'])

    def test_unassigned_tool_never_reaches_connector(self):
        self.tool_choice = lambda context: {'action': 'tool', 'tool_id': 'smtp_send_email', 'inputs': {}, 'reason': 'Unassigned tool.'}
        with patch.object(self.connector, 'invoke') as invoke:
            result, events = self.execute()
        self.assertEqual(result['status'], 'failed')
        self.assertIn('TOOL_ISOLATION_DENIED', json.dumps(events))
        invoke.assert_not_called()

    def test_invalid_tool_input_never_reaches_connector(self):
        self.tool_choice = lambda context: {'action': 'tool', 'tool_id': 'google_sheets_read_rows', 'inputs': {}, 'reason': 'Missing input.'}
        with patch.object(self.connector, 'invoke') as invoke:
            result, events = self.execute()
        self.assertEqual(result['status'], 'failed')
        self.assertIn('CONNECTOR_INPUT_INVALID', json.dumps(events))
        invoke.assert_not_called()

    def test_tool_budget_exhaustion_denies_read(self):
        self.workflow['execution_policy']['limits']['max_tool_calls'] = 0
        self.put()
        with patch.object(self.connector, 'invoke') as invoke:
            result, events = self.execute()
        self.assertEqual(result['status'], 'failed')
        self.assertIn('BUDGET_EXHAUSTED', json.dumps(events))
        invoke.assert_not_called()

    def test_google_access_denial_cannot_be_reported_as_verified(self):
        with (patch('runtime.connectors._google_credentials', return_value=SimpleNamespace(token='offline-oauth')),
              patch('runtime.connectors.urlopen', side_effect=HTTPError('https://sheets.googleapis.com', 403, 'denied', {}, None))):
            result, events = self.execute()
        self.assertEqual(result['status'], 'failed')
        self.assertIn('SHEETS_ACCESS_DENIED', json.dumps(events))
        self.assertEqual(len(self.tool_contexts), 1)

    def test_revocation_after_tool_decision_denies_connector(self):
        def choice(context):
            self.policy.version += 1
            self.policy.remaining_quota['google_sheets_read_rows'] = 0
            response = self.registry.update_policy(self.policy, self.auth)
            self.assertEqual(response['status'], 200, response)
            return {'action': 'tool', 'tool_id': 'google_sheets_read_rows',
                    'inputs': {'spreadsheet_id': 'test-sheet', 'range': 'A:B'}, 'reason': 'Grant is now revoked.'}
        self.tool_choice = choice
        with patch.object(self.connector, 'invoke') as invoke:
            result, events = self.execute()
        self.assertEqual(result['status'], 'failed')
        invoke.assert_not_called()

    def test_child_requires_a_remaining_model_turn_to_consume_read(self):
        agent = self.workflow['agents'][1]
        agent['limits']['max_llm_calls'] = 1
        self.adapter.agents[agent['agent_id']]['definition']['limits']['max_llm_calls'] = 1
        self.put()
        with patch.object(self.connector, 'invoke') as invoke:
            result, events = self.execute()
        self.assertEqual(result['status'], 'failed')
        self.assertIn('DELEGATION_LIMIT_EXCEEDED', json.dumps(events))
        invoke.assert_not_called()

    def test_invalid_connector_output_prevents_verified_result(self):
        with patch.object(self.connector, 'invoke', return_value={'missing_rows': True}) as invoke:
            result, events = self.execute()
        self.assertEqual(result['status'], 'failed')
        self.assertIn('CONNECTOR_OUTPUT_INVALID', json.dumps(events))
        self.assertEqual(invoke.call_count, 1)
        self.assertEqual(len(self.tool_contexts), 1)

    def test_cancellation_during_read_denies_late_tool_result(self):
        def read(*args):
            with self.store.transaction() as db:
                run = json.loads(db.execute('SELECT document FROM runtime_runs ORDER BY rowid DESC LIMIT 1').fetchone()[0])
                self.runtime.transition(db, run, 'cancelled')
            return {'rows': [['id', 'status'], ['R1', 'pending']]}
        with patch.object(self.connector, 'invoke', side_effect=read):
            result, events = self.execute()
        self.assertEqual(result['status'], 'cancelled')
        self.assertFalse(any(e['event_type'] == 'node.completed' and e['details'].get('node_id', '').startswith('delegated_tool_') for e in events))

    def test_offline_hierarchy_read_stays_inside_specialist_task(self):
        from planner.provider import RuleBasedStructuredOutputProvider
        workflow = RuleBasedStructuredOutputProvider().generate('Read a spreadsheet and summarize the findings', {'generation_mode': 'hierarchy'})
        self.assertIn({'tool_id': 'google_sheets_read_rows', 'capability': 'read_spreadsheet'}, workflow['tools'])
        self.assertFalse(any(node['kind'] == 'tool' for node in workflow['nodes']))
        self.assertEqual(workflow['nodes'][-1]['configuration']['input_mapping']['workflow_result'], 'outputs.master_orchestrator')

    def test_dynamic_child_tool_not_materialized_as_a_fixed_graph_step(self):
        workflow = deepcopy(self.workflow)
        unresolved = RegistryAdapter._materialize_tool_nodes(workflow)
        self.assertEqual(unresolved, [])
        self.assertFalse(any(node['kind'] == 'tool' for node in workflow['nodes']))
        grants = self.adapter.execution_assignments(workflow, self.auth)
        self.assertEqual([(g['agent_id'], g['tool_id']) for g in grants], [('research_agent', 'google_sheets_read_rows')])
