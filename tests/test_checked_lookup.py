"""Specialist evidence extraction after an authorized Sheets read."""
import unittest

from runtime.delegation import checked_lookup_output


class CheckedLookupTests(unittest.TestCase):
    def setUp(self):
        self.agent = {'output_schema': {'type': 'object', 'additionalProperties': False,
            'properties': {'findings': {'type': 'string'}, 'matching_record_count': {'type': 'integer'},
                           'missing': {'type': 'boolean'}, 'duplicate': {'type': 'boolean'}},
            'required': ['findings', 'matching_record_count', 'missing', 'duplicate']}}
        self.request = {'spreadsheet_id': 'another-spreadsheet', 'range': 'Shipments!A1:E1000', 'batch_id': 'B-2401'}
        self.rows = {'rows': [['batch_id', 'shipment_id', 'dispatched_at', 'delivery_status', 'notes'],
                              ['B-2401', 'S-9001', '2026-10-11 14:30', 'Delivered', 'Outer cartons intact at dispatch']]}

    def test_verified_single_match_uses_returned_cells(self):
        result = checked_lookup_output(self.agent, self.request, 'google_sheets_read_rows', self.rows)
        self.assertEqual(result['matching_record_count'], 1)
        self.assertFalse(result['missing'])
        self.assertFalse(result['duplicate'])
        self.assertIn('Outer cartons intact at dispatch', result['findings'])

    def test_missing_and_duplicate_evidence(self):
        missing = checked_lookup_output(self.agent, {**self.request, 'batch_id': 'B-9999'},
                                        'google_sheets_read_rows', self.rows)
        self.assertTrue(missing['missing'])
        duplicate = checked_lookup_output(self.agent, self.request, 'google_sheets_read_rows',
                                          {'rows': self.rows['rows'] + [self.rows['rows'][1]]})
        self.assertEqual(duplicate['matching_record_count'], 2)
        self.assertTrue(duplicate['duplicate'])

    def test_ambiguous_identity_or_other_output_schema_falls_back(self):
        request = {**self.request, 'shipment_id': 'S-9001'}
        self.assertIsNone(checked_lookup_output(self.agent, request, 'google_sheets_read_rows', self.rows))
        other = {'output_schema': {'type': 'object', 'properties': {'summary': {'type': 'string'}},
                                   'required': ['summary']}}
        self.assertIsNone(checked_lookup_output(other, self.request, 'google_sheets_read_rows', self.rows))


if __name__ == '__main__':
    unittest.main()
