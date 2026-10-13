"""Scoped Sheets operations using the existing range, target and record-lock rules."""
from copy import deepcopy
import math
import re
from urllib.parse import quote
from runtime.connectors import google_spreadsheet_id
from runtime.sheet_records import GoogleSheetsRecordConnector, table_range, column_label
from .common import Connector, denied


def spreadsheet_reference(inputs):
    """Accept a link or ID while keeping the existing tool field compatible."""
    return google_spreadsheet_id(inputs.get('spreadsheet_url', inputs.get('spreadsheet_id')))



def read_location(value):
    """Read-only tables may contain just a header row; write tables need capacity."""
    try: return table_range(value)
    except ValueError:
        match = re.fullmatch(r'(.*![A-Z]+)([1-9][0-9]*):([A-Z]+)([1-9][0-9]*)', value or '')
        if not match or match[2] != match[4]: raise
        row = int(match[2])
        tab, left, top, right, _ = table_range(f'{match[1]}{row}:{match[3]}{row + 1}')
        return tab, left, top, right, row


def canonical_range(value):
    tab, left, top, right, bottom = table_range(value)
    return f'{tab}!{column_label(left)}{top}:{column_label(right)}{bottom}'


def normalized_write_workflow(workflow):
    """Normalize copied reviewed locations, never the saved revision itself."""
    result = deepcopy(workflow)
    for target in result.get('metadata', {}).get('sheet_write_targets', []):
        target['spreadsheet_id'] = google_spreadsheet_id(target['spreadsheet_id'])
        target['range'] = canonical_range(target['range'])
    for node in result.get('nodes', []):
        if node.get('tool_id') != 'google_sheets_upsert_record': continue
        config = node.get('configuration', {})
        literals = config.get('input')
        if isinstance(literals, dict):
            for key, normalize in [('spreadsheet_id', google_spreadsheet_id), ('range', canonical_range)]:
                if key in literals: literals[key] = normalize(literals[key])
        mapping = config.get('input_mapping', {})
        import ast
        for key, normalize in [('spreadsheet_id', google_spreadsheet_id), ('range', canonical_range)]:
            if key not in mapping: continue
            try: mapping[key] = repr(normalize(ast.literal_eval(mapping[key])))
            except (ValueError, SyntaxError, TypeError): pass  # The existing validator reports unmapped setup constants.
    return result


def normalized_write_targets(targets):
    result = deepcopy(targets or [])
    for target in result:
        target['spreadsheet_id'] = google_spreadsheet_id(target['spreadsheet_id'])
        target['range'] = canonical_range(target['range'])
    return result


class SheetsRead(Connector):
    def __init__(self, definition, api, targets=None):
        super().__init__(definition, api)
        self.targets = {(google_spreadsheet_id(t['spreadsheet_id']), read_location(t['range'])) for t in (targets or [])}

    def execute(self, grant, inputs, effect_id, deadline):
        identifier = spreadsheet_reference(inputs)
        try: location = read_location(inputs['range'])
        except ValueError: denied('SHEETS_RANGE_INVALID', 'Use an approved bounded named table range.', 400)
        if self.targets and (identifier, location) not in self.targets:
            denied('SHEETS_READ_TARGET_NOT_AUTHORIZED', 'This spreadsheet table is outside extension read access.')
        tab, left, top, right, bottom = location
        cell_range = f'{tab}!{column_label(left)}{top}:{column_label(right)}{bottom}'
        result = self.api.request('sheets', 'GET', 'spreadsheets/' + quote(identifier, safe='') + '/values/' + quote(cell_range, safe=''),
                                  ['spreadsheets.readonly'], deadline=deadline)
        rows = result.get('values', [])
        if (not isinstance(rows, list) or len(rows) > bottom - top + 1 or
                any(not isinstance(row, list) or len(row) > right - left + 1 for row in rows)):
            denied('SHEETS_ROW_SCHEMA_INVALID', 'The returned rows exceed the approved table.', 502)
        return {'rows': rows}


