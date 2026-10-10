"""Public planner request boundary."""

from __future__ import annotations

import hashlib
import uuid
from typing import Any

from .auth import authorize_planning
from .contracts import CONTRACT_VERSIONS
from .errors import PlannerFailure
from .idempotency import IdempotencyRecord, IdempotencyStore
from .provider import OpenAIStructuredOutputProvider, StructuredOutputProvider
from .validation import reject_sensitive, validate_workflow, preserve_unmapped_conditions


class PlannerService:
    def __init__(self, provider: StructuredOutputProvider | None = None, idempotency: IdempotencyStore | None = None) -> None:
        self.provider = provider or OpenAIStructuredOutputProvider()
        self.idempotency = idempotency or IdempotencyStore()

    def plan(self, request: dict[str, Any]) -> dict[str, Any]:
        request_id = str(request.get("request_id") or f"req_{uuid.uuid4().hex}")
        try:
            if request.get("operation") != "plan_workflow":
                raise PlannerFailure("INVALID_OPERATION", "The planner accepts only plan_workflow requests.", field="operation")
            payload = request.get("payload")
            if not isinstance(payload, dict):
                raise PlannerFailure("INVALID_REQUEST", "The request payload must be an object.", field="payload")
            objective = payload.get("objective", payload.get("requirement", ""))
            if not isinstance(objective, str) or not objective.strip():
                raise PlannerFailure("VALIDATION_FAILED", "A non-empty objective is required.", field="payload.objective")
            auth = payload.get("auth_context", request.get("auth_context"))
            authorize_planning(auth)
            workspace_id = auth["workspace_id"]
            idempotency_key = request.get("idempotency_key") or payload.get("idempotency_key")
            if not isinstance(idempotency_key, str) or len(idempotency_key) < 8:
                raise PlannerFailure("VALIDATION_FAILED", "An idempotency key of at least 8 characters is required.", field="idempotency_key")
            fingerprint_payload = {"objective": objective.strip(), "context": payload.get("context", {}), "subject_id": auth["subject_id"]}
            fingerprint = self.idempotency.fingerprint(fingerprint_payload)
            existing = self.idempotency.get(workspace_id, idempotency_key)
            if existing:
                if existing.fingerprint != fingerprint:
                    raise PlannerFailure("IDEMPOTENCY_KEY_REUSED", "The idempotency key was already used for a different request.", field="idempotency_key")
                return existing.response
            reject_sensitive(payload)
            workflow = self.provider.generate(objective.strip(), payload.get("context", {}))
            reject_sensitive(workflow)
            self._clear_proposed_assignments(workflow)
            workflow["workflow_id"] = self._workflow_id(workspace_id, objective)
            self._scope_planned_agents(workflow)
            workflow["metadata"] = {**workflow.get("metadata", {}), "contract_versions": CONTRACT_VERSIONS, "unresolved_requirements": workflow.get("metadata", {}).get("unresolved_requirements", [])}
            preserve_unmapped_conditions(workflow)
            normalized = validate_workflow(workflow)
            response = {"request_id": request_id, "status": 200, "data": {"workflow": normalized, "correlation_id": f"corr_{uuid.uuid4().hex}", "contract_versions": CONTRACT_VERSIONS}}
            self.idempotency.put(workspace_id, idempotency_key, IdempotencyRecord(fingerprint, response))
            return response
        except PlannerFailure as exc:
            return {"request_id": request_id, "status": 403 if exc.code in {"AUTHENTICATION_REQUIRED", "PLANNING_NOT_AUTHORIZED"} else 400, "data": None, "error": exc.envelope(request_id)}
        except (ValueError, TypeError, RuntimeError) as exc:
            return {"request_id": request_id, "status": 502, "data": None, "error": PlannerFailure("PLANNER_PROVIDER_FAILED", "The planning provider did not return a usable draft.", retryable=True).envelope(request_id)}

    @staticmethod
    def _clear_proposed_assignments(workflow: dict[str, Any]) -> None:
        """Model proposals describe requirements; only Registry can assign tools."""
        for agent in workflow.get("agents", []):
            agent["allowed_tool_ids"] = []
        for tool in workflow.get("tools", []):
            tool.pop("configuration_reference", None)

    @staticmethod
    def _workflow_id(workspace_id: str, objective: str) -> str:
        digest = hashlib.sha256(f"{workspace_id}:{objective}".encode()).hexdigest()[:16]
        return f"planned_{digest}"

    @staticmethod
    def _scope_planned_agents(workflow: dict[str, Any]) -> None:
        """Prevent unrelated generated revisions from sharing one mutable agent identity."""
        workflow_id = workflow.get("workflow_id", "planned_workflow")
        mapping = {}
        for agent in workflow.get("agents", []):
            old = agent.get("agent_id")
            if not isinstance(old, str):
                continue
            new = f"{workflow_id}_{old}"[:128]
            mapping[old] = new
            agent["agent_id"] = new
        for agent in workflow.get("agents", []):
            parent = agent.get("parent_agent_id")
            if parent in mapping:
                agent["parent_agent_id"] = mapping[parent]
        for node in workflow.get("nodes", []):
            if node.get("agent_id") in mapping:
                node["agent_id"] = mapping[node["agent_id"]]

