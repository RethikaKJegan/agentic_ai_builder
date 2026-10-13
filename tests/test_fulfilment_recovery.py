import json
from copy import deepcopy
from types import SimpleNamespace
import unittest
from workflow_api.procurement_fulfilment import ProcurementFulfilment

class RecoveryTests(unittest.TestCase):
    def setUp(self):
        self.workflow={'tools':[],'nodes':[{'kind':'trigger'},{'kind':'agent'},{'kind':'output'}]}
        owner=self
        class DB:
            def __enter__(self):return self
            def __exit__(self,*args):pass
            def execute(self,*args):return SimpleNamespace(fetchone=lambda:(json.dumps(owner.workflow),))
        self.codes=['MODEL_OUTPUT_SCHEMA_INVALID'];self.saved=[]
        self.service=ProcurementFulfilment();self.service.active=lambda *args:True
        self.service.save_job=lambda *args:self.saved.append(deepcopy(args[-1]))
        self.service.workflows=SimpleNamespace(store=SimpleNamespace(transaction=DB),runtime_runner=SimpleNamespace(runtime=SimpleNamespace(
            events=lambda *args:{'items':[{'event_type':'node.failed','details':{'error_code':c}} for c in self.codes]})))
        self.job={'phase':'STOPPED','fulfilment_policy':{'revision':1},'issues':['runtime:failed'],'actions':{
            'ful_extract_demo':{'state':'failed','run_id':'run_demo','workflow_id':'wf_demo','workflow_version':1}}}
    def test_pure_schema_failure_is_recovered_once(self):
        self.assertTrue(self.service.recover_fulfilment_control('ws',self.job,{}))
        self.assertEqual(self.job['phase'],'FULFILMENT');self.assertEqual(self.job['fulfilment_recovered_actions'],['ful_extract_demo'])
        self.job['phase']='STOPPED';self.job['issues']=['runtime:failed']
        self.job['actions']['ful_extract_demo_control_repair1']=deepcopy(self.job['actions']['ful_extract_demo'])
        self.assertTrue(self.service.recover_fulfilment_control('ws',self.job,{}))
        self.job['phase']='STOPPED';self.job['issues']=['runtime:failed']
        self.job['actions']['ful_extract_demo_structured_control1']=deepcopy(self.job['actions']['ful_extract_demo'])
        self.assertFalse(self.service.recover_fulfilment_control('ws',self.job,{}))
    def test_mutations_and_policy_failures_never_recover(self):
        for case in ('tool','node','authorization','send'):
            with self.subTest(case=case):
                self.setUp()
                if case=='tool':self.workflow['tools']=[{'tool_id':'send_email'}]
                if case=='node':self.workflow['nodes'].append({'kind':'tool'})
                if case=='authorization':self.codes=['APPROVAL_REQUIRED']
                if case=='send':self.job['actions']['ful_notify_demo']=self.job['actions'].pop('ful_extract_demo')
                self.assertFalse(self.service.recover_fulfilment_control('ws',self.job,{}))
                self.assertEqual(self.saved,[])