class SheetsWrite(Connector):
    def __init__(self, definition, api, journal, targets, token_file, lock_directory):
        super().__init__(definition, api, journal)
        self.record = GoogleSheetsRecordConnector(lambda _: {'provider_id': 'google_sheets'}, token_file,
            normalized_write_targets(targets), timeout=30, lock_directory=lock_directory)

    def bind_workflow(self, workflow):
        bound = super().bind_workflow(workflow)
        bound.record = self.record.bind_workflow(normalized_write_workflow(workflow))
        return bound

    def execute(self, grant, inputs, effect_id, deadline):
        inputs = {**inputs, 'spreadsheet_id': spreadsheet_reference(inputs), 'range': canonical_range(inputs['range'])}
        target = self.record.target(inputs)
        identity, fields = inputs['identity'], inputs['fields']
        if not identity.strip() or identity != identity.strip() or any(
                isinstance(v, (dict, list)) or isinstance(v, float) and not math.isfinite(v) for v in fields.values()):
            denied('SHEETS_INPUT_INVALID', 'Use stable nonblank identities and finite scalar values.', 400)
        base = 'spreadsheets/' + quote(target['spreadsheet_id'], safe='')
        with self.record.locked(target['spreadsheet_id'], deadline):
            def action():
                tab, left, top, right, bottom = table_range(target['range'])
                result = self.api.request('sheets', 'GET', base + '/values/' + quote(target['range'], safe=''),
                                          ['spreadsheets'], deadline=deadline)
                rows = result.get('values', [])
                names = rows[0] if rows else []
                if (not isinstance(rows, list) or not isinstance(names, list) or not names or
                        any(not isinstance(name, str) or not name.strip() for name in names) or
                        len(set(names)) != len(names) or len(names) > right - left + 1 or
                        set(fields) - set(names) or target['identity_column'] not in names or
                        len(rows) > bottom - top + 1 or any(not isinstance(row, list) or len(row) > len(names) for row in rows)):
                    denied('SHEETS_ROW_SCHEMA_INVALID', 'Use unique configured headers and valid bounded rows.', 400)
                id_column = names.index(target['identity_column'])
                found, blank, seen = None, None, set()
                for offset, row in enumerate(rows[1:], 1):
                    key = str(row[id_column]).strip() if len(row) > id_column and row[id_column] is not None else ''
                    if key:
                        if key in seen: denied('SHEETS_DUPLICATE_IDENTITY', 'The table has duplicate record identities.', 400)
                        seen.add(key)
                        if key == identity: found = offset
                    elif all(v in ('', None) for v in row) and blank is None: blank = offset
                created = found is None
                if created and not target['allow_create']: denied('SHEETS_RECORD_NOT_FOUND', 'This target does not permit creating records.', 404)
                offset = found if found is not None else blank if blank is not None else len(rows)
                if top + offset > bottom: denied('SHEETS_TABLE_FULL', 'The approved table is full.', 409)
                updates = dict(fields)
                if created: updates[target['identity_column']] = identity
                data = [{'range': f'{tab}!{column_label(left + names.index(name))}{top + offset}',
                         'values': [['' if value is None else value]]} for name, value in updates.items()]
                result = self.api.request('sheets', 'POST', base + '/values:batchUpdate', ['spreadsheets'],
                    {'valueInputOption': 'RAW', 'data': data}, deadline)
                if result.get('totalUpdatedCells') != len(data):
                    denied('SHEETS_RECORD_UNCONFIRMED', 'The provider did not confirm every requested cell.', 502)
                return {'identity': identity, 'row_index': top + offset, 'created': created, 'updated_cells': len(data)}
            return self.write(effect_id, inputs, action)


class SheetsDiscover(SheetsRead):
    """Discover real table locations and headers, excluding business row contents."""
    def execute(self, grant, inputs, effect_id, deadline):
        identifier = spreadsheet_reference(inputs)
        if self.targets and not any(sheet == identifier for sheet, _ in self.targets):
            denied('SHEETS_READ_TARGET_NOT_AUTHORIZED', 'This spreadsheet is outside the optional operator restriction.')
        base = 'spreadsheets/' + quote(identifier, safe='')
        fields = 'spreadsheetId,properties(title),sheets(properties(sheetId,title,gridProperties(rowCount,columnCount)))'
        result = self.api.request('sheets', 'GET', base + '?fields=' + quote(fields, safe=''),
                                  ['spreadsheets.readonly'], deadline=deadline)
        if result.get('spreadsheetId', identifier) != identifier:
            denied('SHEETS_DISCOVERY_INVALID', 'The provider returned a different spreadsheet.', 502)
        sheets = result.get('sheets', [])
        if not isinstance(sheets, list): denied('SHEETS_DISCOVERY_INVALID', 'The spreadsheet metadata is invalid.', 502)
        tables, candidates = [], []
        for sheet in sheets:
            properties = sheet.get('properties', {})
            title, grid = properties.get('title'), properties.get('gridProperties', {})
            if not isinstance(title, str) or not title: continue
            rows, columns = grid.get('rowCount'), grid.get('columnCount')
            if type(rows) is not int or type(columns) is not int or rows < 1 or columns < 1: continue
            tab = "'" + title.replace("'", "''") + "'"
            if self.targets:
                locations = [location for sheet_id, location in sorted(self.targets) if sheet_id == identifier and location[0] == tab]
            else:
                count = min(columns, 200)
                locations = [(tab, 1, 1, count, min(rows, 1000, 100000 // count))]
            for location in locations:
                candidates.append((properties, location))
                if len(candidates) >= 51: break
            if len(candidates) >= 51: break
        for properties, (tab, left, top, right, bottom) in candidates[:50]:
            header_range = f'{tab}!{column_label(left)}{top}:{column_label(right)}{top}'
            header = self.api.request('sheets', 'GET', base + '/values/' + quote(header_range, safe=''),
                                     ['spreadsheets.readonly'], deadline=deadline)
            values = header.get('values', [])
            if (not isinstance(values, list) or len(values) > 1 or
                    values and (not isinstance(values[0], list) or len(values[0]) > right - left + 1)):
                denied('SHEETS_DISCOVERY_INVALID', 'The header response exceeds its requested row.', 502)
            names = ['' if value is None else str(value) for value in (values[0] if values else [])]
            tables.append({'title': properties['title'], 'range': f'{tab}!{column_label(left)}{top}:{column_label(right)}{bottom}',
                           'headers': names, 'grid_rows': properties['gridProperties']['rowCount'],
                           'grid_columns': properties['gridProperties']['columnCount']})
        return {'spreadsheet_id': identifier, 'title': str(result.get('properties', {}).get('title', ''))[:200],
                'tables': tables, 'has_more': len(candidates) > 50}
