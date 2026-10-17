"""Domain-independent, restricted identity-based Google Sheets writes."""
from contextlib import contextmanager
import ast
import fcntl
import hashlib
import json
import math
from pathlib import Path
import re
import time
from urllib.error import HTTPError
from urllib.parse import quote
from urllib.request import Request

from jsonschema import Draft202012Validator
from registry.safety import reject_secrets
from . import connectors
from .service import RuntimeFailure


def column_number(label):
    result = 0
    for char in label:
        result = result * 26 + ord(char) - ord('A') + 1
    return result


def column_label(number):
    result = ''
    while number:
        number, digit = divmod(number - 1, 26)
        result = chr(ord('A') + digit) + result
    return result


def table_range(value):
    if not isinstance(value, str):
        raise ValueError('Use a string table range.')
    match = re.fullmatch(r"('(?:[^']|'')+'|[^'!]+)!([A-Z]+)([1-9][0-9]*):([A-Z]+)([1-9][0-9]*)", value or '')
    if not match:
        raise ValueError('Use an explicit named bounded table range, such as Reviews!A1:F1000.')
    tab, first_col, first_row, last_col, last_row = match.groups()
    left, top, right, bottom = column_number(first_col), int(first_row), column_number(last_col), int(last_row)
    if right < left or bottom <= top or (bottom - top + 1) * (right - left + 1) > 100000:
        raise ValueError('Configure a bounded table with headers and at most 100000 cells.')
    if tab.startswith("'"):
        tab = tab[1:-1].replace("''", "'")
    return "'" + tab.replace("'", "''") + "'", left, top, right, bottom


def write_targets(raw):
    """Validate explicit resource settings before workflow review or dispatch."""
    targets = json.loads(raw) if isinstance(raw, str) else raw
    if not isinstance(targets, list) or not targets:
        raise ValueError('Configure a nonempty array of sheet write targets.')
    seen = set()
    for target in targets:
        if not isinstance(target, dict) or set(target) != {'spreadsheet_id', 'range', 'identity_column', 'writable_columns', 'allow_create'}:
            raise ValueError('Each target requires spreadsheet_id, range, identity_column, writable_columns and allow_create.')
        try:
            target['spreadsheet_id'] = connectors.google_spreadsheet_id(target['spreadsheet_id'])
        except RuntimeFailure:
            raise ValueError('Configure a valid Google spreadsheet ID or URL.') from None
        location = table_range(target['range'])
        columns = target['writable_columns']
        if (not isinstance(target['identity_column'], str) or not target['identity_column'].strip() or
                not isinstance(columns, list) or not columns or any(not isinstance(c, str) or not c.strip() for c in columns) or
                len(set(columns)) != len(columns) or target['identity_column'] in columns or
                type(target['allow_create']) is not bool):
            raise ValueError('Use unique writable column names excluding the identity column, and a boolean allow_create.')
        key = (target['spreadsheet_id'], location)
        if key in seen:
            raise ValueError('A table may have only one write policy.')
        seen.add(key)
    # Overlapping tables cannot be separate authorization boundaries.
    for index, target in enumerate(targets):
        tab, left, top, right, bottom = table_range(target['range'])
        for other in targets[:index]:
            otab, oleft, otop, oright, obottom = table_range(other['range'])
            if (target['spreadsheet_id'] == other['spreadsheet_id'] and tab == otab and
                    max(left, oleft) <= min(right, oright) and max(top, otop) <= min(bottom, obottom)):
                raise ValueError('Write target tables must not overlap.')
    return targets


def effective_write_targets(workflow, ceiling=None):
    """Resolve reviewed revision settings, optionally narrowed by operator policy."""
    from planner.errors import PlannerFailure
    metadata = workflow.get('metadata', {})
    try:
        if 'sheet_write_targets' in metadata:
            targets = write_targets(json.loads(json.dumps(metadata['sheet_write_targets'])))
        elif ceiling:
            targets = write_targets(json.loads(json.dumps(ceiling)))
        else:
            raise ValueError('No workflow write destinations configured.')
    except (ValueError, TypeError):
        raise PlannerFailure('SHEETS_TARGET_REQUIRED', 'Describe spreadsheet IDs, table ranges, identity and output columns in the setup prompt.', field='metadata.sheet_write_targets') from None
    if ceiling:
        for target in targets:
            permitted = next((t for t in ceiling if t['spreadsheet_id'] == target['spreadsheet_id'] and
                table_range(t['range']) == table_range(target['range']) and t['identity_column'] == target['identity_column']), None)
            if (permitted is None or set(target['writable_columns']) - set(permitted['writable_columns']) or
                    target['allow_create'] and not permitted['allow_create']):
                raise PlannerFailure('SHEETS_TARGET_DENIED', 'Workflow spreadsheet access exceeds the operator restriction.', field='metadata.sheet_write_targets')
    return targets


