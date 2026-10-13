"""Gmail connectors with explicit mailbox, recipient and artifact boundaries."""
import base64
from email.message import EmailMessage
from email.policy import SMTP
from email.utils import parseaddr
import hashlib
import re
from urllib.parse import quote, urlencode
from .common import Connector, MAX_ATTACHMENT, decode_data, denied


def safe_filename(value):
    if not isinstance(value, str) or not value or len(value) > 200 or any(c in value for c in '/\\\r\n\x00'):
        denied('ATTACHMENT_NAME_INVALID', 'Use a simple attachment filename.', 400)
    return value


def address(value):
    if not isinstance(value, str) or not re.fullmatch(r'[^\s<>@,;]+@[^\s<>@,;]+\.[^\s<>@,;]+', value):
        denied('MAIL_ADDRESS_INVALID', 'Use one valid mailbox address.', 400)
    return value.lower()


def headers(message):
    result = {}
    for item in message.get('payload', {}).get('headers', []):
        name, value = item.get('name', '').lower(), item.get('value', '')
        if name in {'from', 'to', 'subject', 'message-id', 'references', 'reply-to','in-reply-to','auto-submitted','precedence'}:
            if not isinstance(value, str) or any(c in value for c in '\r\n'):
                denied('MAIL_HEADER_INVALID', 'The provider returned an invalid mail header.', 502)
            if name in result: denied('MAIL_HEADER_INVALID', 'The provider returned ambiguous mail headers.', 502)
            result[name] = value[:2000]
    return result


def parts(payload, depth=0):
    if depth > 8: denied('MAIL_OUTPUT_INVALID', 'The message MIME nesting exceeds its bound.', 502)
    yield payload
    children = payload.get('parts', [])
    if not isinstance(children, list) or len(children) > 100:
        denied('MAIL_OUTPUT_INVALID', 'The message MIME parts exceed their bound.', 502)
    for part in children: yield from parts(part, depth + 1)


def attachment_reference(part):
    # Gmail opaque attachment IDs can change between message reads. Its immutable
    # MIME part IDs let downloads resolve the current ID within the exact message.
    identifier = part.get('partId')
    if isinstance(identifier, str) and re.fullmatch(r'[0-9]+(?:\.[0-9]+)*', identifier):
        return 'part_' + identifier
    return part.get('body', {}).get('attachmentId')


def summarize(message):
    values = headers(message); text, attachments = [], []
    for part in parts(message.get('payload', {})):
        body = part.get('body', {})
        if part.get('filename') and body.get('attachmentId'):
            attachments.append({'attachment_id': attachment_reference(part), 'filename': part['filename'][:200],
                                'mime_type': part.get('mimeType', 'application/octet-stream'), 'size': body.get('size', 0)})
        elif part.get('mimeType') == 'text/plain' and body.get('data'):
            text.append(decode_data(body['data'], 32000).decode('utf-8', errors='replace'))
    result={'message_id': message['id'], 'thread_id': message.get('threadId'),
            'from': values.get('from', ''), 'to': values.get('to', ''), 'subject': values.get('subject', ''),
            'rfc_message_id': values.get('message-id', ''), 'text': '\n'.join(text)[:32000],
            'attachments': attachments[:100], 'snippet': message.get('snippet', '')[:1000]}
    # Keep absent metadata absent for older provider fixtures/consumers.
    if message.get('internalDate'):
        from datetime import datetime,timezone
        try:result['received_at']=datetime.fromtimestamp(int(message['internalDate'])/1000,timezone.utc).isoformat()
        except (ValueError,TypeError,OverflowError,OSError):denied('MAIL_DATE_INVALID','Message receipt timestamp is invalid.',502)
    for field in ('in-reply-to','references','auto-submitted','precedence','reply-to'):
        if field in values:result[field.replace('-','_')]=values[field]
    return result


