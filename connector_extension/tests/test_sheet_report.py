"""Report creation exercises the real adapter/journal against an offline provider."""
from copy import deepcopy
from pathlib import Path
import tempfile
import unittest
import time
from urllib.parse import urlparse, parse_qs, unquote
from connector_extension.catalog import CATALOG
from connector_extension.common import EffectJournal
from connector_extension.google import GoogleAPI
from connector_extension.sheet_creation import SheetResourceStore
from connector_extension.sheet_report import ReportSheetsSetup
from connector_extension.tests.test_sheet_creation import OfflineSheets
from connector_extension.tests.test_connectors import grant
from runtime.service import RuntimeFailure
from workflow_api.procurement import definitions

TOOL = 'extension_sheets_create_report'


class ReportProvider(OfflineSheets):
    def request(self, method, url, headers, body=None, timeout=30):
        parsed = urlparse(url)
        if method == 'GET' and parsed.path.endswith('/values:batchGet'):
            self.calls.append({'method': method, 'url': url, 'body': None})
            if self.fail_verification: raise TimeoutError('offline verification unavailable')
            book = self.books[unquote(parsed.path).split('/')[-2]]
            result = []
            for selection in parse_qs(parsed.query)['ranges']:
                title, cells = selection.rsplit('!', 1)
                table = next(t for t in book['sheets'] if t['properties']['title'] == title[1:-1].replace("''", "'"))
                last = int(''.join(c for c in cells.split(':')[-1] if c.isdigit()))
                result.append({'values': deepcopy([table['headers'], *table['business_rows']][:last])})
            return {'valueRanges': result}
        result = super().request(method, url, headers, body, timeout)
        if method == 'POST' and parsed.path.endswith('/spreadsheets'):
            for actual, spec in zip(self.books[result['spreadsheetId']]['sheets'], body['sheets']):
                actual['business_rows'] = [[next(iter(c['userEnteredValue'].values())) if c else None
                    for c in row['values']] for row in spec['data'][0]['rowData'][1:]]
        return result


class ReportTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.root = Path(self.temp.name)
        self.http = ReportProvider(); self.api = GoogleAPI(lambda scopes, timeout: 'offline', self.http)
        self.journal = EffectJournal(self.root); self.resources = SheetResourceStore(self.root)
        self.workflow = {'workflow_id': 'report_test', 'version': 1, 'metadata': {'workspace_id': 'local-workspace'}}
        self.inputs = {'project_id': 'northwind_report', 'creation_key': 'restock_review_v1', 'title': 'Restock review',
            'tabs': [{'title': 'Inventory', 'headers': ['Product', 'Stock', 'Active', 'Notes'],
                      'rows': [['Example product', 2, True, None], ['=literal', 0.25, False, '']]},
                     {'title': 'External risks', 'headers': ['Finding', 'Source'],
                      'rows': [['Provider fixture only', 'https://example.org/report']]}]}
    def tearDown(self): self.temp.cleanup()
    def connector(self, **kwargs):
        return ReportSheetsSetup(CATALOG[TOOL], self.api, self.journal, self.resources, **kwargs).bind_workflow(self.workflow)
    def invoke(self, value=None, effect='run_one'):
        return self.connector().invoke(grant(TOOL), value or self.inputs, effect)
    def test_atomic_report_creation_and_verified_receipt(self):
        result = self.invoke()
        self.assertEqual(result['written_rows'], 3); self.assertEqual(len(result['report_sha256']), 64)
        self.assertEqual(self.http.write_count, 1)
        self.assertEqual(self.http.books[result['spreadsheet_id']]['sheets'][0]['properties']['gridProperties']['rowCount'], 3)
        posts = [c for c in self.http.calls if c['method'] == 'POST']
        self.assertEqual(len(posts), 1); self.assertTrue(posts[0]['url'].endswith('/spreadsheets'))
        rows = posts[0]['body']['sheets'][0]['data'][0]['rowData']
        self.assertEqual(rows[2]['values'][0], {'userEnteredValue': {'stringValue': '=literal'}})
        self.assertEqual(rows[1]['values'][2], {'userEnteredValue': {'boolValue': True}})
        self.assertEqual(rows[1]['values'][3], {})
    def test_repeated_action_does_not_duplicate_and_changed_data_is_denied(self):
        first = self.invoke(); second = self.invoke()
        self.assertEqual(first['spreadsheet_id'], second['spreadsheet_id']); self.assertTrue(second['reused'])
        changed = deepcopy(self.inputs); changed['tabs'][0]['rows'][0][1] = 7
        with self.assertRaises(RuntimeFailure) as error: self.invoke(changed)
        self.assertEqual(error.exception.code, 'EFFECT_REFERENCE_MISMATCH'); self.assertEqual(self.http.write_count, 1)
    def test_new_run_with_changed_findings_creates_a_separate_report(self):
        first = self.invoke()
        changed = deepcopy(self.inputs); changed['tabs'][1]['rows'][0][0] = 'New public finding'
        second = self.invoke(changed, effect='run_two')
        self.assertNotEqual(first['spreadsheet_id'], second['spreadsheet_id'])
        self.assertEqual(self.http.write_count, 2)
        self.assertEqual(self.invoke(changed, effect='run_two')['spreadsheet_id'], second['spreadsheet_id'])
        self.assertEqual(self.http.write_count, 2)
    def test_new_revision_cannot_collide_even_with_the_same_action_reference(self):
        first = self.invoke()
        self.workflow['version'] = 2
        self.assertNotEqual(first['spreadsheet_id'], self.invoke()['spreadsheet_id'])
    def test_legacy_completed_report_is_preserved_and_does_not_block_new_runs(self):
        connector = self.connector()
        legacy = super(ReportSheetsSetup, connector).execute(grant(TOOL), self.inputs, 'legacy', time.monotonic()+30)
        changed = deepcopy(self.inputs); changed['tabs'][0]['rows'][0][1] = 9
        fresh = self.invoke(changed)
        self.assertNotEqual(legacy['spreadsheet_id'], fresh['spreadsheet_id'])
        self.assertEqual(self.http.books[legacy['spreadsheet_id']]['sheets'][0]['business_rows'][0][1], 2)
        self.assertEqual(connector.reconcile(self.inputs, legacy['spreadsheet_id'])['spreadsheet_id'], legacy['spreadsheet_id'])
    def test_empty_action_reference_is_rejected_before_io(self):
        with self.assertRaises(RuntimeFailure):self.invoke(effect='')
        self.assertEqual(self.http.write_count, 0)
    def test_readback_failure_requires_reconciliation_and_never_recreates(self):
        self.http.fail_verification = True
        with self.assertRaises(Exception): self.invoke()
        self.http.fail_verification = False
        with self.assertRaises(RuntimeFailure) as error: self.invoke()
        self.assertEqual(error.exception.code, 'UNKNOWN_INVOCATION_RESULT')
        result = self.connector().reconcile(self.inputs, 'created_1', effect_id='run_one')
        self.assertEqual(result['written_rows'], 3); self.assertEqual(self.http.write_count, 1)
        self.assertTrue(self.invoke()['reused'])
    def test_external_edits_are_not_overwritten(self):
        self.invoke(); self.http.books['created_1']['sheets'][0]['business_rows'][0][1] = 9
        with self.assertRaises(RuntimeFailure) as error: self.invoke()
        self.assertEqual(error.exception.code, 'SHEETS_REPORT_VERIFICATION_FAILED'); self.assertEqual(self.http.write_count, 1)
    def test_approval_and_existing_target_ceilings_remain_enforced(self):
        authorization = grant(TOOL); authorization.pop('approval_reference')
        with self.assertRaises(RuntimeFailure): self.connector().invoke(authorization, self.inputs, 'run')
        for limits in [dict(read_targets=[{'spreadsheet_id': 'existing'}]), dict(write_targets=[{'spreadsheet_id': 'existing'}])]:
            with self.assertRaises(RuntimeFailure): self.connector(**limits).invoke(grant(TOOL), self.inputs, 'run')
        self.assertEqual(self.http.write_count, 0)
    def test_report_bounds_reject_before_io(self):
        bad = []
        value = deepcopy(self.inputs); value['tabs'][0]['rows'][0].pop(); bad.append(value)
        value = deepcopy(self.inputs); value['tabs'][0]['rows'][0][1] = float('nan'); bad.append(value)
        value = deepcopy(self.inputs); value['tabs'][0]['rows'][0][1] = {'nested': 1}; bad.append(value)
        value = deepcopy(self.inputs); value['row_count'] = 2; bad.append(value)
        value = deepcopy(self.inputs); value['spreadsheet_id'] = 'existing'; bad.append(value)
        value = deepcopy(self.inputs); value['tabs'][0]['rows'] *= 126; bad.append(value)
        for value in bad:
            with self.subTest(value_type=str(type(value))):
                with self.assertRaises(RuntimeFailure): self.invoke(value)
        self.assertEqual(self.http.calls, [])
    def test_report_always_requires_approval_even_in_legacy_automatic_mode(self):
        config = {'enabled_providers': ['google_sheets'], '_automatic_actions': True, 'sheet_creation_enabled': True}
        tool = next(t for t in definitions(config) if t['tool_id'] == TOOL)
        self.assertTrue(tool['approval_required'])

if __name__ == '__main__': unittest.main()
