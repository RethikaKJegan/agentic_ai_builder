from copy import deepcopy
import base64
from email import message_from_bytes
import json
from pathlib import Path
import re
import tempfile
import unittest
from urllib.parse import urlparse,unquote
from fastapi.testclient import TestClient
from connector_extension.app import create_extension_app,STATE_ROOT
from connector_extension.transport import COOKIE
from connector_extension.tests.test_sheet_creation import OfflineSheets
from connector_extension.procurement.store import ProcurementError

CONFIG={'enabled_providers':['google_sheets','gmail'],'sheet_creation_enabled':True,
        'procurement_enabled':True,'procurement_currency_precision':{'INR':2}}
PLAN={'project_id':'project_four','name':'Four-item simulation','simulation':True,
      'context':{'description':'Four supplied requirements','delivery_location':'Demo warehouse',
                 'delivery_deadline':'2099-12-31','quote_deadline':'2099-11-01T12:00:00Z',
                 'time_zone':'Asia/Kolkata','comparison_currency':'INR'},
      'requirements':{'spreadsheet_url':'https://docs.google.com/spreadsheets/d/requirements_book/edit',
          'range':'Requirements!A1:F100','columns':{'item_id':'ID','section':'Category','description':'Product',
              'quantity':'Qty','unit':'Unit','specifications':'Specs'}},
      'vendors':{'spreadsheet_url':'https://docs.google.com/spreadsheets/d/vendors_book/edit',
          'range':'Contacts!A1:D100','columns':{'vendor_id':'ID','name':'Supplier','email':'Email','item_categories':'Categories'}}}


class Providers(OfflineSheets):
    def __init__(self):
        super().__init__();self.drafts=[];self.fail_draft=False
        self.add_book('requirements_book',{'Requirements':['ID','Category','Product','Qty','Unit','Specs']})
        self.books['requirements_book']['sheets'][0]['business_rows']=[
            ['item_pipe','Piping','Pipes',20,'pieces','Test pipe specification'],
            ['item_valve','Piping','Valves',10,'pieces','Test valve specification'],
            ['item_pump','Equipment','Pumps',2,'pieces','Test pump specification'],
            ['item_helmet','Safety','Helmets',15,'pieces','Test helmet specification']]
        self.add_book('vendors_book',{'Contacts':['ID','Supplier','Email','Categories']})
        self.books['vendors_book']['sheets'][0]['business_rows']=[
            ['vendor_a','Piping A','a@example.com','Piping'],['vendor_b','Piping B','b@example.com','Piping'],
            ['vendor_c','Equipment C','c@example.com','Equipment'],['vendor_d','Safety D','d@example.com','Safety']]
    def request(self,method,url,headers,body=None,timeout=30):
        parsed=urlparse(url);path=unquote(parsed.path)
        if '/users/me/' in path:
            self.calls.append({'method':method,'url':url,'body':deepcopy(body)})
            if path.endswith('/profile'):return {'emailAddress':'buyer@example.com'}
            if path.endswith('/drafts') and method=='POST':
                self.write_count+=1
                self.drafts.append(message_from_bytes(base64.urlsafe_b64decode(body['message']['raw'])))
                if self.fail_draft:raise TimeoutError('Uncertain draft response')
                n=len(self.drafts);return {'id':'draft_'+str(n),'message':{'id':'message_'+str(n),'threadId':'thread_'+str(n)}}
            raise AssertionError('Unexpected Gmail operation')
        if '/values/' in path and method=='GET':
            self.calls.append({'method':method,'url':url,'body':deepcopy(body)})
            identifier=path.split('/spreadsheets/')[1].split('/')[0];cellrange=path.split('/values/')[1]
            title=cellrange.rsplit('!',1)[0].strip("'");table=next(t for t in self.books[identifier]['sheets'] if t['properties']['title']==title)
            return {'values':[deepcopy(table['headers']),*deepcopy(table['business_rows'])]}
        if path.endswith('/values:batchUpdate') and method=='POST':
            self.calls.append({'method':method,'url':url,'body':deepcopy(body)});self.write_count+=1
            identifier=path.split('/spreadsheets/')[1].split('/')[0]
            for cell in body['data']:
                title,coordinate=cell['range'].rsplit('!',1);title=title.strip("'")
                table=next(t for t in self.books[identifier]['sheets'] if t['properties']['title']==title)
                match=re.fullmatch(r'([A-Z]+)(\d+)',coordinate);row=int(match[2])-2;column=0
                for char in match[1]:column=column*26+ord(char)-64
                while len(table['business_rows'])<=row:table['business_rows'].append(['']*len(table['headers']))
                table['business_rows'][row][column-1]=cell['values'][0][0]
            return {'totalUpdatedCells':len(body['data'])}
        return super().request(method,url,headers,body,timeout)


