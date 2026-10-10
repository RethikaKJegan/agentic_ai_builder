"""Load and validate the repository's canonical contracts."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator, RefResolver


PROJECT_ROOT = Path(__file__).resolve().parents[1]
CONTRACT_DIR = PROJECT_ROOT / "shared" / "contracts"

CONTRACT_FILES = {
    "workflow": "workflow-schema-v1.json",
    "agent": "agent-contract-v1.json",
    "tool": "tool-contract-v1.json",
    "api": "api-payloads-v1.json",
    "error": "error-format-v1.json",
    "auth": "auth-permissions-v1.json",
    "branching": "branching-approvals-v1.json",
    "run_status": "run-status-versioning-v1.json",
}
CONTRACT_VERSIONS = {
    "workflow": "workflow-schema-v1",
    "agent": "agent-contract-v1",
    "tool": "tool-contract-v1",
    "api": "api-payloads-v1",
    "error": "error-format-v1",
    "auth": "auth-permissions-v1",
    "branching": "branching-approvals-v1",
    "run_status": "run-status-versioning-v1",
}


def load_contracts() -> dict[str, dict[str, Any]]:
    """Load only the canonical schemas; no planner-local copies are used."""
    return {
        name: json.loads((CONTRACT_DIR / filename).read_text())
        for name, filename in CONTRACT_FILES.items()
    }


def validate_instance(instance: Any, contract_name: str) -> None:
    schemas = load_contracts()
    schema = schemas[contract_name]
    resolver = RefResolver.from_schema(schema, store={schema["$id"]: schema})
    errors = sorted(Draft202012Validator(schema, resolver=resolver).iter_errors(instance), key=lambda e: list(e.path))
    if errors:
        first = errors[0]
        path = "".join(f"[{part}]" if isinstance(part, int) else f".{part}" for part in first.path).lstrip(".")
        raise ValueError(f"{contract_name} contract violation at {path or '<root>'}: {first.message}")

