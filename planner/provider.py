"""Replaceable structured-output provider boundary."""

from __future__ import annotations

import json
import os
import re
from typing import Any, Protocol

from .contracts import load_contracts


def _load_project_env() -> None:
    """Load the local project .env without logging or exporting secrets."""
    env_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".env"))
    if not os.path.exists(env_path):
        return
    for line in open(env_path, encoding="utf-8"):
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        name, value = line.split("=", 1)
        name, value = name.strip(), value.strip().strip("\"'")
        if name and name not in os.environ:
            os.environ[name] = value


_load_project_env()


class StructuredOutputProvider(Protocol):
    def generate(self, objective: str, context: dict[str, Any]) -> dict[str, Any]: ...


class OpenAIStructuredOutputProvider:
    """Lazy OpenAI adapter; credentials and raw provider responses never leave this boundary."""

    def __init__(self, client: Any = None, model: str | None = None) -> None:
        self._client = client
        self.model = model or os.getenv("OPENAI_MODEL", "gpt-5")

    def generate(self, objective: str, context: dict[str, Any]) -> dict[str, Any]:
        client = self._client
        if client is None:
            try:
                from openai import OpenAI
            except ImportError as exc:
                raise RuntimeError("OpenAI provider is not installed; inject a provider for local planning.") from exc
            client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
        response = client.responses.create(
            model=self.model,
            input=[
                {"role": "system", "content": "Return only JSON. Produce a workflow draft using exactly the canonical field names in the supplied schema. Do not use aliases such as steps, trigger, or error_handling. Include every required top-level field, use draft status, keep tool assignments empty, and put unknown requirements in metadata.unresolved_requirements. Do not include commentary."},
                {"role": "user", "content": json.dumps({"objective": objective, "context": context, "canonical_workflow_schema": load_contracts()["workflow"]}, sort_keys=True)},
            ],
            text={"format": {"type": "json_object"}},
        )
        raw = getattr(response, "output_text", "")
        return json.loads(raw)


class RuleBasedStructuredOutputProvider:
    """Deterministic local provider used for tests and offline review-only examples."""

    _CAPABILITIES = {
        "classif": "classify_text",
        "categor": "classify_text",
        "retriev": "retrieve_records",
        "search": "retrieve_records",
        "report": "generate_report",
        "spreadsheet": "read_spreadsheet",
        "email": "send_email",
        "notif": "send_notification",
    }
    _ACCEPTED_TOOL_IDS = {
        "read_spreadsheet": "google_sheets_read_rows",
        "send_email": "smtp_send_email",
    }

    def generate(self, objective: str, context: dict[str, Any]) -> dict[str, Any]:
        words = re.findall(r"[a-z0-9]+", objective.lower())
        capabilities = sorted({cap for token, cap in self._CAPABILITIES.items() if any(token in word for word in words)})
        external_write = any(cap in {"send_email", "send_notification"} for cap in capabilities)
        agent_id = "workflow_planner_agent"
        nodes = [
            {"node_id": "objective_received", "kind": "trigger", "label": "Objective received"},
            {"node_id": "plan_objective", "kind": "agent", "label": "Plan objective", "agent_id": agent_id},
        ]
        edges = [{"edge_id": "received_to_plan", "source": "objective_received", "target": "plan_objective"}]
        approval_gates: list[dict[str, Any]] = []
        conditions: list[dict[str, Any]] = []
        conditional = " if " in f" {objective.lower()} " or " when " in f" {objective.lower()} "
        if conditional:
            conditions.append({"condition_id": "objective_condition", "expression": "objective_condition_is_met", "outcomes": ["yes", "no"]})
            nodes.append({"node_id": "objective_condition", "kind": "condition", "label": "Evaluate objective condition", "condition_id": "objective_condition"})
            edges.append({"edge_id": "plan_to_condition", "source": "plan_objective", "target": "objective_condition"})
        if external_write:
            approval_gates.append({"approval_gate_id": "external_action_approval", "approver_roles": ["approver"], "on_reject": "stop", "timeout_seconds": 86400})
            nodes.append({"node_id": "external_action_approval", "kind": "approval", "label": "Approve external action", "approval_gate_id": "external_action_approval"})
            nodes.append({"node_id": "workflow_output", "kind": "output", "label": "Workflow result"})
            nodes.append({"node_id": "rejected_output", "kind": "output", "label": "Approval rejected"})
            if not conditional:
                edges.append({"edge_id": "plan_to_approval", "source": "plan_objective", "target": "external_action_approval"})
            edges.extend([
                {"edge_id": "approval_to_output", "source": "external_action_approval", "target": "workflow_output", "outcome": "approved"},
                {"edge_id": "approval_to_rejected", "source": "external_action_approval", "target": "rejected_output", "outcome": "rejected"},
            ])
            if conditional:
                edges.extend([
                    {"edge_id": "condition_to_approval", "source": "objective_condition", "target": "external_action_approval", "outcome": "yes"},
                    {"edge_id": "condition_to_output_no", "source": "objective_condition", "target": "workflow_output", "outcome": "no"},
                ])
        else:
            nodes.append({"node_id": "workflow_output", "kind": "output", "label": "Workflow result"})
            if conditional:
                edges.extend([
                    {"edge_id": "condition_to_output_yes", "source": "objective_condition", "target": "workflow_output", "outcome": "yes"},
                    {"edge_id": "condition_to_output_no", "source": "objective_condition", "target": "workflow_output", "outcome": "no"},
                ])
            else:
                edges.append({"edge_id": "plan_to_output", "source": "plan_objective", "target": "workflow_output"})
        tool_refs = [{"tool_id": self._ACCEPTED_TOOL_IDS[cap], "capability": cap} for cap in capabilities if cap in self._ACCEPTED_TOOL_IDS]
        unresolved = [] if capabilities else [{"requirement": "No explicit capability identified", "reason": "needs_human_review"}]
        if capabilities:
            unresolved = [{"requirement": cap, "reason": "registry_assignment_pending"} for cap in capabilities]
        return {
            "workflow_id": "planned_workflow",
            "version": 1,
            "name": objective.strip()[:200],
            "description": objective.strip(),
            "status": "draft",
            "inputs": [{"name": "objective_context", "type": "object", "required": False}],
            "outputs": [{"name": "workflow_result", "type": "object", "required": True}],
            "stakeholders": [{"stakeholder_id": "requester", "name": "Requesting builder", "role": "builder"}],
            "agents": [{
                "agent_id": agent_id, "role": "planner", "goal": "Decompose the objective into a reviewable workflow.",
                "instructions": "Produce structured workflow steps and identify unresolved requirements.",
                "model": {"provider": "openai", "model_id": "structured-output"}, "input_schema": {}, "output_schema": {},
                "capabilities": capabilities, "allowed_tool_ids": [], "permissions": ["workflow.read_input"],
                "limits": {"max_llm_calls": 1, "max_tool_calls": 0, "max_tokens": 4000, "max_retries": 1, "timeout_seconds": 300},
                "approval_requirements": ["external_write"] if external_write else [],
            }],
            "tools": tool_refs,
            "nodes": nodes,
            "edges": edges,
            "conditions": conditions,
            "approval_gates": approval_gates,
            "execution_policy": {"limits": {"max_llm_calls": 3, "max_tool_calls": 4, "max_tokens": 4000, "max_retries": 2, "timeout_seconds": 300}, "requires_review_before_execution": True, "allow_external_writes": external_write},
            "error_policy": {"on_validation_error": "reject", "on_runtime_error": "retry", "max_retries": 2},
            "metadata": {"domain": "generic", "unresolved_requirements": unresolved},
        }