class SliceTests(unittest.TestCase):
    def setUp(self):
        STATE_ROOT.mkdir(parents=True,exist_ok=True);self.temp=tempfile.TemporaryDirectory(dir=STATE_ROOT)
        self.http=Providers();self.plan=deepcopy(PLAN);self.sequence=0;self.start()
    def tearDown(self):self.client.close();self.temp.cleanup()
    def start(self):
        self.app=create_extension_app(CONFIG,Path(self.temp.name),transport=self.http,token_supplier=lambda scopes,timeout:'offline')
        self.service=self.app.state.procurement_service;self.auth=self.app.state.extension_auth
        self.client=TestClient(self.app);session=self.client.get('/session');self.client.cookies.set(COOKIE,session.cookies[COOKIE],path='/')
    def request(self,operation,payload,path):
        self.sequence+=1
        return self.client.post(path,json={'request_id':'req_slice','operation':operation,
            'idempotency_key':'slice_request_'+str(self.sequence),'payload':payload})
    def setup(self):
        r=self.request('procurement_setup',self.plan,'/procurement/projects');self.assertEqual(r.status_code,200,r.text);return r.json()['data']
    def advance(self):return self.service.advance(self.plan['project_id'],self.auth)
    def approve(self,state,decision='approved'):
        action=next(a for a in state['actions'].values() if a['state']=='paused_for_approval')
        approval=next(a for a in action['approvals'] if a['status']=='pending')
        r=self.request('decide_approval',{'workflow_id':action['workflow_id'],'workflow_version':1,
            'approval_id':approval['approval_id'],'decision':decision},'/approvals/'+approval['approval_id']+'/decision')
        self.assertEqual(r.status_code,200,r.text)
    def finish(self):
        state=self.setup()
        for _ in range(30):
            if state['phase']=='DRAFTS_READY':return state
            self.assertNotEqual(state['phase'],'STOPPED',state)
            self.approve(state);state=self.advance()
        self.fail('Coordinator did not finish bounded slice')

    def test_four_item_slice_runs_actual_adapters_and_preserves_sources(self):
        before=deepcopy(self.http.books);state=self.setup()
        self.assertEqual(state['phase'],'TRACKING',state)
        self.assertEqual(state['record_counts'],{'project':1,'boq_item':4,'vendor':4,'rfq':4})
        self.assertEqual(self.http.write_count,0)
        state=self.finish();self.assertEqual(self.http.books['requirements_book'],before['requirements_book'])
        self.assertEqual(self.http.books['vendors_book'],before['vendors_book']);self.assertEqual(len(self.http.drafts),4)
        book=self.http.books['created_1'];self.assertEqual([s['properties']['title'] for s in book['sheets']],['BOQ','Vendors','RFQs','Quotations','Orders','Activity'])
        self.assertEqual([len(s['business_rows']) for s in book['sheets']],[4,4,4,0,0,0])
        self.assertTrue(all(i['status']=='CONFIRMED' for i in state['sync_intents']))
        self.assertTrue(all(r['data']['status']=='READY' for r in state['records'] if r['record_type']=='rfq'))
        self.assertEqual({m['To'] for m in self.http.drafts},{'a@example.com','b@example.com','c@example.com','d@example.com'})
        self.assertTrue(all(m['Subject'].startswith('[SIMULATION] RFQ') for m in self.http.drafts))
        counts=self.http.write_count;self.advance();self.setup();self.assertEqual(self.http.write_count,counts)
    def test_restart_keeps_pending_run_and_does_not_duplicate(self):
        state=self.setup();run=state['actions']['tracking']['run_id'];self.client.close();self.start()
        state=self.advance();self.assertEqual(state['actions']['tracking']['run_id'],run);self.assertEqual(self.http.write_count,0)
        self.assertEqual(self.finish()['phase'],'DRAFTS_READY');self.assertEqual(len(self.http.drafts),4)
    def test_missing_quantity_is_persisted_and_stops_all_writes(self):
        self.http.books['requirements_book']['sheets'][0]['business_rows'][0][3]=''
        state=self.setup();self.assertEqual(state['phase'],'NEEDS_CLARIFICATION',state)
        item=next(r for r in state['records'] if r['record_id']=='item_pipe');self.assertIsNone(item['data']['quantity'])
        self.assertEqual(item['data']['status'],'NEEDS_CLARIFICATION');self.assertEqual(self.http.write_count,0)
    def test_rejection_stops_without_mutation(self):
        state=self.setup();self.approve(state,'rejected');state=self.advance()
        self.assertEqual(state['phase'],'STOPPED');self.assertEqual(self.http.write_count,0)
    def test_authentication_scope_and_setup_change_are_denied(self):
        self.setup();p=deepcopy(self.plan);p['context']['delivery_location']='Changed'
        r=self.request('procurement_setup',p,'/procurement/projects');self.assertEqual(r.status_code,409)
        self.client.cookies.clear();self.assertEqual(self.client.get('/procurement/projects/project_four').status_code,401)
        wrong=deepcopy(self.auth);wrong['subject']['workspace_id']='other-workspace'
        with self.assertRaises(ProcurementError):self.service.advance('project_four',wrong)
    def test_ambiguous_or_missing_header_does_not_guess(self):
        self.plan['requirements']['columns']['quantity']='Nonexistent column'
        state=self.setup();self.assertEqual(state['phase'],'STOPPED');self.assertEqual(self.http.write_count,0)
    def test_unmatched_categories_stop_rfqs(self):
        self.http.books['vendors_book']['sheets'][0]['business_rows'][3][3]='Unrelated'
        state=self.setup();self.assertEqual(state['phase'],'NEEDS_CLARIFICATION');self.assertEqual(state['record_counts']['rfq'],0)
    def test_default_catalog_and_configuration_are_unchanged(self):
        with tempfile.TemporaryDirectory(dir=STATE_ROOT) as directory:
            app=create_extension_app({'enabled_providers':[]},Path(directory))
            self.assertFalse(hasattr(app.state,'procurement_service'))
            self.assertEqual(len(app.state.workflow_service.registry.list_tools(app.state.extension_auth)['data']['items']),19)
        with self.assertRaises(ValueError):create_extension_app({**CONFIG,'procurement_enabled':'yes'},Path(self.temp.name))
    def test_unknown_draft_result_is_frozen_without_replay(self):
        self.http.fail_draft=True;state=self.setup()
        for _ in range(25):
            if state['phase']=='STOPPED':break
            self.approve(state);state=self.advance()
        self.assertEqual(state['phase'],'STOPPED');self.assertEqual(len(self.http.drafts),1)
        writes=self.http.write_count;self.advance();self.service.tick();self.assertEqual(self.http.write_count,writes)
        self.client.close();self.start();self.advance();self.assertEqual(len(self.http.drafts),1)
    def test_sync_rejection_marks_target_and_stops(self):
        state=self.setup();self.approve(state);state=self.advance()
        self.assertEqual(state['phase'],'PROJECTIONS');self.approve(state,'rejected');state=self.advance()
        self.assertEqual(state['phase'],'STOPPED');self.assertIn('REJECTED',[i['status'] for i in state['sync_intents']])
        self.assertEqual(len(self.http.drafts),0)
    def test_ingestion_restart_after_commits_replays_same_revisions(self):
        self.setup();job=self.service.job('local-workspace','project_four');job.pop('ingested');self.service.save_job('local-workspace',job)
        before=len(self.service.store.history('local-workspace','project_four'))
        req=self.http.books['requirements_book']['sheets'][0];v=self.http.books['vendors_book']['sheets'][0]
        self.service.ingest('local-workspace','project_four',[req['headers'],*req['business_rows']],[v['headers'],*v['business_rows']])
        self.assertEqual(len(self.service.store.history('local-workspace','project_four')),before)
    def test_fabricated_ingestion_graph_cannot_publish(self):
        self.setup()
        from connector_extension.procurement.runtime_tools import ingestion_workflow
        job=self.service.job('local-workspace','project_four');w=ingestion_workflow(job['plan'],job['ingestion_workflow_id'])
        w['nodes'][3]['configuration']={'input':{'project_id':'project_four','requirements_rows':[],'vendor_rows':[]}}
        from planner.errors import PlannerFailure
        with self.assertRaises(PlannerFailure):self.app.state.workflow_service.configuration_validator(w)
    def test_unprivileged_setup_is_denied(self):
        auth=deepcopy(self.auth);auth['roles']=['viewer'];auth['permissions']=['workflow.view']
        from runtime.service import RuntimeFailure
        with self.assertRaises(RuntimeFailure):self.service.setup(self.plan,auth)
        self.assertEqual(self.http.write_count,0)
    def test_specialist_handoffs_and_worker_advance_are_recorded(self):
        state=self.setup();run=state['actions']['ingestion']['run_id']
        events=self.service.workflows.runtime_runner.runtime.events(run,self.auth)['items']
        self.assertGreaterEqual(sum(e['event_type']=='node.handoff' for e in events),2)
        self.approve(state);self.service.tick()
        self.assertEqual(self.service.status('local-workspace','project_four')['phase'],'PROJECTIONS')

if __name__=='__main__':unittest.main()
