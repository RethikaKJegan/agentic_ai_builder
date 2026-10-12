"""Discovery and automatic customer reply handling; no live email or Google writes."""
from copy import deepcopy
from io import BytesIO
import json
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from tests.test_reply_cases import ReplyCaseTests
from runtime.connectors import GoogleSheetsConnector
from workflow_api.reply_cases import ReplyCases
from workflow_api.sheet_discovery import spreadsheet_references, validate_discovered_setup
from planner.errors import PlannerFailure


class DiscoveryTests(unittest.TestCase):
    @patch('runtime.connectors._google_credentials', return_value=SimpleNamespace(token='test-only'))
    def test_actual_titles_headers_and_ranges_are_discovered_read_only(self, credentials):
        responses = [BytesIO(json.dumps({'properties':{'title':'Factory'}, 'sheets':[
            {'properties':{'title':"Customer's concerns", 'gridProperties':{'columnCount':26,'rowCount':1000}}},
            {'properties':{'title':'Quality records', 'gridProperties':{'columnCount':26,'rowCount':200}}}]}).encode()),
            BytesIO(json.dumps({'values':[[], ['Ticket','Contact Email','Concern','Lot'], ['T1','customer@example.com','Leak','B1']]}).encode()),
            BytesIO(json.dumps({'values':[['Lot','Notes'],['B1','Sample passed']]}).encode())]
        with patch('runtime.connectors.urlopen', side_effect=responses) as network:
            catalog = GoogleSheetsConnector(lambda _: {}, '/tmp/test-token').discover('https://docs.google.com/spreadsheets/d/test-sheet/edit')
        self.assertEqual(catalog['tables'][0]['range'], "'Customer''s concerns'!A2:D1000")
        self.assertEqual(catalog['tables'][1]['headers'], ['Lot','Notes'])
        self.assertTrue(all(c.args[0].get_method() == 'GET' for c in network.call_args_list))
        workflow = {'metadata':{'trigger_templates':[{'provider_id':'google_sheets','resource_id':'test-sheet',
            'poll_input':{'range':catalog['tables'][0]['range'],'identity_field':'Ticket','required_fields':['Ticket','Contact Email']}}],
            'email_recipient_policy':{'mode':'source_row','field':'Contact Email'}, 'sheet_read_targets':[
                {'spreadsheet_id':'test-sheet','range':catalog['tables'][1]['range']}]}}
        validate_discovered_setup(workflow, [catalog])
        workflow['metadata']['trigger_templates'][0]['poll_input']['identity_field'] = 'invented_id'
        with self.assertRaises(PlannerFailure):
            validate_discovered_setup(workflow, [catalog])

    def test_links_are_extracted_without_business_role_rules(self):
        self.assertEqual(spreadsheet_references('Handle complaints using https://docs.google.com/spreadsheets/d/another-sheet/edit'), ['another-sheet'])


