from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from datetime import datetime, timezone
import json
import sqlite3
import tempfile
import unittest
from connector_extension.procurement.store import ProcurementStore, ProcurementError, ROOT, STATE_ROOT, scope_digest

FIXTURES={r['record_id']:r for r in json.loads((ROOT/'contracts/v1/examples.json').read_text())}
NOW=datetime(2026,10,13,3,35,tzinfo=timezone.utc)


class StoreTests(unittest.TestCase):
    def setUp(self):
        STATE_ROOT.mkdir(parents=True,exist_ok=True)
        self.temp=tempfile.TemporaryDirectory(dir=STATE_ROOT)
        self.store=self.open();self.counter=0
        records=[deepcopy(FIXTURES[i]) for i in ('project_demo','evidence_demo','item_demo','vendor_demo')]
        records[0]['data']['status']='DRAFT';records[2]['data']['status']='EXTRACTED';records[3]['data']['status']='NEEDS_REVIEW'
        self.commit(records)

    def tearDown(self):self.temp.cleanup()
    def open(self, trusted=True):
        return ProcurementStore(self.temp.name,currency_precision={'INR':2},clock=lambda:NOW,
            approval_check=(lambda approval,target,operation:True) if trusted else None)
    def get(self,i):return self.store.get('workspace_demo','project_demo',i)
    def commit(self,records,**kw):
        self.counter+=1
        return self.store.commit('workspace_demo','project_demo','transaction_'+str(self.counter),
            [{'record':r,'expected_revision':r['revision']-1} for r in records],**kw)
    def update(self,i,status=None,**values):
        r=self.get(i);r['revision']+=1;r['updated_at']='2026-10-13T09:05:00+05:30'
        if status:r['data']['decision' if r['record_type']=='approval' else 'status']=status
        r['data'].update(values);self.commit([r]);return r
    def assert_code(self,code,fn):
        with self.assertRaises(ProcurementError) as caught:fn()
        self.assertEqual(caught.exception.code,code)
    def quote_ready(self):
        self.update('item_demo','READY');self.update('vendor_demo','ACTIVE')
        self.update('project_demo','VALIDATING');self.update('project_demo','ACTIVE')
        r=deepcopy(FIXTURES['rfq_demo']);r['data'].update(status='DRAFT',scope_digest=scope_digest([self.get('item_demo')]))
        self.commit([r])
        for state in ('READY','SENT','OPEN'):self.update('rfq_demo',state)
        r=deepcopy(FIXTURES['quote_demo']);r['data'].update(status='RECEIVED',rfq_revision=4,scope_digest=self.get('rfq_demo')['data']['scope_digest']);self.commit([r])
        self.update('quote_demo','VALIDATING');self.update('quote_demo','QUALIFYING')
    def order_ready(self):
        self.quote_ready()
        records=[deepcopy(FIXTURES[i]) for i in ('approval_demo','approval_award_demo')]
        for r in records:r['data']['decision']='PENDING'
        records[1]['data']['operation']='award_order'
        self.commit(records)
        for i in ('approval_demo','approval_award_demo'):self.update(i,'APPROVED')
        a=deepcopy(FIXTURES['award_demo']);a['data'].update(status='PROPOSED',quotation_revision=3);self.commit([a])
        self.update('award_demo','APPROVED')
        p=deepcopy(FIXTURES['po_demo']);p['data']['status']='DRAFT'
        p['evidence_ids']=['evidence_demo']
        p['data']['items'][0]['specifications']=self.get('item_demo')['data']['specifications']
        for key in ('packed_quantity','dispatched_quantity','delivered_quantity','buyer_accepted_quantity'):p['data']['items'][0][key]='0'
        self.commit([p]);self.update('po_demo','READY');self.update('po_demo','RELEASED')
        e=deepcopy(FIXTURES['evidence_demo']);e['record_id']='evidence_supplier';e['data'].update(source_id='supplier_fixture',asserted_actor_role='SUPPLIER')
        self.commit([e]);self.event('ACCEPTED');self.update('po_demo','ACCEPTED')
    def event(self,stage):
        e=deepcopy(FIXTURES['event_demo']);e['record_id']='event_'+stage.lower();e['evidence_ids']=['evidence_supplier']
        e['data'].update(event_kind=stage,source_message_id='supplier_fixture',idempotency_key='supplier_'+stage)
        self.commit([e])
    def delivered(self):
        self.order_ready()
        for state,field in (('PACKED','packed_quantity'),('DISPATCHED','dispatched_quantity'),('DELIVERED','delivered_quantity')):
            self.event(state)
            p=self.get('po_demo');p['revision']+=1;p['data']['status']=state;p['data']['items'][0][field]='2';self.commit([p])
    def closed(self):
        self.delivered()
        event=deepcopy(FIXTURES['event_demo']);event['evidence_ids']=['evidence_demo'];event['data'].update(event_kind='BUYER_RECEIPT_CONFIRMED',actor_role='BUYER',source_message_id='simulation_fixture')
        p=self.get('po_demo');p['revision']+=1;p['data'].update(status='CLOSED',buyer_receipt_confirmed=True,
            buyer_acceptance_confirmed=True,resolution_confirmed=True,buyer_confirmation_evidence_ids=['evidence_demo'])
        p['data']['items'][0]['buyer_accepted_quantity']='2';self.commit([event,p])

    def test_restart_retry_retains_history_and_sync(self):
        p=self.get('project_demo');p['revision']+=1;p['data']['status']='VALIDATING'
        changes=[{'record':p,'expected_revision':1}]
        intent={'key':'sync_demo','record_id':'project_demo','record_revision':2,'target':'sheets','payload':{'status':'VALIDATING'}}
        link={'record_id':'project_demo','provider':'google_sheets','resource_type':'spreadsheet','resource_id':'book_demo','metadata':{'owned':False}}
        result=self.store.commit('workspace_demo','project_demo','stable',changes,resources=[link],sync_intents=[intent])
        reopened=self.open();self.assertEqual(result,reopened.commit('workspace_demo','project_demo','stable',changes,resources=[link],sync_intents=[intent]))
        self.assertEqual(len(reopened.history('workspace_demo','project_demo')),5)
        self.assertEqual(reopened.pending_sync('workspace_demo','project_demo')[0]['status'],'PENDING_APPROVAL')
        self.assertEqual(reopened.resources('workspace_demo','project_demo')[0]['resource_id'],'book_demo')
        self.assertEqual(reopened.get('workspace_demo','project_demo','project_demo',1)['data']['status'],'DRAFT')
    def test_same_key_changed_content_is_rejected(self):
        p=self.get('project_demo');p['revision']+=1;p['data']['name']='new'
        changes=[{'record':p,'expected_revision':1}];self.store.commit('workspace_demo','project_demo','stable',changes)
        changes[0]['record']['data']['name']='changed'
        self.assert_code('TRANSACTION_KEY_MISMATCH',lambda:self.store.commit('workspace_demo','project_demo','stable',changes))
    def test_stale_concurrent_revision_has_one_winner(self):
        p=self.get('project_demo');p['revision']+=1
        def write(key):
            try:return self.open().commit('workspace_demo','project_demo',key,[{'record':p,'expected_revision':1}])
            except ProcurementError as e:return e.code
        with ThreadPoolExecutor(2) as pool:out=list(pool.map(write,['race_one','race_two']))
        self.assertEqual(sum(isinstance(r,dict) for r in out),1);self.assertIn('REVISION_CONFLICT',out)
    def test_bad_reference_rolls_back_entire_batch(self):
        p=self.get('project_demo');p['revision']+=1;p['data']['name']='must rollback'
        v=self.get('vendor_demo');v['revision']+=1;v['data']['contact_evidence_ids']=['missing_evidence']
        self.assert_code('REFERENCE_NOT_FOUND',lambda:self.commit([p,v]));self.assertEqual(self.get('project_demo')['revision'],1)
    def test_sync_failure_rolls_back_record(self):
        p=self.get('project_demo');p['revision']+=1
        self.assert_code('SYNC_INTENT_INVALID',lambda:self.commit([p],sync_intents=[{'bad':'intent'}]));self.assertEqual(self.get('project_demo')['revision'],1)
    def test_scope_isolation(self):
        self.assertIsNone(self.store.get('another_workspace','project_demo','project_demo'))
        p=self.get('project_demo');p['revision']+=1;p['workspace_id']='another_workspace'
        self.assert_code('SCOPE_MISMATCH',lambda:self.commit([p]))
    def test_illegal_and_initial_transitions(self):
        self.assert_code('ILLEGAL_TRANSITION',lambda:self.update('project_demo','COMPLETED'))
        r=deepcopy(FIXTURES['rfq_demo']);self.assert_code('INITIAL_STATE_REQUIRED',lambda:self.commit([r]))
    def test_duplicate_evidence_and_immutable_history(self):
        r=self.get('evidence_demo');r['record_id']='evidence_copy'
        self.assert_code('DUPLICATE_SOURCE',lambda:self.commit([r]));self.assertIsNone(self.get('evidence_copy'))
        r=self.get('evidence_demo');r['revision']+=1
        self.assert_code('IMMUTABLE_EVIDENCE',lambda:self.commit([r]))
    def test_verified_label_does_not_establish_trust(self):
        r=self.get('evidence_demo');r['record_id']='evidence_new';r['data'].update(source_id='different',authority_state='VERIFIED_SOURCE',verified_subject_id='buyer_demo')
        self.assert_code('TRUSTED_EVIDENCE_REQUIRED',lambda:self.commit([r]))
    def test_approval_requires_trusted_adapter(self):
        r=deepcopy(FIXTURES['approval_demo']);r['data']['decision']='PENDING';self.commit([r]);self.store=self.open(False)
        self.assert_code('TRUSTED_APPROVAL_REQUIRED',lambda:self.update('approval_demo','APPROVED'))
    def test_quote_arithmetic_scope_deadline_and_compliance(self):
        self.quote_ready()
        for code,mutate in (
            ('LINE_TOTAL_INVALID',lambda d:d['items'][0].update(line_total='1')),
            ('QUOTE_SCOPE_MISMATCH',lambda d:d.update(rfq_revision=1)),
            ('QUOTE_DEADLINE_INVALID',lambda d:d.update(valid_until='2020-01-01')),
            ('COMPLIANCE_EVIDENCE_REQUIRED',lambda d:d.update(compliance_evidence_ids=[]))):
            r=self.get('quote_demo');r['revision']+=1;mutate(r['data']);self.assert_code(code,lambda:self.commit([r]))
    def test_incomplete_quote_cannot_win(self):
        self.quote_ready();self.update('quote_demo','SUPERSEDED')
        a=deepcopy(FIXTURES['award_demo']);a['data'].update(status='PROPOSED',quotation_revision=4,approval_id=None)
        self.assert_code('QUOTE_NOT_QUALIFYING',lambda:self.commit([a]))
    def test_single_offer_is_not_competitive_lowest(self):
        self.quote_ready();a=deepcopy(FIXTURES['award_demo']);a['data'].update(status='PROPOSED',quotation_revision=3,approval_id=None,selection_basis='LOWEST_QUALIFYING_TOTAL')
        self.assert_code('SINGLE_OFFER_REQUIRES_EXCEPTION',lambda:self.commit([a]))
    def test_delivered_is_not_closed(self):
        self.delivered();p=self.get('po_demo');p['revision']+=1;p['data'].update(status='CLOSED',buyer_receipt_confirmed=True,
            buyer_acceptance_confirmed=True,resolution_confirmed=True,buyer_confirmation_evidence_ids=['evidence_demo']);p['data']['items'][0]['buyer_accepted_quantity']='2'
        self.assert_code('BUYER_CONFIRMATION_REQUIRED',lambda:self.commit([p]));self.assertEqual(self.get('po_demo')['data']['status'],'DELIVERED')
    def test_closure_and_project_completion_are_durable(self):
        self.closed();self.update('project_demo','COMPLETED',resolved_item_ids=['item_demo'])
        self.assertEqual(self.open().get('workspace_demo','project_demo','po_demo')['data']['status'],'CLOSED')
        self.assert_code('TERMINAL_RECORD',lambda:self.update('po_demo','CLOSED'))
    def test_project_cannot_claim_unclosed_coverage(self):
        self.quote_ready();self.assert_code('PROJECT_SCOPE_UNRESOLVED',lambda:self.update('project_demo','COMPLETED',resolved_item_ids=['item_demo']))
    def test_quantities_cannot_exceed_order_or_regress(self):
        self.order_ready();p=self.get('po_demo');p['revision']+=1;p['data']['status']='PACKED';p['data']['items'][0]['packed_quantity']='3'
        self.assert_code('QUANTITY_ORDER_INVALID',lambda:self.commit([p]))
        self.event('PACKED');p['data']['items'][0]['packed_quantity']='2';self.commit([p])
        p=self.get('po_demo');p['revision']+=1;p['data']['items'][0]['packed_quantity']='1'
        self.assert_code('QUANTITY_REGRESSION',lambda:self.commit([p]))
    def test_supplier_claim_without_event_cannot_advance(self):
        self.order_ready();p=self.get('po_demo');p['revision']+=1;p['data']['status']='PACKED';p['data']['items'][0]['packed_quantity']='2'
        self.assert_code('SUPPLIER_EVENT_REQUIRED',lambda:self.commit([p]))
    def test_duplicate_event_cannot_apply_twice(self):
        self.order_ready();self.event('PACKED');e=self.get('event_packed');e['record_id']='event_duplicate'
        self.assert_code('DUPLICATE_SOURCE',lambda:self.commit([e]))
    def test_approval_expiry_and_revocation(self):
        r=deepcopy(FIXTURES['approval_demo']);r['data']['decision']='PENDING';self.commit([r])
        self.assert_code('TRUSTED_APPROVAL_REQUIRED',lambda:self.update('approval_demo','APPROVED',expires_at='2020-01-01T00:00:00Z'))
        self.update('approval_demo','APPROVED');self.update('approval_demo','REVOKED')
        self.assertEqual(self.get('approval_demo')['data']['decision'],'REVOKED')
    def test_simulation_cannot_be_enabled_on_existing_project(self):
        self.assert_code('SIMULATION_MODE_IMMUTABLE',lambda:self.update('project_demo',simulation=False))
    def test_hold_resumes_only_to_saved_state(self):
        self.order_ready();self.update('po_demo','ON_HOLD',resume_status='ACCEPTED',unresolved_exception_ids=['issue_demo'])
        self.assert_code('ILLEGAL_TRANSITION',lambda:self.update('po_demo','PACKED',resume_status=None,unresolved_exception_ids=[]))
        self.update('po_demo','ACCEPTED',resume_status=None,unresolved_exception_ids=[])
    def test_real_project_cannot_close_with_simulation_roles(self):
        self.closed()
        records={r['record_id']:r for r in self.store.list_records('workspace_demo','project_demo')}
        records['project_demo']['data']['simulation']=False
        self.assert_code('BUYER_CONFIRMATION_REQUIRED',lambda:self.store.guards(records['po_demo'],records))
    def test_missing_currency_precision_blocks_actionable_state(self):
        self.update('project_demo','VALIDATING');self.store=ProcurementStore(self.temp.name,clock=lambda:NOW)
        self.assert_code('CURRENCY_NOT_CONFIGURED',lambda:self.update('project_demo','ACTIVE'))
    def test_changed_specification_invalidates_quote_selection(self):
        self.quote_ready();self.update('item_demo',specifications='Changed requirement')
        a=deepcopy(FIXTURES['award_demo']);a['data'].update(status='PROPOSED',quotation_revision=3,approval_id=None)
        self.assert_code('STALE_REQUIREMENTS',lambda:self.commit([a]))
    def test_database_has_foreign_keys_and_private_permissions(self):
        self.assertEqual(self.store.path.stat().st_mode&0o777,0o600)
        with self.store.connection() as db:
            self.assertEqual(db.execute('PRAGMA foreign_keys').fetchone()[0],1)
            self.assertEqual(db.execute('PRAGMA foreign_key_check').fetchall(),[])
            self.assertEqual(db.execute('PRAGMA integrity_check').fetchone()[0],'ok')
    def test_outside_state_is_rejected(self):
        self.assert_code('STATE_PATH_INVALID',lambda:ProcurementStore('/tmp/procurement_unscoped'))

if __name__=='__main__':unittest.main()
