from copy import deepcopy
import unittest

from planner.errors import PlannerFailure
from runtime.email_recipients import validate_email_workflow, source_recipient, normalize_generated_email_approvals
from runtime.service import RuntimeFailure


def workflow():
    return {'metadata': {'email_recipient_policy': {'mode': 'source_row', 'field': 'email'},
                         'trigger_templates': [{'provider_id': 'google_sheets', 'input_mapping': {'row': 'row'}}]},
            'nodes': [{'node_id': 'approve', 'kind': 'approval', 'approval_gate_id': 'customer_gate'},
                      {'node_id': 'send', 'kind': 'tool', 'agent_id': 'sender', 'tool_id': 'smtp_send_email',
                       'configuration': {'input_mapping': {'to': 'inputs.row.email'}}}],
            'edges': [{'source': 'approve', 'target': 'send', 'outcome': 'approved'}],
            'agents': [{'agent_id': 'sender', 'approval_requirements': ['customer_gate']}],
            'approval_gates': [{'approval_gate_id': 'customer_gate'}],
            'error_policy': {'max_retries': 0}}


class SourceRecipientTests(unittest.TestCase):
    def test_automatic_source_send_requires_workflow_policy_and_server_opt_in(self):
        automatic = workflow()
        automatic['metadata']['customer_automation'] = {'mode':'automatic', 'manager_email':'approved@example.com',
            'case_fields':{'identity':'case_id', 'complaint':'concern'}, 'close_on_customer_confirmation':True}
        automatic['nodes'][0] = {'node_id':'approve', 'kind':'agent'}
        automatic['agents'][0]['approval_requirements'] = []
        automatic['edges'][0].pop('outcome')
        with self.assertRaises(PlannerFailure):
            validate_email_workflow(automatic, allow_automatic=False)
        validate_email_workflow(automatic, allow_automatic=True, managers=['approved@example.com'])
        self.fixture.connector.require_approval = False
        bound = self.fixture.connector.bind_run(automatic, {'inputs':{'row':{'email':'customer@example.com'}}})
        grant = {**self.fixture.grant, 'approval_required':False, 'approval_reference':None}
        self.assertIn('message_id', bound.invoke(grant, {**self.fixture.inputs,'to':'customer@example.com'}, 'auto:send'))
        with self.assertRaises(RuntimeFailure):
            bound.invoke(grant, {**self.fixture.inputs,'to':'another@example.com'}, 'auto:other')
        with self.assertRaises(PlannerFailure):
            validate_email_workflow(automatic, allow_automatic=True, managers=['other@example.com'])

    def test_actual_email_header_can_have_spaces(self):
        altered = workflow()
        altered['metadata']['email_recipient_policy']['field'] = 'Customer Email'
        altered['nodes'][1]['configuration']['input_mapping']['to'] = 'inputs.row["Customer Email"]'
        self.assertEqual(source_recipient(altered, {'row':{'Customer Email':'customer@example.com'}}), 'customer@example.com')

    def setUp(self):
        from tests.test_runtime import ConnectorTests
        self.fixture = ConnectorTests()
        self.fixture.setUp()

    def test_source_customer_can_receive_after_approval_without_allowlist_change(self):
        bound = self.fixture.connector.bind_run(workflow(), {'inputs': {'row': {'email': 'customer@example.com'}}})
        result = bound.invoke(self.fixture.grant, {**self.fixture.inputs, 'to': 'customer@example.com'}, 'case:send')
        self.assertIn('message_id', result)
        self.assertEqual(self.fixture.calls[-1][1], 'customer@example.com')
        self.assertEqual(self.fixture.connector.allowed_recipients, frozenset({'approved@example.com'}))

    def test_other_customer_and_missing_approval_are_denied(self):
        bound = self.fixture.connector.bind_run(workflow(), {'inputs': {'row': {'email': 'customer@example.com'}}})
        for grant, address in ((self.fixture.grant, 'other@example.com'),
                               ({**self.fixture.grant, 'approval_reference': None}, 'customer@example.com')):
            with self.assertRaises(RuntimeFailure):
                bound.invoke(grant, {**self.fixture.inputs, 'to': address}, 'case:send')
        self.assertEqual(self.fixture.calls, [])

    def test_invalid_source_addresses_are_rejected_before_transport(self):
        for email in (None, '', '[REDACTED]', 'a@example.com,b@example.com', 'a@example.com\r\nBcc:x@example.com'):
            with self.subTest(email=email), self.assertRaises(RuntimeFailure):
                source_recipient(workflow(), {'row': {'email': email}})
        self.assertEqual(self.fixture.calls, [])

    def test_model_recipient_or_approval_bypass_is_rejected(self):
        for change in ('model', 'approval', 'source'):
            altered = deepcopy(workflow())
            if change == 'model':
                altered['nodes'][1]['configuration']['input_mapping']['to'] = 'outputs.master.recipient'
            elif change == 'approval':
                altered['edges'][0]['outcome'] = 'rejected'
            else:
                altered['metadata']['trigger_templates'][0]['input_mapping']['row'] = {'constant': {'email': 'x@example.com'}}
            with self.assertRaises(PlannerFailure):
                validate_email_workflow(altered)

    def test_generated_gate_alias_is_aligned_and_published_mismatch_is_rejected(self):
        generated = workflow()
        generated['agents'][0]['approval_requirements'] = ['human_email_approval']
        with self.assertRaises(PlannerFailure) as failure:
            validate_email_workflow(generated)
        self.assertEqual(failure.exception.code, 'EMAIL_APPROVAL_GATE_MISMATCH')
        normalize_generated_email_approvals(generated)
        self.assertEqual(generated['agents'][0]['approval_requirements'], ['customer_gate'])
        validate_email_workflow(generated)
