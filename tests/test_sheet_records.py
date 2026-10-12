"""Restricted record writes and published domain workflows; offline providers only."""
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from io import BytesIO
import json
from pathlib import Path
import re
import tempfile
import time
from types import SimpleNamespace
import unittest
from unittest.mock import patch
from urllib.error import HTTPError
from urllib.parse import unquote, urlparse

from runtime.service import RuntimeFailure
from runtime.sheet_records import GoogleSheetsRecordConnector, write_targets, validate_record_workflow, table_range, column_number
from runtime.model import BoundedLLM
from workflow_api.live_providers import create_configured_app, registry_configuration
from workflow_api.slack_gmail import mapped_draft

ROOT = Path(__file__).resolve().parents[1]
TOOL = json.loads((ROOT / 'shared/contracts/examples/tools/google-sheets-upsert-record.json').read_text())


class SheetsHTTP:
    def __init__(self, tables):
        self.tables, self.requests = deepcopy(tables), []

    def __call__(self, request, timeout):
        self.requests.append(request)
        path = unquote(urlparse(request.full_url).path)
        if request.get_method() == 'GET':
            value = path.split('/values/', 1)[1]
            tab, left, top, right, bottom = table_range(value)
            name = tab[1:-1].replace("''", "'")
            rows = [r[left - 1:right] for r in self.tables[name][top - 1:bottom]]
            return BytesIO(json.dumps({'values': rows}).encode())
        self.assert_batch(path)
        body = json.loads(request.data)
        assert body['valueInputOption'] == 'RAW'
        for item in body['data']:
            tab, col, row = re.fullmatch(r"'((?:[^']|'')+)'!([A-Z]+)([1-9][0-9]*)", item['range']).groups()
            table, index, column = self.tables[tab.replace("''", "'")], int(row) - 1, column_number(col) - 1
            while len(table) <= index:
                table.append([])
            while len(table[index]) <= column:
                table[index].append('')
            table[index][column] = item['values'][0][0]
        return BytesIO(json.dumps({'totalUpdatedCells': len(body['data'])}).encode())

    @staticmethod
    def assert_batch(path):
        assert path.endswith('/values:batchUpdate')


class RecordConnectorTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.target = dict(spreadsheet_id='test-sheet', range='Records!A1:D20', identity_column='id',
                           writable_columns=['draft', 'status'], allow_create=True)
        self.connector = GoogleSheetsRecordConnector(lambda _: {'provider_id': 'google_sheets'}, 'unused',
            [self.target], timeout=1, require_approval=False, lock_directory=self.temp.name)
        self.grant = {**TOOL, 'authorization_state': 'authorized', 'authorization_reference': 'offline-grant',
                      'credential_reference': 'offline-credential', 'approval_required': False, 'destination': 'configured_spreadsheet'}
        self.http = SheetsHTTP({'Records': [['id', 'draft', 'status', 'staff_notes'], ['R2', '', 'New', '=existing_formula'], ['R1', '', 'New', 'keep']]})
        credentials = patch('runtime.connectors._google_credentials', return_value=SimpleNamespace(token='offline-only', scopes=['https://www.googleapis.com/auth/spreadsheets']))
        credentials.start(); self.addCleanup(credentials.stop)
        network = patch('runtime.connectors.urlopen', side_effect=self.http)
        network.start(); self.addCleanup(network.stop)

    def save(self, identity='R1', fields=None, **changes):
        inputs = {k: self.target[k] for k in ('spreadsheet_id', 'range', 'identity_column')}
        inputs.update(identity=identity, fields=fields or {'draft': 'Verified draft', 'status': 'Draft ready'}, **changes)
        return self.connector.invoke(self.grant, inputs, 'offline-effect')

    def test_sorted_rows_sparse_literal_updates_and_identical_replay(self):
        first = self.save(fields={'draft': '=literal draft', 'status': 'Draft ready'})
        self.assertEqual(first, dict(identity='R1', row_index=3, created=False, updated_cells=2))
        self.assertEqual(self.http.tables['Records'][2], ['R1', '=literal draft', 'Draft ready', 'keep'])
        self.assertEqual(self.http.tables['Records'][1][3], '=existing_formula')
        second = self.save(fields={'draft': '=literal draft', 'status': 'Draft ready'})
        self.assertEqual(second['updated_cells'], 0)
        self.assertEqual(len([r for r in self.http.requests if r.get_method() == 'POST']), 1)

    def test_concurrent_creations_do_not_overwrite_and_survive_new_connector(self):
        other = GoogleSheetsRecordConnector(self.connector.resolve, 'unused', [self.target], timeout=1,
            require_approval=False, lock_directory=self.temp.name)
        def save(identity):
            connector = self.connector if identity == 'R3' else other
            return connector.invoke(self.grant, {k: self.target[k] for k in ('spreadsheet_id', 'range', 'identity_column')} |
                {'identity': identity, 'fields': {'draft': identity}}, identity)
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(save, ['R3', 'R4']))
        self.assertEqual({r['row_index'] for r in results}, {4, 5})
        self.assertEqual(self.save('R3', {'draft': 'R3'})['updated_cells'], 0)
        self.assertEqual({r[0] for r in self.http.tables['Records'][1:]}, {'R1', 'R2', 'R3', 'R4'})

    def test_forbidden_tables_columns_and_identity_changes_never_reach_google(self):
        for changes in ({'range': 'Other!A1:D20'}, {'spreadsheet_id': 'other-sheet'}, {'fields': {'staff_notes': 'overwrite'}}, {'fields': {'id': 'R2'}}):
            with self.subTest(changes=changes), self.assertRaises(RuntimeFailure) as failed:
                self.save(**changes)
            self.assertEqual(failed.exception.code, 'SHEETS_TARGET_DENIED')
        self.assertFalse(self.http.requests)

    def test_approval_and_exact_binding_required(self):
        for changes in ({'approval_required': True}, {'authorization_state': 'pending_approval'}, {'tool_id': 'other'}):
            with patch.dict(self.grant, changes), self.assertRaises(RuntimeFailure) as failed:
                self.save()
            self.assertEqual(failed.exception.code, 'SHEETS_NOT_AUTHORIZED')
        self.assertFalse(self.http.requests)

    def test_read_only_google_consent_is_rejected_before_provider_requests(self):
        with patch('runtime.connectors._google_credentials', return_value=SimpleNamespace(token='offline-only', scopes=['https://www.googleapis.com/auth/spreadsheets.readonly'])):
            with self.assertRaises(RuntimeFailure) as failed:
                self.save()
        self.assertEqual(failed.exception.code, 'GOOGLE_WRITE_CONSENT_REQUIRED')
        self.assertFalse(self.http.requests)

    def test_duplicate_ids_and_headers_block_without_write(self):
        for table in ([['id', 'draft', 'status', 'staff_notes'], ['R1'], ['R1']], [['id', 'draft', 'draft', 'status']]):
            self.http.tables['Records'] = table
            with self.assertRaises(RuntimeFailure):
                self.save()
        self.assertFalse(any(r.get_method() == 'POST' for r in self.http.requests))

    def test_missing_record_creation_policy_capacity_and_partial_row_preservation(self):
        self.connector.targets[0]['allow_create'] = False
        with self.assertRaises(RuntimeFailure) as failed:
            self.save('new')
        self.assertEqual(failed.exception.code, 'SHEETS_RECORD_NOT_FOUND')
        self.connector.targets[0]['allow_create'] = True
        self.http.tables['Records'] += [['', '', '', 'pending staff entry'], []]
        self.assertEqual(self.save('new')['row_index'], 5)
        self.assertEqual(self.http.tables['Records'][3][3], 'pending staff entry')
        self.http.tables['Records'] = [self.http.tables['Records'][0]] + [[f'R{i}'] for i in range(19)]
        with self.assertRaises(RuntimeFailure) as failed:
            self.save('overflow')
        self.assertEqual(failed.exception.code, 'SHEETS_TABLE_FULL')

    def test_provider_denial_and_uncertain_write_are_not_retried(self):
        for error in (HTTPError('https://sheets.googleapis.com', 403, 'Denied', {}, None), TimeoutError()):
            with patch('runtime.connectors.urlopen', side_effect=[self.http_result(), error]) as network, self.assertRaises(RuntimeFailure):
                self.save()
            self.assertEqual(network.call_count, 2)

    def http_result(self):
        return BytesIO(json.dumps({'values': self.http.tables['Records']}).encode())

    def test_invalid_operator_targets(self):
        for change in ({'range': 'A:Z'}, {'range': []}, {'spreadsheet_id': None}, {'writable_columns': ['id']}, {'allow_create': 'yes'}):
            with self.assertRaises(ValueError):
                write_targets([self.target | change])
        with self.assertRaises(ValueError):
            write_targets([self.target, self.target | {'range': 'Records!B1:F30'}])

    def test_busy_table_lock_is_bounded(self):
        other = GoogleSheetsRecordConnector(self.connector.resolve, 'unused', [self.target], timeout=1,
            require_approval=False, lock_directory=self.temp.name)
        with self.connector.locked('test-sheet', time.monotonic() + 1):
            with self.assertRaises(RuntimeFailure) as failed:
                with other.locked('test-sheet', time.monotonic() + .03):
                    self.fail('Busy lock was acquired')
        self.assertEqual(failed.exception.code, 'SHEETS_LOCK_TIMEOUT')
        self.assertFalse(self.http.requests)

    def test_non_scalar_and_nonfinite_fields_are_rejected(self):
        for fields in ({'draft': {'nested': 'data'}}, {'draft': float('inf')}):
            with self.assertRaises(RuntimeFailure):
                self.save(fields=fields)
        self.assertFalse(self.http.requests)

    def test_explicit_offset_table_resolves_correct_cell(self):
        self.connector.targets = write_targets([self.target | {'range': 'Records!C4:F20'}])
        self.http.tables['Records'] = [[], [], [], ['', '', 'id', 'draft', 'status', 'staff_notes'], ['', '', 'R1', '', 'New', 'keep']]
        result = self.save(range='Records!C4:F20')
        self.assertEqual(result['row_index'], 5)
        self.assertEqual(self.http.tables['Records'][4], ['', '', 'R1', 'Verified draft', 'Draft ready', 'keep'])

    def test_workflow_binding_isolated_between_spreadsheets(self):
        base = GoogleSheetsRecordConnector(self.connector.resolve, 'unused', timeout=1, require_approval=False,
            lock_directory=self.temp.name)
        def workflow(sheet):
            return {'metadata': {'sheet_write_targets': [self.target | {'spreadsheet_id': sheet}]}, 'nodes': [],
                    'tools': [{'tool_id': 'google_sheets_upsert_record'}]}
        first, second = base.bind_workflow(workflow('test-sheet')), base.bind_workflow(workflow('other-sheet'))
        self.assertEqual(first.targets[0]['spreadsheet_id'], 'test-sheet')
        self.assertEqual(second.targets[0]['spreadsheet_id'], 'other-sheet')
        inputs = {k: self.target[k] for k in ('spreadsheet_id', 'range', 'identity_column')} | {'identity': 'R1', 'fields': {'draft': 'text'}}
        for adapter in (base, second):
            with self.assertRaises(RuntimeFailure) as failed:
                adapter.invoke(self.grant, inputs, 'attempted-redirect')
            self.assertEqual(failed.exception.code, 'SHEETS_TARGET_DENIED')
        self.assertFalse(self.http.requests)

    def test_operator_ceiling_cannot_be_broadened_by_workflow_metadata(self):
        for change in ({'spreadsheet_id': 'other-sheet'}, {'writable_columns': ['staff_notes']}, {'range': 'Records!A1:D30'}):
            workflow = {'metadata': {'sheet_write_targets': [self.target | change]}, 'nodes': [],
                        'tools': [{'tool_id': 'google_sheets_upsert_record'}]}
            with self.assertRaises(RuntimeFailure) as failed:
                self.connector.bind_workflow(workflow)
            self.assertEqual(failed.exception.code, 'SHEETS_TARGET_DENIED')
        self.assertFalse(self.http.requests)


