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
        "weather": "retrieve_records",
        "forecast": "retrieve_records",
        "github": "retrieve_records",
        "repository": "retrieve_records",
        "repo": "retrieve_records",
        "drive": "retrieve_records",
        "file": "retrieve_records",
        "calendar": "retrieve_records",
        "meeting": "retrieve_records",
        "document": "retrieve_records",
        "docs": "retrieve_records",
        "rest": "retrieve_records",
        "api": "retrieve_records",
        "book": "retrieve_records",
        "library": "retrieve_records",
        "report": "generate_report",
        "spreadsheet": "read_spreadsheet",
        "sheets": "read_spreadsheet",
        "sheet": "read_spreadsheet",
        "row": "read_spreadsheet",
        "update": "update_spreadsheet",
        "append": "update_spreadsheet",
        "email": "send_email",
        "notif": "send_notification",
    }
    _ACCEPTED_TOOL_IDS = {
        "read_spreadsheet": "google_sheets_read_rows",
        "update_spreadsheet": "google_sheets_update_row",
        "send_email": "smtp_send_email",
    }

    @staticmethod
    def _tool_for(capability: str, words: set[str]) -> str | None:
        """Choose a provider-specific tool from the request while retaining generic capabilities."""
        if capability == "retrieve_records":
            if any(word in words for word in {"weather", "forecast", "temperature"}):
                return "open_meteo_forecast"
            if any(word in words for word in {"book", "books", "library", "isbn"}):
                return "open_library_search"
            if any(word in words for word in {"github", "repository", "repo", "issue", "pull"}):
                return "github_rest_request"
            if any(word in words for word in {"drive", "file", "files"}):
                return "google_drive_list_files"
            if any(word in words for word in {"calendar", "meeting", "event", "events"}):
                return "google_calendar_list_events"
            if any(word in words for word in {"document", "docs"}):
                return "google_docs_read"
            if any(word in words for word in {"api", "rest", "http"}):
                return "generic_rest_request"
        if capability == "send_notification":
            return "webhook_send" if "webhook" in words else "slack_send_notification"
        if capability == "send_email" and "brevo" in words:
            return "brevo_send_email"
        return RuleBasedStructuredOutputProvider._ACCEPTED_TOOL_IDS.get(capability)

    def _generate_hierarchy(self, objective: str, words: list[str], context: dict[str, Any]) -> dict[str, Any]:
        """Build a canonical multi-agent graph from the same capability analysis.

        This remains deterministic for offline tests; the OpenAI provider receives
        the same generation mode in its structured prompt and can produce a richer
        graph without changing the contract or Registry boundary.
        """
        # Build the canonical linear plan first while retaining server-validated
        # resource context.  Dropping this context made a hierarchy workflow
        # silently fall back to a global connector default.
        workflow = self.generate(objective, {key: value for key, value in context.items() if key != "generation_mode"})
        condition_nodes = [node for node in workflow["nodes"] if node.get("kind") == "condition"]
        condition_node = condition_nodes[0] if condition_nodes else None
        capabilities = workflow["agents"][0]["capabilities"] or ["classify_text"]
        tools_by_capability = {tool["capability"]: tool for tool in workflow["tools"]}
        base_agent = workflow["agents"][0]
        master = {**base_agent, "agent_id": "workflow_master_agent", "role": "Master orchestrator",
                  "goal": "Coordinate specialist agents and combine their results.",
                  "instructions": "Delegate each specialist task, then combine validated results." , "capabilities": [],
                  "allowed_tool_ids": [], "hierarchy_role": "master"}
        agents = [master]
        nodes = [{"node_id": "objective_received", "kind": "trigger", "label": "Objective received"},
                 {"node_id": "master_orchestrator", "kind": "agent", "label": "Master orchestrator", "agent_id": master["agent_id"]}]
        edges = [{"edge_id": "received_to_master", "source": "objective_received", "target": "master_orchestrator"}]
        previous = "master_orchestrator"
        if condition_node:
            nodes.append(condition_node)
            edges.append({"edge_id": "master_to_condition", "source": previous, "target": condition_node["node_id"]})
            previous = condition_node["node_id"]
        for index, capability in enumerate(capabilities[:6], 1):
            agent_id = f"specialist_agent_{index}"
            agent = {**base_agent, "agent_id": agent_id, "role": capability.replace("_", " ").title() + " specialist",
                     "goal": f"Perform the {capability.replace('_', ' ')} part of the request.",
                     "instructions": f"Complete the assigned {capability.replace('_', ' ')} task and return structured data.",
                     "capabilities": [capability], "allowed_tool_ids": [], "parent_agent_id": master["agent_id"], "hierarchy_role": "sub_agent"}
            agents.append(agent)
            agent_node = f"specialist_{index}"
            nodes.append({"node_id": agent_node, "kind": "agent", "label": agent["role"], "agent_id": agent_id})
            edges.append({"edge_id": f"{previous}_to_{agent_node}", "source": previous, "target": agent_node,
                          **({"outcome": "yes"} if previous == "objective_condition" else {})})
            previous = agent_node
            tool = tools_by_capability.get(capability)
            if tool:
                tool_node = f"specialist_{index}_action"
                mapping = {}
                if capability == "read_spreadsheet": mapping = {"spreadsheet_id": "inputs.spreadsheet_id", "range": "inputs.range"}
                elif capability == "send_email": mapping = {"to": "inputs.email_to", "subject": "inputs.email_subject", "body": "inputs.email_body"}
                elif capability == "update_spreadsheet": mapping = {"spreadsheet_id": "inputs.spreadsheet_id", "range": "inputs.range", "values": "inputs.values"}
                elif capability == "retrieve_records": mapping = {"path": "inputs.path", "query": "inputs.query"}
                elif capability == "send_notification": mapping = {"text": "inputs.notification_text"}
                if capability in {"send_email", "send_notification", "update_spreadsheet"}:
                    gate_id = f"external_action_approval_{index}"
                    workflow["approval_gates"].append({"approval_gate_id": gate_id, "approver_roles": ["approver"], "on_reject": "stop", "timeout_seconds": 86400})
                    approval_node = f"approval_{index}"
                    nodes.append({"node_id": approval_node, "kind": "approval", "label": "Approve external action", "approval_gate_id": gate_id})
                    edges.append({"edge_id": f"{agent_node}_to_{approval_node}", "source": agent_node, "target": approval_node})
                    previous = approval_node
                    workflow["execution_policy"]["allow_external_writes"] = True
                nodes.append({"node_id": tool_node, "kind": "tool", "label": tool["tool_id"].replace("_", " ").title(), "agent_id": agent_id,
                              "tool_id": tool["tool_id"], "configuration": {"input_mapping": mapping}})
                edges.append({"edge_id": f"{previous}_to_{tool_node}", "source": previous, "target": tool_node, **({"outcome": "approved"} if previous.startswith("approval_") else {})})
                previous = tool_node
        nodes.extend([{"node_id": "combined_result", "kind": "transform", "label": "Combined result"},
                      {"node_id": "workflow_output", "kind": "output", "label": "Workflow result", "configuration": {"input_mapping": {"workflow_result": f"outputs.{previous}"}}}])
        edges.extend([{"edge_id": "last_to_combined", "source": previous, "target": "combined_result"},
                      {"edge_id": "combined_to_output", "source": "combined_result", "target": "workflow_output"}])
        if condition_node:
            edges.append({"edge_id": "condition_to_no_output", "source": condition_node["node_id"], "target": "workflow_output", "outcome": "no"})
        workflow["agents"], workflow["nodes"], workflow["edges"] = agents, nodes, edges
        workflow["metadata"]["generation_mode"] = "hierarchy"
        return workflow

    @staticmethod
    def _google_sheet_id(objective: str, context: dict[str, Any]) -> str | None:
        """Extract one workflow-owned Google Sheet resource without accepting URLs as tool inputs."""
        candidates = [context.get("google_sheets_resource"), objective]
        for candidate in candidates:
            if not isinstance(candidate, str):
                continue
            match = re.search(r"(?:docs\\.google\\.com/spreadsheets/d/)?([A-Za-z0-9_-]{20,})", candidate)
            if match:
                return match.group(1)
        return None

    def generate(self, objective: str, context: dict[str, Any]) -> dict[str, Any]:
        if context.get("generation_mode") == "hierarchy":
            return self._generate_hierarchy(objective, [], context)
        words = re.findall(r"[a-z0-9]+", objective.lower())
        capabilities = sorted({cap for token, cap in self._CAPABILITIES.items() if any(token in word for word in words)})
        external_write = any(cap in {"send_email", "send_notification", "update_spreadsheet"} for cap in capabilities)
        objective_lower = objective.lower()
        row_trigger = bool(re.search(r"\b(new|added|created)\b.{0,40}\b(row|lead|record)\b|\b(row|lead|record)\b.{0,40}\b(new|added|created)\b", objective_lower))
        trigger_template = None
        trigger_resource_missing = False
        if row_trigger:
            sheet_id = self._google_sheet_id(objective, context)
            trigger_resource_missing = sheet_id is None
            trigger_template = {"provider_id": "google_sheets", "delivery": "poll", "event_type": "row.created", "resource_id": sheet_id or "resource_required", "poll_interval_seconds": 10, "baseline_policy": "current_only", "poll_input": {"range": "A:Z"}, "input_mapping": {"objective_context": "row", "spreadsheet_id": "spreadsheet_id", "range": "range", "condition_result": {"constant": True}, "email_to": "row.email", "email_subject": {"constant": "Follow-up from the workflow"}, "email_body": "row.requirements", "values": {"constant": []}}}
        elif "pull request" in objective_lower or "github pr" in objective_lower:
            trigger_template = {"provider_id": "github_webhook", "delivery": "push", "event_type": "pull_request", "resource_id": "configured_default", "baseline_policy": "current_only"}
        elif "incoming email" in objective_lower or "new email" in objective_lower:
            trigger_template = {"provider_id": "gmail_watch", "delivery": "push", "event_type": "message.created", "resource_id": "configured_default", "baseline_policy": "current_only"}
        elif "slack message" in objective_lower:
            trigger_template = {"provider_id": "slack_events", "delivery": "push", "event_type": "message", "resource_id": "configured_default", "baseline_policy": "current_only"}
        agent_id = "workflow_planner_agent"
        nodes = [
            {"node_id": "objective_received", "kind": "trigger",
             "label": "New spreadsheet row" if row_trigger else "Objective received"},
            {"node_id": "plan_objective", "kind": "agent", "label": "Plan objective", "agent_id": agent_id},
        ]
        edges = [{"edge_id": "received_to_plan", "source": "objective_received", "target": "plan_objective"}]
        approval_gates: list[dict[str, Any]] = []
        conditions: list[dict[str, Any]] = []
        conditional = " if " in f" {objective.lower()} " or " when " in f" {objective.lower()} "
        if conditional:
            conditions.append({"condition_id": "objective_condition", "expression": "inputs.condition_result", "outcomes": ["yes", "no"]})
            nodes.append({"node_id": "objective_condition", "kind": "condition", "label": "Evaluate objective condition", "condition_id": "objective_condition"})
            edges.append({"edge_id": "plan_to_condition", "source": "plan_objective", "target": "objective_condition"})
        approval_node = None
        if external_write:
            approval_gates.append({"approval_gate_id": "external_action_approval", "approver_roles": ["approver"], "on_reject": "stop", "timeout_seconds": 86400})
            approval_node = {"node_id": "external_action_approval", "kind": "approval", "label": "Approve external action", "approval_gate_id": "external_action_approval"}
            nodes.append(approval_node)
        else:
            approval_node = None
        tool_refs = [{"tool_id": selected, "capability": cap}
                     for cap in capabilities if (selected := self._tool_for(cap, set(words))) is not None]
        input_fields = [{"name": "objective_context", "type": "object", "required": False}]
        if conditional:
            input_fields.append({"name": "condition_result", "type": "boolean", "required": True})
        for cap in capabilities:
            if cap == "read_spreadsheet":
                input_fields.extend([
                    {"name": "spreadsheet_id", "type": "string", "required": True},
                    {"name": "range", "type": "string", "required": True},
                ])
            elif cap == "send_email":
                input_fields.extend([
                    {"name": "email_to", "type": "string", "required": True},
                    {"name": "email_subject", "type": "string", "required": True},
                    {"name": "email_body", "type": "string", "required": True},
                ])
            elif cap == "update_spreadsheet":
                input_fields.extend([
                    {"name": "spreadsheet_id", "type": "string", "required": True},
                    {"name": "range", "type": "string", "required": True},
                    {"name": "values", "type": "array", "required": True},
                ])
            elif cap == "retrieve_records":
                input_fields.extend([
                    {"name": "path", "type": "string", "required": True},
                    {"name": "query", "type": "object", "required": False},
                ])
            elif cap == "send_notification":
                if self._tool_for(cap, set(words)) == "slack_send_notification":
                    input_fields.append({"name": "notification_text", "type": "string", "required": True})
                else:
                    input_fields.extend([
                        {"name": "path", "type": "string", "required": True},
                        {"name": "body", "type": "object", "required": True},
                    ])
        unique_fields, seen_names = [], set()
        for field in input_fields:
            if field["name"] not in seen_names:
                unique_fields.append(field)
                seen_names.add(field["name"])
        input_fields = unique_fields
        previous = "objective_condition" if conditional else "plan_objective"
        approval_inserted = False
        if conditional:
            edges.append({"edge_id": "condition_to_no_output", "source": "objective_condition", "target": "workflow_output", "outcome": "no"})
        for index, tool in enumerate(tool_refs):
            node_id = tool["capability"]
            node = {"node_id": node_id, "kind": "tool", "label": tool["capability"].replace("_", " ").title(),
                    "agent_id": agent_id, "tool_id": tool["tool_id"], "configuration": {"input_mapping": {}}}
            if tool["capability"] == "read_spreadsheet":
                node["configuration"]["input_mapping"] = {"spreadsheet_id": "inputs.spreadsheet_id", "range": "inputs.range"}
            elif tool["capability"] == "send_email":
                node["configuration"]["input_mapping"] = {"to": "inputs.email_to", "subject": "inputs.email_subject", "body": "inputs.email_body"}
            elif tool["capability"] == "update_spreadsheet":
                node["configuration"]["input_mapping"] = {"spreadsheet_id": "inputs.spreadsheet_id", "range": "inputs.range", "values": "inputs.values"}
            elif tool["capability"] == "retrieve_records":
                node["configuration"]["input_mapping"] = {"path": "inputs.path", "query": "inputs.query"}
            elif tool["capability"] == "send_notification":
                node["configuration"]["input_mapping"] = ({"text": "inputs.notification_text"}
                    if tool["tool_id"] == "slack_send_notification" else {"path": "inputs.path", "body": "inputs.body"})
            nodes.append(node)
            if external_write and tool["capability"] in {"send_email", "send_notification", "update_spreadsheet"}:
                if not approval_inserted:
                    if previous == "objective_condition":
                        edges.append({"edge_id": "condition_to_approval", "source": previous, "target": "external_action_approval", "outcome": "yes"})
                    else:
                        edges.append({"edge_id": "plan_to_approval", "source": previous, "target": "external_action_approval"})
                    approval_inserted = True
                    source = "external_action_approval"
                    outcome = "approved"
                else:
                    source = previous
                    outcome = None
                edges.append({"edge_id": f"{source}_to_{node_id}", "source": source, "target": node_id, **({"outcome": outcome} if outcome else {})})
                previous = node_id
            else:
                edges.append({"edge_id": f"{previous}_to_{node_id}", "source": previous, "target": node_id,
                              **({"outcome": "yes"} if previous == "objective_condition" else {})})
                previous = node_id
        output_node = {"node_id": "workflow_output", "kind": "output", "label": "Workflow result"}
        nodes.append(output_node)
        if external_write:
            edges.append({"edge_id": "approval_to_rejected", "source": "external_action_approval", "target": "rejected_output", "outcome": "rejected"})
            nodes.append({"node_id": "rejected_output", "kind": "output", "label": "Approval rejected",
                          "configuration": {"input_mapping": {"workflow_result": "inputs"}}})
        if previous == "objective_condition":
            output_node["configuration"] = {"input_mapping": {"workflow_result": "inputs"}}
            edges.append({"edge_id": "condition_to_output_yes", "source": previous, "target": "workflow_output", "outcome": "yes"})
        else:
            output_node["configuration"] = {"input_mapping": {"workflow_result": f"outputs.{previous}"}}
            edges.append({"edge_id": "last_to_output", "source": previous, "target": "workflow_output"})
        unresolved = [] if capabilities else [{"requirement": "No explicit capability identified", "reason": "needs_human_review"}]
        if capabilities:
            unresolved = [{"requirement": cap, "reason": "registry_assignment_pending"} for cap in capabilities]
        if trigger_resource_missing:
            unresolved.append({"requirement": "google_sheets_trigger_resource", "reason": "resource_reference_required"})
        return {
            "workflow_id": "planned_workflow",
            "version": 1,
            "name": objective.strip()[:200],
            "description": objective.strip(),
            "status": "draft",
            "inputs": input_fields,
            "outputs": [{"name": "workflow_result", "type": "object", "required": True}],
            "stakeholders": [{"stakeholder_id": "requester", "name": "Requesting builder", "role": "builder"}],
            "agents": [{
                "agent_id": agent_id, "role": "planner", "goal": "Decompose the objective into a reviewable workflow.",
                "instructions": "Produce structured workflow steps and identify unresolved requirements.",
                "model": {"provider": "openai", "model_id": "structured-output"}, "input_schema": {}, "output_schema": {},
                "capabilities": capabilities, "allowed_tool_ids": [], "permissions": ["workflow.read_input"],
                "limits": {"max_llm_calls": 1, "max_tool_calls": max(1, len(tool_refs)), "max_tokens": 4000, "max_retries": 1, "timeout_seconds": 300},
                "approval_requirements": [],
            }],
            "tools": tool_refs,
            "nodes": nodes,
            "edges": edges,
            "conditions": conditions,
            "approval_gates": approval_gates,
            "execution_policy": {"limits": {"max_llm_calls": 3, "max_tool_calls": 4, "max_tokens": 4000, "max_retries": 2, "timeout_seconds": 300}, "requires_review_before_execution": True, "allow_external_writes": external_write},
            "error_policy": {"on_validation_error": "reject", "on_runtime_error": "retry", "max_retries": 2},
            "metadata": {"domain": "generic", "unresolved_requirements": unresolved,
                         **({"trigger_templates": [trigger_template]} if trigger_template else {})},
        }

