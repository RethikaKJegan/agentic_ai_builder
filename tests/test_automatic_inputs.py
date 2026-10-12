"""Prompt-only proposals use existing constants and actual trigger data."""
from copy import deepcopy
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from planner import PlannerService
from planner.errors import PlannerFailure
from planner.provider import RuleBasedStructuredOutputProvider
from tests.test_planner import request
from tests.test_live_providers import draft
from workflow_api.live_providers import LivePlannerProvider
from workflow_api.service import WorkflowService


class AutomaticInputTests(unittest.TestCase):
    def test_manual_inputs_are_rejected_instead_of_defaulted(self):
        workflow = draft()
        workflow['metadata'].update(execution_input_mode='automatic', trigger_templates=[])
        with self.assertRaises(PlannerFailure) as failed:
            WorkflowService.validate_document(workflow)
        self.assertEqual(failed.exception.code, 'AUTOMATIC_INPUT_SOURCE_REQUIRED')

    def test_optional_unmapped_inputs_also_require_a_source(self):
        workflow = draft()
        workflow['metadata']['execution_input_mode'] = 'automatic'
        WorkflowService.validate_document(workflow)
        workflow['inputs'].append({'name': 'extra_context', 'type': 'object', 'required': False})
        with self.assertRaises(PlannerFailure) as failed:
            WorkflowService.validate_document(workflow)
        self.assertEqual(failed.exception.code, 'AUTOMATIC_INPUT_SOURCE_REQUIRED')

    def test_empty_fields_cannot_hide_an_unbound_input_reference(self):
        workflow = draft()
        workflow['metadata']['execution_input_mode'] = 'automatic'
        workflow['nodes'][2]['configuration']['input_mapping']['row'] = 'inputs.unknown_row'
        with self.assertRaises(PlannerFailure) as failed:
            WorkflowService.validate_document(workflow)
        self.assertEqual(failed.exception.code, 'AUTOMATIC_INPUT_SOURCE_REQUIRED')

    def test_live_planner_corrects_manual_fields_before_saving(self):
        provider = LivePlannerProvider('gpt-5.6-luna', ['owner@example.com'], SimpleNamespace())
        correct = draft()
        for agent in correct['agents']:
            agent['model']['model_id'] = 'gpt-5.6-luna'
        incorrect = deepcopy(correct)
        incorrect['inputs'].append({'name': 'request_text', 'type': 'string', 'required': True})
        with patch.object(provider.provider, 'generate', side_effect=[incorrect, correct]) as generate:
            result = provider.generate('Watch the configured source and analyse new rows.', {'execution_input_mode': 'automatic'})
        self.assertEqual(generate.call_count, 2)
        self.assertEqual(result['metadata']['execution_input_mode'], 'automatic')
        self.assertIn('AUTOMATIC_INPUT_SOURCE_REQUIRED',
            {item['code'] for item in generate.call_args.args[1]['validation_feedback']})

    def test_automatic_proposal_has_separate_identity(self):
        # This provider supplies a fully configured manual-start proposal.
        class Provider(RuleBasedStructuredOutputProvider):
            def generate(self, objective, context):
                workflow = super().generate(objective, context)
                workflow['inputs'] = []
                return workflow
        service = PlannerService(Provider())
        legacy = service.plan(request('Summarize the objective', 'legacy_identity_123'))
        automatic_request = request('Summarize the objective', 'automatic_identity_123')
        automatic_request['payload']['context'] = {'execution_input_mode': 'automatic'}
        automatic = service.plan(automatic_request)
        self.assertEqual(automatic['status'], 200, automatic)
        self.assertNotEqual(legacy['data']['workflow']['workflow_id'], automatic['data']['workflow']['workflow_id'])

    def test_provider_cannot_bypass_automatic_validation_by_omitting_marker(self):
        class Provider(RuleBasedStructuredOutputProvider):
            def generate(self, objective, context):
                workflow = super().generate(objective, context)
                workflow['inputs'] = [{'name': 'unknown_source', 'type': 'string', 'required': True}]
                return workflow
        automatic_request = request('Summarize the objective')
        automatic_request['payload']['context'] = {'execution_input_mode': 'automatic'}
        result = PlannerService(Provider()).plan(automatic_request)
        self.assertEqual(result['error']['error_code'], 'AUTOMATIC_INPUT_SOURCE_REQUIRED')
