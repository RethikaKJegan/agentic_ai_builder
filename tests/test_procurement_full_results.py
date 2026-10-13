from contextlib import nullcontext
from copy import deepcopy
from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import patch

from workflow_api.procurement import IntegratedProcurement
from connector_extension.procurement.service import ProcurementService
from runtime.trace import snapshot

class FullResultsTests(TestCase):
    def service(self, run):
        self.auth={'subject':{'workspace_id':'workspace'}}
        self.seen=[]
        def load(db, identifier, auth):
            self.seen.append((identifier,auth))
            return deepcopy(run)
        service=IntegratedProcurement.__new__(IntegratedProcurement)
        service.automatic=lambda job:False
        service.workflows=SimpleNamespace(runtime_runner=SimpleNamespace(runtime=SimpleNamespace(
            store=SimpleNamespace(transaction=lambda:nullcontext(None)),load=load)))
        return service

    def test_complete_thread_retains_reply_omitted_from_trace(self):
        messages=[{'message_id':str(i),'text':'x'*2000} for i in range(20)]
        outputs={'action':{'messages':messages}}
        short=snapshot(outputs)
        self.assertLess(len(short['action']['messages']),len(messages))
        run={'status':'completed','workflow_id':'wf','workflow_version':1,'outputs':outputs}
        service=self.service(run);job={'actions':{'read':{'run_id':'run','workflow_id':'wf','workflow_version':1}}}
        with patch.object(ProcurementService,'run_action',return_value=short):
            result=service.run_action('workspace',job,'read',{},self.auth)
        self.assertEqual(result,outputs)
        self.assertEqual(result['action']['messages'][-1]['message_id'],'19')
        self.assertEqual(self.seen,[('run',self.auth)])
        result['action']['messages'].clear()
        self.assertEqual(len(run['outputs']['action']['messages']),20)

    def test_pending_action_does_not_read_outputs(self):
        service=self.service({})
        with patch.object(ProcurementService,'run_action',return_value=None):
            self.assertIsNone(service.run_action('workspace',{},'read',{},self.auth))
        self.assertEqual(self.seen,[])
