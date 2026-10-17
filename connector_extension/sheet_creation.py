"""Approved, bounded spreadsheet provisioning with stable setup receipts."""
from copy import deepcopy
import json
import os
from pathlib import Path
import re
import sqlite3
from workflow_api.auxiliary_database import connection as database_connection
import time
from urllib.parse import quote, urlencode
from jsonschema import Draft202012Validator
from runtime.connectors import google_spreadsheet_id
from runtime.sheet_records import column_label
from runtime.service import digest
from .common import Connector, denied

MARKER_KEY = 'builder_extension_setup'
MAX_CELLS = 1_000_000
META_FIELDS = 'spreadsheetId,properties(title),developerMetadata,sheets(properties,developerMetadata)'


def setup_inputs(inputs):
    """Normalize only copies; never alter a saved workflow revision."""
    value = deepcopy(inputs)
    if 'spreadsheet_url' in value:
        value['spreadsheet_id'] = google_spreadsheet_id(value.pop('spreadsheet_url'))
    elif 'spreadsheet_id' in value:
        value['spreadsheet_id'] = google_spreadsheet_id(value['spreadsheet_id'])
    value.setdefault('row_count', 1000)
    titles = set()
    for table in value['tabs']:
        title = table['title']
        if title != title.strip() or any(c in title for c in '[]:*?/\\\r\n\x00') or title.casefold() in titles:
            denied('SHEETS_SETUP_INVALID', 'Use unique, unambiguous tab titles without reserved characters.', 400)
        titles.add(title.casefold())
        headers = table['headers']
        if (len(set(headers)) != len(headers) or
                any(h != h.strip() or not h or any(c in h for c in '\r\n\x00') for h in headers)):
            denied('SHEETS_SETUP_INVALID', 'Use unique nonblank literal column headers.', 400)
    if sum(value['row_count'] * len(t['headers']) for t in value['tabs']) > MAX_CELLS:
        denied('SHEETS_SETUP_TOO_LARGE', 'Requested tables exceed the one-million-cell setup bound.', 400)
    return value


class SheetResourceStore:
    """Resource ownership only; this is not the future procurement case database."""
    def __init__(self, root, database_url=None):
        self.database_url=database_url
        self.path = Path(root) / 'sheet-resources.sqlite3'
        if self.path.is_symlink(): denied('STATE_PATH_INVALID', 'Resource state cannot be a symlink.')
        with database_connection(self.path,database_url=self.database_url) as db:
            db.execute('CREATE TABLE IF NOT EXISTS resources (workspace TEXT, project TEXT, spreadsheet TEXT, '
                       'sheet INTEGER, spreadsheet_owned INTEGER, tab_owned INTEGER, manifest TEXT, '
                       'workflow TEXT, revision INTEGER, PRIMARY KEY(workspace,project,spreadsheet,sheet))')
            db.execute('CREATE TABLE IF NOT EXISTS observations (workspace TEXT, project TEXT, marker TEXT, '
                       'spreadsheet TEXT, workflow TEXT, revision INTEGER, PRIMARY KEY(workspace,project,marker))')
        if self.path.exists():os.chmod(self.path, 0o600)

    def observe(self, namespace, project, marker, identifier):
        with database_connection(self.path,database_url=self.database_url) as db:
            db.execute('INSERT OR IGNORE INTO observations VALUES (?,?,?,?,?,?)',
                       (namespace[0], project, marker, identifier, namespace[1], namespace[2]))

    def remember(self, namespace, receipt):
        with database_connection(self.path,database_url=self.database_url) as db:
            for table in receipt['tabs']:
                db.execute('INSERT INTO resources VALUES (?,?,?,?,?,?,?,?,?) '
                           'ON CONFLICT(workspace,project,spreadsheet,sheet) DO UPDATE SET '
                           'spreadsheet_owned=MAX(resources.spreadsheet_owned,excluded.spreadsheet_owned), '
                           'tab_owned=MAX(resources.tab_owned,excluded.tab_owned), manifest=excluded.manifest',
                           (namespace[0], receipt['project_id'], receipt['spreadsheet_id'], table['sheet_id'],
                            int(receipt['spreadsheet_created']), int(table['created']), json.dumps(receipt),
                            namespace[1], namespace[2]))