def normalize_generated_record_schemas(workflow):
    """Tighten explicit save-field output schemas in fresh proposals only."""
    for node in workflow.get('nodes', []):
        if node.get('tool_id') != 'google_sheets_upsert_record':
            continue
        expression = node.get('configuration', {}).get('input_mapping', {}).get('fields')
        try:
            value = ast.parse(expression, mode='eval').body
            path = []
            while isinstance(value, (ast.Attribute, ast.Subscript)):
                path.insert(0, value.attr if isinstance(value, ast.Attribute) else ast.literal_eval(value.slice))
                value = value.value
            if not isinstance(value, ast.Name) or value.id not in {'outputs', 'nodes'} or len(path) < 2:
                continue
            source = next(n for n in workflow['nodes'] if n['node_id'] == path[0] and n['kind'] == 'agent')
            schema = next(a['output_schema'] for a in workflow['agents'] if a['agent_id'] == source['agent_id'])
            for key in path[1:]:
                schema = schema['properties'][key]
            if schema.get('type') == 'object' and schema.get('properties') and 'additionalProperties' not in schema:
                schema['additionalProperties'] = False
        except (ValueError, TypeError, KeyError, SyntaxError, StopIteration):
            continue


def validate_record_workflow(workflow, targets=None):
    """Validate configured graph destinations at generation/review/publication."""
    from planner.errors import PlannerFailure
    nodes = [n for n in workflow['nodes'] if n.get('tool_id') == 'google_sheets_upsert_record']
    referenced = any(t['tool_id'] == 'google_sheets_upsert_record' for t in workflow['tools'])
    metadata = workflow.get('metadata', {})
    # An empty list declares no write destinations. Read-only workflows may
    # include it even when another connector (such as SMTP) performs a write.
    has_targets = 'sheet_write_targets' in metadata and metadata['sheet_write_targets'] != []
    if not (referenced or nodes or has_targets):
        return []
    targets = effective_write_targets(workflow, targets)
    for node in nodes:
        configuration = node.get('configuration', {})
        if 'input' in configuration and 'input_mapping' in configuration:
            raise PlannerFailure('SHEETS_RECORD_MAPPING_REQUIRED', 'Use one complete input object or one input mapping.', field=node['node_id'])
        literals = dict(configuration.get('input', {}))
        mapping = configuration.get('input_mapping', {})
        for key in ('spreadsheet_id', 'range', 'identity_column'):
            if key in mapping:
                try:
                    literals[key] = ast.literal_eval(mapping[key])
                except (ValueError, SyntaxError, TypeError):
                    raise PlannerFailure('SHEETS_TARGET_REQUIRED', 'Save table locations as setup constants.', field=node['node_id']) from None
        matched = [t for t in targets if all(literals.get(k) == t[k] for k in ('spreadsheet_id', 'range', 'identity_column'))]
        if len(matched) != 1:
            raise PlannerFailure('SHEETS_TARGET_DENIED', 'The save table is not an approved write target.', field=node['node_id'])
        if any(k not in literals and k not in mapping for k in ('identity', 'fields')):
            raise PlannerFailure('SHEETS_RECORD_MAPPING_REQUIRED', 'Map a stable identity and structured record fields.', field=node['node_id'])
        if 'fields' in literals and (not isinstance(literals['fields'], dict) or set(literals['fields']) - set(matched[0]['writable_columns'])):
            raise PlannerFailure('SHEETS_TARGET_DENIED', 'The save fields include unapproved columns.', field=node['node_id'])
        if 'fields' in mapping:
            # Save only an object already checked against a declared agent output
            # schema. Runtime also checks actual values and column authorization.
            try:
                expression = ast.parse(mapping['fields'], mode='eval').body
                path = []
                while isinstance(expression, (ast.Attribute, ast.Subscript)):
                    path.insert(0, expression.attr if isinstance(expression, ast.Attribute) else ast.literal_eval(expression.slice))
                    expression = expression.value
                if not isinstance(expression, ast.Name) or expression.id not in {'outputs', 'nodes'} or len(path) < 2:
                    raise ValueError()
                source = next(n for n in workflow['nodes'] if n['node_id'] == path[0] and n['kind'] == 'agent')
                schema = next(a['output_schema'] for a in workflow['agents'] if a['agent_id'] == source['agent_id'])
                for key in path[1:]:
                    schema = schema['properties'][key]
                properties = schema.get('properties', {})
                if (schema.get('type') != 'object' or schema.get('additionalProperties') is not False or not properties or
                        not schema.get('required') or set(properties) - set(matched[0]['writable_columns'])):
                    raise ValueError()
                for property_schema in properties.values():
                    types = property_schema.get('type')
                    types = [types] if isinstance(types, str) else types
                    if not types or set(types) - {'string', 'number', 'integer', 'boolean', 'null'}:
                        raise ValueError()
            except (ValueError, KeyError, TypeError, SyntaxError, StopIteration):
                raise PlannerFailure('SHEETS_RECORD_SCHEMA_REQUIRED', 'Map fields from an explicit scalar-field agent output schema containing only approved columns.', field=node['node_id']) from None
    return targets


