#!/usr/bin/env python3
"""Validate the v1 shared contracts and their positive/negative fixtures."""

from __future__ import annotations

import json
import re
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker


ROOT = Path(__file__).resolve().parents[1]
CONTRACTS = ROOT / "shared" / "contracts"
EXAMPLES = CONTRACTS / "examples"


def load(path: Path):
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def validator(schema_path: Path) -> Draft202012Validator:
    schema = load(schema_path)
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema, format_checker=FormatChecker())


def assert_valid(checker: Draft202012Validator, path: Path) -> None:
    errors = sorted(checker.iter_errors(load(path)), key=lambda error: list(error.path))
    assert not errors, f"{path}: expected valid, got {errors[0].message}"


def assert_invalid(checker: Draft202012Validator, path: Path) -> None:
    errors = list(checker.iter_errors(load(path)))
    assert errors, f"{path}: expected schema failure"


def assert_document_valid(checker: Draft202012Validator, document: dict, label: str) -> None:
    errors = sorted(checker.iter_errors(document), key=lambda error: list(error.path))
    assert not errors, f"{label}: expected valid, got {errors[0].message}"


def validate_workflows() -> None:
    checker = validator(CONTRACTS / "workflow-schema-v1.json")
    for path in sorted((EXAMPLES / "workflows").glob("*.json")):
        assert_valid(checker, path)
        document = load(path)
        node_ids = {node["node_id"] for node in document["nodes"]}
        assert len(node_ids) == len(document["nodes"]), f"{path}: duplicate node ID"
        for edge in document["edges"]:
            assert edge["source"] in node_ids, f"{path}: missing edge source"
            assert edge["target"] in node_ids, f"{path}: missing edge target"


def validate_agents() -> None:
    checker = validator(CONTRACTS / "agent-contract-v1.json")
    assert_valid(checker, EXAMPLES / "agents" / "valid-classifier.json")
    assert_invalid(checker, EXAMPLES / "agents" / "incomplete-agent.json")

    overprivileged = load(EXAMPLES / "agents" / "overprivileged-agent.json")
    assert any(permission.endswith(".*") for permission in overprivileged["permissions"]), "over-privileged fixture lost its wildcard permission"

    secret_bearing = load(EXAMPLES / "agents" / "secret-bearing-agent.json")
    assert re.search(r"(?:api[_-]?key|secret|token)\s*=\s*\S+", secret_bearing["instructions"], re.IGNORECASE)


def validate_tools() -> None:
    checker = validator(CONTRACTS / "tool-contract-v1.json")
    for path in [EXAMPLES / "tools" / "smtp-send-email.json", EXAMPLES / "tools" / "google-sheets-read.json"]:
        assert_valid(checker, path)
    assert_invalid(checker, EXAMPLES / "tools" / "incomplete-tool.json")

    fixtures = load(EXAMPLES / "tools" / "authorization-fixtures.json")
    for name, fixture in fixtures.items():
        assert fixture["expected"] == "reject", f"{name}: fixture must reject"
    assert fixtures["missing_credentials"]["availability"] == "needs_configuration"
    assert fixtures["unavailable_tool"]["availability"] == "disabled"
    assert fixtures["cross_agent_assignment"]["agent_a_tools"] != [fixtures["cross_agent_assignment"]["agent_b_requested_tool"]]


def validate_api_and_control_contracts() -> None:
    fixture_path = EXAMPLES / "api-control-fixtures.json"
    fixtures = load(fixture_path)

    api = validator(CONTRACTS / "api-payloads-v1.json")
    assert_document_valid(api, {"request_envelope": fixtures["valid_request"], "response_envelope": {"request_id": "req_123", "status": 200, "data": {}}, "collection_response": {"items": [], "has_more": False}, "operation_names": ["plan_workflow", "execute_workflow"]}, "API contract")
    assert fixtures["valid_request"]["request_id"]
    assert fixtures["valid_error"]["error_code"].isupper()

    error = validator(CONTRACTS / "error-format-v1.json")
    assert_document_valid(error, fixtures["valid_error"], "error contract")
    for required in ("error_code", "message", "request_id", "retryable"):
        assert required in fixtures["valid_error"]

    auth = validator(CONTRACTS / "auth-permissions-v1.json")
    assert_document_valid(auth, fixtures["viewer_denied"], "authorization contract")

    branching = validator(CONTRACTS / "branching-approvals-v1.json")
    assert_document_valid(branching, fixtures["valid_approval"], "branching contract")
    invalid_branch = fixtures["invalid_branch"]
    outcomes = set(invalid_branch["condition"]["outcomes"])
    branch_outcomes = {branch["outcome"] for branch in invalid_branch["branches"]}
    assert not branch_outcomes <= outcomes, "invalid branch fixture unexpectedly became valid"

    run_status = validator(CONTRACTS / "run-status-versioning-v1.json")
    assert_document_valid(run_status, {"workflow_revision_states": ["draft", "validated"], "run_states": ["queued", "completed"], "run_event": fixtures["valid_run_event"], "idempotency_request": fixtures["duplicate_execution"]}, "run status contract")
    assert fixtures["invalid_transition"]["from"] == "completed"
    assert fixtures["invalid_transition"]["to"] == "running"


def main() -> None:
    validate_workflows()
    validate_agents()
    validate_tools()
    validate_api_and_control_contracts()
    print("Shared contract schemas and fixtures are valid.")


if __name__ == "__main__":
    main()
