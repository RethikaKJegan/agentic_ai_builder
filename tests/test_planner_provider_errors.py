"""SDK errors must be safe, retryable API failures, not invalid-data errors."""
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest

import httpx
from openai import APITimeoutError, APIConnectionError, RateLimitError, APIStatusError
from planner import PlannerService
from planner.provider import OpenAIStructuredOutputProvider
from tests.test_planner import request
from workflow_api.service import WorkflowService
from workflow_api.storage import WorkflowStore


class ProviderErrorTests(unittest.TestCase):
    def test_sdk_errors_become_retryable_safe_api_errors(self):
        http_request = httpx.Request('POST', 'https://example.invalid/responses')
        errors = [
            (APITimeoutError(request=http_request), 'PLANNER_PROVIDER_TIMEOUT', 504),
            (APIConnectionError(message='private-provider-diagnostic', request=http_request), 'PLANNER_PROVIDER_UNAVAILABLE', 502),
            (RateLimitError('private-provider-diagnostic', response=httpx.Response(429, request=http_request), body={}), 'PLANNER_RATE_LIMITED', 429),
            (APIStatusError('private-provider-diagnostic', response=httpx.Response(503, request=http_request), body={}), 'PLANNER_PROVIDER_FAILED', 502),
        ]
        auth = {'subject': {'subject_id': 'operator', 'workspace_id': 'local-workspace'}, 'roles': ['admin'],
                'permissions': ['workflow.plan'], 'scopes': [], 'decision': 'allow'}
        for error, code, status in errors:
            with self.subTest(code=code), tempfile.TemporaryDirectory() as directory:
                class Provider:
                    def generate(self, objective, context):
                        raise error
                service = WorkflowService(WorkflowStore(Path(directory) / 'workflows.sqlite3'), PlannerService(Provider()))
                api_request = request()
                api_request['payload'].pop('auth_context')
                result = service.handle(api_request, auth)
                self.assertEqual(result['status'], status)
                self.assertEqual(result['data']['error']['error_code'], code)
                self.assertTrue(result['data']['error']['retryable'])
                self.assertNotIn('private-provider-diagnostic', json.dumps(result))
                self.assertNotIn('example.invalid', json.dumps(result))
                with service.store.transaction() as db:
                    self.assertEqual(db.execute('SELECT COUNT(*) FROM revisions').fetchone()[0], 0)

    def test_planning_request_has_separate_bounded_timeout_and_no_storage(self):
        from tests.test_sheet_records import authored_workflow
        workflow = authored_workflow(('Reviews', 'Kitchen', 'review_id', 'order_id', 'checker'))
        calls = []
        def response(**kwargs):
            calls.append(kwargs)
            return SimpleNamespace(output_text=json.dumps(workflow))
        client = SimpleNamespace(responses=SimpleNamespace(create=response))
        provider = OpenAIStructuredOutputProvider(client=client, timeout_seconds=180)
        provider.generate('Prepare checked drafts.', {'generation_mode': 'hierarchy'})
        self.assertEqual(calls[0]['timeout'], 180)
        self.assertFalse(calls[0]['store'])
        for value in (0, 29, 301, '180', True):
            with self.assertRaises(ValueError):
                OpenAIStructuredOutputProvider(client=client, timeout_seconds=value)

    def test_ambiguous_or_unsupported_setup_literals_are_not_guessed(self):
        from planner.validation import normalize_generated_inputs
        for config in ({'input': {'x': 'one'}, 'input_mapping': {'x': 'inputs.x'}},
                       {'input': {'x': {'nested': 'object'}}, 'input_mapping': {'y': 'inputs.y'}}):
            workflow = {'nodes': [{'configuration': config}]}
            normalize_generated_inputs(workflow)
            self.assertIn('input', config)

    def test_explicit_open_field_schema_is_not_silently_overridden(self):
        from runtime.sheet_records import normalize_generated_record_schemas
        from tests.test_sheet_records import authored_workflow
        workflow = authored_workflow(('Reviews', 'Kitchen', 'review_id', 'order_id', 'checker'))
        schema = workflow['agents'][0]['output_schema']['properties']['draft_fields']
        schema['additionalProperties'] = True
        normalize_generated_record_schemas(workflow)
        self.assertTrue(schema['additionalProperties'])
