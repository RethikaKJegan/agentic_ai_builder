"""Privacy-safe planner errors."""

from __future__ import annotations

from dataclasses import dataclass, field as dataclass_field
from typing import Any


@dataclass
class PlannerFailure(Exception):
    code: str
    message: str
    retryable: bool = False
    field: str | None = None
    details: dict[str, Any] = dataclass_field(default_factory=dict)

    def envelope(self, request_id: str) -> dict[str, Any]:
        return {
            "error_code": self.code,
            "message": self.message,
            "request_id": request_id,
            "retryable": self.retryable,
            "field": self.field,
            "details": self.details,
        }


def validation_error(request_id: str, message: str, field: str | None = None, **details: Any) -> dict[str, Any]:
    return PlannerFailure("WORKFLOW_VALIDATION_FAILED", message, field=field, details=details).envelope(request_id)

