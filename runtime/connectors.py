"""SMTP through trusted opaque-reference resolution and recipient allowlists."""
from email.message import EmailMessage
from email.utils import formatdate
import hashlib
import json
import os
import re
import smtplib
import ssl
import time
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import quote, urlparse
from urllib.request import Request, urlopen

from jsonschema import Draft202012Validator
from registry.safety import reject_secrets
from .service import RuntimeFailure


def google_spreadsheet_id(resource):
    """Normalize an operator/workflow Sheet reference, never a request host."""
    if not isinstance(resource, str) or not resource.strip() or any(char in resource for char in '\r\n'):
        raise RuntimeFailure('SHEETS_INPUT_INVALID', 'Use a spreadsheet ID or HTTPS Google Sheets URL.', 400)
    resource = resource.strip()
    if '://' not in resource:
        if not re.fullmatch(r'[A-Za-z0-9_-]+', resource):
            raise RuntimeFailure('SHEETS_INPUT_INVALID', 'Use a spreadsheet ID or HTTPS Google Sheets URL.', 400)
        return resource
    parsed = urlparse(resource)
    match = re.fullmatch(r'/spreadsheets/d/([A-Za-z0-9_-]+)(?:/.*)?', parsed.path)
    if parsed.scheme != 'https' or parsed.netloc != 'docs.google.com' or not match:
        raise RuntimeFailure('SHEETS_INPUT_INVALID', 'Use a spreadsheet ID or HTTPS Google Sheets URL.', 400)
    return match.group(1)


def _google_credentials(token_file):
    """Load and refresh an operator-managed OAuth token without leaking it."""
    try:
        from google.oauth2.credentials import Credentials
        from google.auth.transport.requests import Request as GoogleRequest
    except ImportError:
        raise RuntimeFailure('GOOGLE_CLIENT_UNAVAILABLE', 'Install the Google integration dependencies on the runtime host.', 503) from None
    try:
        credentials = Credentials.from_authorized_user_file(str(token_file))
    except (OSError, ValueError):
        raise RuntimeFailure('GOOGLE_TOKEN_INVALID', 'Google authorization is invalid. Run scripts/authorize_google.py again.', 503) from None
    try:
        if not credentials.valid:
            credentials.refresh(GoogleRequest())
            from scripts.integration_config import private_write
            private_write(Path(token_file), credentials.to_json())
    except Exception:
        raise RuntimeFailure('GOOGLE_TOKEN_REFRESH_FAILED', 'Google authorization could not be refreshed. Run scripts/authorize_google.py again.', 503) from None
    if not credentials.token:
        raise RuntimeFailure('GOOGLE_TOKEN_INVALID', 'Google authorization is invalid. Run scripts/authorize_google.py again.', 503)
    return credentials


