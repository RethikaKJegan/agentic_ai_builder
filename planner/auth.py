"""Planning authorization, deliberately separate from tool authorization."""

from __future__ import annotations

from typing import Any

from .errors import PlannerFailure


def authorize_planning(context: dict[str, Any] | None) -> None:
    if not context or not context.get("subject_id") or not context.get("workspace_id"):
        raise PlannerFailure("AUTHENTICATION_REQUIRED", "An authenticated subject and workspace are required.")
    roles = set(context.get("roles", []))
    permissions = set(context.get("permissions", []))
    if "admin" not in roles and "builder" not in roles and "workflow.plan" not in permissions:
        raise PlannerFailure("PLANNING_NOT_AUTHORIZED", "The subject is not authorized to plan workflows.")