class MailConnector(Connector):
    def __init__(self, definition, api, journal=None, artifacts=None, account=None, recipients=None):
        super().__init__(definition, api, journal, artifacts)
        self.account = address(account) if account else None
        self.recipients = frozenset(address(value) for value in (recipients or []))

    def get_message(self, identifier, deadline):
        return self.api.request('gmail', 'GET', 'messages/' + quote(identifier, safe='') + '?format=full', ['gmail.readonly'], deadline=deadline)

    def recipient(self, recipient):
        normalized = address(recipient)
        if self.recipients and normalized not in self.recipients:
            denied('DESTINATION_NOT_AUTHORIZED', 'The recipient is outside the optional operator restriction.')
        return normalized

    def profile(self, deadline):
        result = self.api.request('gmail', 'GET', 'profile', ['gmail.readonly'], deadline=deadline)
        return {'email_address': address(result.get('emailAddress'))}

    def execute(self, grant, inputs, effect_id, deadline):
        action = self.definition['tool_id'].removeprefix('extension_mail_')
        if action == 'profile': return self.profile(deadline)
        if action == 'search':
            query = {'q': inputs['query'], 'maxResults': inputs.get('limit', 50)}
            if 'page_token' in inputs: query['pageToken'] = inputs['page_token']
            result = self.api.request('gmail', 'GET', 'messages?' + urlencode(query), ['gmail.readonly'], deadline=deadline)
            messages = result.get('messages', [])
            if not isinstance(messages, list) or len(messages) > query['maxResults']:
                denied('MAIL_OUTPUT_INVALID', 'The search response exceeds its requested limit.', 502)
            return {'messages': [{'message_id': message['id'], 'thread_id': message.get('threadId')} for message in messages],
                    'next_page_token': result.get('nextPageToken')}
        if action == 'message': return {'message': summarize(self.get_message(inputs['message_id'], deadline))}
        if action == 'thread':
            result = self.api.request('gmail', 'GET', 'threads/' + quote(inputs['thread_id'], safe='') + '?format=full', ['gmail.readonly'], deadline=deadline)
            messages = result.get('messages', [])
            if len(messages) > 100: denied('MAIL_OUTPUT_INVALID', 'The thread has more than 100 messages; use message reads.', 502)
            return {'thread_id': result['id'], 'messages': [summarize(message) for message in messages]}
        if action == 'attachment':
            message = self.get_message(inputs['message_id'], deadline)
            matching = [part for part in parts(message.get('payload', {})) if part.get('body', {}).get('attachmentId') and
                        inputs['attachment_id'] in {attachment_reference(part), part['body']['attachmentId']}]
            if len(matching) != 1: denied('ATTACHMENT_NOT_FOUND', 'The attachment does not belong to this message.', 404)
            part = matching[0]; name = safe_filename(part.get('filename'))
            if part.get('body', {}).get('size', MAX_ATTACHMENT + 1) > MAX_ATTACHMENT:
                denied('ATTACHMENT_TOO_LARGE', 'The attachment exceeds five MiB.', 400)
            result = self.api.request('gmail', 'GET', 'messages/' + quote(inputs['message_id'], safe='') + '/attachments/' + quote(part['body']['attachmentId'], safe=''),
                                     ['gmail.readonly'], deadline=deadline)
            content = decode_data(result.get('data'))
            reference = self.artifacts.put(self.namespace, content)
            return {'artifact_id': reference, 'filename': name, 'mime_type': part.get('mimeType', 'application/octet-stream'), 'size': len(content)}
        thread_id = original_id = references = None
        if action == 'reply':
            original = self.get_message(inputs['message_id'], deadline)
            values = headers(original)
            recipient = self.recipient(parseaddr(values.get('reply-to') or values.get('from', ''))[1])
            subject = values.get('subject', '')
            if not subject.lower().startswith('re:'): subject = 'Re: ' + subject
            original_id = values.get('message-id')
            if not original_id or not re.fullmatch(r'<[^<>\s]+@[^<>\s]+>', original_id):
                denied('MAIL_THREAD_REFERENCE_REQUIRED', 'The original message lacks a valid thread reference.', 400)
            thread_id = original.get('threadId')
            if not thread_id: denied('MAIL_THREAD_REFERENCE_REQUIRED', 'The original message lacks a Gmail thread ID.', 400)
            references = (values.get('references', '') + ' ' + original_id).strip()
        else:
            recipient = self.recipient(inputs['to']); subject = inputs['subject']
        if any(c in subject for c in '\r\n'): denied('MAIL_HEADER_INVALID', 'Mail subjects must not contain line breaks.', 400)
        message = EmailMessage(policy=SMTP)
        rfc_id = '<' + hashlib.sha256(effect_id.encode()).hexdigest() + '@connector-extension.local>'
        sender = self.account or self.profile(deadline)['email_address']
        message['From'], message['To'], message['Subject'] = sender, recipient, subject
        message['Message-ID'] = rfc_id
        if original_id:
            message['In-Reply-To'] = original_id; message['References'] = references
        message.set_content(inputs['body'])
        total = 0
        for attachment in inputs.get('attachments', []):
            content = self.artifacts.get(self.namespace, attachment['artifact_id']); total += len(content)
            if total > MAX_ATTACHMENT: denied('ATTACHMENT_TOO_LARGE', 'Combined attachments exceed five MiB.', 400)
            filename = safe_filename(attachment['filename'])
            mime = attachment['mime_type']
            if not re.fullmatch(r'[A-Za-z0-9!#$&^_.+-]+/[A-Za-z0-9!#$&^_.+-]+', mime):
                denied('ATTACHMENT_TYPE_INVALID', 'Use a valid attachment MIME type.', 400)
            main, sub = mime.split('/')
            message.add_attachment(content, maintype=main, subtype=sub, filename=filename)
        payload = {'raw': base64.urlsafe_b64encode(message.as_bytes()).decode()}
        if thread_id: payload['threadId'] = thread_id
        def send():
            path = 'drafts' if action == 'draft' else 'messages/send'
            scopes = ['gmail.compose'] if action == 'draft' else ['gmail.send']
            result = self.api.request('gmail', 'POST', path, scopes, {'message': payload} if action == 'draft' else payload, deadline)
            record = result['message'] if action == 'draft' else result
            output = {'message_id': record['id'], 'thread_id': record.get('threadId'), 'rfc_message_id': rfc_id}
            if action == 'draft': output['draft_id'] = result['id']
            return output
        return self.write(effect_id, inputs, send)