class SheetsSetup(Connector):
    def __init__(self, definition, api, journal, resources, read_targets=None, write_targets=None):
        super().__init__(definition, api, journal)
        self.resources = resources
        self.read_ids = {google_spreadsheet_id(t['spreadsheet_id']) for t in (read_targets or [])}
        self.write_ceiling = bool(write_targets)

    def manifest(self, inputs):
        if not self.namespace: denied('WORKSPACE_REQUIRED', 'Bind setup to a reviewed workspace/workflow revision.')
        if list(Draft202012Validator(self.definition['input_schema']).iter_errors(inputs)):
            denied('CONNECTOR_INPUT_INVALID', 'Use the exact reviewed spreadsheet setup input.', 400)
        value = setup_inputs(inputs)
        if self.write_ceiling:
            denied('SHEETS_CREATION_CEILING', 'Existing fixed write ceilings do not authorize spreadsheet/tab provisioning.')
        if self.read_ids and ('spreadsheet_id' not in value or value['spreadsheet_id'] not in self.read_ids):
            denied('SHEETS_READ_TARGET_NOT_AUTHORIZED', 'Setup verification is outside the operator read ceiling.')
        return value

    def stable_effect(self, value):
        return 'sheet_setup_' + digest([self.namespace[0], value['project_id'], value['creation_key']])

    def marker(self, value):
        return digest([self.definition['tool_id'], self.stable_effect(value)])

    def journal_row(self, value):
        key = digest([self.definition['tool_id'], self.stable_effect(value)])
        with self.journal.connection(write=False) as db:
            row = db.execute('SELECT fingerprint,state,result FROM effects WHERE key=?', (key,)).fetchone()
        if row and row[0] != digest(value):
            denied('EFFECT_REFERENCE_MISMATCH', 'This project creation key belongs to different reviewed inputs.')
        return key, row

    def metadata(self, identifier, deadline):
        result = self.api.request('sheets', 'GET', 'spreadsheets/' + quote(identifier, safe='') + '?fields=' +
                                  quote(META_FIELDS, safe=''), ['spreadsheets.readonly'], deadline=deadline)
        if result.get('spreadsheetId') != identifier or not isinstance(result.get('sheets'), list) or len(result['sheets']) > 500:
            denied('SHEETS_SETUP_INVALID_RESULT', 'Provider metadata does not identify a bounded expected spreadsheet.', 502)
        return result

    @staticmethod
    def table_map(metadata):
        result = {}
        for sheet in metadata['sheets']:
            p = sheet.get('properties', {})
            if not isinstance(p.get('title'), str) or type(p.get('sheetId')) is not int:
                denied('SHEETS_SETUP_INVALID_RESULT', 'Provider returned invalid tab identities.', 502)
            key = p['title'].casefold()
            if key in result: denied('SHEETS_TAB_CONFLICT', 'Provider tab names are ambiguous.')
            result[key] = sheet
        return result

    def header_rows(self, identifier, tables, deadline):
        if not tables: return []
        ranges = []
        for table in tables:
            p = table['properties']; grid = p.get('gridProperties', {})
            columns, rows = grid.get('columnCount'), grid.get('rowCount')
            if type(columns) is not int or not 1 <= columns <= 100 or type(rows) is not int or rows < 1:
                denied('SHEETS_TAB_CONFLICT', 'Existing table dimensions cannot be safely verified within setup bounds.')
            tab = "'" + p['title'].replace("'", "''") + "'"
            ranges.append(tab + '!A1:' + column_label(columns) + '1')
        result = self.api.request('sheets', 'GET', 'spreadsheets/' + quote(identifier, safe='') +
            '/values:batchGet?' + urlencode([('ranges', r) for r in ranges] + [('valueRenderOption', 'UNFORMATTED_VALUE')]),
            ['spreadsheets.readonly'], deadline=deadline)
        values = result.get('valueRanges')
        if not isinstance(values, list) or len(values) != len(tables):
            denied('SHEETS_SETUP_INVALID_RESULT', 'Provider did not confirm every requested header row.', 502)
        headers = []
        for value in values:
            rows = value.get('values', [])
            if not isinstance(rows, list) or len(rows) > 1 or rows and not isinstance(rows[0], list):
                denied('SHEETS_SETUP_INVALID_RESULT', 'Provider header response exceeds one row.', 502)
            header = list(rows[0]) if rows else []
            while header and header[-1] == '': header.pop()
            headers.append(header)
        return headers

    def has_marker(self, metadata, marker, sheet_id=None):
        entries = list(metadata.get('developerMetadata', []))
        for sheet in metadata['sheets']: entries.extend(sheet.get('developerMetadata', []))
        return any(entry.get('metadataKey') == MARKER_KEY and entry.get('metadataValue') == marker and
                   (entry.get('location', {}).get('spreadsheet') is True if sheet_id is None else
                    entry.get('location', {}).get('sheetId') == sheet_id) for entry in entries)

    def receipt(self, value, metadata, deadline, require_owned=False):
        identifier = metadata['spreadsheetId']; existing = self.table_map(metadata); tables = []
        for spec in value['tabs']:
            table = existing.get(spec['title'].casefold())
            if not table or table['properties']['title'] != spec['title']:
                denied('SHEETS_TAB_CONFLICT', 'A reviewed tab is missing or has a different title.')
            tables.append(table)
        headers = self.header_rows(identifier, tables, deadline); marker = self.marker(value); result = []
        for spec, table, actual in zip(value['tabs'], tables, headers):
            if actual != spec['headers']:
                denied('SHEETS_TAB_CONFLICT', 'Existing headers differ from the reviewed setup; no overwrite is permitted.')
            p = table['properties']; owned = self.has_marker(metadata, marker, p['sheetId'])
            if require_owned and not owned: denied('SHEETS_SETUP_RECONCILIATION_REQUIRED', 'A tab lacks the expected creation marker.')
            result.append({'sheet_id': p['sheetId'], 'title': p['title'], 'headers': actual,
                           'grid_rows': p['gridProperties']['rowCount'], 'grid_columns': p['gridProperties']['columnCount'],
                           'created': owned})
        spreadsheet_owned = self.has_marker(metadata, marker)
        if require_owned and (not spreadsheet_owned or metadata.get('properties', {}).get('title') != value['title']):
            denied('SHEETS_SETUP_RECONCILIATION_REQUIRED', 'The spreadsheet creation marker/title does not match this intent.')
        proposals = []
        for table in result:
            if len(table['headers']) < 2 or table['grid_rows'] < 2: continue
            tab = "'" + table['title'].replace("'", "''") + "'"
            proposals.append({'spreadsheet_id': identifier, 'range': tab + '!A1:' + column_label(len(table['headers'])) +
                              str(min(value['row_count'], table['grid_rows'])), 'identity_column': table['headers'][0],
                              'writable_columns': table['headers'][1:], 'allow_create': True})
        return {'project_id': value['project_id'], 'creation_key': value['creation_key'], 'spreadsheet_id': identifier,
                'spreadsheet_url': 'https://docs.google.com/spreadsheets/d/' + identifier + '/edit',
                'spreadsheet_created': spreadsheet_owned, 'tabs': result, 'proposed_write_targets': proposals, 'reused': False}

    @staticmethod
    def marker_value(marker, sheet_id=None):
        return {'metadataKey': MARKER_KEY, 'metadataValue': marker, 'visibility': 'DOCUMENT',
                'location': {'spreadsheet': True} if sheet_id is None else {'sheetId': sheet_id}}

    def execute(self, grant, inputs, effect_id, deadline):
        value = self.manifest(inputs); key, old = self.journal_row(value)
        create = self.definition['tool_id'] == 'extension_sheets_create'
        if old:
            if old[1] != 'completed':
                denied('UNKNOWN_INVOCATION_RESULT', 'Setup result is uncertain; reconcile it before another create.')
            stored = json.loads(old[2]); metadata = self.metadata(stored['spreadsheet_id'], deadline)
            result = self.receipt(value, metadata, deadline, require_owned=create); result['reused'] = True
            self.resources.remember(self.namespace, result)
            return result
        remaining = deadline - time.monotonic()
        if remaining <= 0: denied('CONNECTOR_TIMEOUT', 'Setup deadline expired.', 504)
        self.api.token(['spreadsheets'], min(30, remaining))
        metadata = existing = None
        if not create:
            metadata = self.metadata(value['spreadsheet_id'], deadline); existing = self.table_map(metadata)
            found = [existing[spec['title'].casefold()] for spec in value['tabs'] if spec['title'].casefold() in existing]
            actual = self.header_rows(value['spreadsheet_id'], found, deadline)
            for table, headers in zip(found, actual):
                spec = next(t for t in value['tabs'] if t['title'].casefold() == table['properties']['title'].casefold())
                if table['properties']['title'] != spec['title'] or headers != spec['headers']:
                    denied('SHEETS_TAB_CONFLICT', 'An existing tab/header conflicts; no mutation was made.')
        def provision():
            marker = self.marker(value)
            if create:
                sheets = []
                for index, spec in enumerate(value['tabs'], 1):
                    sheets.append({'properties': {'sheetId': index, 'title': spec['title'],
                        'gridProperties': {'rowCount': value['row_count'], 'columnCount': len(spec['headers'])}},
                        'developerMetadata': [self.marker_value(marker,index)],
                        'data': [{'startRow': 0, 'startColumn': 0, 'rowData': [{'values': [
                            {'userEnteredValue': {'stringValue': h}} for h in spec['headers']]}]}]})
                metadata_tags = [self.marker_value(marker)]
                body = {'properties': {'title': value['title']}, 'sheets': sheets, 'developerMetadata': metadata_tags}
                response = self.api.request('sheets', 'POST', 'spreadsheets', ['spreadsheets'], body, deadline)
                identifier = response.get('spreadsheetId')
                if not isinstance(identifier, str) or not re.fullmatch(r'[A-Za-z0-9_-]{1,255}', identifier):
                    denied('SHEETS_SETUP_INVALID_RESULT', 'Provider creation did not return a spreadsheet identity.', 502)
                self.resources.observe(self.namespace, value['project_id'], marker, identifier)
                return self.receipt(value, self.metadata(identifier, deadline), deadline, require_owned=True)
            identifier = value['spreadsheet_id']; updated_metadata = metadata
            used = {table['properties']['sheetId'] for table in existing.values()}; requests = []; candidate = 1
            for spec in value['tabs']:
                if spec['title'].casefold() in existing: continue
                while candidate in used: candidate += 1
                used.add(candidate)
                requests.extend([{'addSheet': {'properties': {'sheetId': candidate, 'title': spec['title'],
                    'gridProperties': {'rowCount': value['row_count'], 'columnCount': len(spec['headers'])}}}},
                    {'updateCells': {'start': {'sheetId': candidate, 'rowIndex': 0, 'columnIndex': 0},
                        'rows': [{'values': [{'userEnteredValue': {'stringValue': h}} for h in spec['headers']]}],
                        'fields': 'userEnteredValue'}},
                    {'createDeveloperMetadata': {'developerMetadata': self.marker_value(marker, candidate)}}])
            if requests:
                self.api.request('sheets', 'POST', 'spreadsheets/' + quote(identifier, safe='') + ':batchUpdate',
                    ['spreadsheets'], {'requests': requests}, deadline)
                self.resources.observe(self.namespace, value['project_id'], marker, identifier)
                updated_metadata = self.metadata(identifier, deadline)
            return self.receipt(value, updated_metadata, deadline)
        # Stable setup identity spans new run IDs; inputs remain fingerprinted.
        result = self.write(self.stable_effect(value), value, provision)
        self.resources.remember(self.namespace, result)
        return result

    def reconcile(self, inputs, identifier):
        """Operator-only read verification; no provider mutation or blind retry."""
        value = self.manifest(inputs); key, old = self.journal_row(value)
        if not old: denied('SHEETS_SETUP_RECONCILIATION_REQUIRED', 'No existing intent matches this setup key.')
        create = self.definition['tool_id'] == 'extension_sheets_create'
        identifier = google_spreadsheet_id(identifier)
        if not create and identifier != value['spreadsheet_id']:
            denied('SHEETS_SETUP_RECONCILIATION_REQUIRED', 'Reconcile only the reviewed destination.')
        deadline = time.monotonic() + self.timeout
        result = self.receipt(value, self.metadata(identifier, deadline), deadline, require_owned=create)
        if list(Draft202012Validator(self.definition['output_schema']).iter_errors(result)):
            denied('SHEETS_SETUP_INVALID_RESULT', 'Reconciled setup does not match the output schema.')
        with self.journal.connection() as db:
            db.execute('BEGIN IMMEDIATE')
            current = db.execute('SELECT fingerprint,state,result FROM effects WHERE key=?', (key,)).fetchone()
            if not current or current[0] != digest(value): denied('EFFECT_REFERENCE_MISMATCH', 'The setup intent changed.')
            if current[1] == 'completed' and json.loads(current[2])['spreadsheet_id'] != identifier:
                denied('EFFECT_REFERENCE_MISMATCH', 'Do not replace a completed setup with another spreadsheet.')
            db.execute("UPDATE effects SET state='completed',result=? WHERE key=?", (json.dumps(result), key))
        self.resources.remember(self.namespace, result)
        return result
