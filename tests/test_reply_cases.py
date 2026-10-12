"""Reply correlation, durable deduplication and explicit notification checks."""
from email.message import EmailMessage
from pathlib import Path
from tempfile import TemporaryDirectory
import json
import unittest

from workflow_api.reply_cases import ReplyCases
from workflow_api.storage import WorkflowStore


class ReplyCaseTests(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.store = WorkflowStore(Path(self.temp.name) / 'cases.sqlite3')
        with self.store.transaction() as db:
            db.execute('CREATE TABLE runtime_runs (workspace TEXT, run_id TEXT, document TEXT)')
            workflow = {'workflow_id': 'restaurant', 'version': 1,
                        'metadata': {'email_recipient_policy': {'mode': 'source_row', 'field': 'email'}},
                        'nodes': [{'node_id': 'send', 'tool_id': 'smtp_send_email', 'configuration': {
                            'input_mapping': {'to': 'inputs.row.email', 'subject': "'Order update'", 'body': "'We checked your order.'"}}}]}
            self.store.put(db, 'workspace', workflow)
            run = {'run_id': 'run_one', 'workflow_id': 'restaurant', 'workflow_version': 1, 'status': 'completed',
                   'inputs': {'row': {'review_id': 'R101', 'order_id': 'O501', 'email': 'customer@example.com',
                                      'complaint': 'Cold food'}},
                   'outputs': {'send': {'message_id': '<original@agentic-ai-builder.local>'}}}
            db.execute('INSERT INTO runtime_runs VALUES (?,?,?)', ('workspace', 'run_one', json.dumps(run)))
        self.sent = []
        sent = self.sent
        class SMTP:
            def __init__(self, *args, **kwargs): pass
            def __enter__(self): return self
            def __exit__(self, *args): pass
            def ehlo(self): pass
            def starttls(self, context): pass
            def login(self, user, password): pass
            def send_message(self, message):
                sent.append(message)
                return {}
        class Model:
            def __init__(self): self.responses = self
            def create(self, **kwargs):
                self.text = kwargs['input'][1]['content']
                return type('Response', (), {'output_text': json.dumps({
                    'decision': 'resolution_confirmed' if 'resolved' in self.text else 'manager_review',
                    'reason': 'Customer response reviewed.', 'customer_followup': 'We will look into this.'})})()
        self.cases = ReplyCases(self.store, 'boss@example.com', 'test-password', 'boss@example.com',
                                Model(), 'test-model', smtp_factory=SMTP)
        self.cases.sync_sent_runs('workspace')

    def email(self, sender, body, in_reply_to='<original@agentic-ai-builder.local>'):
        message = EmailMessage()
        message['From'] = sender
        message['To'] = 'boss@example.com'
        message['Message-ID'] = '<customer-reply@example.com>'
        message['In-Reply-To'] = in_reply_to
        message.set_content(body)
        return message.as_bytes()

    def test_matching_sender_and_thread_deduplicates_reply(self):
        self.assertFalse(self.cases.accept_message('workspace', 'boss@example.com', '1', '10',
                                                   self.email('stranger@example.com', 'Issue unresolved')))
        self.assertFalse(self.cases.accept_message('workspace', 'boss@example.com', '1', '11',
                                                   self.email('customer@example.com', 'Issue unresolved', '<other@example.com>')))
        reply = self.email('customer@example.com', 'Packaging was intact but food was cold.')
        self.assertTrue(self.cases.accept_message('workspace', 'boss@example.com', '1', '12', reply))
        self.assertFalse(self.cases.accept_message('workspace', 'boss@example.com', '1', '12', reply))
        self.assertFalse(self.cases.accept_message('workspace', 'boss@example.com', '1', '15', reply))
        case = self.cases.list_cases('workspace')[0]
        self.assertEqual(case['status'], 'Needs manager review')
        self.assertEqual(len(case['replies']), 1)
        self.assertEqual(case['replies'][0]['previews']['manager_notice']['to'], 'boss@example.com')

    def test_closure_requires_confirmed_latest_reply_and_sends_boss_once(self):
        self.cases.accept_message('workspace', 'boss@example.com', '1', '12',
                                  self.email('customer@example.com', 'Thanks, the issue is resolved.'))
        case = self.cases.list_cases('workspace')[0]
        self.assertEqual(case['status'], 'Awaiting closure confirmation')
        reply_id = case['replies'][0]['reply_id']
        self.cases.send_action('workspace', case['case_id'], reply_id, 'confirm_closure')
        self.assertEqual(self.cases.list_cases('workspace')[0]['status'], 'Closed')
        self.assertEqual(self.sent[0]['To'], 'boss@example.com')
        with self.assertRaisesRegex(ValueError, 'LATEST_OPEN_REPLY_REQUIRED'):
            self.cases.send_action('workspace', case['case_id'], reply_id, 'confirm_closure')
        self.assertEqual(len(self.sent), 1)

    def test_unresolved_reply_cannot_close_and_followup_threads(self):
        self.cases.accept_message('workspace', 'boss@example.com', '1', '13',
                                  self.email('customer@example.com', 'Still cold.'))
        case = self.cases.list_cases('workspace')[0]
        reply_id = case['replies'][0]['reply_id']
        with self.assertRaisesRegex(ValueError, 'RESOLUTION_NOT_CONFIRMED'):
            self.cases.send_action('workspace', case['case_id'], reply_id, 'confirm_closure')
        self.cases.send_action('workspace', case['case_id'], reply_id, 'customer_followup')
        self.assertEqual(self.sent[0]['To'], 'customer@example.com')
        self.assertEqual(self.sent[0]['In-Reply-To'], '<original@agentic-ai-builder.local>')
        second = self.email('customer@example.com', 'Issue still unresolved', self.sent[0]['Message-ID'])
        second = second.replace(b'<customer-reply@example.com>', b'<second-reply@example.com>')
        self.assertTrue(self.cases.accept_message('workspace', 'boss@example.com', '1', '14', second))
        self.assertEqual(len(self.cases.list_cases('workspace')[0]['replies']), 2)


if __name__ == '__main__':
    unittest.main()
