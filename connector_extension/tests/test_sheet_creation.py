"""Actual provisioning adapters and approval/runtime tests with an offline Sheets API."""
from copy import deepcopy
import json
from pathlib import Path
import re
import sqlite3
import tempfile
import unittest
from urllib.parse import urlparse, parse_qs, unquote
from fastapi.testclient import TestClient
from connector_extension.app import create_extension_app, STATE_ROOT
from connector_extension.catalog import CATALOG
from connector_extension.common import EffectJournal
from connector_extension.google import GoogleAPI
from connector_extension.sheet_creation import SheetsSetup, SheetResourceStore
from connector_extension.procurement.layout import tracking_inputs, tracking_workflow
from connector_extension.examples import connector_workflow
from connector_extension.tests.test_connectors import grant
from connector_extension.transport import COOKIE
from runtime.service import RuntimeFailure
from runtime.sheet_records import write_targets


class OfflineSheets:
    def __init__(self):
        self.books = {}; self.calls = []; self.write_count = 0; self.lose_write_response = False
        self.fail_verification = False
    def add_book(self, identifier, tables):
        self.books[identifier] = {'spreadsheetId': identifier, 'properties': {'title': 'Existing'},
            'developerMetadata': [], 'sheets': [{'properties': {'sheetId': i, 'title': title,
                'gridProperties': {'rowCount': 1000, 'columnCount': len(headers)}},
                'developerMetadata': [], 'headers': headers, 'business_rows': [['keep','untouched']]}
                for i,(title,headers) in enumerate(tables.items())]}
    def request(self, method, url, headers, body=None, timeout=30):
        self.calls.append({'method': method, 'url': url, 'body': deepcopy(body)})
        parsed = urlparse(url); path = unquote(parsed.path).removeprefix('/v4/')
        if method == 'POST' and path == 'spreadsheets':
            if any(m.get('location',{}).get('sheetId') is not None for m in body.get('developerMetadata',[])):
                raise RuntimeFailure('PROVIDER_HTTP_400','Top-level metadata must have spreadsheet location.',502)
            for source in body['sheets']:
                if any(m.get('location',{}).get('sheetId')!=source['properties']['sheetId']
                       for m in source.get('developerMetadata',[])):
                    raise RuntimeFailure('PROVIDER_HTTP_400','Sheet metadata must match its container.',502)
            self.write_count += 1; identifier = 'created_' + str(self.write_count)
            book = {'spreadsheetId': identifier, 'properties': body['properties'],
                    'developerMetadata': deepcopy(body['developerMetadata']), 'sheets': []}
            for source in body['sheets']:
                table = {'properties':deepcopy(source['properties']), 'developerMetadata':deepcopy(source.get('developerMetadata',[])),
                    'headers':[v['userEnteredValue']['stringValue'] for v in source['data'][0]['rowData'][0]['values']],
                    'business_rows':[]}
                book['sheets'].append(table)
            self.books[identifier] = book
            if self.lose_write_response: self.lose_write_response = False; raise TimeoutError('offline lost response')
            return deepcopy(book)
        if method == 'POST' and path.endswith(':batchUpdate'):
            self.write_count += 1; identifier = path.split('/')[1].removesuffix(':batchUpdate')
            book = deepcopy(self.books[identifier])
            for change in body['requests']:
                if 'addSheet' in change:
                    book['sheets'].append({'properties':deepcopy(change['addSheet']['properties']),
                                          'developerMetadata':[],'headers':[],'business_rows':[]})
                elif 'updateCells' in change:
                    spec=change['updateCells'];table=next(t for t in book['sheets'] if t['properties']['sheetId']==spec['start']['sheetId'])
                    table['headers']=[v['userEnteredValue']['stringValue'] for v in spec['rows'][0]['values']]
                elif 'createDeveloperMetadata' in change:
                    book['developerMetadata'].append(deepcopy(change['createDeveloperMetadata']['developerMetadata']))
                else: raise AssertionError('Unexpected mutation')
            self.books[identifier] = book
            if self.lose_write_response: self.lose_write_response=False;raise TimeoutError('offline lost response')
            return {'spreadsheetId': identifier, 'replies':[{} for _ in body['requests']]}
        identifier = path.split('/')[1]
        if identifier not in self.books: raise RuntimeFailure('PROVIDER_REQUEST_FAILED','offline access denied',502)
        book = self.books[identifier]
        if path.endswith('/values:batchGet'):
            if self.fail_verification: raise TimeoutError('offline read timeout')
            ranges = parse_qs(parsed.query)['ranges']; values=[]
            for cell_range in ranges:
                title=cell_range.rsplit('!',1)[0][1:-1].replace("''", "'")
                table=next(t for t in book['sheets'] if t['properties']['title']==title)
                values.append({'range':cell_range,'values':[deepcopy(table['headers'])]})
            return {'valueRanges':values}
        return deepcopy(book)


