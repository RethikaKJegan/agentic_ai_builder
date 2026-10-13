import io
import json
import sqlite3
import tempfile
import unittest
from urllib.error import HTTPError
from runtime.service import RuntimeFailure
from connector_extension.common import JSONTransport, EffectJournal
from connector_extension.app import STATE_ROOT
from connector_extension.tests import test_procurement_slice as slice_tests
from connector_extension.procurement.store import ProcurementError


class DiagnosticsTests(unittest.TestCase):
    def test_http_status_and_safe_message_survive_without_full_body(self):
        def opener(request,timeout):
            raise HTTPError(request.full_url,400,'private',{},io.BytesIO(json.dumps({'error':{
                'status':'INVALID_ARGUMENT','message':'Metadata IDs must be positive.',
                'other_private_field':'do not store'}}).encode()))
        with tempfile.TemporaryDirectory(dir=STATE_ROOT) as root:
            journal=EffectJournal(root);transport=JSONTransport(opener)
            with self.assertRaises(RuntimeFailure) as caught:
                journal.perform('tool_test','effect_test',{},lambda:transport.request('POST','https://example.com/create',{},{}))
            self.assertEqual(caught.exception.code,'UNKNOWN_INVOCATION_RESULT')
            with sqlite3.connect(journal.path) as db:state,result=db.execute('SELECT state,result FROM effects').fetchone()
            self.assertEqual(state,'started');self.assertNotIn('other_private_field',result)
            self.assertEqual(json.loads(result)['provider_diagnostic']['http_status'],400)
            self.assertIn('Metadata IDs',json.loads(result)['provider_diagnostic']['message'])
            with self.assertRaises(RuntimeFailure):journal.perform('tool_test','effect_test',{},lambda:self.fail('Repeated write'))
    def test_secret_error_message_is_not_retained(self):
        def opener(request,timeout):
            raise HTTPError(request.full_url,401,'private',{},io.BytesIO(json.dumps({'error':{
                'status':'UNAUTHENTICATED','message':'Bearer sensitive-value'}}).encode()))
        with self.assertRaises(RuntimeFailure) as caught:JSONTransport(opener).request('GET','https://example.com',{})
        self.assertNotIn('message',caught.exception.provider_diagnostic)


class TrackingRecoveryTests(slice_tests.SliceTests):
    # Inherit the proven slice fixture helpers, but run only these recovery tests.
    def test_operator_retry_keeps_original_intent_and_has_a_fresh_gate(self):
        state=self.setup();old=state['actions']['tracking'];self.http.lose_write_response=True
        self.approve(state);state=self.advance();self.assertEqual(state['phase'],'STOPPED')
        writes=self.http.write_count
        state=self.service.retry_tracking(self.plan['project_id'],old['run_id'],True,self.auth)
        self.assertEqual(state['phase'],'TRACKING');self.assertEqual(self.http.write_count,writes)
        self.assertNotEqual(state['actions']['tracking']['run_id'],old['run_id'])
        self.assertEqual(state['actions']['tracking']['state'],'paused_for_approval')
        self.assertEqual(state['recovery_history'][0]['previous_run_id'],old['run_id'])
        self.service.retry_tracking(self.plan['project_id'],old['run_id'],True,self.auth)
        self.assertEqual(self.http.write_count,writes)
        with sqlite3.connect(self.service.store.path.parent/'effects.sqlite3') as db:
            self.assertEqual(db.execute("SELECT COUNT(*) FROM effects WHERE state='started'").fetchone()[0],1)
    def test_missing_operator_confirmation_is_rejected(self):
        state=self.setup();old=state['actions']['tracking'];self.http.lose_write_response=True;self.approve(state);self.advance()
        with self.assertRaises(ProcurementError) as caught:self.service.retry_tracking(self.plan['project_id'],old['run_id'],False,self.auth)
        self.assertEqual(caught.exception.code,'OPERATOR_ABSENCE_CONFIRMATION_REQUIRED')
    def test_known_returned_id_requires_readonly_reconciliation(self):
        state=self.setup();old=state['actions']['tracking'];self.http.fail_verification=True;self.approve(state);self.advance()
        with self.assertRaises(ProcurementError) as caught:self.service.retry_tracking(self.plan['project_id'],old['run_id'],True,self.auth)
        self.assertEqual(caught.exception.code,'TRACKING_RESOURCE_RECONCILIATION_REQUIRED')
    def test_confirmed_http_rejection_permits_fresh_gate_without_absence_claim(self):
        from runtime.service import RuntimeFailure
        original=self.http.request
        def rejected(method,url,headers,body=None,timeout=30):
            if method=='POST' and url.endswith('/spreadsheets'):raise RuntimeFailure('PROVIDER_HTTP_400','Rejected before creation',502)
            return original(method,url,headers,body,timeout)
        self.http.request=rejected
        state=self.setup();old=state['actions']['tracking'];self.approve(state);self.advance()
        state=self.service.retry_tracking(self.plan['project_id'],old['run_id'],False,self.auth)
        self.assertEqual(state['phase'],'TRACKING');self.assertEqual(self.http.write_count,0)
        self.assertFalse(state['recovery_history'][0]['absence_reported'])
        self.assertEqual(state['recovery_history'][0]['retry_basis'],'CONFIRMED_HTTP_400_REJECTION')


# Avoid re-running inherited base cases in this recovery-specific class.
for name in list(slice_tests.SliceTests.__dict__):
    if name.startswith('test_') and name not in TrackingRecoveryTests.__dict__:setattr(TrackingRecoveryTests,name,None)

if __name__=='__main__':unittest.main()
