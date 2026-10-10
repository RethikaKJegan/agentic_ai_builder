from copy import deepcopy
import unittest

from planner import PlannerService
from planner.idempotency import IdempotencyStore
from planner.provider import OpenAIStructuredOutputProvider, RuleBasedStructuredOutputProvider
from planner.contracts import validate_instance
from planner.validation import validate_workflow


AUTH = {"subject_id": "builder-1", "workspace_id": "workspace-1", "roles": ["builder"], "permissions": ["workflow.plan"]}


def local_service():
    return PlannerService(provider=RuleBasedStructuredOutputProvider())


def request(objective="Classify support requests and notify the owner", key="idem-12345678"):
    return {"request_id": "req-1", "operation": "plan_workflow", "idempotency_key": key, "payload": {"objective": objective, "auth_context": AUTH}}


class PlannerTests(unittest.TestCase):
    def test_secrets_in_proposed_assignments_are_rejected_before_removal(self):
        class SecretProvider(RuleBasedStructuredOutputProvider):
            def generate(self, objective, context):
                workflow = super().generate(objective, context)
                workflow['tools'][0]['configuration_reference'] = 'sk-testsecret12345678'
                return workflow

        result = PlannerService(SecretProvider()).plan(request('Send email'))
        self.assertEqual(result['error']['error_code'], 'SENSITIVE_DATA_DETECTED')
        self.assertIsNone(result['data'])

    def test_valid_generic_planning_returns_contract_workflow(self):
        result = local_service().plan(request())
        self.assertEqual(result["status"], 200)
        workflow = result["data"]["workflow"]
        validate_instance(workflow, "workflow")
        self.assertEqual(workflow["status"], "draft")
        self.assertEqual(workflow["nodes"][0]["kind"], "trigger")
        self.assertEqual(workflow["nodes"][-1]["kind"], "output")


    def test_missing_objective_and_viewer_are_rejected(self):
        missing = local_service().plan({**request(), "payload": {"auth_context": AUTH}})
        self.assertEqual(missing["error"]["field"], "payload.objective")
        denied = local_service().plan({**request(), "payload": {"objective": "make a plan", "auth_context": {**AUTH, "roles": ["viewer"], "permissions": []}}})
        self.assertEqual(denied["error"]["error_code"], "PLANNING_NOT_AUTHORIZED")


    def test_idempotency_is_workspace_scoped_and_rejects_mismatch(self):
        service = PlannerService(provider=RuleBasedStructuredOutputProvider(), idempotency=IdempotencyStore())
        first = service.plan(request())
        repeated = service.plan({**request(), "request_id": "req-2"})
        self.assertEqual(repeated, first)
        mismatch = service.plan(request("a different objective", "idem-12345678"))
        self.assertEqual(mismatch["error"]["error_code"], "IDEMPOTENCY_KEY_REUSED")


    def test_unknown_external_operations_remain_unresolved_without_fabrication(self):
        workflow = RuleBasedStructuredOutputProvider().generate("Reconcile the moon ledger with an unknown provider", {})
        self.assertEqual(workflow["tools"], [])
        self.assertTrue(workflow["metadata"]["unresolved_requirements"])


    def test_external_write_has_approval_gate(self):
        result = local_service().plan(request("Send an email notification to the owner"))
        workflow = result["data"]["workflow"]
        self.assertTrue(workflow["approval_gates"])
        self.assertTrue(workflow["execution_policy"]["requires_review_before_execution"])

    def test_provider_neutral_sheet_wording_creates_read_capability_and_trigger_metadata(self):
        result = local_service().plan(request(
            "When a new row is added to Google Sheets, read the record and notify the owner",
            "sheets-12345678"))
        workflow = result["data"]["workflow"]
        self.assertIn({"tool_id": "google_sheets_read_rows", "capability": "read_spreadsheet"}, workflow["tools"])
        self.assertEqual(workflow["nodes"][0]["label"], "New spreadsheet row")
        template = workflow["metadata"]["trigger_templates"][0]
        self.assertEqual(template["event_type"], "row.created")
        self.assertEqual(template["provider_id"], "google_sheets")

    def test_sheet_trigger_binds_the_resource_provided_for_this_workflow(self):
        sheet_id = "1TTlDwqo9j7E3K95eNqAg6bDR7t5MlAOFxmKF3frhGKY"
        workflow = RuleBasedStructuredOutputProvider().generate(
            "When a new row is added to Google Sheets, qualify the lead",
            {"google_sheets_resource": f"https://docs.google.com/spreadsheets/d/{sheet_id}/edit"},
        )
        template = workflow["metadata"]["trigger_templates"][0]
        self.assertEqual(template["resource_id"], sheet_id)
        self.assertNotIn("configured_default", repr(workflow))

    def test_sheet_trigger_without_resource_requires_a_binding_before_publication(self):
        workflow = RuleBasedStructuredOutputProvider().generate(
            "When a new row is added to Google Sheets, qualify the lead", {})
        self.assertIn({"requirement": "google_sheets_trigger_resource", "reason": "resource_reference_required"},
                      workflow["metadata"]["unresolved_requirements"])

    def test_provider_words_select_catalog_tool_without_credentials(self):
        for objective, tool_id in (("Get the weather forecast", "open_meteo_forecast"),
                                   ("Search GitHub repositories", "github_rest_request"),
                                   ("List files from Drive", "google_drive_list_files"),
                                   ("Notify the team in Slack", "slack_send_notification")):
            workflow = RuleBasedStructuredOutputProvider().generate(objective, {})
            self.assertIn(tool_id, {tool["tool_id"] for tool in workflow["tools"]})
            self.assertNotIn("api_key", repr(workflow))
            self.assertNotIn("password", repr(workflow))

    def test_hierarchy_mode_returns_multiple_canonical_agents(self):
        workflow = RuleBasedStructuredOutputProvider().generate(
            "When a lead arrives, classify it and notify Slack",
            {"generation_mode": "hierarchy"},
        )
        self.assertGreaterEqual(len(workflow["agents"]), 3)
        self.assertEqual(workflow["metadata"]["generation_mode"], "hierarchy")
        self.assertTrue(any(node["kind"] == "agent" and node["agent_id"] == "workflow_master_agent" for node in workflow["nodes"]))
        validate_workflow(workflow)

    def test_condition_has_declared_paths_and_external_rejection_path(self):
        conditional = local_service().plan(request("If the request is urgent, send an email notification"))
        workflow = conditional["data"]["workflow"]
        self.assertEqual(workflow["conditions"][0]["outcomes"], ["yes", "no"])
        self.assertTrue(any(edge.get("outcome") == "yes" for edge in workflow["edges"]))

    def test_generic_domains_share_one_contract_shape(self):
        service = local_service()
        for index, objective in enumerate((
            "Classify a support request",
            "Prepare an employee onboarding plan",
            "Review a procurement request",
            "Generate a reporting summary",
        )):
            result = service.plan(request(objective, f"key-{index:08d}"))
            self.assertEqual(result["status"], 200)
            self.assertEqual(result["data"]["workflow"]["metadata"]["domain"], "generic")

    def test_openai_adapter_returns_structured_data_without_provider_payload(self):
        class FakeResponses:
            def create(self, **kwargs):
                self.kwargs = kwargs
                return type("Response", (), {"output_text": '{"nodes": []}'})()

        class FakeClient:
            def __init__(self):
                self.responses = FakeResponses()

        client = FakeClient()
        result = OpenAIStructuredOutputProvider(client=client, model="test-model").generate("make a plan", {})
        self.assertEqual(result, {"nodes": []})
        self.assertNotIn("api_key", repr(client.responses.kwargs))


    def test_malformed_model_output_is_rejected_before_persistence(self):
        class BadProvider:
            def generate(self, objective, context):
                return {"workflow_id": "bad"}

        service = PlannerService(provider=BadProvider())
        result = service.plan(request("build a plan", "bad-model-123"))
        self.assertEqual(result["error"]["error_code"], "WORKFLOW_VALIDATION_FAILED")


    def test_duplicate_and_broken_graph_rejected(self):
        workflow = RuleBasedStructuredOutputProvider().generate("classify a request", {})
        duplicate = deepcopy(workflow)
        duplicate["nodes"].append(deepcopy(duplicate["nodes"][0]))
        with self.assertRaisesRegex(Exception, "unique"):
            validate_workflow(duplicate)

    def test_missing_reference_cycle_and_graph_bounds_are_rejected(self):
        workflow = RuleBasedStructuredOutputProvider().generate("classify a request", {})
        broken = deepcopy(workflow)
        broken["edges"][0]["target"] = "missing_node"
        with self.assertRaisesRegex(Exception, "target"):
            validate_workflow(broken)
        cyclic = deepcopy(workflow)
        cyclic["edges"].append({"edge_id": "output_to_output", "source": "workflow_output", "target": "workflow_output"})
        with self.assertRaisesRegex(Exception, "cycle"):
            validate_workflow(cyclic)
        with self.assertRaisesRegex(Exception, "maximum node"):
            validate_workflow(workflow, max_nodes=1)

    def test_secret_like_prompt_is_rejected_and_not_echoed(self):
        result = local_service().plan(request("Use api_key=sk-test-secret-value to send an email", "secret-1234"))
        self.assertEqual(result["error"]["error_code"], "SENSITIVE_DATA_DETECTED")
        self.assertNotIn("sk-test-secret-value", repr(result))

    def test_provider_failure_is_safe_and_retryable(self):
        class FailingProvider:
            def generate(self, objective, context):
                raise RuntimeError("provider raw response api_key=sk-secret")

        result = PlannerService(provider=FailingProvider()).plan(request("make a plan", "provider-1234"))
        self.assertEqual(result["status"], 502)
        self.assertTrue(result["error"]["retryable"])
        self.assertNotIn("sk-secret", repr(result))

    def test_unsupported_model_condition_preserves_reviewable_draft_and_branches(self):
        original = RuleBasedStructuredOutputProvider().generate('If a Slack message arrives from Rethika K, send an email', {})
        original['conditions'][0]['expression'] = "event.user === 'Rethika K' && event.text.includes('tested')"
        class ModelProvider:
            def generate(self, objective, context):
                return deepcopy(original)
        service = PlannerService(provider=ModelProvider())
        result = service.plan(request('Notify me when Rethika sends a Slack message', 'slack-review-1234'))
        self.assertEqual(result['status'], 200, result)
        workflow = result['data']['workflow']
        self.assertEqual(workflow['conditions'][0]['expression'], 'inputs.condition_review_1')
        self.assertEqual(workflow['edges'], original['edges'])
        self.assertIn({'name': 'condition_review_1', 'type': 'boolean', 'required': True,
            'description': 'Explicit reviewed condition result; provider event mapping must be configured before publication.'}, workflow['inputs'])
        self.assertTrue(any(item.get('reason') == 'condition_mapping_required' for item in workflow['metadata']['unresolved_requirements'] if isinstance(item, dict)))
        validate_workflow(workflow)
        self.assertEqual(service.plan(request('Notify me when Rethika sends a Slack message', 'slack-review-1234')), result)

    def test_valid_model_condition_is_unchanged_and_saved_invalid_expression_still_rejected(self):
        workflow = RuleBasedStructuredOutputProvider().generate('If a Slack message arrives, send an email', {})
        workflow['conditions'][0]['expression'] = 'inputs.sender_id == inputs.expected_sender_id'
        class ModelProvider:
            def generate(self, objective, context):
                return deepcopy(workflow)
        result = PlannerService(provider=ModelProvider()).plan(request('Slack sender filter', 'valid-filter-1234'))
        self.assertEqual(result['status'], 200)
        self.assertEqual(result['data']['workflow']['conditions'], workflow['conditions'])
        workflow['conditions'][0]['expression'] = '__import__("os").system("echo invalid")'
        with self.assertRaisesRegex(Exception, 'deterministic language'):
            validate_workflow(workflow)

    def test_unmapped_condition_does_not_hide_missing_branch(self):
        workflow = RuleBasedStructuredOutputProvider().generate('If a Slack message arrives, send an email', {})
        workflow['conditions'][0]['expression'] = 'sender is Rethika K'
        workflow['edges'] = [edge for edge in workflow['edges'] if edge.get('outcome') != 'no']
        class ModelProvider:
            def generate(self, objective, context):
                return deepcopy(workflow)
        result = PlannerService(provider=ModelProvider()).plan(request('Slack sender filter', 'missing-branch-1234'))
        self.assertEqual(result['status'], 400)
        self.assertEqual(result['error']['error_code'], 'WORKFLOW_VALIDATION_FAILED')

    def test_error_envelope_matches_canonical_contract(self):
        result = local_service().plan(request("", "error-1234"))
        validate_instance(result["error"], "error")
        self.assertEqual(result["error"]["request_id"], "req-1")


if __name__ == "__main__":
    unittest.main()