class GoogleSheetsRecordConnector:
    external_write = True

    def __init__(self, resolve, token_file, targets=None, timeout=15, require_approval=True, lock_directory=None):
        self.resolve, self.token_file = resolve, token_file
        self.targets = write_targets(json.loads(json.dumps(targets))) if targets else []
        self.timeout, self.require_approval = timeout, require_approval
        if not 1 <= timeout <= 120:
            raise ValueError('Configure a bounded connector timeout.')
        self.lock_directory = Path(lock_directory or Path(__file__).resolve().parents[1] / '.local/sheet-record-locks')

    def bind_workflow(self, workflow):
        from planner.errors import PlannerFailure
        try:
            targets = validate_record_workflow(workflow, self.targets)
        except PlannerFailure as exc:
            raise RuntimeFailure(exc.code, 'The reviewed workflow does not authorize this spreadsheet access.', 403) from None
        return GoogleSheetsRecordConnector(self.resolve, self.token_file, targets, self.timeout,
                                          self.require_approval, self.lock_directory)

    @staticmethod
    def reservation(grant):
        # One registered tool invocation. Its internal read/write HTTP requests
        # do not create extra agent tool invocations or expand reviewed limits.
        return {'tool_calls': 1, 'estimated_cost_usd': 0}

    def target(self, inputs):
        matches = [t for t in self.targets if all(inputs.get(k) == t[k] for k in ('spreadsheet_id', 'range', 'identity_column'))]
        if len(matches) != 1 or set(inputs.get('fields', {})) - set(matches[0]['writable_columns']):
            raise RuntimeFailure('SHEETS_TARGET_DENIED', 'The table or output columns are not approved.', 403)
        return matches[0]

    @contextmanager
    def locked(self, spreadsheet_id, deadline):
        self.lock_directory.mkdir(parents=True, exist_ok=True)
        filename = hashlib.sha256(spreadsheet_id.encode()).hexdigest() + '.lock'
        with (self.lock_directory / filename).open('a') as handle:
            while True:
                try:
                    fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
                    break
                except BlockingIOError:
                    if time.monotonic() >= deadline:
                        raise RuntimeFailure('SHEETS_LOCK_TIMEOUT', 'The record table is busy; no write was attempted.')
                    time.sleep(min(.02, max(0, deadline - time.monotonic())))
            try:
                yield
            finally:
                fcntl.flock(handle, fcntl.LOCK_UN)

    def invoke(self, grant, inputs, effect_id):
        reject_secrets(inputs)
        if (grant.get('authorization_state') != 'authorized' or grant.get('tool_id') != 'google_sheets_upsert_record' or
                not grant.get('authorization_reference') or not grant.get('credential_reference') or
                grant.get('destination') != 'configured_spreadsheet' or
                ((self.require_approval or grant.get('approval_required', True)) and not grant.get('approval_reference'))):
            raise RuntimeFailure('SHEETS_NOT_AUTHORIZED', 'Record writes require an exact approved binding.', 403)
        if list(Draft202012Validator(grant['input_schema']).iter_errors(inputs)):
            raise RuntimeFailure('CONNECTOR_INPUT_INVALID', 'Record inputs do not match the registered schema.', 400)
        target = self.target(inputs)
        identity = inputs['identity']
        if not identity.strip() or identity != identity.strip():
            raise RuntimeFailure('SHEETS_INPUT_INVALID', 'Use a nonblank stable identity without surrounding whitespace.', 400)
        fields = inputs['fields']
        if any(isinstance(v, (dict, list)) or isinstance(v, float) and not math.isfinite(v) for v in fields.values()):
            raise RuntimeFailure('SHEETS_INPUT_INVALID', 'Record fields must be finite scalar values.', 400)
        if self.resolve(grant['credential_reference']).get('provider_id') != 'google_sheets':
            raise RuntimeFailure('SHEETS_NOT_CONFIGURED', 'Configure a Google Sheets credential.', 503)
        deadline = time.monotonic() + self.timeout
        with self.locked(inputs['spreadsheet_id'], deadline):
            credentials = connectors._google_credentials(self.token_file)
            granted = set(getattr(credentials, 'granted_scopes', None) or getattr(credentials, 'scopes', None) or [])
            if not granted & {'https://www.googleapis.com/auth/spreadsheets',
                              'https://www.googleapis.com/auth/drive',
                              'https://www.googleapis.com/auth/drive.file'}:
                raise RuntimeFailure('GOOGLE_WRITE_CONSENT_REQUIRED',
                    'The Google connection is read-only. Run scripts/authorize_google.py and allow Google Sheets edit access.', 403)
            headers = {'Authorization': 'Bearer ' + credentials.token, 'Content-Type': 'application/json'}
            base = 'https://sheets.googleapis.com/v4/spreadsheets/' + quote(inputs['spreadsheet_id'], safe='')

            def request(url, data=None):
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    raise RuntimeFailure('SHEETS_TIMEOUT', 'The record operation exceeded its time limit.')
                req = Request(url, data=json.dumps(data).encode() if data is not None else None,
                              method='POST' if data is not None else 'GET', headers=headers)
                try:
                    with connectors.urlopen(req, timeout=remaining) as response:
                        return json.load(response)
                except HTTPError as exc:
                    if exc.code in {401, 403}:
                        raise RuntimeFailure('SHEETS_ACCESS_DENIED', 'Google denied access to the configured table.', 403) from None
                    category = ('SHEETS_RATE_LIMITED' if exc.code == 429 else
                                'SHEETS_PROVIDER_UNAVAILABLE' if exc.code >= 500 else 'SHEETS_REQUEST_REJECTED')
                    raise RuntimeFailure(category, 'Google rejected the record request; inspect the tracking projection before retrying.', 502) from None
                except RuntimeFailure:
                    raise
                except Exception:
                    raise RuntimeFailure('SHEETS_RECORD_FAILED', 'The record provider result is uncertain; no automatic replay is allowed.', 502) from None

            rows = request(base + '/values/' + quote(inputs['range'], safe='') + '?valueRenderOption=UNFORMATTED_VALUE').get('values', [])
            tab, left, top, right, bottom = table_range(inputs['range'])
            names = rows[0] if rows else []
            if (not names or any(not isinstance(c, str) or not c.strip() for c in names) or
                    len(names) != len(set(names)) or len(names) > right - left + 1 or
                    set([target['identity_column'], *target['writable_columns']]) - set(names) or
                    len(rows) > bottom - top + 1 or any(not isinstance(r, list) or len(r) > len(names) for r in rows)):
                raise RuntimeFailure('SHEETS_ROW_SCHEMA_INVALID', 'The table must have unique configured headers and valid rows.', 400)
            id_column = names.index(target['identity_column'])
            found, seen, blank = None, set(), None
            for offset, row in enumerate(rows[1:], start=1):
                key = str(row[id_column]).strip() if len(row) > id_column and row[id_column] is not None else ''
                if key:
                    if key in seen:
                        raise RuntimeFailure('SHEETS_DUPLICATE_IDENTITY', 'The table contains duplicate stable identities.', 400)
                    seen.add(key)
                    if key == identity:
                        found = offset
                elif all(v in ('', None) for v in row) and blank is None:
                    blank = offset
            created = found is None
            if created and not target['allow_create']:
                raise RuntimeFailure('SHEETS_RECORD_NOT_FOUND', 'The stable identity does not exist in this table.', 404)
            offset = found if found is not None else blank if blank is not None else len(rows)
            if top + offset > bottom:
                raise RuntimeFailure('SHEETS_TABLE_FULL', 'The approved table has no empty record capacity.', 409)
            existing = rows[offset] if offset < len(rows) else []
            updates = dict(fields)
            if created:
                updates[target['identity_column']] = identity
            data = []
            for name, value in updates.items():
                index = names.index(name)
                previous = existing[index] if index < len(existing) else ''
                value = '' if value is None else value
                if previous == value and type(previous) is type(value):
                    continue
                data.append({'range': f'{tab}!{column_label(left + index)}{top + offset}', 'values': [[value]]})
            updated = 0
            if data:
                result = request(base + '/values:batchUpdate', {'valueInputOption': 'RAW', 'data': data})
                updated = result.get('totalUpdatedCells')
                if type(updated) is not int or updated != len(data):
                    raise RuntimeFailure('SHEETS_RECORD_UNCONFIRMED', 'The write response did not confirm every requested cell.', 502)
            output = {'identity': identity, 'row_index': top + offset, 'created': created, 'updated_cells': updated}
            if list(Draft202012Validator(grant['output_schema']).iter_errors(output)):
                raise RuntimeFailure('CONNECTOR_OUTPUT_INVALID', 'The record result does not match its schema.')
            return output