def authored_workflow(domain, spreadsheet_id='test-sheet'):
    """Offline planner response fixture, not domain code in the runtime."""
    source, evidence, identity, related, checker = domain
    workflow = mapped_draft(dict(team_id='T123', conversation_id='D123', sender_id='', recipient='owner@example.com'))
    template = deepcopy(workflow['agents'][0])
    agents = []
    for agent_id, role, capabilities, permissions, calls in (
        ('supervisor', 'master', ['classify_text'], ['workflow.read_input'], 4),
        (checker, 'sub_agent', ['read_spreadsheet'], ['data.read'], 3),
        ('draft_specialist', 'sub_agent', ['generate_report'], ['workflow.read_input'], 1),
        ('record_saver', None, ['update_spreadsheet'], ['data.write'], 0)):
        agent = deepcopy(template)
        agent.update(agent_id=agent_id, role=agent_id, goal='Return checked structured results.',
            instructions='Use provided records as evidence. Report missing or ambiguous records without inventing facts.',
            model={'provider': 'openai', 'model_id': 'gpt-5.6-luna', 'temperature': .1},
            capabilities=capabilities, permissions=permissions, approval_requirements=[], allowed_tool_ids=[],
            input_schema={'type': 'object'}, output_schema={'type': 'object'})
        agent['limits'].update(max_llm_calls=calls, max_tool_calls=4 if agent_id == 'record_saver' else 2,
            max_tokens=16000 if calls else 1, max_retries=0, timeout_seconds=300, max_estimated_cost_usd=.15 if calls else 0)
        if role:
            agent['hierarchy_role'] = role
        if role == 'sub_agent':
            agent['parent_agent_id'] = 'supervisor'
        agents.append(agent)
    def fields_schema(names):
        return {'type': 'object', 'additionalProperties': False, 'required': names,
                'properties': {name: {'type': 'string'} for name in names}}
    agents[0]['output_schema'] = {'type': 'object', 'additionalProperties': False, 'required': ['draft_fields', 'status_fields'],
        'properties': {'draft_fields': fields_schema(['findings', 'subject', 'body', 'status']), 'status_fields': fields_schema(['status'])}}
    workflow.update(workflow_id='draft-' + source.lower(), name=source + ' checked drafts',
        inputs=[{'name': 'row', 'type': 'object', 'required': True}], outputs=[], agents=agents, conditions=[], approval_gates=[],
        tools=[{'tool_id': 'google_sheets_read_rows', 'capability': 'read_spreadsheet'},
               {'tool_id': 'google_sheets_upsert_record', 'capability': 'update_spreadsheet'}])
    workflow['nodes'] = [dict(node_id='incoming', kind='trigger', label='Incoming record'),
        dict(node_id='master', kind='agent', label='Master', agent_id='supervisor', configuration={'input_mapping': {'row': 'inputs.row'}})]
    for node_id, tab, key, output in [('save_draft', 'Followups', identity, 'draft_fields'), ('save_status', source, identity, 'status_fields')]:
        workflow['nodes'].append(dict(node_id=node_id, kind='tool', label=node_id, agent_id='record_saver', tool_id='google_sheets_upsert_record',
            configuration={'input_mapping': {'spreadsheet_id': repr(spreadsheet_id), 'range': repr(tab + '!A1:E100'),
                'identity_column': repr(key), 'identity': 'inputs.row.' + identity, 'fields': 'outputs.master.' + output}}))
    workflow['nodes'].append(dict(node_id='done', kind='output', label='Done', configuration={'input_mapping': {'result': 'outputs.master'}}))
    workflow['edges'] = [dict(edge_id=str(i), source=a, target=b) for i, (a, b) in enumerate(zip(
        ['incoming', 'master', 'save_draft', 'save_status'], ['master', 'save_draft', 'save_status', 'done']))]
    workflow['execution_policy'].update(allow_external_writes=True)
    workflow['execution_policy']['limits'].update(max_llm_calls=12, max_tool_calls=8, max_tokens=64000, max_retries=0,
        timeout_seconds=300, max_estimated_cost_usd=1)
    workflow['metadata']['dynamic_delegation'] = {'master': {'max_rounds': 4, 'max_tasks': 6}}
    workflow['metadata']['sheet_write_targets'] = [dict(spreadsheet_id=spreadsheet_id, range=tab + '!A1:E100',
        identity_column=identity, writable_columns=columns, allow_create=tab == 'Followups') for tab, columns in
        [('Followups', ['findings', 'subject', 'body', 'status']), (source, ['status'])]]
    workflow['metadata']['trigger_templates'] = [dict(provider_id='google_sheets', resource_id=spreadsheet_id, delivery='poll',
        event_type='row.created', baseline_policy='current_only', poll_interval_seconds=10,
        poll_input={'range': source + '!A1:E100', 'identity_field': identity, 'required_fields': [identity, related, 'complaint']},
        input_mapping={'row': 'row'})]
    return workflow


