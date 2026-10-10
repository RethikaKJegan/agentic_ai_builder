"""SMTP through trusted opaque-reference resolution and recipient allowlists."""
from email.message import EmailMessage
from email.utils import formatdate
import hashlib
import json
import os
import smtplib
import ssl
import time
from pathlib import Path
from urllib.parse import quote
from urllib.request import Request, urlopen

from jsonschema import Draft202012Validator
from registry.safety import reject_secrets
from .service import RuntimeFailure


class SMTPConnector:
    external_write = True

    def __init__(self, resolve, allowed_recipients, allowed_hosts, timeout=30, transport=smtplib.SMTP):
        # All arguments are operator/server-owned. The resolver returns secrets
        # only here; they never enter workflow documents, records, or traces.
        self.resolve = resolve
        self.allowed_recipients, self.allowed_hosts = frozenset(allowed_recipients), frozenset(allowed_hosts)
        self.timeout, self.transport = timeout, transport
        if not 1 <= timeout <= 120:
            raise ValueError('Configure an SMTP timeout within the runtime ceiling.')

    @staticmethod
    def reservation(grant):
        return {'tool_calls': 1, 'estimated_cost_usd': 0}

    def invoke(self, grant, inputs, effect_id):
        reject_secrets(inputs)
        if (grant.get('authorization_state') != 'authorized' or grant.get('tool_id') != 'smtp_send_email' or
                not grant.get('authorization_reference') or not grant.get('credential_reference') or
                grant.get('destination') != 'verified_recipients' or not grant.get('approval_reference')):
            raise RuntimeFailure('SMTP_NOT_AUTHORIZED', 'SMTP requires an exact authorized approved credential binding.', 403)
        if list(Draft202012Validator(grant['input_schema']).iter_errors(inputs)):
            raise RuntimeFailure('CONNECTOR_INPUT_INVALID', 'Connector inputs do not meet the assignment schema.', 400)
        recipient = inputs.get('to')
        if (not isinstance(recipient, str) or recipient not in self.allowed_recipients or
                any(c in recipient for c in '\r\n') or
                set(inputs) - {'to', 'subject', 'body'} or
                not all(isinstance(inputs.get(k), str) for k in ('subject', 'body')) or
                any(c in inputs['subject'] for c in '\r\n')):
            raise RuntimeFailure('DESTINATION_NOT_AUTHORIZED', 'Use one explicitly allowlisted recipient and safe message fields.', 403)
        configuration = self.resolve(grant['credential_reference'])
        if (configuration.get('host') not in self.allowed_hosts or configuration.get('port') != 587 or
                not all(isinstance(configuration.get(k), str) and configuration[k] for k in ('username', 'password', 'sender')) or
                any(c in configuration['sender'] for c in '\r\n')):
            raise RuntimeFailure('SMTP_NOT_CONFIGURED', 'Configure an approved SMTP host and sender.', 503)
        # Stable Message-ID is audit/reconciliation data, NOT a promise of SMTP
        # idempotency. No automatic retries occur after uncertain submission.
        message_id = '<' + hashlib.sha256(effect_id.encode()).hexdigest() + '@agentic-ai-builder.local>'
        message = EmailMessage()
        message['From'], message['To'], message['Subject'] = configuration['sender'], recipient, inputs['subject']
        message['Message-ID'], message['Date'] = message_id, formatdate(localtime=False)
        message.set_content(inputs['body'])
        try:
            deadline = time.monotonic() + self.timeout
            def remaining(smtp=None):
                seconds = deadline - time.monotonic()
                if seconds <= 0:
                    raise RuntimeFailure('SMTP_DELIVERY_UNCERTAIN', 'The SMTP invocation duration expired.')
                if smtp is not None and getattr(smtp, 'sock', None) is not None:
                    smtp.sock.settimeout(seconds)
                return seconds
            with self.transport(configuration['host'], configuration['port'], timeout=remaining()) as smtp:
                remaining(smtp)
                smtp.ehlo()
                remaining(smtp)
                smtp.starttls(context=ssl.create_default_context())
                remaining(smtp)
                smtp.ehlo()
                remaining(smtp)
                smtp.login(configuration['username'], configuration['password'])
                remaining(smtp)
                refused = smtp.send_message(message)
                if refused:
                    raise RuntimeFailure('SMTP_DELIVERY_UNCERTAIN', 'The provider did not confirm recipient acceptance.')
        except Exception as exc:
            raise RuntimeFailure('SMTP_DELIVERY_UNCERTAIN', 'SMTP submission failed or has an uncertain result; do not automatically resend.') from None
        output = {'message_id': message_id}
        if list(Draft202012Validator(grant['output_schema']).iter_errors(output)):
            raise RuntimeFailure('CONNECTOR_OUTPUT_INVALID', 'The connector result does not meet the assignment schema.')
        return output


