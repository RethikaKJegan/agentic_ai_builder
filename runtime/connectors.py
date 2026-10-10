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
from urllib.parse import quote, urlparse
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
        if (grant.get('authorization_state') != 'authorized' or grant.get('tool_id') not in {'smtp_send_email', 'brevo_send_email'} or
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

    def poll_changes(self, grant, inputs, previous_cursor=None):
        """Read a sheet range and return replay-safe row events plus a cursor.

        Scheduling and durable checkpoint storage remain lifecycle concerns; this
        method only performs the provider read and creates stable row identities.
        """
        output = self.invoke(grant, inputs, 'poll:' + (previous_cursor or 'initial'))
        rows = output.get('rows', [])
        snapshot = hashlib.sha256(json.dumps(rows, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
        changes = [] if previous_cursor == snapshot else [
            {'event_id': f'row:{snapshot}:{index}', 'row_index': index, 'row': row}
            for index, row in enumerate(rows)
        ]
        return {'cursor': snapshot, 'changes': changes}


class GoogleSheetsUpdateConnector(GoogleSheetsConnector):
    """Update a configured range through the same trusted OAuth boundary."""
    external_write = True

    def invoke(self, grant, inputs, effect_id):
        reject_secrets(inputs)
        if (grant.get('authorization_state') != 'authorized' or
                grant.get('tool_id') != 'google_sheets_update_row' or
                not grant.get('authorization_reference') or not grant.get('credential_reference') or
                grant.get('destination') != 'configured_spreadsheet'):
            raise RuntimeFailure('SHEETS_NOT_AUTHORIZED', 'Google Sheets updates require an exact approved binding.', 403)
        if list(Draft202012Validator(grant['input_schema']).iter_errors(inputs)):
            raise RuntimeFailure('CONNECTOR_INPUT_INVALID', 'Connector inputs do not meet the assignment schema.', 400)
        spreadsheet_id, cell_range, values = inputs.get('spreadsheet_id'), inputs.get('range'), inputs.get('values')
        if not isinstance(spreadsheet_id, str) or not isinstance(cell_range, str) or not isinstance(values, list):
            raise RuntimeFailure('SHEETS_INPUT_INVALID', 'Use a spreadsheet ID, A1 range, and a values array.', 400)
        configuration = self.resolve(grant['credential_reference'])
        if configuration.get('provider_id') != 'google_sheets':
            raise RuntimeFailure('SHEETS_NOT_CONFIGURED', 'Configure a Google Sheets credential reference.', 503)
        try:
            from google.oauth2.credentials import Credentials
            from google.auth.transport.requests import Request as GoogleRequest
            credentials = Credentials.from_authorized_user_file(str(self.token_file))
            if not credentials.valid:
                credentials.refresh(GoogleRequest())
            body = json.dumps({'range': cell_range, 'majorDimension': 'ROWS', 'values': values}).encode()
            request = Request(
                'https://sheets.googleapis.com/v4/spreadsheets/' + quote(spreadsheet_id, safe='') +
                '/values/' + quote(cell_range, safe='') + '?valueInputOption=USER_ENTERED',
                data=body, method='PUT', headers={'Authorization': 'Bearer ' + credentials.token,
                'Content-Type': 'application/json', 'Accept': 'application/json'})
            with urlopen(request, timeout=self.timeout) as response:
                payload = json.load(response)
            output = {'updated_cells': int(payload.get('updatedCells', 0))}
        except Exception:
            raise RuntimeFailure('SHEETS_UPDATE_FAILED', 'Google Sheets update failed; provider details are suppressed.', 502) from None
        if list(Draft202012Validator(grant['output_schema']).iter_errors(output)):
            raise RuntimeFailure('CONNECTOR_OUTPUT_INVALID', 'The connector result does not meet the assignment schema.')
        return output


class HTTPJSONConnector:
    """Provider-neutral JSON HTTP adapter with server-owned endpoint policy.

    The workflow can supply data and query parameters, but never a destination
    URL or credential. The operator binds the base URL and optional bearer
    token in the opaque credential reference.
    """
    external_write = False
    retry_safe = True

    def __init__(self, resolve, provider_id, base_url, timeout=30, method='GET', external_write=False,
                 required_tool_id=None, headers=None):
        self.resolve, self.provider_id, self.base_url = resolve, provider_id, base_url.rstrip('/')
        self.timeout, self.method, self.external_write = timeout, method.upper(), external_write
        self.required_tool_id, self.headers = required_tool_id, dict(headers or {})
        parsed = urlparse(self.base_url)
        if parsed.scheme not in {'http', 'https'} or not parsed.netloc:
            raise ValueError('Connector base URL must be an absolute HTTP(S) URL.')

    @staticmethod
    def reservation(grant):
        return {'tool_calls': 1, 'estimated_cost_usd': 0}

    def _authorized(self, grant):
        return (grant.get('authorization_state') == 'authorized' and
                (self.required_tool_id is None or grant.get('tool_id') == self.required_tool_id) and
                bool(grant.get('authorization_reference')) and bool(grant.get('credential_reference')))

    def invoke(self, grant, inputs, effect_id):
        reject_secrets(inputs)
        if not self._authorized(grant):
            raise RuntimeFailure('CONNECTOR_NOT_AUTHORIZED', 'The connector requires an exact authorized credential binding.', 403)
        if list(Draft202012Validator(grant['input_schema']).iter_errors(inputs)):
            raise RuntimeFailure('CONNECTOR_INPUT_INVALID', 'Connector inputs do not meet the assignment schema.', 400)
        configuration = self.resolve(grant['credential_reference'])
        if configuration.get('provider_id') != self.provider_id:
            raise RuntimeFailure('CONNECTOR_NOT_CONFIGURED', 'The provider credential is not configured.', 503)
        path = inputs.get('path', '')
        if not isinstance(path, str) or path.startswith('http') or any(c in path for c in '\r\n'):
            raise RuntimeFailure('DESTINATION_NOT_AUTHORIZED', 'The request path must be relative to the configured provider.', 403)
        url = self.base_url + ('/' if path and not path.startswith('/') else '') + path
        query = inputs.get('query') or {}
        if not isinstance(query, dict) or any(not isinstance(k, str) or not isinstance(v, (str, int, float, bool)) for k, v in query.items()):
            raise RuntimeFailure('CONNECTOR_INPUT_INVALID', 'Query parameters must be scalar values.', 400)
        if query:
            from urllib.parse import urlencode
            url += '?' + urlencode(query)
        body = inputs.get('body')
        data = None if body is None else json.dumps(body).encode()
        headers = {'Accept': 'application/json', **self.headers}
        token = configuration.get('token')
        if token:
            headers['Authorization'] = 'Bearer ' + token
        if data is not None:
            headers['Content-Type'] = 'application/json'
        try:
            request = Request(url, data=data, method=self.method, headers=headers)
            with urlopen(request, timeout=self.timeout) as response:
                raw = response.read()
                payload = json.loads(raw.decode() or '{}')
        except Exception:
            raise RuntimeFailure('PROVIDER_REQUEST_FAILED', 'The provider request failed; provider details are suppressed.', 502) from None
        output = {'result': payload}
        if list(Draft202012Validator(grant['output_schema']).iter_errors(output)):
            raise RuntimeFailure('CONNECTOR_OUTPUT_INVALID', 'The connector result does not meet the assignment schema.')
        return output


class SlackWebhookConnector(HTTPJSONConnector):
    external_write = True

    def __init__(self, resolve, timeout=30):
        super().__init__(resolve, 'slack', 'https://hooks.slack.com', timeout=timeout,
                         method='POST', external_write=True, required_tool_id='slack_send_notification')

    def invoke(self, grant, inputs, effect_id):
        # Slack incoming webhook URLs are credentials; the workflow only supplies text.
        reject_secrets(inputs)
        if not self._authorized(grant):
            raise RuntimeFailure('SLACK_NOT_AUTHORIZED', 'Slack requires an exact authorized credential binding.', 403)
        if list(Draft202012Validator(grant['input_schema']).iter_errors(inputs)):
            raise RuntimeFailure('CONNECTOR_INPUT_INVALID', 'Connector inputs do not meet the assignment schema.', 400)
        configuration = self.resolve(grant['credential_reference'])
        webhook = configuration.get('webhook_url', '')
        parsed = urlparse(webhook)
        if configuration.get('provider_id') != 'slack' or parsed.scheme != 'https' or parsed.netloc != 'hooks.slack.com':
            raise RuntimeFailure('SLACK_NOT_CONFIGURED', 'Configure an approved Slack incoming webhook.', 503)
        try:
            request = Request(webhook, data=json.dumps({'text': inputs.get('text', inputs.get('message', ''))}).encode(),
                              method='POST', headers={'Content-Type': 'application/json', 'Accept': 'text/plain'})
            with urlopen(request, timeout=self.timeout) as response:
                result = response.read().decode() or 'ok'
        except Exception:
            raise RuntimeFailure('SLACK_DELIVERY_FAILED', 'Slack delivery failed; provider details are suppressed.', 502) from None
        output = {'result': result}
        if list(Draft202012Validator(grant['output_schema']).iter_errors(output)):
            raise RuntimeFailure('CONNECTOR_OUTPUT_INVALID', 'The connector result does not meet the assignment schema.')
        return output


class GoogleAPIConnector(HTTPJSONConnector):
    """Read-only Drive, Calendar, and Docs calls using the shared OAuth token."""
    def __init__(self, resolve, token_file, provider_id, base_url, timeout=30, required_tool_id=None):
        self.token_file = Path(token_file)
        super().__init__(resolve, provider_id, base_url, timeout=timeout, required_tool_id=required_tool_id)

    def invoke(self, grant, inputs, effect_id):
        reject_secrets(inputs)
        if not self._authorized(grant):
            raise RuntimeFailure('GOOGLE_API_NOT_AUTHORIZED', 'Google API requires an exact authorized credential binding.', 403)
        if list(Draft202012Validator(grant['input_schema']).iter_errors(inputs)):
            raise RuntimeFailure('CONNECTOR_INPUT_INVALID', 'Connector inputs do not meet the assignment schema.', 400)
        configuration = self.resolve(grant['credential_reference'])
        if configuration.get('provider_id') != self.provider_id:
            raise RuntimeFailure('GOOGLE_API_NOT_CONFIGURED', 'Configure the requested Google API credential.', 503)
        try:
            from google.oauth2.credentials import Credentials
            from google.auth.transport.requests import Request as GoogleRequest
            credentials = Credentials.from_authorized_user_file(str(self.token_file))
            if not credentials.valid:
                credentials.refresh(GoogleRequest())
            self.headers['Authorization'] = 'Bearer ' + credentials.token
            return super().invoke(grant, inputs, effect_id)
        except RuntimeFailure:
            raise
        except Exception:
            raise RuntimeFailure('GOOGLE_API_REQUEST_FAILED', 'Google API request failed; provider details are suppressed.', 502) from None