class PublishedDraftTests(unittest.TestCase):
    def test_read_only_sheets_with_email_and_empty_write_targets(self):
        workflow = {'nodes': [{'node_id': 'send', 'tool_id': 'smtp_send_email'}],
                    'tools': [{'tool_id': 'google_sheets_read_rows'}, {'tool_id': 'smtp_send_email'}],
                    'metadata': {'sheet_write_targets': []}}
        self.assertEqual(validate_record_workflow(workflow), [])
        workflow['tools'].append({'tool_id': 'google_sheets_upsert_record'})
        from planner.errors import PlannerFailure
        with self.assertRaises(PlannerFailure) as failed:
            validate_record_workflow(workflow)
        self.assertEqual(failed.exception.code, 'SHEETS_TARGET_REQUIRED')

    def test_restaurant_and_manufacturing_planning_publication_polling_and_restart(self):
        for domain in [('Reviews', 'Kitchen', 'review_id', 'order_id', 'kitchen_checker'),
                       ('Defects', 'Quality', 'case_id', 'batch_id', 'quality_checker')]:
            with self.subTest(domain=domain):
                self.run_domain(domain)

    def test_missing_and_ambiguous_supporting_records_require_staff_review(self):
        domain = ('Reviews', 'Kitchen', 'review_id', 'order_id', 'kitchen_checker')
        for records in ([], [['X501', 'One'], ['X501', 'Two']]):
            with self.subTest(records=records):
                self.run_domain(domain, supporting_records=records,
                    expected_finding='Missing or ambiguous record; staff review required', expected_status='Needs staff review')

    def test_partial_write_failure_does_not_resend_after_restart(self):
        self.run_domain(('Reviews', 'Kitchen', 'review_id', 'order_id', 'kitchen_checker'), fail_status=True)

    def test_default_action_approvals_pause_each_save(self):
        self.run_domain(('Reviews', 'Kitchen', 'review_id', 'order_id', 'kitchen_checker'), action_approval=True)

    def test_another_spreadsheet_requires_no_environment_destination_list(self):
        self.run_domain(('Defects', 'Quality', 'case_id', 'batch_id', 'quality_checker'), spreadsheet_id='another-factory-sheet')

    def test_optional_operator_ceiling_still_allows_legacy_workflows(self):
        self.run_domain(('Reviews', 'Kitchen', 'review_id', 'order_id', 'kitchen_checker'), legacy_targets=True)

    def test_generated_mixed_inputs_and_implicit_field_schema_are_normalized(self):
        self.run_domain(('Reviews', 'Kitchen', 'review_id', 'order_id', 'kitchen_checker'), mixed_generated=True)

    def run_domain(self, domain, supporting_records=None, expected_finding='Recorded dispatch delay', expected_status='Draft ready', fail_status=False, action_approval=False, spreadsheet_id='test-sheet', legacy_targets=False, mixed_generated=False):
        source, evidence, identity, related, checker = domain
        with tempfile.TemporaryDirectory(dir=ROOT / '.local') as directory:
            path = Path(directory)
            (path / 'token.json').write_text('{}')
            targets = [dict(spreadsheet_id=spreadsheet_id, range='Followups!A1:E100', identity_column=identity,
                writable_columns=['findings', 'subject', 'body', 'status'], allow_create=True),
                dict(spreadsheet_id=spreadsheet_id, range=source + '!A1:E100', identity_column=identity,
                writable_columns=['status'], allow_create=False)]
            env = dict(OPENAI_API_KEY='offline-only', OPENAI_MODEL='gpt-5.6-luna', GMAIL_SMTP_USER='owner@example.com',
                GMAIL_SMTP_PASSWORD='offline-only', GOOGLE_TOKEN_FILE=str(path / 'token.json'), BUILDER_EMAIL_RECIPIENTS='owner@example.com',
                BUILDER_SHEETS_DIRECT_WRITE='0' if action_approval else '1')
            if legacy_targets:
                env['BUILDER_SHEETS_WRITE_TARGETS'] = json.dumps(targets)
            http = SheetsHTTP({source: [[identity, related, 'complaint', 'status', 'staff_notes'], ['old', 'old-order', 'Old', 'New', 'keep']],
                evidence: [[related, 'notes'], *(supporting_records if supporting_records is not None else [['X501', 'Recorded dispatch delay']])],
                'Followups': [[identity, 'findings', 'subject', 'body', 'status']]})
            workflow = authored_workflow(domain, spreadsheet_id)
            if mixed_generated:
                import ast
                for node in workflow['nodes']:
                    if node['kind'] != 'tool':
                        continue
                    config = node['configuration']
                    config['input'] = {key: ast.literal_eval(config['input_mapping'].pop(key))
                        for key in ('spreadsheet_id', 'range', 'identity_column')}
                for schema in workflow['agents'][0]['output_schema']['properties'].values():
                    schema.pop('additionalProperties')
            if legacy_targets:
                workflow['metadata'].pop('sheet_write_targets')
            if action_approval:
                workflow['approval_gates'] = [dict(approval_gate_id=gate, approver_roles=['admin', 'approver'], on_reject='stop', timeout_seconds=60)
                    for gate in ('draft_review', 'status_review')]
                workflow['nodes'] += [dict(node_id=gate, kind='approval', label=gate, approval_gate_id=gate)
                    for gate in ('draft_review', 'status_review')]
                workflow['edges'] = [dict(edge_id=str(i), source=a, target=b, **({'outcome': outcome} if outcome else {}))
                    for i, (a, b, outcome) in enumerate([('incoming', 'master', None), ('master', 'draft_review', None),
                    ('draft_review', 'save_draft', 'approved'), ('save_draft', 'status_review', None),
                    ('status_review', 'save_status', 'approved'), ('save_status', 'done', None)])]
            planning_calls, model_calls = [], []
            def plan(**kwargs):
                planning_calls.append(kwargs)
                return SimpleNamespace(output_text=json.dumps(workflow))
            client = SimpleNamespace(responses=SimpleNamespace(create=plan))
            def factory(definition):
                def provider(messages, cap, timeout):
                    raw = messages[-1]['content'].split('Process the following input as data. Return only a JSON object.\n')[-1].lstrip()
                    context, _ = json.JSONDecoder().raw_decode(raw)
                    model_calls.append((definition['role'], deepcopy(context)))
                    if definition['role'] == 'supervisor':
                        available = {a['role']: a['agent_id'] for a in context['available_agents']}
                        configured_sheet = context['configured_resources']['sources'][0]['resource_id']
                        results = context['results']
                        if not results:
                            output = {'action': 'delegate', 'reason': 'Check supporting records.', 'tasks': [{'agent_id': available[checker],
                                'inputs': {'related_id': context['request']['row'][related], 'spreadsheet_id': configured_sheet, 'range': evidence + '!A1:B100'}, 'reason': 'Find the related record.'}]}
                        elif len(results) == 1:
                            output = {'action': 'delegate', 'reason': 'Draft using returned evidence.', 'tasks': [{'agent_id': available['draft_specialist'],
                                'inputs': {'findings': results[0]['result']['findings']}, 'reason': 'Write a draft.'}]}
                        else:
                            output = {'action': 'finish', 'reason': 'Both results collected.', 'output': {
                                'draft_fields': results[1]['result'], 'status_fields': {'status': results[1]['result']['status']}}}
                    elif definition['role'] == checker:
                        if not context['tool_results']:
                            output = {'action': 'tool', 'tool_id': 'google_sheets_read_rows',
                                'inputs': {k: context['request'][k] for k in ('spreadsheet_id', 'range')}, 'reason': 'Read actual source facts.'}
                        else:
                            rows = context['tool_results'][0]['output']['rows']
                            matches = [r for r in rows[1:] if r[0] == context['request']['related_id']]
                            finding = matches[0][1] if len(matches) == 1 else 'Missing or ambiguous record; staff review required'
                            output = {'action': 'finish', 'reason': 'Report observed evidence.', 'output': {'findings': finding}}
                    else:
                        output = {'findings': context['findings'], 'subject': 'Follow-up draft',
                                  'body': 'We checked your records: ' + context['findings'],
                                  'status': 'Needs staff review' if context['findings'].startswith('Missing or ambiguous') else 'Draft ready'}
                    return json.dumps(output), 1, 20
                return BoundedLLM(definition, provider, lambda messages: 100, 0, 0)
            def transport(request, timeout):
                if fail_status and request.get_method() == 'POST' and source in json.loads(request.data)['data'][0]['range']:
                    http.requests.append(request)
                    raise TimeoutError('Offline uncertain status write')
                return http(request, timeout)
            with (patch('workflow_api.live_providers.REGISTRY', path / 'registry.json'),
                  patch('runtime.connectors._google_credentials', return_value=SimpleNamespace(token='offline-only', scopes=['https://www.googleapis.com/auth/spreadsheets'])),
                  patch('runtime.connectors.urlopen', side_effect=transport)):
                app = create_configured_app(env, path / 'runs.sqlite3', client=client, model_factory=factory)
                service, auth = app.state.workflow_service, app.state.live_operator_auth
                def call(operation, payload, key):
                    response = service.handle(dict(request_id=key, idempotency_key=key, operation=operation, payload=payload), auth)
                    self.assertEqual(response['status'], 200, response)
                    return response['data']
                planned = call('plan_workflow', {'objective': 'Monitor ' + source + ', check ' + evidence + ' and save drafts only.',
                    'context': {'generation_mode': 'hierarchy', 'execution_input_mode': 'automatic'}}, 'plan-domain')['workflow']
                ref = {'workflow_id': planned['workflow_id'], 'workflow_version': planned['version']}
                call('save_workflow_version', {**ref, 'base_version': 0, 'workflow': planned}, 'save-domain')
                call('validate_workflow', ref, 'validate-domain')
                call('approve_workflow', {**ref, 'action': 'approve'}, 'review-domain')
                call('approve_workflow', {**ref, 'action': 'publish'}, 'publish-domain')
                service.lifecycle.activate(dict(request_id='activate', idempotency_key='activate-domain', payload={**ref, 'triggers': []}), auth)
                scheduler = app.state.live_workers[0]
                baseline = scheduler.tick()
                with service.store.transaction() as db:
                    bindings = [json.loads(r[0]) for r in db.execute('SELECT document FROM lifecycle_triggers')]
                self.assertEqual(baseline['polled'], 1, bindings)
                self.assertFalse(model_calls)
                http.tables[source].append(['new-case', 'X501', 'Customer complaint', 'New', 'keep'])
                scheduler.last_polled.clear()
                self.assertEqual(scheduler.tick()['dispatched'], 1)
                with service.store.transaction() as db:
                    run = json.loads(db.execute('SELECT document FROM runtime_runs').fetchone()[0])
                if action_approval:
                    self.assertEqual(run['status'], 'paused_for_approval')
                    self.assertFalse(any(r.get_method() == 'POST' for r in http.requests))
                    for index in range(2):
                        pending = next(a for a in run['approvals'] if a['status'] == 'pending')
                        call('decide_approval', {**ref, 'approval_id': pending['approval_id'], 'decision': 'approved'}, 'approve-save-' + str(index))
                        app.state.live_workers[1].drain()
                        with service.store.transaction() as db:
                            run = json.loads(db.execute('SELECT document FROM runtime_runs').fetchone()[0])
                        if index == 0:
                            self.assertEqual(run['status'], 'paused_for_approval')
                            self.assertEqual(len(http.tables['Followups']), 2)
                            self.assertEqual(http.tables[source][2][3], 'New')
                self.assertEqual(run['status'], 'failed' if fail_status else 'completed', run)
                if fail_status:
                    self.assertEqual(run['error_code'], 'SHEETS_RECORD_FAILED')
                self.assertEqual(http.tables['Followups'][1], ['new-case', expected_finding, 'Follow-up draft',
                    'We checked your records: ' + expected_finding, expected_status])
                self.assertEqual(http.tables[source][2][-2:], ['New' if fail_status else expected_status, 'keep'])
                self.assertEqual(run['usage']['workflow']['tool_calls'], 3)
                self.assertEqual({agent for agent, _ in model_calls}, {'supervisor', checker, 'draft_specialist'})
                resources = next(context['configured_resources'] for role, context in model_calls if role == 'supervisor')
                self.assertEqual(resources['sources'][0]['resource_id'], spreadsheet_id)
                self.assertNotIn('credential_reference', json.dumps(resources))
                self.assertEqual(len(model_calls), 6)
                self.assertTrue(all('/spreadsheets/' + spreadsheet_id + '/' in r.full_url for r in http.requests))
                writes = len([r for r in http.requests if r.get_method() == 'POST'])
                events = service.runtime_runner.runtime.events(run['run_id'], auth)['items']
                self.assertEqual(len([e for e in events if e['event_type'] == 'agent.spawned']), 2)
                self.assertFalse(any(r.get_method() == 'POST' and not r.full_url.endswith('values:batchUpdate') for r in http.requests))
                self.assertNotIn('smtp_send_email', [t['tool_id'] for t in planned['tools']])
                context = json.loads(planning_calls[0]['input'][1]['content'])['context']
                self.assertEqual(context['sheet_write_targets'], targets if legacy_targets else [])
                self.assertEqual(context['sheet_target_mode'], 'workflow_metadata')
                self.assertIn('google_sheets_upsert_record', context['available_tools'])
                self.assertEqual(context['sheet_record_tool']['availability'], 'enabled')
                self.assertEqual(context['sheet_record_tool']['approval_required'], action_approval)
                # Reconstruct Registry/auth and checkpoint from durable storage.
                restarted = create_configured_app(env, path / 'runs.sqlite3', client=client, model_factory=factory)
                restarted.state.live_workers[0].tick()
                with restarted.state.workflow_service.store.transaction() as db:
                    self.assertEqual(db.execute('SELECT COUNT(*) FROM runtime_runs').fetchone()[0], 1)
                self.assertEqual(len(http.tables['Followups']), 2)
                self.assertEqual(len(model_calls), 6)
                self.assertEqual(len([r for r in http.requests if r.get_method() == 'POST']), writes)

    def test_live_configuration_exposes_prompt_scoped_writer_without_env_targets(self):
        with tempfile.TemporaryDirectory() as directory:
            token = Path(directory) / 'token.json'; token.write_text('{}')
            env = dict(GOOGLE_TOKEN_FILE=str(token), GMAIL_SMTP_USER='owner@example.com', GMAIL_SMTP_PASSWORD='offline',
                BUILDER_EMAIL_RECIPIENTS='owner@example.com')
            self.assertIn('google_sheets_upsert_record', [t['definition']['tool_id'] for t in registry_configuration(env)['tools']])
            env['BUILDER_SHEETS_DIRECT_WRITE'] = '1'
            direct = registry_configuration(env)
            self.assertFalse(next(t['definition']['approval_required'] for t in direct['tools'] if t['definition']['tool_id'] == 'google_sheets_upsert_record'))
            env.pop('BUILDER_SHEETS_DIRECT_WRITE')
            env['BUILDER_SHEETS_WRITE_TARGETS'] = json.dumps([dict(spreadsheet_id='test-sheet', range='Records!A1:B100',
                identity_column='id', writable_columns=['draft'], allow_create=True)])
            config = registry_configuration(env)
            self.assertTrue(next(t['definition']['approval_required'] for t in config['tools'] if t['definition']['tool_id'] == 'google_sheets_upsert_record'))

    def test_publication_rejects_dynamic_or_unapproved_graph_destinations(self):
        from planner.errors import PlannerFailure
        workflow = authored_workflow(('Reviews', 'Kitchen', 'review_id', 'order_id', 'checker'))
        workflow['metadata'].pop('sheet_write_targets')
        target = dict(spreadsheet_id='test-sheet', range='Followups!A1:E100', identity_column='review_id',
            writable_columns=['findings', 'subject', 'body', 'status'], allow_create=True)
        for targets in ([], [target]):
            with self.assertRaises(PlannerFailure):
                validate_record_workflow(workflow, targets)
        workflow['nodes'][2]['configuration']['input_mapping']['range'] = 'inputs.row.range'
        with self.assertRaises(PlannerFailure):
            validate_record_workflow(workflow, [target])

    def test_publication_rejects_untyped_or_forbidden_output_fields(self):
        from planner.errors import PlannerFailure
        workflow = authored_workflow(('Reviews', 'Kitchen', 'review_id', 'order_id', 'checker'))
        targets = [dict(spreadsheet_id='test-sheet', range=tab + '!A1:E100', identity_column='review_id',
            writable_columns=columns, allow_create=tab == 'Followups') for tab, columns in
            [('Followups', ['findings', 'subject', 'body', 'status']), ('Reviews', ['status'])]]
        validate_record_workflow(workflow, targets)
        for change in ({'additionalProperties': True}, {'properties': {'staff_notes': {'type': 'string'}}},
                       {'properties': {'findings': {'type': 'object'}}}):
            changed = deepcopy(workflow)
            changed['agents'][0]['output_schema']['properties']['draft_fields'].update(change)
            with self.assertRaises(PlannerFailure) as failed:
                validate_record_workflow(changed, targets)
            self.assertEqual(failed.exception.code, 'SHEETS_RECORD_SCHEMA_REQUIRED')