class GoogleSheetsConnector:
    """Read rows through an operator-authorized Google OAuth token."""
    external_write = False

    def __init__(self, resolve, token_file, timeout=30):
        self.resolve, self.token_file, self.timeout = resolve, Path(token_file), timeout
        if not 1 <= timeout <= 120:
            raise ValueError('Configure a Sheets timeout within the runtime ceiling.')

    @staticmethod
    def reservation(grant):
        return {'tool_calls': 1, 'estimated_cost_usd': 0}

    def invoke(self, grant, inputs, effect_id):
        reject_secrets(inputs)
        if (grant.get('authorization_state') != 'authorized' or
                grant.get('tool_id') != 'google_sheets_read_rows' or
                not grant.get('authorization_reference') or not grant.get('credential_reference')):
            raise RuntimeFailure('SHEETS_NOT_AUTHORIZED', 'Google Sheets requires an exact authorized credential binding.', 403)
        if list(Draft202012Validator(grant['input_schema']).iter_errors(inputs)):
            raise RuntimeFailure('CONNECTOR_INPUT_INVALID', 'Connector inputs do not meet the assignment schema.', 400)
        spreadsheet_id, cell_range = inputs.get('spreadsheet_id'), inputs.get('range')
        if (not isinstance(spreadsheet_id, str) or not spreadsheet_id or
                not isinstance(cell_range, str) or not cell_range or any(c in spreadsheet_id + cell_range for c in '\r\n')):
            raise RuntimeFailure('SHEETS_INPUT_INVALID', 'Use a spreadsheet ID and A1 range.', 400)
        configuration = self.resolve(grant['credential_reference'])
        if configuration.get('provider_id') != 'google_sheets':
            raise RuntimeFailure('SHEETS_NOT_CONFIGURED', 'Configure a Google Sheets credential reference.', 503)
        try:
            from google.oauth2.credentials import Credentials
            from google.auth.transport.requests import Request as GoogleRequest
            credentials = Credentials.from_authorized_user_file(str(self.token_file))
            if not credentials.valid:
                credentials.refresh(GoogleRequest())
            if not credentials.token:
                raise ValueError('missing token')
            request = Request(
                'https://sheets.googleapis.com/v4/spreadsheets/' + quote(spreadsheet_id, safe='') +
                '/values/' + quote(cell_range, safe=''),
                headers={'Authorization': 'Bearer ' + credentials.token, 'Accept': 'application/json'},
            )
            with urlopen(request, timeout=self.timeout) as response:
                payload = json.load(response)
            output = {'rows': payload.get('values', [])}
        except Exception:
            raise RuntimeFailure('SHEETS_READ_FAILED', 'Google Sheets read failed; provider details are suppressed.', 502) from None
        if list(Draft202012Validator(grant['output_schema']).iter_errors(output)):
            raise RuntimeFailure('CONNECTOR_OUTPUT_INVALID', 'The connector result does not meet the assignment schema.')
        return output