class CreationTests(unittest.TestCase):
    def setUp(self):
        STATE_ROOT.mkdir(parents=True,exist_ok=True);self.temp=tempfile.TemporaryDirectory(dir=STATE_ROOT)
        self.root=Path(self.temp.name);self.http=OfflineSheets();self.api=GoogleAPI(lambda scopes,timeout:'offline',self.http)
        self.journal=EffectJournal(self.root);self.resources=SheetResourceStore(self.root)
        self.workflow={'workflow_id':'setup_demo','version':1,'metadata':{'workspace_id':'local-workspace'}}
        self.inputs={'project_id':'project_demo','creation_key':'tracking_v1','title':'Tracking',
                     'tabs':[{'title':'Items','headers':['item_id','quantity']}]}
    def tearDown(self):self.temp.cleanup()
    def connector(self, tool='extension_sheets_create', **kwargs):
        return SheetsSetup(CATALOG[tool],self.api,self.journal,self.resources,**kwargs).bind_workflow(self.workflow)
    def invoke(self, inputs=None, tool='extension_sheets_create', effect='first'):
        return self.connector(tool).invoke(grant(tool),inputs or self.inputs,effect)

    def test_create_literal_headers_manifest_and_reviewable_targets(self):
        data=deepcopy(self.inputs);data['tabs'][0]['headers'].append('=literal_header')
        result=self.invoke(data);self.assertEqual(result['spreadsheet_id'],'created_1')
        self.assertTrue(result['spreadsheet_created']);self.assertTrue(result['tabs'][0]['created'])
        self.assertEqual(result['tabs'][0]['headers'],data['tabs'][0]['headers'])
        body=self.http.calls[0]['body'];self.assertEqual(body['sheets'][0]['data'][0]['rowData'][0]['values'][-1],
                                                     {'userEnteredValue':{'stringValue':'=literal_header'}})
        self.assertEqual(len(write_targets(result['proposed_write_targets'])),1)
        with sqlite3.connect(self.resources.path) as db:
            row=db.execute('SELECT project,spreadsheet_owned,tab_owned FROM resources').fetchone()
        self.assertEqual(row,('project_demo',1,1))

    def test_restart_and_new_run_reuse_same_creation_key(self):
        first=self.invoke();second=self.invoke(effect='another_run');self.assertEqual(self.http.write_count,1)
        self.assertEqual(first['spreadsheet_id'],second['spreadsheet_id']);self.assertTrue(second['reused'])
        restarted=SheetsSetup(CATALOG['extension_sheets_create'],self.api,EffectJournal(self.root),
            SheetResourceStore(self.root)).bind_workflow(self.workflow)
        third=restarted.invoke(grant('extension_sheets_create'),{**self.inputs,'row_count':1000},'restart')
        self.assertTrue(third['reused']);self.assertEqual(self.http.write_count,1)

    def test_changed_input_under_existing_key_is_denied(self):
        self.invoke();calls=len(self.http.calls)
        with self.assertRaises(RuntimeFailure):self.invoke({**self.inputs,'title':'Changed'})
        self.assertEqual(len(self.http.calls),calls)

    def test_projects_have_independent_setup_keys(self):
        first=self.invoke();second=self.invoke({**self.inputs,'project_id':'other_project'})
        self.assertNotEqual(first['spreadsheet_id'],second['spreadsheet_id']);self.assertEqual(self.http.write_count,2)

    def test_unknown_create_is_not_repeated_and_read_reconciliation_recovers(self):
        self.http.lose_write_response=True
        with self.assertRaises(RuntimeFailure):self.invoke()
        count=self.http.write_count
        with self.assertRaises(RuntimeFailure):self.invoke(effect='retry')
        self.assertEqual(self.http.write_count,count)
        result=self.connector().reconcile(self.inputs,'created_1');self.assertTrue(result['spreadsheet_created'])
        result=self.invoke(effect='reconciled');self.assertTrue(result['reused']);self.assertEqual(self.http.write_count,1)

    def test_reconciliation_rejects_wrong_marker_and_changed_manifest(self):
        self.http.lose_write_response=True
        with self.assertRaises(RuntimeFailure):self.invoke()
        self.http.add_book('unrelated',{'Items':['item_id','quantity']})
        with self.assertRaises(RuntimeFailure):self.connector().reconcile(self.inputs,'unrelated')
        with self.assertRaises(RuntimeFailure):self.connector().reconcile({**self.inputs,'title':'Other'},'created_1')
        self.assertEqual(self.http.write_count,1)

    def test_verification_failure_retains_creation_observation_and_never_recreates(self):
        self.http.fail_verification=True
        with self.assertRaises(RuntimeFailure):self.invoke()
        with sqlite3.connect(self.resources.path) as db:
            self.assertEqual(db.execute('SELECT spreadsheet FROM observations').fetchone()[0],'created_1')
        with self.assertRaises(RuntimeFailure):self.invoke(effect='retry')
        self.http.fail_verification=False;self.connector().reconcile(self.inputs,'created_1')
        self.assertEqual(self.http.write_count,1)

    def test_completed_setup_rechecks_headers_instead_of_mutating(self):
        self.invoke();self.http.books['created_1']['sheets'][0]['headers']=['item_id','changed']
        with self.assertRaises(RuntimeFailure):self.invoke(effect='another_run')
        self.assertEqual(self.http.write_count,1)

    def test_bounds_titles_and_headers_fail_before_provider_access(self):
        variants=[]
        for tabs in ([{'title':'Bad/title','headers':['id','q']}],
                     [{'title':'Items','headers':['id','id']}],
                     [{'title':'Items','headers':['id','q']},{'title':'items','headers':['id','other']}],
                     [{'title':'Items','headers':['id',' blank']}],
                     [{'title':'Table'+str(i),'headers':['h'+str(j) for j in range(100)]} for i in range(20)]):
            variants.append({**self.inputs,'tabs':tabs,'row_count':10000})
        for data in variants:
            with self.assertRaises(RuntimeFailure):self.invoke(data)
        self.assertFalse(self.http.calls)

    def test_approval_binding_namespace_and_operator_ceilings(self):
        binding=grant('extension_sheets_create');binding['approval_reference']=None
        with self.assertRaises(RuntimeFailure):self.connector().invoke(binding,self.inputs,'bad')
        unbound=SheetsSetup(CATALOG['extension_sheets_create'],self.api,self.journal,self.resources)
        with self.assertRaises(RuntimeFailure):unbound.invoke(grant('extension_sheets_create'),self.inputs,'bad')
        for connector in (self.connector(write_targets=[{'spreadsheet_id':'one'}]),
                          self.connector(read_targets=[{'spreadsheet_id':'one'}])):
            with self.assertRaises(RuntimeFailure):connector.invoke(grant('extension_sheets_create'),self.inputs,'ceiling')
        self.assertFalse(self.http.calls)

    def test_missing_edit_scope_fails_before_intent_or_write(self):
        def token(scopes,timeout):raise RuntimeFailure('GOOGLE_SCOPE_REQUIRED','offline missing scope',403)
        connector=SheetsSetup(CATALOG['extension_sheets_create'],GoogleAPI(token,self.http),self.journal,self.resources).bind_workflow(self.workflow)
        with self.assertRaises(RuntimeFailure):connector.invoke(grant('extension_sheets_create'),self.inputs,'scope')
        self.assertFalse(self.http.calls)
        with sqlite3.connect(self.journal.path) as db:self.assertEqual(db.execute('SELECT COUNT(*) FROM effects').fetchone()[0],0)

    def test_add_tabs_preserves_existing_business_data_and_reuses_matching_headers(self):
        self.http.add_book('original',{'Legacy':['id','value'],'Items':['item_id','quantity']})
        before=deepcopy(self.http.books['original']['sheets'][0])
        data={k:v for k,v in self.inputs.items() if k!='title'};data['spreadsheet_url']='https://docs.google.com/spreadsheets/d/original/edit'
        data['tabs'].append({'title':"Manager's notes",'headers':['note_id','text']})
        result=self.invoke(data,'extension_sheets_add_tabs');self.assertFalse(result['spreadsheet_created'])
        self.assertFalse(result['tabs'][0]['created']);self.assertTrue(result['tabs'][1]['created'])
        self.assertEqual(self.http.books['original']['sheets'][0],before)
        self.assertEqual(self.http.write_count,1)
        batch=next(c['body'] for c in self.http.calls if c['method']=='POST')
        self.assertEqual(len(batch['requests']),3)
        self.invoke(data,'extension_sheets_add_tabs',effect='second');self.assertEqual(self.http.write_count,1)

    def test_conflicting_headers_are_rejected_before_journal_or_mutation(self):
        self.http.add_book('original',{'Items':['id','other']});data={k:v for k,v in self.inputs.items() if k!='title'};data['spreadsheet_id']='original'
        with self.assertRaises(RuntimeFailure) as caught:self.invoke(data,'extension_sheets_add_tabs')
        self.assertEqual(caught.exception.code,'SHEETS_TAB_CONFLICT');self.assertEqual(self.http.write_count,0)
        with sqlite3.connect(self.journal.path) as db:self.assertEqual(db.execute('SELECT COUNT(*) FROM effects').fetchone()[0],0)

    def test_all_existing_tables_do_not_write_or_claim_ownership(self):
        self.http.add_book('original',{'Items':['item_id','quantity']});data={k:v for k,v in self.inputs.items() if k!='title'};data['spreadsheet_id']='original'
        result=self.invoke(data,'extension_sheets_add_tabs');self.assertEqual(self.http.write_count,0)
        self.assertFalse(result['tabs'][0]['created'])

    def test_add_unknown_result_reconciliation_uses_exact_destination(self):
        self.http.add_book('original',{'Legacy':['id','value']});data={k:v for k,v in self.inputs.items() if k!='title'};data['spreadsheet_id']='original';self.http.lose_write_response=True
        with self.assertRaises(RuntimeFailure):self.invoke(data,'extension_sheets_add_tabs')
        with self.assertRaises(RuntimeFailure):self.connector('extension_sheets_add_tabs').reconcile(data,'different')
        result=self.connector('extension_sheets_add_tabs').reconcile(data,'original')
        self.assertTrue(result['tabs'][0]['created']);self.assertEqual(self.http.write_count,1)

    def test_layout_is_six_tables_and_defensive_copy(self):
        first=tracking_inputs('project_demo','Demo');first['tabs'][0]['headers'].append('changed')
        second=tracking_inputs('project_demo','Demo');self.assertEqual(len(second['tabs']),6)
        self.assertNotIn('changed',second['tabs'][0]['headers']);result=self.invoke(second)
        self.assertEqual(len(result['proposed_write_targets']),6)
        self.assertEqual(len(write_targets(result['proposed_write_targets'])),6)


