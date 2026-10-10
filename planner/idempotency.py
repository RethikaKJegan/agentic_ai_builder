"""Workspace-scoped idempotency for planning responses."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from threading import Lock
from typing import Any


@dataclass(frozen=True)
class IdempotencyRecord:
    fingerprint: str
    response: dict[str, Any]


class IdempotencyStore:
    def __init__(self) -> None:
        self._records: dict[tuple[str, str], IdempotencyRecord] = {}
        self._lock = Lock()

    @staticmethod
    def fingerprint(payload: dict[str, Any]) -> str:
        encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
        return hashlib.sha256(encoded.encode()).hexdigest()

    def get(self, workspace_id: str, key: str) -> IdempotencyRecord | None:
        with self._lock:
            return self._records.get((workspace_id, key))

    def put(self, workspace_id: str, key: str, record: IdempotencyRecord) -> None:
        with self._lock:
            self._records[(workspace_id, key)] = record

