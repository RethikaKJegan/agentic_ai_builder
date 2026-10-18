import base64
from copy import deepcopy
from datetime import datetime, timedelta, timezone
from email import message_from_bytes
from email.policy import default
import io
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from urllib.error import HTTPError
from connector_extension.catalog import CATALOG, GOOGLE
from connector_extension.common import ArtifactStore, Connector, EffectJournal, JSONTransport, MAX_ATTACHMENT, NoRedirect
from connector_extension.google import GoogleAPI, GoogleToken
from connector_extension.calendar import CalendarConnector
from connector_extension.mail import MailConnector
from connector_extension.search import SearchConnector
from connector_extension.sheets import SheetsRead, SheetsWrite
from connector_extension.authorize_google import required_scopes, save_credentials
from registry.contracts import validate
from runtime.service import RuntimeFailure


class FakeTransport:
    def __init__(self, *responses): self.responses, self.calls = list(responses), []
    def request(self, method, url, headers, body=None, timeout=30):
        self.calls.append({'method': method, 'url': url, 'body': deepcopy(body), 'timeout': timeout, 'headers': headers})
        if not self.responses: raise AssertionError('Unexpected request')
        result = self.responses.pop(0)
        if isinstance(result, Exception): raise result
        return result


def grant(tool_id):
    definition = CATALOG[tool_id]
    return {'tool_id': tool_id, 'authorization_state': 'authorized', 'authorization_reference': 'authz_offline',
            'credential_reference': 'cred_extension_' + definition['provider_id'], 'approval_reference': 'approval_offline',
            'input_schema': definition['input_schema'], 'output_schema': definition['output_schema'],
            'destination': next(iter(definition.get('allowed_destinations', [])), None)}


class ConnectorTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.journal, self.artifacts = EffectJournal(self.root), ArtifactStore(self.root)
        self.workflow = {'workflow_id': 'extension_test', 'version': 1, 'metadata': {'workspace_id': 'local-workspace'}}
        self.target = {'spreadsheet_id': 'sheet_one', 'range': 'BOQ!A1:C10', 'identity_column': 'item_id',
                       'writable_columns': ['quantity', 'status'], 'allow_create': True}
        self.event = {'summary': 'Quote deadline', 'start': {'dateTime': '2026-11-01T10:00:00+05:30', 'timeZone': 'Asia/Kolkata'},
                      'end': {'dateTime': '2026-11-01T11:00:00+05:30', 'timeZone': 'Asia/Kolkata'},
                      'reminders': {'useDefault': False, 'overrides': [{'method': 'popup', 'minutes': 30}]}}
    def tearDown(self): self.temp.cleanup()
    def api(self, transport): return GoogleAPI(lambda scopes, timeout: 'offline-access', transport)
    def calendar(self, action, transport):
        return CalendarConnector(CATALOG['extension_calendar_' + action], self.api(transport), self.journal, ['primary'])
    def mail(self, action, transport):
        return MailConnector(CATALOG['extension_mail_' + action], self.api(transport), self.journal, self.artifacts,
                             'buyer@example.com', ['vendor@example.com']).bind_workflow(self.workflow)
    def message(self):
        return {'id': 'msg_1', 'threadId': 'thread_1', 'payload': {'mimeType': 'multipart/mixed', 'headers': [
            {'name': 'From', 'value': 'Vendor <vendor@example.com>'}, {'name': 'To', 'value': 'buyer@example.com'},
            {'name': 'Subject', 'value': 'RFQ 123'}, {'name': 'Message-ID', 'value': '<quote123@vendor.example.com>'}],
            'parts': [{'mimeType': 'text/plain', 'body': {'data': base64.urlsafe_b64encode(b'Price is 100').decode()}},
                      {'mimeType': 'application/pdf', 'filename': 'quote.pdf', 'body': {'attachmentId': 'att_1', 'size': 4}}]}}

    def test_catalog_uses_unchanged_contract(self):
        self.assertEqual(len(CATALOG), 20)
        for definition in CATALOG.values():
            validate(definition, 'tool')
            self.assertEqual(definition['retry_policy']['max_retries'], 0)

    def test_calendar_create_carries_timezone_reminders_and_deduplicates(self):
        transport = FakeTransport({'id': 'event_1', 'status': 'confirmed'})
        connector = self.calendar('create', transport)
        inputs = {'calendar_id': 'primary', 'event': self.event}
        result = connector.invoke(grant('extension_calendar_create'), inputs, 'intent_1')
        self.assertEqual(result['event_id'], 'event_1')
        self.assertEqual(connector.invoke(grant('extension_calendar_create'), inputs, 'intent_1'), result)
        self.assertEqual(len(transport.calls), 1)
        self.assertEqual(transport.calls[0]['body']['reminders'], self.event['reminders'])
        self.assertEqual(len(transport.calls[0]['body']['id']), 64)
        self.assertTrue(transport.calls[0]['url'].endswith('?sendUpdates=none'))

    def test_calendar_list_pagination_update_and_cancel(self):
        transport = FakeTransport({'items': [{'id': 'e1', 'summary': 'Due', 'attendees': ['hidden']}], 'nextPageToken': 'page_2'},
                                  {'id': 'e1'}, {})
        result = self.calendar('list', transport).invoke(grant('extension_calendar_list'), {'calendar_id': 'primary', 'limit': 2, 'page_token': 'page_1'}, 'read')
        self.assertEqual(result['next_page_token'], 'page_2'); self.assertNotIn('attendees', result['events'][0])
        self.calendar('update', transport).invoke(grant('extension_calendar_update'), {'calendar_id': 'primary', 'event_id': 'e1', 'event': self.event}, 'update')
        result = self.calendar('cancel', transport).invoke(grant('extension_calendar_cancel'), {'calendar_id': 'primary', 'event_id': 'e1'}, 'cancel')
        self.assertEqual(result['status'], 'cancelled'); self.assertEqual([c['method'] for c in transport.calls], ['GET', 'PATCH', 'DELETE'])

    def test_calendar_denies_scope_invalid_dates_and_unreviewed_writes(self):
        transport = FakeTransport()
        connector = self.calendar('create', transport)
        for inputs in [{'calendar_id': 'other', 'event': self.event},
                       {'calendar_id': 'primary', 'event': {**self.event, 'end': self.event['start']}},
                       {'calendar_id': 'primary', 'event': {**self.event, 'attendees': [{'email': 'outside@example.com'}]}}]:
            with self.assertRaises(RuntimeFailure): connector.invoke(grant('extension_calendar_create'), inputs, 'bad')
        unreviewed = grant('extension_calendar_create'); unreviewed.pop('approval_reference')
        with self.assertRaises(RuntimeFailure): connector.invoke(unreviewed, {'calendar_id': 'primary', 'event': self.event}, 'bad')
        self.assertFalse(transport.calls)

    def test_uncertain_write_is_not_repeated_after_restart(self):
        transport = FakeTransport(TimeoutError('private provider details'))
        connector = self.calendar('create', transport)
        inputs = {'calendar_id': 'primary', 'event': self.event}
        for _ in range(2):
            connector.journal = EffectJournal(self.root)
            with self.assertRaises(RuntimeFailure) as error: connector.invoke(grant('extension_calendar_create'), inputs, 'uncertain')
            self.assertEqual(error.exception.code, 'UNKNOWN_INVOCATION_RESULT')
            self.assertNotIn('private provider', str(error.exception))
        self.assertEqual(len(transport.calls), 1)

    def test_effect_key_reuse_different_inputs_is_denied(self):
        transport = FakeTransport({'id': 'e1'})
        connector = self.calendar('create', transport)
        connector.invoke(grant('extension_calendar_create'), {'calendar_id': 'primary', 'event': self.event}, 'key')
        with self.assertRaises(RuntimeFailure) as error:
            connector.invoke(grant('extension_calendar_create'), {'calendar_id': 'primary', 'event': {**self.event, 'summary': 'Different'}}, 'key')
        self.assertEqual(error.exception.code, 'EFFECT_REFERENCE_MISMATCH')

    def test_multiple_sheets_read_and_foreign_target_denial(self):
        transport = FakeTransport({'values': [['id', 'qty'], ['p1', 2]]}, {'values': [['vendor'], ['seller']]})
        connector = SheetsRead(CATALOG['google_sheets_read_rows'], self.api(transport),
            [{'spreadsheet_id': 'sheet_one', 'range': 'Items!A1:B10'}, {'spreadsheet_id': 'sheet_two', 'range': 'Vendors!A1:A10'}])
        for sheet, cell_range in [('sheet_one', 'Items!A1:B10'), ('sheet_two', 'Vendors!A1:A10')]:
            result = connector.invoke(grant('google_sheets_read_rows'), {'spreadsheet_id': sheet, 'range': cell_range}, 'read')
            self.assertEqual(len(result['rows']), 2)
        with self.assertRaises(RuntimeFailure): connector.invoke(grant('google_sheets_read_rows'), {'spreadsheet_id': 'foreign', 'range': 'Items!A1:B10'}, 'read')
        self.assertEqual(len(transport.calls), 2)

    def test_sheet_upsert_reuses_target_validation_and_raw_cell_writes(self):
        transport = FakeTransport({'values': [['item_id', 'quantity', 'status'], ['p1', 2, 'Open']]}, {'totalUpdatedCells': 1})
        connector = SheetsWrite(CATALOG['google_sheets_upsert_record'], self.api(transport), self.journal, [self.target], self.root/'token.json', self.root/'locks')
        inputs = {'spreadsheet_id': 'sheet_one', 'range': 'BOQ!A1:C10', 'identity_column': 'item_id', 'identity': 'p1', 'fields': {'status': '=literal'}}
        result = connector.invoke(grant('google_sheets_upsert_record'), inputs, 'save')
        self.assertEqual(result, {'identity': 'p1', 'row_index': 2, 'created': False, 'updated_cells': 1})
        self.assertEqual(transport.calls[-1]['body']['valueInputOption'], 'RAW')
        connector.invoke(grant('google_sheets_upsert_record'), inputs, 'save')
        self.assertEqual(len(transport.calls), 2)
        with self.assertRaises(RuntimeFailure): connector.invoke(grant('google_sheets_upsert_record'), {**inputs, 'fields': {'item_id': 'evil'}}, 'bad')

    def test_sheet_create_and_duplicate_identity_block(self):
        for rows, expected in [([['item_id', 'quantity', 'status']], True),
                               ([['item_id', 'quantity', 'status'], ['p1'], ['p1']], False)]:
            transport = FakeTransport({'values': rows}, {'totalUpdatedCells': 2})
            connector = SheetsWrite(CATALOG['google_sheets_upsert_record'], self.api(transport), self.journal, [self.target], self.root/'token.json', self.root/'locks')
            inputs = {'spreadsheet_id': 'sheet_one', 'range': 'BOQ!A1:C10', 'identity_column': 'item_id', 'identity': 'p2', 'fields': {'quantity': 5}}
            if expected: self.assertTrue(connector.invoke(grant('google_sheets_upsert_record'), inputs, 'create')['created'])
            else:
                with self.assertRaises(RuntimeFailure): connector.invoke(grant('google_sheets_upsert_record'), inputs, 'duplicate')
                self.assertEqual(len(transport.calls), 1)

    def test_mail_search_message_and_thread(self):
        transport = FakeTransport({'messages': [{'id': 'msg_1', 'threadId': 'thread_1'}], 'nextPageToken': 'next'}, self.message(), {'id': 'thread_1', 'messages': [self.message()]})
        result = self.mail('search', transport).invoke(grant('extension_mail_search'), {'query': 'subject:RFQ', 'limit': 1}, 'read')
        self.assertEqual(result['next_page_token'], 'next')
        result = self.mail('message', transport).invoke(grant('extension_mail_message'), {'message_id': 'msg_1'}, 'read')
        self.assertEqual(result['message']['text'], 'Price is 100'); self.assertEqual(result['message']['attachments'][0]['filename'], 'quote.pdf')
        result = self.mail('thread', transport).invoke(grant('extension_mail_thread'), {'thread_id': 'thread_1'}, 'read')
        self.assertEqual(len(result['messages']), 1)

    def test_download_attachment_returns_private_reference_and_send_mime(self):
        transport = FakeTransport(self.message(), {'data': base64.urlsafe_b64encode(b'%PDF').decode()}, {'id': 'sent_1', 'threadId': 'new_thread'})
        attachment = self.mail('attachment', transport).invoke(grant('extension_mail_attachment'), {'message_id': 'msg_1', 'attachment_id': 'att_1'}, 'read')
        self.assertEqual(attachment['size'], 4); self.assertNotIn('data', attachment)
        inputs = {'to': 'vendor@example.com', 'subject': 'RFQ', 'body': 'Please quote.', 'attachments': [{k: attachment[k] for k in ['artifact_id', 'filename', 'mime_type']}]}
        self.mail('send', transport).invoke(grant('extension_mail_send'), inputs, 'send')
        encoded = transport.calls[-1]['body']['raw']
        parsed = message_from_bytes(base64.urlsafe_b64decode(encoded), policy=default)
        self.assertEqual(next(parsed.iter_attachments()).get_payload(decode=True), b'%PDF')
        self.assertEqual(parsed['To'], 'vendor@example.com')

    def test_long_attachment_ids_download_and_invalid_ids_fail_before_requests(self):
        for size in (404, 4096):
            identifier = 'A' * size
            message = self.message()
            message['payload']['parts'][1]['body']['attachmentId'] = identifier
            transport = FakeTransport(message, {'data': base64.urlsafe_b64encode(b'%PDF').decode()})
            result = self.mail('attachment', transport).invoke(grant('extension_mail_attachment'),
                {'message_id': 'msg_1', 'attachment_id': identifier}, 'download_' + str(size))
            self.assertEqual(self.artifacts.get(['local-workspace', 'extension_test', 1], result['artifact_id']), b'%PDF')
            self.assertTrue(transport.calls[-1]['url'].endswith('/attachments/' + identifier))
        for identifier in ('A' * 4097, '', 'invalid/id', 'bad\nheader'):
            transport = FakeTransport()
            with self.assertRaises(RuntimeFailure):
                self.mail('attachment', transport).invoke(grant('extension_mail_attachment'),
                    {'message_id': 'msg_1', 'attachment_id': identifier}, 'invalid')
            self.assertFalse(transport.calls)

    def test_stable_attachment_part_resolves_changed_provider_id(self):
        from connector_extension.mail import summarize
        original = self.message()
        original['payload']['parts'][1]['partId'] = '1.2'
        original['payload']['parts'][1]['body']['attachmentId'] = 'old_' + 'A' * 400
        reference = summarize(original)['attachments'][0]['attachment_id']
        self.assertEqual(reference, 'part_1.2')
        refreshed = deepcopy(original)
        refreshed['payload']['parts'][1]['body']['attachmentId'] = 'new_' + 'B' * 400
        transport = FakeTransport(refreshed, {'data': base64.urlsafe_b64encode(b'%PDF').decode()})
        result = self.mail('attachment', transport).invoke(grant('extension_mail_attachment'),
            {'message_id': 'msg_1', 'attachment_id': reference}, 'stable_download')
        self.assertEqual(result['size'], 4)
        self.assertTrue(transport.calls[-1]['url'].endswith('/attachments/' + 'new_' + 'B' * 400))
        transport = FakeTransport(refreshed)
        with self.assertRaises(RuntimeFailure):
            self.mail('attachment', transport).invoke(grant('extension_mail_attachment'),
                {'message_id': 'msg_1', 'attachment_id': 'part_9'}, 'wrong_part')
        self.assertEqual(len(transport.calls), 1)

    def test_mail_reply_derives_exact_thread_headers_and_recipient(self):
        transport = FakeTransport(self.message(), {'id': 'reply_1', 'threadId': 'thread_1'})
        result = self.mail('reply', transport).invoke(grant('extension_mail_reply'), {'message_id': 'msg_1', 'body': 'Thank you.'}, 'reply')
        self.assertEqual(result['thread_id'], 'thread_1')
        payload = transport.calls[-1]['body']; self.assertEqual(payload['threadId'], 'thread_1')
        parsed = message_from_bytes(base64.urlsafe_b64decode(payload['raw']), policy=default)
        self.assertEqual(parsed['In-Reply-To'], '<quote123@vendor.example.com>'); self.assertEqual(parsed['Subject'], 'Re: RFQ 123')

    def test_draft_does_not_use_send_endpoint(self):
        transport = FakeTransport({'id': 'draft_1', 'message': {'id': 'msg_2', 'threadId': 'thread_2'}})
        result = self.mail('draft', transport).invoke(grant('extension_mail_draft'), {'to': 'vendor@example.com', 'subject': 'RFQ', 'body': 'Please quote'}, 'draft')
        self.assertEqual(result['draft_id'], 'draft_1'); self.assertTrue(transport.calls[0]['url'].endswith('/drafts'))

    def test_mail_denies_unapproved_recipients_headers_and_paths(self):
        transport = FakeTransport()
        connector = self.mail('send', transport)
        for to, subject in [('evil@example.com', 'RFQ'), ('vendor@example.com', 'Injected\r\nBcc: evil@example.com')]:
            with self.assertRaises(RuntimeFailure): connector.invoke(grant('extension_mail_send'), {'to': to, 'subject': subject, 'body': 'Hi'}, 'bad')
        with self.assertRaises(RuntimeFailure): connector.invoke(grant('extension_mail_send'), {'to': 'vendor@example.com', 'subject': 'RFQ', 'body': 'Hi', 'attachments': [{'artifact_id': '../../credentials.json', 'filename': 'file', 'mime_type': 'text/plain'}]}, 'bad')
        self.assertFalse(transport.calls)

    def test_attachment_scope_tampering_size_and_symlink_denied(self):
        reference = self.artifacts.put(['workspace', 'wf', 1], b'file')
        with self.assertRaises(RuntimeFailure): self.artifacts.get(['workspace', 'other', 1], reference)
        path = self.artifacts.directory(['workspace', 'wf', 1])/reference
        path.write_bytes(b'tampered')
        with self.assertRaises(RuntimeFailure): self.artifacts.get(['workspace', 'wf', 1], reference)
        path.unlink(); path.symlink_to(self.root/'elsewhere')
        with self.assertRaises(RuntimeFailure): self.artifacts.get(['workspace', 'wf', 1], reference)
        with self.assertRaises(RuntimeFailure): self.artifacts.put(['workspace', 'wf', 1], b'x'*(MAX_ATTACHMENT+1))

    def test_brave_search_uses_fixed_endpoint_bounded_sources(self):
        transport = FakeTransport({'web': {'results': [{'title': 'Vendor', 'url': 'https://example.com/catalog', 'description': 'Catalog'}, {'url': 'file:///etc/passwd'}]}})
        connector = SearchConnector(CATALOG['extension_web_search'], transport, lambda _: 'offline-search-key')
        result = connector.invoke(grant('extension_web_search'), {'query': 'pipe suppliers', 'limit': 2}, 'search')
        self.assertEqual(len(result['results']), 1); self.assertTrue(transport.calls[0]['url'].startswith('https://api.search.brave.com/'))
        self.assertNotIn('offline-search-key', json.dumps(result))

    def test_exact_tool_schema_and_authorization_are_required(self):
        connector = self.calendar('list', FakeTransport())
        for change in [{'tool_id': 'extension_calendar_create'}, {'authorization_state': 'denied'}, {'input_schema': {'type': 'object'}}]:
            with self.assertRaises(RuntimeFailure): connector.invoke({**grant('extension_calendar_list'), **change}, {'calendar_id': 'primary'}, 'bad')

    def test_transport_blocks_redirects_oversized_bodies_and_secrets(self):
        class Response(io.BytesIO):
            def geturl(self): return 'https://approved.example/api'
        transport = JSONTransport(lambda request, timeout: Response(b'12345'), max_bytes=4)
        with self.assertRaises(RuntimeFailure) as error: transport.request('GET', 'https://approved.example/api', {})
        self.assertEqual(error.exception.code, 'PROVIDER_RESPONSE_TOO_LARGE')
        with self.assertRaises(RuntimeFailure): NoRedirect().redirect_request(None, None, None, None, None, None)
        with self.assertRaises(RuntimeFailure): transport.request('GET', 'http://unapproved.example', {})

    def test_google_scope_implication_and_refresh_storage(self):
        token_file = self.root/'google-token.json'; token_file.write_text('{}')
        class Credentials:
            valid = True; token = 'offline'; granted_scopes = None; scopes = [GOOGLE+'spreadsheets', GOOGLE+'calendar.events']
            def to_json(self): return '{}'
        with patch('google.oauth2.credentials.Credentials.from_authorized_user_file', return_value=Credentials()):
            self.assertEqual(GoogleToken(token_file)(['spreadsheets.readonly','calendar.events.readonly'], 5), 'offline')
            with self.assertRaises(RuntimeFailure): GoogleToken(token_file)(['gmail.readonly'], 5)
        class Verified(Credentials):
            refresh_token='offline-refresh'; granted_scopes=[GOOGLE+'spreadsheets']
        save_credentials(Verified(),token_file,[GOOGLE+'spreadsheets.readonly'])
        self.assertEqual(os.stat(token_file).st_mode & 0o777, 0o600)
        with self.assertRaises(ValueError): save_credentials(Verified(), token_file, [GOOGLE+'gmail.send'])
        scopes = required_scopes(['google_sheets']); self.assertNotIn(GOOGLE+'spreadsheets.readonly',scopes)