class CreationRuntimeTests(unittest.TestCase):
    def setUp(self):
        STATE_ROOT.mkdir(parents=True,exist_ok=True);self.temp=tempfile.TemporaryDirectory(dir=STATE_ROOT);self.root=Path(self.temp.name)
        self.http=OfflineSheets();self.app=create_extension_app({'enabled_providers':['google_sheets'],'sheet_creation_enabled':True},
            self.root,transport=self.http,token_supplier=lambda scopes,timeout:'offline')
        self.client=TestClient(self.app);session=self.client.get('/session');self.client.cookies.set(COOKIE,session.cookies[COOKIE],path='/')
    def tearDown(self):self.client.close();self.temp.cleanup()
    def mutation(self,op,payload,path,method='POST'):
        r=self.client.request(method,path,json={'request_id':'req_test','operation':op,
            'idempotency_key':op+'_'+payload.get('workflow_id',payload.get('approval_id','test'))+'_'+payload.get('action',''),
            'payload':payload});self.assertEqual(r.status_code,200,r.text);return r.json()['data']
    def publish(self,w):
        identity=w['workflow_id'];ref={'workflow_id':identity,'workflow_version':1}
        self.mutation('save_workflow_version',{**ref,'base_version':0,'workflow':w},'/workflows/'+identity+'/versions/1','PUT')
        self.mutation('validate_workflow',ref,'/workflows/'+identity+'/validate')
        for action in ('approve','publish'):self.mutation('approve_workflow',{**ref,'action':action},'/workflows/'+identity+'/approve')
        return ref

    def test_create_runs_only_after_action_approval_and_emits_confirmed_result(self):
        ref=self.publish(tracking_workflow('project_demo','Demo',workflow_id='runtime_creation'))
        run=self.mutation('execute_workflow',{**ref,'inputs':{}},'/workflows/runtime_creation/execute')['run']
        self.assertEqual(run['status'],'paused_for_approval');self.assertFalse(self.http.calls)
        approval=run['approvals'][0]['approval_id']
        self.mutation('decide_approval',{**ref,'approval_id':approval,'decision':'approved'},'/approvals/'+approval+'/decision')
        run=self.client.get('/runs/'+run['run_id']).json()['data']['run'];self.assertEqual(run['status'],'completed')
        self.assertEqual(self.http.write_count,1)
        events=self.client.get('/runs/'+run['run_id']+'/events').json()['data']['items']
        result=next(e['details']['output'] for e in events if e['event_type']=='node.completed' and e['details'].get('node_id')=='action')
        self.assertEqual(len(result['tabs']),6);self.assertEqual(result['spreadsheet_id'],'created_1')

    def test_rejected_creation_never_calls_google(self):
        ref=self.publish(tracking_workflow('project_demo','Demo',workflow_id='runtime_rejected'))
        run=self.mutation('execute_workflow',{**ref,'inputs':{}},'/workflows/runtime_rejected/execute')['run'];a=run['approvals'][0]['approval_id']
        self.mutation('decide_approval',{**ref,'approval_id':a,'decision':'rejected'},'/approvals/'+a+'/decision')
        self.assertFalse(self.http.calls)

    def test_creation_disabled_by_default_and_config_flag_is_typed(self):
        with tempfile.TemporaryDirectory(dir=STATE_ROOT) as path:
            app=create_extension_app({'enabled_providers':['google_sheets']},Path(path),token_supplier=lambda scopes,timeout:'offline')
            items=app.state.workflow_service.registry.list_tools(app.state.extension_auth)['data']['items']
            setup=[i for i in items if i['tool_id'] in {'extension_sheets_create','extension_sheets_add_tabs'}]
            self.assertEqual(len(setup),2);self.assertTrue(all(i['definition']['availability']=='disabled' for i in setup))
            self.assertFalse((Path(path)/'sheet-resources.sqlite3').exists())
        with self.assertRaises(ValueError):create_extension_app({'sheet_creation_enabled':'yes'},self.root)

    def test_creation_without_dedicated_gate_or_literal_setup_fails_review(self):
        service=self.app.state.workflow_service;auth=self.app.state.extension_auth
        w=tracking_workflow('project_demo','Demo');w['nodes']=[n for n in w['nodes'] if n['node_id']!='review'];w['edges'][0]={'edge_id':'direct','source':'start','target':'action'}
        with self.assertRaises(Exception):service.configuration_validator(w)
        w=tracking_workflow('project_demo','Demo');next(n for n in w['nodes'] if n['node_id']=='action')['configuration']={'input_mapping':{'title':'inputs.title'}}
        with self.assertRaises(Exception):service.configuration_validator(w)
        self.assertFalse(self.http.calls)
