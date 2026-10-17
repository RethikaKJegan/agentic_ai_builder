"""Native MESH generation/publication/runtime with offline Google providers."""
from copy import deepcopy
from io import BytesIO
import base64
from email import message_from_bytes
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch
from fastapi.testclient import TestClient
from connector_extension.tests.test_procurement_slice import Providers, PLAN, CONFIG
from connector_extension.google import GoogleAPI
from workflow_api.live_providers import create_configured_app
from workflow_api.main import COOKIE
from workflow_api.procurement import ProcurementPlanner, validate_plan
from connector_extension.procurement.store import ProcurementError

ROOT=Path(__file__).resolve().parents[1]


class ProcurementProviders(Providers):
    def __init__(self):super().__init__();self.sent=[];self.unknown_send=False
    def request(self,method,url,headers,body=None,timeout=30):
        if url.endswith('/messages/send'):
            self.sent.append(message_from_bytes(base64.urlsafe_b64decode(body['raw'])))
            if self.unknown_send:raise TimeoutError('unknown send')
            n=len(self.sent);return {'id':'sent_'+str(n),'threadId':'sent_thread_'+str(n)}
        return super().request(method,url,headers,body,timeout)


class IntegratedTests(unittest.TestCase):
    def setUp(self):
        root=ROOT/'.local/connector-extension';root.mkdir(exist_ok=True)
        self.temp=tempfile.TemporaryDirectory(dir=root);self.addCleanup(self.temp.cleanup);self.path=Path(self.temp.name)
        self.http=ProcurementProviders();self.sequence=0
        (self.path/'token.json').write_text('{}');(self.path/'config.json').write_text(json.dumps(CONFIG))
        self.env=dict(OPENAI_API_KEY='offline',OPENAI_MODEL='gpt-5.6-luna',GMAIL_SMTP_USER='owner@example.com',
            GMAIL_SMTP_PASSWORD='offline',GOOGLE_TOKEN_FILE=str(self.path/'token.json'),BUILDER_EMAIL_RECIPIENTS='owner@example.com',
            BUILDER_PROCUREMENT_ENABLED='1',BUILDER_PROCUREMENT_CONFIG=str(self.path/'config.json'),
            BUILDER_PROCUREMENT_STATE=str(self.path/'native'))
        self.catalogs=[{'spreadsheet_id':name,'tables':[{'title':t['properties']['title'],
            'range':t['properties']['title']+'!A1:'+('F' if name=='requirements_book' else 'D')+'1000',
            'header_row':1,'headers':t['headers']} for t in book['sheets']]} for name,book in self.http.books.items()]
        raw=deepcopy(PLAN);raw.pop('project_id')
        for kind,fields in [('requirements',['item_id','section','description','quantity','unit','specifications','delivery_location','delivery_deadline']),
                            ('vendors',['vendor_id','name','email','item_categories'])]:
            raw[kind]['columns']={key:raw[kind]['columns'].get(key) for key in fields}
        self.sdk=SimpleNamespace(responses=SimpleNamespace(create=lambda **kw:SimpleNamespace(output_text=json.dumps(raw),status='completed')))
        self.patches=[patch('workflow_api.live_providers.REGISTRY',self.path/'registry.json'),
            patch('connector_extension.google.GoogleAPI',side_effect=lambda token:GoogleAPI(lambda scopes,timeout:'offline',self.http)),
            patch('runtime.connectors._google_credentials',return_value=SimpleNamespace(token='offline',scopes=['https://www.googleapis.com/auth/spreadsheets'])),
            patch('runtime.connectors.urlopen',side_effect=self.urlopen)]
        for p in self.patches:p.start();self.addCleanup(p.stop)
        self.start()
    def urlopen(self,request,timeout):
        body=json.loads(request.data) if request.data else None
        return BytesIO(json.dumps(self.http.request(request.get_method(),request.full_url,{},body,timeout)).encode())
    def model_factory(self, definition):
        from runtime.model import BoundedLLM
        def provider(messages, cap, timeout):
            if definition.get('hierarchy_role') == 'master':
                content = next(m['content'] for m in messages if 'Return only a JSON object.\n' in m['content'])
                context, _ = json.JSONDecoder().raw_decode(content.split('Return only a JSON object.\n',1)[1].lstrip())
                if not context['results'] and not getattr(self,'skip_reviews',False):
                    result = {'action':'delegate', 'reason':'Review actual source records before preparation.', 'tasks':[
                        {'agent_id':a['agent_id'], 'inputs':context['request'], 'reason':a['goal']} for a in context['available_agents']]}
                else:
                    result = {'action':'finish', 'reason':'Both source reviews returned.', 'output':{'summary':'Source records reviewed; deterministic validation controls preparation.'}}
            else:
                result = {'summary':'Reviewed the original source records without changing values.'}
            return json.dumps(result), 100, 50
        return BoundedLLM(definition, provider, lambda messages:1000, 0, 0)

    def start(self):
        self.app=create_configured_app({**self.env, 'BUILDER_ENVIRONMENT': 'test', 'BUILDER_DEV_AUTH': '1'},self.path/'workflows.sqlite3',client=self.sdk,model_factory=self.model_factory)
        self.service=self.app.state.workflow_service;self.auth=self.app.state.live_operator_auth
        self.service.planner.provider.discoverer=lambda ref:next(c for c in self.catalogs if c['spreadsheet_id']==ref)
        self.procurement=self.app.state.procurement_service
        self.client=TestClient(self.app);self.addCleanup(self.client.close)
        r=self.client.get('/session');self.client.cookies.set(COOKIE,r.cookies[COOKIE],path='/')
    def call(self,operation,payload):
        self.sequence+=1
        r=self.service.handle({'request_id':'req_native','operation':operation,'idempotency_key':'native_'+str(self.sequence),'payload':payload},self.auth)
        self.assertEqual(r['status'],200,r);return r['data']
    def prepare(self):
        w=self.call('plan_workflow',{'objective':'Procurement RFQ simulation from https://docs.google.com/spreadsheets/d/requirements_book/edit and https://docs.google.com/spreadsheets/d/vendors_book/edit',
            'context':{'execution_input_mode':'automatic'}})['workflow']
        self.plan=w['metadata']['procurement_plan'];self.ref={'workflow_id':w['workflow_id'],'workflow_version':1}
        self.call('save_workflow_version',{**self.ref,'base_version':0,'workflow':w})
        self.call('validate_workflow',self.ref)
        self.call('approve_workflow',{**self.ref,'action':'approve'})
        self.call('approve_workflow',{**self.ref,'action':'publish'})
        activation=self.service.lifecycle.activate({'request_id':'activate','idempotency_key':'native_activate','payload':{**self.ref,'triggers':[]}},self.auth)
        self.release_id=activation['release']['release_id']
        run=self.call('execute_workflow',{**self.ref,'inputs':{}})['run']
        self.assertEqual(run['status'],'completed',run)
        return self.procurement.status('local-workspace',self.plan['project_id'])
    def approve(self,state,decision='approved'):
        action=next(a for a in state['actions'].values() if a['state']=='paused_for_approval')
        approval=next(a for a in action['approvals'] if a['status']=='pending')
        self.call('decide_approval',{'workflow_id':action['workflow_id'],'workflow_version':1,
            'approval_id':approval['approval_id'],'decision':decision})
    def advance(self):return self.procurement.advance(self.plan['project_id'],self.auth)
    def to_sending(self):
        state=self.prepare()
        for _ in range(25):
            if state['phase']=='SENDING':return state
            self.assertNotEqual(state['phase'],'STOPPED',state['issues'])
            self.approve(state);state=self.advance()
        self.fail('Preparation did not finish')
    def test_native_prompt_to_approved_sends_and_tracking(self):
        before=deepcopy(self.http.books);state=self.to_sending()
        self.assertEqual(len(self.http.drafts),4);self.assertEqual(len(self.http.sent),0)
        ingestion = state['actions']['ingestion']
        events = self.service.runtime_runner.runtime.events(ingestion['run_id'],self.auth)['items']
        self.assertEqual(len([e for e in events if e['event_type']=='agent.spawned']),2)
        observed = next(e['details']['observation'] for e in events if e['event_type']=='node.observed' and e['details'].get('node_id')=='master')
        self.assertIn('requirements_rows',observed)
        self.assertIn('vendor_rows',observed)
        for kind in ('delegated_task','delegated_result'):
            self.assertEqual(len([e for e in events if e['event_type']=='node.handoff' and e['details'].get('transfer_kind')==kind]),2)
        self.assertTrue(any(e['event_type']=='node.completed' and e['details'].get('node_id')=='master' for e in events))
        pending_ids={k:a['run_id'] for k,a in state['actions'].items()}
        self.start();state=self.advance()
        self.assertEqual({k:a['run_id'] for k,a in state['actions'].items()},pending_ids)
        for _ in range(12):
            if state['phase']=='RFQS_SENT':break
            self.approve(state);state=self.advance()
            self.assertNotEqual(state['phase'],'STOPPED',state['issues'])
        self.assertEqual(state['phase'],'RFQS_SENT')
        self.assertEqual(len(self.http.sent),4)
        self.assertEqual({m['To'] for m in self.http.sent},{'a@example.com','b@example.com','c@example.com','d@example.com'})
        self.assertTrue(all(r['data']['status']=='OPEN' and r['data']['gmail_message_id'] for r in state['records'] if r['record_type']=='rfq'))
        self.assertTrue(all(i['status']=='CONFIRMED' for i in state['sync_intents']))
        self.assertEqual(self.http.books['requirements_book'],before['requirements_book'])
        self.assertEqual(self.http.books['vendors_book'],before['vendors_book'])
        status=self.client.get('/procurement/projects/'+self.plan['project_id']);self.assertEqual(status.status_code,200)
        self.advance();self.assertEqual(len(self.http.sent),4)
        self.start();self.advance();self.assertEqual(len(self.http.sent),4)
    def test_rejected_send_never_submits(self):
        state=self.to_sending();self.approve(state,'rejected');state=self.advance()
        self.assertEqual(state['phase'],'STOPPED');self.assertEqual(self.http.sent,[])
    def test_unknown_send_is_frozen_and_not_replayed(self):
        state=self.to_sending();self.http.unknown_send=True;self.approve(state);state=self.advance()
        self.assertEqual(state['phase'],'STOPPED');self.assertEqual(len(self.http.sent),1)
        self.advance();self.assertEqual(len(self.http.sent),1)
    def test_parent_disable_stops_coordinator(self):
        state=self.prepare();before=self.http.write_count
        self.service.lifecycle.disable({'request_id':'disable','idempotency_key':'disable_native','payload':{
            'workflow_id':self.ref['workflow_id'],'expected_release_id':self.release_id}},self.auth)
        self.advance();self.assertEqual(self.http.write_count,before)
        self.approve(state)
        self.assertEqual(self.http.write_count,before)
    def test_fabricated_ingestion_cannot_validate(self):
        state=self.prepare();job=self.procurement.job('local-workspace',self.plan['project_id'])
        from connector_extension.procurement.runtime_tools import ingestion_workflow
        w=ingestion_workflow(self.plan,job['ingestion_workflow_id']);w['nodes'][3]['configuration']={'input':{
            'project_id':self.plan['project_id'],'requirements_rows':[],'vendor_rows':[]}}
        with self.assertRaises(ProcurementError):self.service.configuration_validator(w)
    def test_master_cannot_skip_required_reviews(self):
        self.skip_reviews=True
        state=self.prepare()
        self.assertEqual(state['phase'],'STOPPED')
        self.assertEqual(state['record_counts']['boq_item'],0)
        self.assertEqual(self.http.write_count,0)

    def test_disabled_procurement_returns_a_canonical_setup_error(self):
        from workflow_api.main import create_app
        with TestClient(create_app(dev_auth=True,database=self.path/'disabled.sqlite3',start_workers=False)) as client:
            session=client.get('/session');client.cookies.set(COOKIE,session.cookies[COOKIE],path='/')
            r=client.get('/procurement/projects/project_missing')
            self.assertEqual(r.status_code,503)
            self.assertEqual(r.json()['data']['error']['error_code'],'PROCUREMENT_UNAVAILABLE')

    def test_communication_preview_is_read_only_before_start(self):
        w=self.call('plan_workflow',{'objective':'Procurement RFQ from https://docs.google.com/spreadsheets/d/requirements_book/edit and https://docs.google.com/spreadsheets/d/vendors_book/edit',
            'context':{'execution_input_mode':'automatic'}})['workflow']
        self.call('save_workflow_version',{'workflow_id':w['workflow_id'],'workflow_version':1,'base_version':0,'workflow':w})
        r=self.client.get('/procurement/workflows/'+w['workflow_id']+'/1/communication')
        self.assertEqual(r.status_code,200,r.text)
        preview=r.json()['data']['workflow']
        self.assertEqual(len([a for a in preview['agents'] if a.get('hierarchy_role')=='sub_agent']),2)
        self.assertEqual(self.http.write_count,0)
        status=self.client.get('/procurement/projects/'+w['metadata']['procurement_plan']['project_id'])
        self.assertEqual(status.json()['data']['error']['error_code'],'PROCUREMENT_PROJECT_NOT_FOUND')

    def test_unknown_source_mapping_rejected(self):
        plan=deepcopy(PLAN);plan['requirements']['columns']['quantity']='Invented'
        with self.assertRaises(ProcurementError):validate_plan(plan,self.catalogs)


if __name__=='__main__':unittest.main()
