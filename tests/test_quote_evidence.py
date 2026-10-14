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

class ComplianceStatementTests(unittest.TestCase):
    def issues(self, source, statement):
        from workflow_api.procurement_quotes import quote_issues, NUMBERS
        output={'evidence':[source], 'items':[], 'financials':{'currency':'INR',**{key:'0' for key in NUMBERS}},
                'delivery_date':'2026-11-10','valid_until':'2026-10-31','compliance_statement':statement}
        text='0\n2026-11-10\n2026-10-31\n'+source
        output['evidence']=[text]
        return quote_issues(output,text,[],'INR')

    def test_gmail_wrapping_preserves_compliance(self):
        statement='The pumps fully comply with all specifications in this RFQ.'
        self.assertEqual(self.issues('Specification compliance: The pumps fully comply with all\r\n specifications in this RFQ.',statement),[])

    def test_missing_paraphrased_or_negative_statement_does_not_qualify(self):
        for source,statement in [('No compliance information.',None),
            ('The pumps meet some specifications.','The pumps fully comply with all specifications.'),
            ('The pumps do not comply.','The pumps comply.')]:
            with self.subTest(source=source):
                self.assertIn('COMPLIANCE_STATEMENT_REQUIRED',self.issues(source,statement))
