import unittest
from workflow_api.procurement_quotes import grounded_evidence

class QuoteEvidenceTests(unittest.TestCase):
    def test_nonadjacent_genuine_lines(self):
        text='Currency: INR\n\nItem ID: ITEM-003\nQuantity: 4\n\nSubtotal: 20000\nShipping: 500'
        self.assertTrue(grounded_evidence('Currency: INR\n\nSubtotal: 20000\nShipping: 500',text))
    def test_whitespace_and_mail_wrapping(self):
        self.assertTrue(grounded_evidence('Payment terms: Payment within 30 days.', 'Payment terms: Payment within\r\n30 days.'))
    def test_invented_values_and_numeric_prefixes(self):
        self.assertFalse(grounded_evidence('Shipping: 500','Shipping: 5000'))
        self.assertFalse(grounded_evidence('Tax: 0','Tax: 0.50'))
        self.assertFalse(grounded_evidence('Subtotal: 10000\nShipping: 500','Subtotal: 20000\nShipping: 500'))
    def test_reordered_lines_and_empty_evidence(self):
        self.assertFalse(grounded_evidence('Shipping: 500\nSubtotal: 20000','Subtotal: 20000\nShipping: 500'))
        self.assertFalse(grounded_evidence('  ','Subtotal: 20000'))
