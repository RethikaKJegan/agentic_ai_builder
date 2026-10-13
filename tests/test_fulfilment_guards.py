from copy import deepcopy
import json
import unittest
from connector_extension.tests import test_procurement_store as fixture
from connector_extension.procurement.store import ProcurementError
from workflow_api.procurement import IntegratedProcurement

class FulfilmentGuardTests(unittest.TestCase):
    def setUp(self):
        self.fixture=fixture.StoreTests();self.fixture.setUp();self.addCleanup(self.fixture.tearDown)
        self.fixture.order_ready();self.service=object.__new__(IntegratedProcurement);self.service.store=self.fixture.store;self.service.model='offline'
        self.service.fulfilment_initialize();self.counter=0
        self.job={'plan':{'project_id':'project_demo','simulation':True},'prefix':'guard_test','actions':{},
            'fulfilment_policy':{'settings':{'allow_delivery_reschedule':False,'manager_email':'manager@example.com'}}}
    def packet(self,kind,quantity=None,role='SUPPLIER'):
        self.counter+=1;po=self.fixture.get('po_demo');line=po['data']['items'][0]
        output={'event_kind':kind,'items':[] if quantity is None else [{'item_id':line['item_id'],'quantity':quantity,'unit':line['unit']}],
            'quantity_mode':'cumulative','tracking_reference':'TRACK-001' if kind=='DISPATCHED' else None,
            'expected_delivery_date':None,'receipt_confirmed':role=='BUYER','acceptance_confirmed':role=='BUYER',
            'resolution_confirmed':role=='BUYER','note':'Explicit '+kind+' update.'}
        text=json.dumps(output);output['evidence']=[text]
        message={'message_id':'guard_message_'+str(self.counter),'thread_id':'guard_thread','from':'supplier@example.com',
            'received_at':fixture.NOW.isoformat(),'text':text}
        return po,message,output
    def apply(self,kind,quantity=None,role='SUPPLIER'):
        po,message,output=self.packet(kind,quantity,role)
        return self.service.apply_fulfilment('workspace_demo',self.job,po,message,role,output)
    def test_partial_progress_and_quantity_bounds(self):
        self.apply('PACKED','1');self.assertEqual(self.fixture.get('po_demo')['data']['status'],'PARTIALLY_PACKED')
        with self.assertRaises(ProcurementError):self.apply('DISPATCHED','2')
        self.assertEqual(self.fixture.get('po_demo')['data']['items'][0]['dispatched_quantity'],'0')
        self.apply('DISPATCHED','1');self.apply('DELIVERED','1')
        self.assertEqual(self.fixture.get('po_demo')['data']['status'],'PARTIALLY_DELIVERED')
        for kind in ('PACKED','DISPATCHED','DELIVERED'):self.apply(kind,'2')
        self.assertEqual(self.fixture.get('po_demo')['data']['status'],'DELIVERED')
    def test_exception_requires_buyer_resolution(self):
        self.apply('EXCEPTION_RAISED');po=self.fixture.get('po_demo')
        self.assertEqual(po['data']['status'],'ON_HOLD');self.assertTrue(po['data']['unresolved_exception_ids'])
        with self.assertRaises(ProcurementError):self.apply('EXCEPTION_RESOLVED',role='SUPPLIER')
        self.apply('EXCEPTION_RESOLVED',role='BUYER')
        self.assertEqual(self.fixture.get('po_demo')['data']['status'],'ACCEPTED')
        self.assertEqual(self.fixture.get('po_demo')['data']['unresolved_exception_ids'],[])
    def test_supplier_cannot_confirm_buyer_receipt(self):
        with self.assertRaises(ProcurementError) as caught:self.apply('BUYER_RECEIPT_CONFIRMED','2')
        self.assertEqual(caught.exception.code,'BUYER_CONFIRMATION_REQUIRED')
    def test_on_hold_requests_buyer_resolution_instead_of_closing(self):
        self.apply('EXCEPTION_RAISED');calls=[]
        self.job['fulfilment_policy']['settings']['buyer_email']='buyer@example.com'
        self.service.fulfilment_notice=lambda *args,**kwargs:(calls.append(args) or {'action':{}})
        po=self.fixture.get('po_demo')
        self.assertTrue(self.service.finish_order('workspace_demo',self.job,po,{}))
        self.assertEqual(calls[0][4],'buyer@example.com')
        self.assertEqual(self.fixture.get('po_demo')['data']['status'],'ON_HOLD')
    def test_duplicate_message_does_not_add_quantity_or_notify_twice(self):
        po,message,output=self.packet('PACKED','1');calls=[];notices=[]
        self.service.run_action=lambda *args:(calls.append(True) or {'action':output})
        self.service.fulfilment_notice=lambda *args,**kwargs:(notices.append(True) or {'action':{}})
        self.service.save_job=lambda *args:None
        for _ in range(2):self.service.process_fulfilment_message('workspace_demo',self.job,self.fixture.get('po_demo'),message,'SUPPLIER',{})
        self.assertEqual(self.fixture.get('po_demo')['data']['items'][0]['packed_quantity'],'1')
        self.assertEqual(len(calls),1);self.assertEqual(len(notices),1)

