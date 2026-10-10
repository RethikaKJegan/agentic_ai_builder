"""Slack DM -> durable release -> approval -> SMTP acceptance, offline only."""
from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace
import json
import tempfile
import unittest
from unittest.mock import patch

from workflow_api.slack_gmail import (create_configured_app, prepare_draft, operator_auth,
                                      authenticate, validate_settings, registry_configuration)
from workflow_api.slack_socket import SlackSocketReceiver
from workflow_api.scheduler import TriggerScheduler
from runtime.worker import RuntimeWorker

ROOT = Path(__file__).resolve().parents[1]


class FakeSMTP:
    messages = []
    def __init__(self, host, port, timeout):
        assert host == 'smtp.gmail.com' and port == 587 and timeout > 0
    def __enter__(self): return self
    def __exit__(self, *args): pass
    def ehlo(self): pass
    def starttls(self, context): pass
    def login(self, username, password):
        assert username and password
    def send_message(self, message):
        self.messages.append(message)
        return {}


class FakeSocket:
    def __init__(self):
        self.socket_mode_request_listeners = []
        self.acks = []
        self.connected = self.closed = False
    def connect(self): self.connected = True
    def close(self): self.closed = True
    def send_socket_mode_response(self, response): self.acks.append(response)


class SlackGmailTests(unittest.TestCase):
    def setUp(self):
        (ROOT / '.local/tests').mkdir(parents=True, exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(dir=ROOT / '.local/tests')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.settings = dict(team_id='T123', conversation_id='D123', sender_id='U123', recipient='owner@example.com')
        self.env = dict(SLACK_APP_TOKEN='xapp-test-only', GMAIL_SMTP_USER='owner@example.com', GMAIL_SMTP_PASSWORD='test-only')
        self.registry_patch = patch('workflow_api.slack_gmail.REGISTRY', self.root / 'registry.json')
        self.registry_patch.start()
        self.addCleanup(self.registry_patch.stop)
        self.app = create_configured_app(self.settings, self.env, self.root / 'workflows.sqlite3')
        self.service = self.app.state.workflow_service
        self.auth = operator_auth()
        prepare_draft(self.service, self.settings)
        self.ref = dict(workflow_id='slack-dm-gmail', workflow_version=1)
        self.approve_and_activate()
        self.socket = FakeSocket()
        self.receiver = SlackSocketReceiver(self.service, lambda w, s: authenticate(self.service, w, s), 'T123', 'D123', 'U123', client=self.socket)
        FakeSMTP.messages = []
        self.service.runtime_runner.connectors['smtp_send_email'].transport = FakeSMTP

    def call(self, operation, payload, key):
        result = self.service.handle(dict(request_id='req_' + key, operation=operation, idempotency_key=key, payload=payload), self.auth)
        self.assertEqual(result['status'], 200, result)
        return result['data']

    def approve_and_activate(self):
        self.call('validate_workflow', self.ref, 'validate_slack_draft')
        self.call('approve_workflow', {**self.ref, 'action': 'approve'}, 'approve_slack_draft')
        self.call('approve_workflow', {**self.ref, 'action': 'publish'}, 'publish_slack_draft')
        self.service.lifecycle.activate(dict(request_id='req_activate', idempotency_key='activate_slack_draft', payload={**self.ref, 'triggers': []}), self.auth)

    def event(self):
        return dict(type='event_callback', team_id='T123', event_id='Ev123', event=dict(type='message', channel_type='im', channel='D123', user='U123', text='A matching personal DM', ts='123.456'))

    def count(self, table):
        with self.service.store.transaction() as db:
            return db.execute('SELECT COUNT(*) FROM ' + table).fetchone()[0]

    def test_dm_approval_smtp_and_restart_deduplication(self):
        request = SimpleNamespace(type='events_api', envelope_id='envelope_123', payload=self.event())
        self.receiver.process(self.socket, request)
        self.assertEqual(self.socket.acks, [{'envelope_id': 'envelope_123'}])
        self.assertEqual(self.count('lifecycle_jobs'), 1)
        scheduler = TriggerScheduler(self.service, lambda w, s: authenticate(self.service, w, s))
        self.assertEqual(scheduler.tick()['dispatched'], 1)
        self.assertEqual(FakeSMTP.messages, [])
        with self.service.store.transaction() as db:
            run = json.loads(db.execute('SELECT document FROM runtime_runs').fetchone()[0])
        self.assertEqual(run['status'], 'paused_for_approval')
        approval_id = run['approvals'][0]['approval_id']
        # Restart while waiting for approval, reconstructing fresh Registry grants.
        self.service = create_configured_app(self.settings, self.env, self.root / 'workflows.sqlite3').state.workflow_service
        self.service.runtime_runner.connectors['smtp_send_email'].transport = FakeSMTP
        self.call('decide_approval', {**self.ref, 'approval_id': approval_id, 'decision': 'approved'}, 'approve_slack_email')
        worker = RuntimeWorker(self.service.runtime_runner, lambda w, s: authenticate(self.service, w, s))
        worker.drain()
        self.assertEqual(len(FakeSMTP.messages), 1)
        self.assertEqual(FakeSMTP.messages[0]['To'], self.settings['recipient'])
        self.assertIn('A matching personal DM', FakeSMTP.messages[0].get_content())
        self.assertEqual(self.service.runtime_runner.runtime.get_run(run['run_id'], self.auth)['status'], 'completed')
        restarted = create_configured_app(self.settings, self.env, self.root / 'workflows.sqlite3').state.workflow_service
        receiver = SlackSocketReceiver(restarted, lambda w, s: authenticate(restarted, w, s), 'T123', 'D123', 'U123')
        self.assertEqual(receiver.route(self.event()), 1)
        self.assertEqual(self.count('lifecycle_jobs'), 1)
        worker.drain()
        self.assertEqual(len(FakeSMTP.messages), 1)

    def test_wrong_team_channel_sender_and_bot_are_ignored(self):
        events = []
        for key, value in [('channel', 'DOTHER'), ('user', 'UOTHER'), ('channel_type', 'channel'), ('subtype', 'message_changed'), ('bot_id', 'B123')]:
            event = self.event(); event['event'][key] = value; events.append(event)
        event = self.event(); event['team_id'] = 'TOTHER'; events.append(event)
        for event in events:
            self.assertEqual(self.receiver.route(event), 0)
        self.assertEqual(self.count('lifecycle_jobs'), 0)

    def test_no_ack_on_storage_failure(self):
        request = SimpleNamespace(type='events_api', envelope_id='envelope_123', payload=self.event())
        with patch.object(self.service.lifecycle, 'ingest', side_effect=OSError('test-only')):
            self.receiver.process(self.socket, request)
        self.assertEqual(self.socket.acks, [])

    def test_setup_preserves_existing_revision(self):
        with self.service.store.transaction() as db:
            before = self.service.store.get(db, 'local-workspace', 'slack-dm-gmail')
        self.assertFalse(prepare_draft(self.service, self.settings))
        with self.service.store.transaction() as db:
            self.assertEqual(self.service.store.get(db, 'local-workspace', 'slack-dm-gmail'), before)

    def test_socket_lifecycle(self):
        self.receiver.start()
        self.assertTrue(self.socket.connected)
        self.assertEqual(self.socket.socket_mode_request_listeners, [self.receiver.process])
        self.receiver.stop()
        self.assertTrue(self.socket.closed)

    def test_recipient_restriction_and_missing_configuration(self):
        connector = self.service.runtime_runner.connectors['smtp_send_email']
        with self.service.store.transaction() as db:
            workflow = self.service.store.get(db, 'local-workspace', 'slack-dm-gmail')
        grant = self.service.registry_adapter.execution_assignments(workflow, self.auth)[0]
        with self.assertRaisesRegex(Exception, 'allowlisted'):
            connector.invoke(grant, dict(to='other@example.com', subject='Test', body='Test'), 'effect_1')
        self.assertEqual(FakeSMTP.messages, [])
        with self.assertRaisesRegex(ValueError, 'SLACK_APP_TOKEN'):
            create_configured_app(self.settings, {**self.env, 'SLACK_APP_TOKEN': ''}, self.root / 'other.sqlite3')
        with self.assertRaisesRegex(ValueError, 'GMAIL_SMTP'):
            registry_configuration({})
        with self.assertRaises(ValueError):
            validate_settings({**self.settings, 'conversation_id': 'C123'})

    def test_disable_stops_incoming_dispatch(self):
        with self.service.store.transaction() as db:
            release_id = db.execute('SELECT release_id FROM lifecycle_active').fetchone()[0]
        self.service.lifecycle.disable(dict(request_id='req_disable', idempotency_key='disable_slack_release', payload={'workflow_id': self.ref['workflow_id'], 'expected_release_id': release_id}), self.auth)
        self.assertEqual(self.receiver.route(self.event()), 0)
        self.assertEqual(self.count('lifecycle_jobs'), 0)

    def test_rejected_email_does_not_send(self):
        self.receiver.route(self.event())
        TriggerScheduler(self.service, lambda w, s: authenticate(self.service, w, s)).tick()
        with self.service.store.transaction() as db:
            run = json.loads(db.execute('SELECT document FROM runtime_runs').fetchone()[0])
        self.call('decide_approval', {**self.ref, 'approval_id': run['approvals'][0]['approval_id'], 'decision': 'rejected'}, 'reject_slack_email')
        RuntimeWorker(self.service.runtime_runner, lambda w, s: authenticate(self.service, w, s)).drain()
        self.assertEqual(FakeSMTP.messages, [])
        self.assertEqual(self.service.runtime_runner.runtime.get_run(run['run_id'], self.auth)['status'], 'rejected')

    def test_uncertain_smtp_submission_is_not_retried(self):
        self.receiver.route(self.event())
        TriggerScheduler(self.service, lambda w, s: authenticate(self.service, w, s)).tick()
        with self.service.store.transaction() as db:
            run = json.loads(db.execute('SELECT document FROM runtime_runs').fetchone()[0])
        self.call('decide_approval', {**self.ref, 'approval_id': run['approvals'][0]['approval_id'], 'decision': 'approved'}, 'approve_uncertain_email')
        class UncertainSMTP(FakeSMTP):
            def send_message(self, message):
                super().send_message(message)
                raise OSError('Connection lost after submission')
        self.service.runtime_runner.connectors['smtp_send_email'].transport = UncertainSMTP
        worker = RuntimeWorker(self.service.runtime_runner, lambda w, s: authenticate(self.service, w, s))
        worker.drain(); worker.drain()
        self.assertEqual(len(FakeSMTP.messages), 1)
        self.assertEqual(self.service.runtime_runner.runtime.get_run(run['run_id'], self.auth)['status'], 'blocked')

    def test_fastapi_startup_and_shutdown_use_real_lifecycle(self):
        from fastapi.testclient import TestClient
        receiver = SlackSocketReceiver(self.service, lambda w, s: authenticate(self.service, w, s), 'T123', 'D123', 'U123', client=self.socket)
        app = create_configured_app(self.settings, self.env, self.root / 'lifecycle.sqlite3', receiver_factory=lambda *args: receiver)
        with TestClient(app) as client:
            self.assertTrue(self.socket.connected)
            response = client.get('/session')
            self.assertEqual(response.status_code, 200)
            self.assertTrue(response.json()['data']['runtime_available'])
        self.assertTrue(self.socket.closed)
