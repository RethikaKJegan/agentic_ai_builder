from copy import deepcopy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from fastapi.testclient import TestClient
from connector_extension.app import create_extension_app, STATE_ROOT, ROOT, configuration, state_directory
from connector_extension.catalog import CATALOG
from connector_extension.examples import connector_workflow
from connector_extension.tests.test_connectors import FakeTransport
from connector_extension.transport import COOKIE


class ExtensionApplicationTests(unittest.TestCase):
    def setUp(self):
        STATE_ROOT.mkdir(parents=True, exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(dir=STATE_ROOT)
        self.state = Path(self.temp.name)
        self.config = {'enabled_providers': ['google_sheets', 'google_calendar', 'gmail', 'brave_search'],
                      'sheet_reads': [{'spreadsheet_id': 'sheet_one', 'range': 'Items!A1:B10'}],
                      'calendars': ['primary'], 'mail_account': 'buyer@example.com', 'mail_recipients': ['vendor@example.com']}
        self.transport = FakeTransport()
        self.app = create_extension_app(self.config, self.state, transport=self.transport,
                                       token_supplier=lambda scopes, timeout: 'offline', search_key='offline-search-key')
        self.client = TestClient(self.app)
        session = self.client.get('/session')
        self.client.cookies.set(COOKIE, session.cookies[COOKIE], path='/')
    def tearDown(self): self.client.close(); self.temp.cleanup()
    def mutation(self, operation, payload, path, method='POST', key=None):
        key = key or operation + '_' + payload.get('workflow_id', 'test')
        result = self.client.request(method, path, json={'request_id': 'req_test', 'operation': operation,
            'idempotency_key': key, 'payload': payload})
        self.assertEqual(result.status_code, 200, result.text)
        return result.json()['data']
    def publish(self, tool_id, inputs, identity):
        workflow = connector_workflow(tool_id, inputs, identity)
        ref = {'workflow_id': identity, 'workflow_version': 1}
        saved = self.mutation('save_workflow_version', {**ref, 'base_version': 0, 'workflow': workflow}, f'/workflows/{identity}/versions/1', 'PUT')
        self.assertEqual(saved['workflow']['status'], 'draft')
        self.mutation('validate_workflow', ref, f'/workflows/{identity}/validate')
        self.mutation('approve_workflow', {**ref, 'action': 'approve'}, f'/workflows/{identity}/approve', key='approve_'+identity)
        self.mutation('approve_workflow', {**ref, 'action': 'publish'}, f'/workflows/{identity}/approve', key='publish_'+identity)
        return ref

    def test_registry_discovery_and_disabled_provider_readiness(self):
        response = self.client.get('/tools')
        self.assertEqual(response.status_code, 200)
        items = response.json()['data']['items']; self.assertEqual(len(items), 19)
        write = next(item for item in items if item['tool_id'] == 'google_sheets_upsert_record')
        self.assertEqual(write['definition']['availability'], 'enabled')
        response = self.client.post('/integrations/gmail/test').json()['data']
        self.assertTrue(response['configured']); self.assertFalse(response['tested'])
        self.assertFalse(self.transport.calls)

    def test_actual_calendar_connector_uses_runtime_approval_and_trace(self):
        event = {'summary': 'Quote deadline', 'start': {'date': '2026-11-01'}, 'end': {'date': '2026-11-02'}}
        ref = self.publish('extension_calendar_create', {'calendar_id': 'primary', 'event': event}, 'calendar_smoke')
        self.transport.responses.append({'id': 'event_1', 'status': 'confirmed'})
        result = self.mutation('execute_workflow', {**ref, 'inputs': {}}, '/workflows/calendar_smoke/execute')
        run = result['run']; self.assertEqual(run['status'], 'paused_for_approval'); self.assertFalse(self.transport.calls)
        approval = run['approvals'][0]
        self.mutation('decide_approval', {**ref, 'approval_id': approval['approval_id'], 'decision': 'approved'}, f"/approvals/{approval['approval_id']}/decision")
        response = self.client.get('/runs/'+run['run_id']).json()['data']['run']
        self.assertEqual(response['status'], 'completed'); self.assertEqual(len(self.transport.calls), 1)
        events = self.client.get('/runs/'+run['run_id']+'/events').json()['data']['items']
        action = next(e for e in events if e['event_type']=='node.completed' and e['details'].get('node_id')=='action')
        self.assertEqual(action['details']['output']['event_id'], 'event_1')
        self.assertTrue(any(e['event_type']=='node.handoff' for e in events))
        serialized = json.dumps(events); self.assertNotIn('offline-search-key', serialized); self.assertNotIn('Bearer', serialized)

    def test_actual_mail_send_rejection_prevents_provider_call(self):
        ref = self.publish('extension_mail_send', {'to':'vendor@example.com','subject':'RFQ','body':'Please quote'}, 'mail_smoke')
        run = self.mutation('execute_workflow', {**ref, 'inputs': {}}, '/workflows/mail_smoke/execute')['run']
        self.assertEqual(run['status'], 'paused_for_approval')
        approval = run['approvals'][0]
        self.mutation('decide_approval', {**ref,'approval_id':approval['approval_id'],'decision':'rejected'}, f"/approvals/{approval['approval_id']}/decision")
        self.assertEqual(self.client.get('/runs/'+run['run_id']).json()['data']['run']['status'],'rejected')
        self.assertFalse(self.transport.calls)

    def test_sheets_and_search_execute_through_real_registry(self):
        for tool_id,inputs,response,identity in [
            ('google_sheets_read_rows', {'spreadsheet_id':'sheet_one','range':'Items!A1:B10'}, {'values':[['id','qty'],['p1',2]]},'sheet_smoke'),
            ('extension_web_search', {'query':'pipe suppliers','limit':1}, {'web':{'results':[{'title':'Catalog','url':'https://example.com','description':'Sources'}]}},'search_smoke')]:
            ref=self.publish(tool_id,inputs,identity); self.transport.responses.append(response)
            run=self.mutation('execute_workflow',{**ref,'inputs':{}},f'/workflows/{identity}/execute')['run']
            self.assertEqual(run['status'],'completed')
        self.assertEqual(len(self.transport.calls),2)

    def test_extension_defaults_cannot_activate_unconfigured_providers(self):
        with tempfile.TemporaryDirectory(dir=STATE_ROOT) as directory:
            app=create_extension_app({'enabled_providers':[]},Path(directory))
            tools=app.state.workflow_service.registry.list_tools(app.state.extension_auth)['data']['items']
            self.assertTrue(all(item['definition']['availability']=='disabled' for item in tools))
            self.assertFalse(app.state.workflow_service.runtime_runner.connectors)
            self.assertFalse((Path(directory)/'google-token.json').exists())

    def test_state_paths_and_existing_databases_are_isolated(self):
        before={path:hashlib.sha256(path.read_bytes()).hexdigest() for path in [ROOT/'.env',ROOT/'token.json',ROOT/'credentials.json'] if path.exists()}
        with self.assertRaises(ValueError): state_directory(ROOT/'.local')
        with self.assertRaises(ValueError): state_directory(ROOT)
        with tempfile.TemporaryDirectory(dir=STATE_ROOT) as directory:
            app=create_extension_app({'enabled_providers':[]},Path(directory))
            self.assertEqual(Path(app.state.workflow_service.store.path),Path(directory)/'workflows.sqlite3')
            self.assertFalse((Path(directory)/'registry.json').exists())
        for path,fingerprint in before.items(): self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(),fingerprint)

    def test_untrusted_routes_origins_and_payload_authority_denied(self):
        response=self.client.get('/tools',headers={'origin':'https://outside.example'})
        self.assertEqual(response.status_code,403)
        response=self.client.get('/tools',headers={'host':'outside.example'})
        self.assertEqual(response.status_code,403)
        self.client.cookies.clear();self.assertEqual(self.client.get('/tools').status_code,401)

    def test_config_validation_and_optional_planner_catalog(self):
        for config in [{'enabled_providers':['unknown']},{'calendars':'primary'},{'secret':'raw'}, {'search_cost_per_call_usd':-1}]:
            with self.assertRaises(Exception): configuration(config)
        class Provider:
            contexts=[]
            def generate(self,objective,context):
                self.contexts.append(context)
                return connector_workflow('google_sheets_read_rows',{'spreadsheet_id':'sheet_one','range':'Items!A1:B10'},'planned_check')
        provider=Provider()
        with tempfile.TemporaryDirectory(dir=STATE_ROOT) as directory:
            app=create_extension_app(self.config,Path(directory),token_supplier=lambda scopes,timeout:'offline',planner_provider=provider)
            result=app.state.workflow_service.handle({'request_id':'req_plan','operation':'plan_workflow','idempotency_key':'planning_fixture',
                'payload':{'objective':'Read approved requirements'}},app.state.extension_auth)
            self.assertEqual(result['status'],200,result)
            self.assertIn('extension_calendar_create',provider.contexts[0]['available_tools'])
            self.assertIn('google_sheets_upsert_record',provider.contexts[0]['available_tools'])

    def test_actual_mail_send_approval_completes_with_mime_result(self):
        ref=self.publish('extension_mail_send',{'to':'vendor@example.com','subject':'RFQ','body':'Please quote'},'mail_approved')
        self.transport.responses.append({'id':'sent_1','threadId':'thread_1'})
        run=self.mutation('execute_workflow',{**ref,'inputs':{}},'/workflows/mail_approved/execute')['run']
        self.assertFalse(self.transport.calls)
        approval=run['approvals'][0]
        self.mutation('decide_approval',{**ref,'approval_id':approval['approval_id'],'decision':'approved'},f"/approvals/{approval['approval_id']}/decision")
        self.assertEqual(self.client.get('/runs/'+run['run_id']).json()['data']['run']['status'],'completed')
        self.assertTrue(self.transport.calls[0]['url'].endswith('/messages/send'))

    def test_actual_sheet_write_is_workflow_bound_and_approval_gated(self):
        target={'spreadsheet_id':'sheet_one','range':'BOQ!A1:C10','identity_column':'item_id','writable_columns':['quantity','status'],'allow_create':True}
        config={**self.config,'sheet_writes':[target]}
        transport=FakeTransport({'values':[['item_id','quantity','status'],['p1',1,'Open']]},{'totalUpdatedCells':1})
        with tempfile.TemporaryDirectory(dir=STATE_ROOT) as directory:
            app=create_extension_app(config,Path(directory),transport=transport,token_supplier=lambda scopes,timeout:'offline')
            service=app.state.workflow_service;auth=app.state.extension_auth
            workflow=connector_workflow('google_sheets_upsert_record',{'spreadsheet_id':'sheet_one','range':'BOQ!A1:C10',
                'identity_column':'item_id','identity':'p1','fields':{'status':'RFQ ready'}},'write_check',sheet_targets=[target])
            ref={'workflow_id':'write_check','workflow_version':1}
            def handle(operation,payload,key):
                result=service.handle({'request_id':'req_test','operation':operation,'idempotency_key':key,'payload':payload},auth)
                self.assertEqual(result['status'],200,result);return result['data']
            handle('save_workflow_version',{**ref,'base_version':0,'workflow':workflow},'save_write_check')
            handle('validate_workflow',ref,'validate_write_check')
            handle('approve_workflow',{**ref,'action':'approve'},'approve_write_check')
            run=handle('execute_workflow',{**ref,'inputs':{}},'execute_write_check')['run']
            self.assertEqual(run['status'],'paused_for_approval');self.assertFalse(transport.calls)
            handle('decide_approval',{**ref,'approval_id':run['approvals'][0]['approval_id'],'decision':'approved'},'decision_write_check')
            self.assertEqual(service.runtime_runner.runtime.get_run(run['run_id'],auth)['status'],'completed')
            self.assertEqual(len(transport.calls),2)

    def test_distinct_cookie_and_ui_copy_preserve_original_state(self):
        from connector_extension.launch_ui import prepare_ui
        self.assertEqual(COOKIE,'builder_extension_session')
        with tempfile.TemporaryDirectory() as directory:
            source=Path(directory)/'source';source.mkdir()
            (source/'node_modules').mkdir();(source/'.next').mkdir()
            (source/'package.json').write_text('{}');(source/'.env.local').write_text('private fixture')
            (source/'.next'/'live').write_text('keep')
            target=prepare_ui(self.state,source)
            self.assertTrue((target/'node_modules').is_symlink())
            self.assertFalse((target/'.env.local').exists());self.assertFalse((target/'.next').exists())
            self.assertEqual((source/'.next'/'live').read_text(),'keep')

    def test_new_writes_without_dedicated_action_gate_cannot_be_approved(self):
        workflow=connector_workflow('extension_calendar_create',{'calendar_id':'primary','event':{
            'summary':'Deadline','start':{'date':'2026-11-01'},'end':{'date':'2026-11-02'}}},'no_gate')
        workflow['approval_gates']=[];workflow['nodes']=[node for node in workflow['nodes'] if node['kind']!='approval']
        workflow['edges']=[{'edge_id':'start_action','source':'start','target':'action'},{'edge_id':'action_finish','source':'action','target':'finish'}]
        service,auth=self.app.state.workflow_service,self.app.state.extension_auth
        ref={'workflow_id':'no_gate','workflow_version':1}
        result=service.handle({'request_id':'req_test','operation':'save_workflow_version','idempotency_key':'save_no_gate',
                              'payload':{**ref,'base_version':0,'workflow':workflow}},auth)
        self.assertEqual(result['status'],200,result)
        result=service.handle({'request_id':'req_test','operation':'validate_workflow','idempotency_key':'validate_no_gate',
                              'payload':ref},auth)
        self.assertEqual(result['data']['error']['error_code'],'APPROVAL_REQUIRED');self.assertFalse(self.transport.calls)