class SMTPConnector:
    external_write = True

    def bind_run(self, workflow, run):
        from copy import copy
        from .email_recipients import source_recipient
        recipient = source_recipient(workflow, run['inputs'])
        if recipient is None:
            return self
        bound = copy(self)
        bound.allowed_recipients = frozenset({recipient})
        from .customer_automation import automatic_policy
        bound.require_approval = self.require_approval or automatic_policy(workflow) is None
        bound.routine_only = automatic_policy(workflow) is not None
        return bound

    def __init__(self, resolve, allowed_recipients, allowed_hosts, timeout=30, transport=smtplib.SMTP, require_approval=True):
        # All arguments are operator/server-owned. The resolver returns secrets
        # only here; they never enter workflow documents, records, or traces.
        self.resolve = resolve
        self.allowed_recipients, self.allowed_hosts = frozenset(allowed_recipients), frozenset(allowed_hosts)
        self.timeout, self.transport = timeout, transport
        self.require_approval = require_approval
        self.routine_only = False
        if not 1 <= timeout <= 120:
            raise ValueError('Configure an SMTP timeout within the runtime ceiling.')

    @staticmethod
    def reservation(grant):
        return {'tool_calls': 1, 'estimated_cost_usd': 0}

    def invoke(self, grant, inputs, effect_id):
        reject_secrets(inputs)
        if (grant.get('authorization_state') != 'authorized' or grant.get('tool_id') not in {'smtp_send_email', 'brevo_send_email'} or
                not grant.get('authorization_reference') or not grant.get('credential_reference') or
                grant.get('destination') != 'verified_recipients' or
                ((self.require_approval or grant.get('approval_required', True)) and not grant.get('approval_reference'))):
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
        if self.routine_only:
            from .customer_automation import routine_email_allowed
            if not routine_email_allowed(inputs['body']):
                raise RuntimeFailure('COMPENSATION_REVIEW_REQUIRED', 'A compensation commitment requires manager authorization.', 403)
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
        self.allowed_ranges = None
        if not 1 <= timeout <= 120:
            raise ValueError('Configure a Sheets timeout within the runtime ceiling.')

    def bind_workflow(self, workflow):
        from copy import copy
        from .customer_automation import automatic_policy
        if automatic_policy(workflow) is None:
            return self
        bound = copy(self)
        locations = [(t['spreadsheet_id'], t['range']) for t in workflow['metadata'].get('sheet_read_targets', [])]
        locations += [(t['resource_id'], t['poll_input']['range']) for t in workflow['metadata'].get('trigger_templates', [])
                      if t.get('provider_id') == 'google_sheets']
        bound.allowed_ranges = {(google_spreadsheet_id(s), r) for s,r in locations}
        # Quoted and unquoted simple tab names refer to the same published table.
        for s,r in list(bound.allowed_ranges):
            match = re.fullmatch(r"'([A-Za-z0-9_]+)'!(.+)",r)
            if match:
                bound.allowed_ranges.add((s, match[1]+'!'+match[2]))
            else:
                match = re.fullmatch(r'([A-Za-z0-9_]+)!(.+)',r)
                if match:
                    bound.allowed_ranges.add((s, "'"+match[1]+"'!"+match[2]))
        return bound

    @staticmethod
    def reservation(grant):
        return {'tool_calls': 1, 'estimated_cost_usd': 0}

    def discover(self, resource):
        """Inspect an explicitly supplied setup link using the operator's read consent."""
        spreadsheet_id = google_spreadsheet_id(resource)
        credentials = _google_credentials(self.token_file)
        base = 'https://sheets.googleapis.com/v4/spreadsheets/' + quote(spreadsheet_id, safe='')
        headers = {'Authorization': 'Bearer ' + credentials.token, 'Accept': 'application/json'}
        def read(url):
            with urlopen(Request(url, headers=headers), timeout=self.timeout) as response:
                return json.load(response)
        def column(number):
            result = ''
            while number:
                number, rest = divmod(number - 1, 26)
                result = chr(65 + rest) + result
            return result
        try:
            metadata = read(base + '?fields=properties.title,sheets.properties')
            sheets = metadata.get('sheets', [])
            if not sheets or len(sheets) > 32:
                raise RuntimeFailure('SHEETS_DISCOVERY_LIMIT', 'Use a spreadsheet with between one and 32 tabs.', 400)
            tables = []
            for sheet in sheets:
                prop = sheet['properties']
                if prop.get('sheetType', 'GRID') != 'GRID':
                    continue
                grid = prop['gridProperties']
                columns = min(grid['columnCount'], 128)
                named = "'" + prop['title'].replace("'", "''") + "'!"
                sampled = read(base + '/values/' + quote(named + f'A1:{column(columns)}10', safe='')).get('values', [])
                index = next((i for i, row in enumerate(sampled) if any(str(v).strip() for v in row)), None)
                if index is None:
                    continue
                actual_headers = sampled[index]
                if (any(not isinstance(h, str) or not h.strip() for h in actual_headers) or
                        len(set(actual_headers)) != len(actual_headers)):
                    raise RuntimeFailure('SHEETS_HEADERS_AMBIGUOUS', 'Each populated table needs unique, nonempty column headers.', 400)
                if grid['columnCount'] > 128 and len(actual_headers) == 128:
                    raise RuntimeFailure('SHEETS_DISCOVERY_LIMIT', 'Tables with more than 128 populated columns need a smaller source table.', 400)
                cell_range = named + f'A{index + 1}:{column(len(actual_headers))}{grid["rowCount"]}'
                tables.append({'title': prop['title'], 'range': cell_range, 'header_row': index + 1,
                               'headers': actual_headers, 'sample_summary': {
                                   'rows_inspected': len(sampled[index + 1:index + 4]),
                                   'nonempty_columns': {h: sum(len(r) > i and bool(str(r[i]).strip()) for r in sampled[index + 1:index + 4])
                                                        for i,h in enumerate(actual_headers)}}})
            if not tables:
                raise RuntimeFailure('SHEETS_TABLES_REQUIRED', 'Add table headers before generating the workflow.', 400)
            return {'spreadsheet_id': spreadsheet_id, 'title': metadata.get('properties', {}).get('title', ''), 'tables': tables}
        except RuntimeFailure:
            raise
        except HTTPError as exc:
            code = 'SHEETS_ACCESS_DENIED' if exc.code in {401, 403} else 'SHEETS_DISCOVERY_FAILED'
            raise RuntimeFailure(code, 'Cannot inspect this spreadsheet. Check the link and Google account access.', 403 if exc.code in {401,403} else 502) from None
        except Exception:
            raise RuntimeFailure('SHEETS_DISCOVERY_FAILED', 'Spreadsheet setup discovery failed.', 502) from None

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
        spreadsheet_id = google_spreadsheet_id(spreadsheet_id)
        if self.allowed_ranges is not None and (spreadsheet_id,cell_range) not in self.allowed_ranges:
            raise RuntimeFailure('SHEETS_READ_TARGET_NOT_AUTHORIZED', 'Read only the tables published for this workflow.', 403)
        configuration = self.resolve(grant['credential_reference'])
        if configuration.get('provider_id') != 'google_sheets':
            raise RuntimeFailure('SHEETS_NOT_CONFIGURED', 'Configure a Google Sheets credential reference.', 503)
        try:
            credentials = _google_credentials(self.token_file)
            base = 'https://sheets.googleapis.com/v4/spreadsheets/' + quote(spreadsheet_id, safe='')
            headers = {'Authorization': 'Bearer ' + credentials.token, 'Accept': 'application/json'}
            def read(url):
                with urlopen(Request(url, headers=headers), timeout=self.timeout) as response:
                    return json.load(response)
            try:
                payload = read(base + '/values/' + quote(cell_range, safe=''))
            except HTTPError as exc:
                if exc.code != 400:
                    raise
                match = re.fullmatch(r"('(?:[^']|'')+'|[^!]+)!([A-Z]+[1-9][0-9]*:[A-Z]+[1-9][0-9]*|[A-Z]+:[A-Z]+)", cell_range)
                if not match:
                    raise RuntimeFailure('SHEETS_RANGE_INVALID', 'Check the actual worksheet tab name and A1 range.', 400) from None
                requested = match[1]
                if requested.startswith("'"):
                    requested = requested[1:-1].replace("''", "'")
                metadata = read(base + '?fields=sheets.properties.title')
                titles = [sheet['properties']['title'] for sheet in metadata.get('sheets', [])]
                if len(titles) != 1 or requested in titles:
                    raise RuntimeFailure('SHEETS_RANGE_INVALID', 'The range is invalid or the requested tab is missing. Use the actual worksheet tab name.', 400) from None
                resolved = "'" + titles[0].replace("'", "''") + "'!" + match[2]
                payload = read(base + '/values/' + quote(resolved, safe=''))
            output = {'rows': payload.get('values', [])}
        except RuntimeFailure:
            raise
        except HTTPError as exc:
            if exc.code in {401, 403}:
                raise RuntimeFailure('SHEETS_ACCESS_DENIED', 'Google denied access to this Sheet. Reauthorize and confirm the authorized account can open the Sheet.', 403) from None
            raise RuntimeFailure('SHEETS_READ_FAILED', 'Google Sheets read failed; provider details are suppressed.', 502) from None
        except Exception:
            raise RuntimeFailure('SHEETS_READ_FAILED', 'Google Sheets read failed; provider details are suppressed.', 502) from None
        if list(Draft202012Validator(grant['output_schema']).iter_errors(output)):
            raise RuntimeFailure('CONNECTOR_OUTPUT_INVALID', 'The connector result does not meet the assignment schema.')
        return output

    def poll_changes(self, grant, inputs, previous_cursor=None, *, event_type=None, identity_field=None, required_fields=None, baseline_policy='current_only'):
        """Read a sheet range and return replay-safe row events plus a cursor.

        Scheduling and durable checkpoint storage remain lifecycle concerns; this
        method only performs the provider read and creates stable row identities.
        """
        output = self.invoke(grant, inputs, 'poll:' + (previous_cursor or 'initial'))
        rows = output.get('rows', [])
        headers = rows[0] if rows and isinstance(rows[0], list) else []
        data_rows = rows[1:] if headers else rows
        if event_type == 'row.created':
            return self._created_rows(inputs, headers, data_rows, previous_cursor, identity_field, required_fields or [], baseline_policy)
        current = {str(index): hashlib.sha256(json.dumps(row, separators=(',', ':')).encode()).hexdigest()
                   for index, row in enumerate(data_rows, start=2)}
        try:
            prior = json.loads(previous_cursor) if previous_cursor else {}
            previous_rows = prior.get('rows', {}) if isinstance(prior, dict) else {}
        except (TypeError, ValueError):
            previous_rows = {}
        changes = []
        for index, row in enumerate(data_rows, start=2):
            fingerprint = current[str(index)]
            if previous_rows.get(str(index)) == fingerprint:
                continue
            values = row if isinstance(row, list) else [row]
            record = ({str(header): values[position] if position < len(values) else ''
                       for position, header in enumerate(headers)} if headers else {'values': values})
            changes.append({'event_id': f'row:{index}:{fingerprint}', 'row_index': index,
                            'row': record, 'row_values': values})
        cursor = json.dumps({'version': 1, 'rows': current}, sort_keys=True, separators=(',', ':'))
        return {'cursor': cursor, 'changes': changes}

    @staticmethod
    def _created_rows(inputs, headers, rows, previous_cursor, identity_field, required_fields, baseline_policy='current_only'):
        if (not isinstance(identity_field, str) or not identity_field or not isinstance(required_fields, list) or
                any(not isinstance(field, str) or not field for field in required_fields) or
                any(not isinstance(header, str) or not header for header in headers) or
                len(set(headers)) != len(headers) or identity_field not in headers or set(required_fields) - set(headers)):
            raise RuntimeFailure('SHEETS_ROW_SCHEMA_INVALID', 'Configure unique headers, an identity field and existing required fields.', 400)
        try:
            prior = json.loads(previous_cursor) if previous_cursor else {'version': 2, 'seen': []}
            if prior.get('version') != 2 or not isinstance(prior.get('seen'), list):
                raise ValueError()
            seen = set(prior['seen'])
        except (TypeError, ValueError, AttributeError):
            raise RuntimeFailure('SHEETS_CURSOR_INVALID', 'The stored row-created cursor requires review.', 409) from None
        changes, identities = [], set()
        for index, values in enumerate(rows, start=2):
            if not isinstance(values, list):
                raise RuntimeFailure('SHEETS_ROW_SCHEMA_INVALID', 'Sheet rows must contain cell lists.', 400)
            record = {header: values[position] if position < len(values) else '' for position, header in enumerate(headers)}
            identity = str(record[identity_field]).strip()
            if not identity:
                continue
            if identity in identities:
                raise RuntimeFailure('SHEETS_DUPLICATE_IDENTITY', 'Each nonempty row identity must be unique.', 400)
            identities.add(identity)
            fingerprint = hashlib.sha256(json.dumps([inputs['spreadsheet_id'], inputs['range'], identity_field, identity]).encode()).hexdigest()
            # Baseline every existing identity, including partial rows. New partial
            # rows stay unseen until the workflow's required fields are populated.
            if previous_cursor is None and baseline_policy == 'current_only':
                seen.add(fingerprint)
                continue
            if fingerprint in seen or any(not str(record[field]).strip() for field in required_fields):
                continue
            seen.add(fingerprint)
            changes.append({'event_id': 'row.created:' + fingerprint, 'row_index': index, 'row': record, 'row_values': values})
        return {'cursor': json.dumps({'version': 2, 'seen': sorted(seen)}, separators=(',', ':')), 'changes': changes}


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
            credentials = _google_credentials(self.token_file)
            body = json.dumps({'range': cell_range, 'majorDimension': 'ROWS', 'values': values}).encode()
            request = Request(
                'https://sheets.googleapis.com/v4/spreadsheets/' + quote(spreadsheet_id, safe='') +
                '/values/' + quote(cell_range, safe='') + '?valueInputOption=USER_ENTERED',
                data=body, method='PUT', headers={'Authorization': 'Bearer ' + credentials.token,
                'Content-Type': 'application/json', 'Accept': 'application/json'})
            with urlopen(request, timeout=self.timeout) as response:
                payload = json.load(response)
            output = {'updated_cells': int(payload.get('updatedCells', 0))}
        except RuntimeFailure:
            raise
        except HTTPError as exc:
            if exc.code in {401, 403}:
                raise RuntimeFailure('SHEETS_ACCESS_DENIED', 'Google denied access to this Sheet. Reauthorize and confirm the authorized account can edit the Sheet.', 403) from None
            raise RuntimeFailure('SHEETS_UPDATE_FAILED', 'Google Sheets update failed; provider details are suppressed.', 502) from None
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
