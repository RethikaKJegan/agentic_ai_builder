"""Bounded report export into a newly created spreadsheet, never an existing file."""
import json
import math
from urllib.parse import quote, urlencode
from runtime.service import digest
from runtime.sheet_records import column_label
from .common import denied
from .sheet_creation import SheetsSetup


class ReportSheetsSetup(SheetsSetup):
    def manifest(self, inputs):
        value = super().manifest(inputs)
        value['row_count'] = max(2, max(len(tab['rows']) + 1 for tab in value['tabs']))
        cells = 0
        for tab in value['tabs']:
            for row in tab['rows']:
                if len(row) != len(tab['headers']):
                    denied('SHEETS_REPORT_INVALID', 'Every report row must match the header width.', 400)
                if any(type(cell) is float and not math.isfinite(cell) for cell in row):
                    denied('SHEETS_REPORT_INVALID', 'Report numbers must be finite.', 400)
                cells += len(row)
        if cells > 10000 or len(json.dumps(value, ensure_ascii=False).encode('utf-8')) > 256000:
            denied('SHEETS_REPORT_TOO_LARGE', 'Report exceeds 10,000 data cells or 256 KB.', 400)
        return value

    def creation_rows(self, spec):
        rows = super().creation_rows(spec)
        for row in spec['rows']:
            cells = []
            for value in row:
                # Explicit stringValue keeps formula-looking external text literal.
                key = 'boolValue' if type(value) is bool else 'numberValue' if type(value) in (int, float) else 'stringValue'
                cells.append({} if value is None else {'userEnteredValue': {key: value}})
            rows.append({'values': cells})
        return rows

    def receipt(self, value, metadata, deadline, require_owned=False):
        result = super().receipt(value, metadata, deadline, require_owned=require_owned)
        ranges = ["'" + tab['title'].replace("'", "''") + "'!A1:" +
                  column_label(len(tab['headers'])) + str(len(tab['rows']) + 1) for tab in value['tabs']]
        response = self.api.request('sheets', 'GET', 'spreadsheets/' + quote(result['spreadsheet_id'], safe='') +
            '/values:batchGet?' + urlencode([('ranges', r) for r in ranges] +
                [('valueRenderOption', 'UNFORMATTED_VALUE')]), ['spreadsheets.readonly'], deadline=deadline)
        actual = response.get('valueRanges')
        if not isinstance(actual, list) or len(actual) != len(value['tabs']):
            denied('SHEETS_REPORT_VERIFICATION_FAILED', 'Provider did not verify every report tab.', 502)
        for tab, received in zip(value['tabs'], actual):
            rows = received.get('values', []) if isinstance(received, dict) else None
            expected = [tab['headers'], *tab['rows']]
            if not isinstance(rows, list) or len(rows) > len(expected):
                denied('SHEETS_REPORT_VERIFICATION_FAILED', 'Provider report rows exceed the reviewed range.', 502)
            for index, target in enumerate(expected):
                row = rows[index] if index < len(rows) else []
                if not isinstance(row, list) or len(row) > len(target):
                    denied('SHEETS_REPORT_VERIFICATION_FAILED', 'Provider report row has unexpected width.', 502)
                for col, cell in enumerate(target):
                    found = row[col] if col < len(row) else None
                    # Sheets omits trailing blank cells/rows; bool is not a number.
                    blank = cell is None or cell == ''
                    equal = (found is None or found == '') if blank else (
                        type(found) is bool and type(cell) is bool and found == cell if type(found) is bool or type(cell) is bool
                        else found == cell)
                    if not equal:
                        denied('SHEETS_REPORT_VERIFICATION_FAILED', 'Created report differs from approved content; reconcile before retry.', 502)
        result.update(written_rows=sum(len(t['rows']) for t in value['tabs']), report_sha256=digest(value['tabs']))
        return result
