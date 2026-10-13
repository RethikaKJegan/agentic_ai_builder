"""Generalized Sheets with fake provider access and real revision authorization."""
from copy import deepcopy
import json
from pathlib import Path
import tempfile
import time
import unittest
from connector_extension.app import create_extension_app, STATE_ROOT
from connector_extension.catalog import CATALOG
from connector_extension.common import EffectJournal
from connector_extension.examples import connector_workflow
from connector_extension.google import GoogleAPI
from connector_extension.sheets import SheetsRead, SheetsDiscover, SheetsWrite
from connector_extension.tests.test_connectors import FakeTransport, grant
from runtime.service import RuntimeFailure


def metadata(identifier, title='Project Items', rows=1000, columns=3):
    return {'spreadsheetId':identifier,'properties':{'title':'Tender'},'sheets':[{'properties':{
        'title':title,'sheetId':0,'gridProperties':{'rowCount':rows,'columnCount':columns}}}]}


class GeneralizedSheetsTests(unittest.TestCase):
    def setUp(self):
        STATE_ROOT.mkdir(parents=True,exist_ok=True)
        self.temp=tempfile.TemporaryDirectory(dir=STATE_ROOT);self.root=Path(self.temp.name)
    def tearDown(self): self.temp.cleanup()
    def api(self,transport): return GoogleAPI(lambda scopes,timeout:'offline',transport)

    def test_read_different_links_without_configured_ids(self):
        transport=FakeTransport({'values':[['item_id'],['p1']]},{'values':[['vendor_id'],['v1']]})
        connector=SheetsRead(CATALOG['google_sheets_read_rows'],self.api(transport))
        for identifier,cell_range in [('first_project','Items!A1:A10'),('second_project','Vendors!A1:A10')]:
            result=connector.invoke(grant('google_sheets_read_rows'),{
                'spreadsheet_url':f'https://docs.google.com/spreadsheets/d/{identifier}/edit','range':cell_range},'read')
            self.assertEqual(len(result['rows']),2)
        self.assertIn('/first_project/',transport.calls[0]['url']);self.assertIn('/second_project/',transport.calls[1]['url'])

    def test_foreign_urls_duplicate_reference_and_google_access_denial(self):
        transport=FakeTransport();connector=SheetsRead(CATALOG['google_sheets_read_rows'],self.api(transport))
        for inputs in [{'spreadsheet_url':'https://evil.example/spreadsheets/d/a/edit','range':'Tab!A1:A10'},
                       {'spreadsheet_url':'https://docs.google.com/spreadsheets/d/a/edit','spreadsheet_id':'a','range':'Tab!A1:A10'}]:
            with self.assertRaises(RuntimeFailure): connector.invoke(grant('google_sheets_read_rows'),inputs,'bad')
        self.assertFalse(transport.calls)
        denied=FakeTransport(RuntimeFailure('PROVIDER_REQUEST_FAILED','Google denied access',502))
        with self.assertRaises(RuntimeFailure): SheetsRead(CATALOG['google_sheets_read_rows'],self.api(denied)).invoke(
            grant('google_sheets_read_rows'),{'spreadsheet_url':'https://docs.google.com/spreadsheets/d/no_access/edit','range':'Tab!A1:A10'},'read')
        self.assertEqual(len(denied.calls),1)

    def test_discovery_returns_actual_tabs_headers_and_bounds_only(self):
        transport=FakeTransport(metadata('book'),{'values':[['item_id','quantity','status']]})
        connector=SheetsDiscover(CATALOG['extension_sheets_discover'],self.api(transport))
        result=connector.invoke(grant('extension_sheets_discover'),{'spreadsheet_url':'https://docs.google.com/spreadsheets/d/book/edit'},'discover')
        table=result['tables'][0]
        self.assertEqual(table['title'],'Project Items');self.assertEqual(table['headers'],['item_id','quantity','status'])
        self.assertEqual(table['range'],"'Project Items'!A1:C1000")
        self.assertFalse(result['has_more']);self.assertNotIn('rows',table)
        self.assertIn('A1%3AC1',transport.calls[1]['url'])

    def test_discovery_obeys_optional_operator_ceiling(self):
        transport=FakeTransport(metadata('allowed'),{'values':[['id','qty']]})
        connector=SheetsDiscover(CATALOG['extension_sheets_discover'],self.api(transport),[
            {'spreadsheet_id':'allowed','range':"'Project Items'!B3:C100"}])
        with self.assertRaises(RuntimeFailure):connector.invoke(grant('extension_sheets_discover'),{'spreadsheet_id':'other'},'bad')
        self.assertFalse(transport.calls)
        result=connector.invoke(grant('extension_sheets_discover'),{'spreadsheet_id':'allowed'},'ok')
        self.assertEqual(result['tables'][0]['range'],"'Project Items'!B3:C100")
        self.assertIn('B3%3AC3',transport.calls[1]['url'])

    def test_general_write_is_unbound_until_exact_workflow_targets_are_reviewed(self):
        transport=FakeTransport({'values':[['item_id','quantity','status'],['p1',1,'Open']]},{'totalUpdatedCells':1})
        connector=SheetsWrite(CATALOG['google_sheets_upsert_record'],self.api(transport),EffectJournal(self.root),[],self.root/'token.json',self.root/'locks')
        inputs={'spreadsheet_id':'https://docs.google.com/spreadsheets/d/new_project/edit','range':'BOQ!A1:C10',
                'identity_column':'item_id','identity':'p1','fields':{'status':'Ready'}}
        with self.assertRaises(RuntimeFailure): connector.invoke(grant('google_sheets_upsert_record'),inputs,'unbound')
        self.assertFalse(transport.calls)
        target={'spreadsheet_id':inputs['spreadsheet_id'],'range':'BOQ!A1:C10','identity_column':'item_id','writable_columns':['status'],'allow_create':False}
        workflow=connector_workflow('google_sheets_upsert_record',inputs,'general_write',sheet_targets=[target]);workflow['metadata']['workspace_id']='local-workspace'
        original=deepcopy(workflow);bound=connector.bind_workflow(workflow)
        result=bound.invoke(grant('google_sheets_upsert_record'),inputs,'bound')
        self.assertEqual(result['updated_cells'],1);self.assertEqual(workflow,original)
        with self.assertRaises(RuntimeFailure):bound.invoke(grant('google_sheets_upsert_record'),{**inputs,'spreadsheet_id':'other_project'},'bad')
        with self.assertRaises(RuntimeFailure):bound.invoke(grant('google_sheets_upsert_record'),{**inputs,'fields':{'quantity':10}},'bad_column')
        self.assertEqual(len(transport.calls),2)

    def test_app_enables_sheets_without_resource_configuration(self):
        app=create_extension_app({'enabled_providers':['google_sheets']},self.root,transport=FakeTransport(),token_supplier=lambda scopes,timeout:'offline')
        tools=app.state.workflow_service.registry.list_tools(app.state.extension_auth)['data']['items']
        sheet_tools=[tool for tool in tools if tool['definition']['provider_id']=='google_sheets']
        self.assertEqual(len(sheet_tools),5)
        existing=[tool for tool in sheet_tools if tool['tool_id'] not in {'extension_sheets_create','extension_sheets_add_tabs'}]
        self.assertTrue(all(tool['definition']['availability']=='enabled' for tool in existing))

    def test_planning_discovers_multiple_user_links_before_generation(self):
        class Provider:
            contexts=[]
            def generate(self,objective,context):
                self.contexts.append(context)
                return connector_workflow('google_sheets_read_rows',{'spreadsheet_id':'first_book','range':"'Project Items'!A1:C10"},'new_plan')
        provider=Provider();transport=FakeTransport(metadata('first_book'),{'values':[['id','qty','status']]},
                                                  metadata('second_book','Vendors'),{'values':[['id','email','name']]})
        app=create_extension_app({'enabled_providers':['google_sheets']},self.root,transport=transport,
            token_supplier=lambda scopes,timeout:'offline',planner_provider=provider)
        service=app.state.workflow_service
        result=service.handle({'request_id':'req_test','operation':'plan_workflow','idempotency_key':'general_plan',
            'payload':{'objective':'Read https://docs.google.com/spreadsheets/d/first_book/edit and https://docs.google.com/spreadsheets/d/second_book/edit'}},app.state.extension_auth)
        self.assertEqual(result['status'],200,result)
        self.assertEqual([catalog['spreadsheet_id'] for catalog in provider.contexts[0]['discovered_spreadsheets']],['first_book','second_book'])
        self.assertFalse(provider.contexts[0]['sheet_write_targets']);self.assertEqual(len(transport.calls),4)
        self.assertNotIn('values',json.dumps(provider.contexts[0]['discovered_spreadsheets']))

    def test_discovery_failure_stops_generation_without_cached_fake_headers(self):
        class Provider:
            calls=0
            def generate(self,*args):self.calls+=1;raise AssertionError('Must not generate')
        provider=Provider();transport=FakeTransport(RuntimeFailure('PROVIDER_REQUEST_FAILED','Access denied',502))
        app=create_extension_app({'enabled_providers':['google_sheets']},self.root,transport=transport,token_supplier=lambda scopes,timeout:'offline',planner_provider=provider)
        result=app.state.workflow_service.handle({'request_id':'req_test','operation':'plan_workflow','idempotency_key':'failed_setup',
            'payload':{'objective':'Read https://docs.google.com/spreadsheets/d/denied/edit'}},app.state.extension_auth)
        self.assertEqual(result['data']['error']['error_code'],'SHEETS_DISCOVERY_FAILED');self.assertEqual(provider.calls,0)

    def test_distinct_workflows_can_write_different_sheets_with_one_configuration(self):
        transport=FakeTransport({'values':[['item_id','status'],['p1','Open']]},{'totalUpdatedCells':1},
                                {'values':[['item_id','status'],['p1','Open']]},{'totalUpdatedCells':1})
        app=create_extension_app({'enabled_providers':['google_sheets']},self.root,transport=transport,token_supplier=lambda scopes,timeout:'offline')
        service,auth=app.state.workflow_service,app.state.extension_auth
        for number,identifier in enumerate(['project_one','project_two'],1):
            link=f'https://docs.google.com/spreadsheets/d/{identifier}/edit'
            inputs={'spreadsheet_id':link,'range':'BOQ!A1:B10','identity_column':'item_id','identity':'p1','fields':{'status':'Ready'}}
            target={'spreadsheet_id':link,'range':'BOQ!A1:B10','identity_column':'item_id','writable_columns':['status'],'allow_create':False}
            workflow=connector_workflow('google_sheets_upsert_record',inputs,f'workflow_{number}',sheet_targets=[target])
            ref={'workflow_id':workflow['workflow_id'],'workflow_version':1}
            def handle(operation,payload,key):
                result=service.handle({'request_id':'req_test','operation':operation,'idempotency_key':key+str(number),'payload':payload},auth)
                self.assertEqual(result['status'],200,result);return result['data']
            handle('save_workflow_version',{**ref,'base_version':0,'workflow':workflow},'save_book')
            handle('validate_workflow',ref,'validate_book')
            handle('approve_workflow',{**ref,'action':'approve'},'approve_book')
            run=handle('execute_workflow',{**ref,'inputs':{}},'execute_book')['run']
            self.assertEqual(run['status'],'paused_for_approval')
            handle('decide_approval',{**ref,'approval_id':run['approvals'][0]['approval_id'],'decision':'approved'},'decide_book')
            self.assertEqual(service.runtime_runner.runtime.get_run(run['run_id'],auth)['status'],'completed')
        self.assertEqual(len(transport.calls),4)
        self.assertIn('/project_one/',transport.calls[1]['url']);self.assertIn('/project_two/',transport.calls[3]['url'])

    def test_header_only_spreadsheet_can_be_discovered_and_read(self):
        transport=FakeTransport(metadata('header_only','Items',rows=1,columns=2),{'values':[['item_id','quantity']]},
                                {'values':[['item_id','quantity']]})
        discovery=SheetsDiscover(CATALOG['extension_sheets_discover'],self.api(transport))
        table=discovery.invoke(grant('extension_sheets_discover'),{'spreadsheet_id':'header_only'},'discover')['tables'][0]
        self.assertEqual(table['range'],"'Items'!A1:B1")
        reader=SheetsRead(CATALOG['google_sheets_read_rows'],self.api(transport))
        result=reader.invoke(grant('google_sheets_read_rows'),{'spreadsheet_id':'header_only','range':table['range']},'read')
        self.assertEqual(result['rows'],[['item_id','quantity']])
