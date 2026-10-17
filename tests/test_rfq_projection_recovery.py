from contextlib import nullcontext
from copy import deepcopy
import json
from types import SimpleNamespace
import unittest
from workflow_api.procurement_projection_recovery import RFQProjectionRecovery

class ProjectionRecoveryTests(unittest.TestCase):
    def setUp(self):
        self.fields={'status':'OPEN','gmail_message_id':'mail','gmail_thread_ids':'thread','revision':5}
        self.inputs={'spreadsheet_id':'book','range':"'RFQs'!A1:F20",'identity_column':'rfq_id','identity':'rfq_demo','fields':self.fields}
        self.intent={'key':'sent_rfq_demo','record_id':'rfq_demo','payload':{'inputs':self.inputs}}
        self.job={'phase':'STOPPED','issues':['runtime:failed'],'plan':{'project_id':'project'},'actions':{
            'sync_sent_rfq_demo':{'state':'failed','run_id':'failed','workflow_id':'wf','workflow_version':1},
            'send_rfq_demo':{'state':'completed','run_id':'sent'}}}
        self.record={'revision':5,'data':{'status':'OPEN','gmail_message_id':'mail','gmail_thread_ids':['thread']}}
        self.prior={'revision':2,'data':{'status':'READY','gmail_message_id':None,'gmail_thread_ids':[]}}
        self.rows=[['rfq_id',*self.fields],['rfq_demo','READY','','',2]]
        self.workflow={'nodes':[{'kind':'tool','tool_id':'google_sheets_upsert_record','configuration':{'input':self.inputs}}]}
        self.codes=['SHEETS_RECORD_FAILED'];self.saved=[];self.calls=[]
        owner=self
        class DB:
            def execute(self,*args):return SimpleNamespace(fetchone=lambda:(json.dumps(owner.workflow),))
        self.service=RFQProjectionRecovery();self.service.active=lambda *a:True;self.service.automatic=lambda *a:True
        self.service.store=SimpleNamespace(pending_sync=lambda *a:[self.intent],get=lambda *a:self.prior if len(a)==4 else self.record)
        self.service.workflows=SimpleNamespace(store=SimpleNamespace(transaction=lambda **k:nullcontext(DB())),runtime_runner=SimpleNamespace(runtime=SimpleNamespace(
            events=lambda *a:{'items':[{'event_type':'node.failed','details':{'error_code':c}} for c in self.codes]})))
        self.service.phase2_action=lambda *a:self.calls.append(a) or {'action':{'rows':self.rows}}
        self.service.save_job=lambda *a:self.saved.append(deepcopy(a[-1]))
    def test_unchanged_prior_row_resumes_without_send(self):
        self.assertTrue(self.service.recover_rfq_projection('ws',self.job,{}))
        self.assertEqual(self.job['phase'],'SENDING')
        self.assertEqual(self.job['actions']['sync_sent_rfq_demo']['run_id'],'failed')
        self.assertEqual(self.job['actions']['send_rfq_demo']['run_id'],'sent')
        self.assertEqual(self.calls[0][3],'google_sheets_read_rows')
    def test_applied_row_reconciles_and_second_failure_stops(self):
        self.rows[1]=['rfq_demo',*self.fields.values()]
        self.assertTrue(self.service.recover_rfq_projection('ws',self.job,{}))
        self.job['phase']='STOPPED';self.job['issues']=['runtime:failed']
        self.job['actions']['sync_sent_rfq_demo_reconcile1']=deepcopy(self.job['actions']['sync_sent_rfq_demo'])
        self.assertFalse(self.service.recover_rfq_projection('ws',self.job,{}))
    def test_authority_send_and_conflict_fail_closed(self):
        for case in ('permission','send','row','duplicate','input','inactive'):
            self.setUp()
            if case=='permission':self.codes=['SHEETS_ACCESS_DENIED']
            if case=='send':self.job['actions']['send_rfq_demo']['state']='failed'
            if case=='row':self.rows[1][1]='MANUALLY_EDITED'
            if case=='duplicate':self.rows.append(self.rows[1][:])
            if case=='input':self.workflow['nodes'][0]['configuration']['input']={'identity':'different'}
            if case=='inactive':self.service.active=lambda *a:False
            with self.subTest(case=case):
                self.assertFalse(self.service.recover_rfq_projection('ws',self.job,{}));self.assertEqual(self.saved,[])

    def test_recovery_is_bound_to_the_original_projection_revision(self):
        self.workflow['nodes'][0]['tool_id']='extension_mail_send'
        self.assertFalse(self.service.recover_rfq_projection('ws',self.job,{}))
        self.assertEqual(self.calls,[])