class AutomaticReplyTests(unittest.TestCase):
    def setUp(self):
        fixture = ReplyCaseTests()
        fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        self.fixture, self.store, self.sent, self.cases = fixture, fixture.store, fixture.sent, fixture.cases
        with self.store.transaction() as db:
            workflow = self.store.get(db,'workspace','restaurant',1)
            workflow['metadata']['customer_automation'] = {'mode':'automatic','manager_email':'manager@example.com',
                'case_fields':{'identity':'Ticket','reference':'Lot','complaint':'Concern'},
                'close_on_customer_confirmation':True,'instructions':'Handle concerns, follow up and escalate unresolved cases.'}
            workflow['metadata']['email_recipient_policy']['field'] = 'Contact Email'
            workflow['nodes'][0]['configuration']['input_mapping']['to'] = 'inputs.row["Contact Email"]'
            self.store.put(db,'workspace',workflow)
            raw = json.loads(db.execute('SELECT document FROM runtime_runs').fetchone()[0])
            raw['inputs']['row'] = {'Ticket':'C104','Lot':'B2401','Concern':'Loose lids','Contact Email':'customer@example.com'}
            db.execute('UPDATE runtime_runs SET document=?',(json.dumps(raw),))
            db.execute('DELETE FROM customer_cases')
        class Model:
            def __init__(self): self.responses=self; self.calls=[]; self.missing_evidence=False
            def create(self, **kwargs):
                payload=json.loads(kwargs['input'][1]['content']); self.calls.append(payload)
                body=payload['customer_reply']
                decision='resolution_confirmed' if body=='The issue is resolved. Thank you.' else 'manager_review' if 'manager' in body else 'unresolved'
                return SimpleNamespace(output_text=json.dumps({'action':'finish','decision':decision,
                    'reason':'Customer response reviewed.','customer_followup':'Thank you for the update. We will follow up with the next steps.',
                    'resolution_evidence':body if decision=='resolution_confirmed' and not self.missing_evidence else ''}))
        self.model=Model()
        self.cases.model=self.model; self.cases.automatic_enabled=True; self.cases.active_check=lambda *_: True
        self.cases.sync_sent_runs('workspace')

    def accept(self, body, uid='12', ref='<original@agentic-ai-builder.local>'):
        raw=self.fixture.email('customer@example.com',body,ref).replace(b'<customer-reply@example.com>', ('<reply-'+uid+'@example.com>').encode())
        return self.cases.accept_message('workspace','boss@example.com','1',uid,raw)

    def test_escalation_and_closure_run_without_manual_clicks_and_do_not_duplicate(self):
        self.assertTrue(self.accept('Please ask the manager to review the issue.'))
        self.assertFalse(self.model.calls)
        self.assertEqual(self.cases.process_pending('workspace'),1)
        self.assertEqual([m['To'] for m in self.sent],['customer@example.com','manager@example.com'])
        self.assertEqual(self.sent[0]['In-Reply-To'],'<reply-12@example.com>')
        self.assertIn('Loose lids',self.sent[1].get_content())
        self.assertEqual(self.cases.list_cases('workspace')[0]['status'],'Needs manager review')
        self.cases.process_pending('workspace')
        self.assertEqual(len(self.sent),2)
        self.assertTrue(self.accept('The issue is resolved. Thank you.','13',self.sent[0]['Message-ID']))
        self.cases.process_pending('workspace')
        self.assertEqual(self.cases.list_cases('workspace')[0]['status'],'Closed')
        self.assertEqual(self.sent[-1]['To'],'manager@example.com')
        self.assertTrue(str(self.sent[-1]['Subject']).startswith('Case closed: C104'))

    def test_restart_drains_persisted_job_and_missing_confirmation_does_not_close(self):
        self.accept('The issue is resolved. Thank you.')
        self.model.missing_evidence=True
        restarted=ReplyCases(self.store,'boss@example.com','test-password','boss@example.com',self.model,'test-model',
            smtp_factory=self.cases.smtp_factory,automatic_enabled=True,active_check=lambda *_:True)
        restarted.process_pending('workspace')
        self.assertEqual(restarted.list_cases('workspace')[0]['status'],'Needs manager review')
        self.assertEqual([m['To'] for m in self.sent],['manager@example.com'])

    def test_disabled_workflow_and_auto_responses_send_nothing(self):
        self.accept('The issue remains unresolved.')
        self.cases.active_check=lambda *_:False
        self.cases.process_pending('workspace')
        self.assertFalse(self.sent)
        self.assertEqual(self.cases.list_cases('workspace')[0]['replies'][0]['job']['error_code'],'AUTOMATION_NOT_ACTIVE')
        raw=self.fixture.email('customer@example.com','Out of office').replace(b'From:',b'Auto-Submitted: auto-replied\nFrom:',1)
        self.assertFalse(self.cases.accept_message('workspace','boss@example.com','1','20',raw))

    def test_uncertain_submission_is_never_automatically_repeated(self):
        original=self.cases.smtp_factory
        class Uncertain(original):
            def send_message(inner,message):
                self.sent.append(message)
                raise RuntimeError('Connection dropped')
        self.cases.smtp_factory=Uncertain
        self.accept('The issue is still unresolved.')
        self.cases.process_pending('workspace'); self.cases.process_pending('workspace')
        self.assertEqual(len(self.sent),1)
        reply=self.cases.list_cases('workspace')[0]['replies'][0]
        self.assertEqual(reply['actions']['customer_followup'],'submission_uncertain')
        self.assertEqual(reply['job']['error_code'],'SMTP_DELIVERY_UNCERTAIN')

    def test_master_can_request_fresh_published_evidence_before_deciding(self):
        reader_calls=[]
        self.cases.evidence_reader=lambda case,requests: reader_calls.append(requests) or [{'rows':[['Lot','Notes'],['B2401','Checked']]}]
        previous=self.model.create
        def create(**kwargs):
            payload=json.loads(kwargs['input'][1]['content'])
            if not payload['read_results']:
                return SimpleNamespace(output_text=json.dumps({'action':'read','read_requests':[{
                    'spreadsheet_id':'test-sheet','range':'Quality!A1:B100','match_column':'Lot','source_column':'Lot'}]}))
            return previous(**kwargs)
        self.model.create=create
        self.accept('Please ask the manager to inspect the latest records.')
        self.cases.process_pending('workspace')
        self.assertEqual(len(reader_calls),1)
        self.assertEqual(self.model.calls[0]['read_results'][0]['rows'][1],['B2401','Checked'])
        self.assertEqual(self.cases.list_cases('workspace')[0]['replies'][0]['model_calls'],2)
