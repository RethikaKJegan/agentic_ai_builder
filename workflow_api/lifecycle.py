"""Durable published-release, trigger, dispatch, and overview lifecycle.

The records in this module are data, never executable authority. Every dispatch
reconstructs a server-owned automation identity and refreshes Registry grants.
"""
from __future__ import annotations

from copy import deepcopy
import ast
from datetime import datetime, timedelta, timezone
import hashlib
import hmac
import json
import re
from uuid import uuid4

from jsonschema import Draft202012Validator
from registry.safety import reject_secrets


SUPPORTED_PROVIDERS = {
    "fake_push": "push",
    "fake_poll": "poll",
    "fake_schedule": "schedule",
    "generic_hmac_webhook": "push",
    "google_sheets": "poll",
    "github_webhook": "push",
    "slack_events": "push",
    "gmail_watch": "push",
    "brevo_webhook": "push",
    "configured_webhook": "push",
    "generic_rest": "poll",
    "google_drive": "poll",
    "google_calendar": "poll",
    "google_docs": "poll",
    "open_meteo": "poll",
    "open_library": "poll",
}
ACTIVE_RUN_STATES = {"queued", "running", "paused_for_approval"}


class LifecycleFailure(Exception):
    def __init__(self, code, message, status=409, retryable=False):
        super().__init__(message)
        self.code, self.status, self.retryable = code, status, retryable


def now_iso(clock):
    return datetime.fromtimestamp(clock(), timezone.utc).isoformat()


def identifier(prefix):
    return prefix + uuid4().hex


def json_digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, allow_nan=False).encode()).hexdigest()


class TriggerAdapter:
    """Provider boundary used by real signed webhooks and deterministic fakes."""

    def prepare(self, trigger):
        if trigger["provider_id"] not in SUPPORTED_PROVIDERS:
            raise LifecycleFailure("TRIGGER_PROVIDER_UNSUPPORTED", "This incoming event provider is not supported.", 400)
        if SUPPORTED_PROVIDERS[trigger["provider_id"]] != trigger["delivery"]:
            raise LifecycleFailure("TRIGGER_DELIVERY_MISMATCH", "The provider does not support this delivery mode.", 400)
        if trigger["delivery"] == "schedule":
            try:
                from zoneinfo import ZoneInfo
                ZoneInfo(trigger.get("timezone") or "")
            except Exception:
                raise LifecycleFailure("INVALID_TIMEZONE", "Use an IANA timezone for scheduled triggers.", 400) from None
            if not isinstance(trigger.get("schedule"), str) or len(trigger["schedule"].split()) != 5:
                raise LifecycleFailure("INVALID_SCHEDULE", "Use a five-field cron schedule.", 400)
        if trigger["delivery"] == "poll" and (type(trigger.get("poll_interval_seconds")) is not int or trigger["poll_interval_seconds"] < 1):
            raise LifecycleFailure("INVALID_POLL_INTERVAL", "Polling requires a positive interval.", 400)
        return "provider_" + json_digest({k: v for k, v in trigger.items() if k != "credential_reference"})[:24]

    def cleanup(self, _trigger):
        return True


class LifecycleService:
    def __init__(self, workflows, clock, adapter=None, trigger_secrets=None):
        self.workflows, self.store, self.clock = workflows, workflows.store, clock
        self.adapter = adapter or TriggerAdapter()
        self.trigger_secrets = dict(trigger_secrets or {})
        self.leased_tokens = {}
        with self.store.transaction(write=True) as db:
            db.execute("CREATE TABLE IF NOT EXISTS lifecycle_releases (workspace TEXT, release_id TEXT PRIMARY KEY, workflow_id TEXT, version INTEGER, generation INTEGER, state TEXT, document TEXT NOT NULL, UNIQUE(workspace, workflow_id, generation))")
            db.execute("CREATE TABLE IF NOT EXISTS lifecycle_active (workspace TEXT, workflow_id TEXT, release_id TEXT, PRIMARY KEY(workspace, workflow_id))")
            db.execute("CREATE TABLE IF NOT EXISTS lifecycle_operations (workspace TEXT, operation_id TEXT PRIMARY KEY, subject TEXT, idempotency_key TEXT, fingerprint TEXT, document TEXT NOT NULL, UNIQUE(workspace, subject, idempotency_key))")
            db.execute("CREATE TABLE IF NOT EXISTS lifecycle_triggers (workspace TEXT, binding_id TEXT PRIMARY KEY, release_id TEXT, workflow_id TEXT, state TEXT, provider_reference TEXT, document TEXT NOT NULL)")
            db.execute("CREATE TABLE IF NOT EXISTS lifecycle_identities (workspace TEXT, identity_id TEXT PRIMARY KEY, authority TEXT NOT NULL, document TEXT NOT NULL)")
            db.execute("CREATE TABLE IF NOT EXISTS lifecycle_receipts (workspace TEXT, receipt_id TEXT PRIMARY KEY, binding_id TEXT, event_identity TEXT, document TEXT NOT NULL, UNIQUE(workspace, binding_id, event_identity))")
            db.execute("CREATE TABLE IF NOT EXISTS lifecycle_jobs (workspace TEXT, job_id TEXT PRIMARY KEY, release_id TEXT, workflow_id TEXT, state TEXT, available_at TEXT, lease_until TEXT, attempt INTEGER, document TEXT NOT NULL, UNIQUE(workspace, workflow_id, release_id, job_id))")
            db.execute("CREATE TABLE IF NOT EXISTS lifecycle_checkpoints (workspace TEXT, binding_id TEXT, cursor TEXT, updated_at TEXT, PRIMARY KEY(workspace, binding_id))")
            db.execute("CREATE TABLE IF NOT EXISTS lifecycle_overview_events (sequence INTEGER PRIMARY KEY AUTOINCREMENT, workspace TEXT, workflow_id TEXT, document TEXT NOT NULL)")
            db.execute("CREATE TABLE IF NOT EXISTS lifecycle_tombstones (workspace TEXT, workflow_id TEXT, deleted_at TEXT, cleanup_state TEXT, PRIMARY KEY(workspace, workflow_id))")
            db.execute('CREATE TABLE IF NOT EXISTS lifecycle_preparations (operation_id TEXT PRIMARY KEY, workspace TEXT NOT NULL, document TEXT NOT NULL)')
            db.execute('CREATE INDEX IF NOT EXISTS lifecycle_preparations_workspace ON lifecycle_preparations(workspace)')
            db.execute('CREATE INDEX IF NOT EXISTS lifecycle_jobs_ready ON lifecycle_jobs(workspace,state,available_at,lease_until)')
            db.execute('CREATE TABLE IF NOT EXISTS lifecycle_job_claims (job_id TEXT PRIMARY KEY, token TEXT NOT NULL)')
            db.execute('CREATE INDEX IF NOT EXISTS lifecycle_triggers_active ON lifecycle_triggers(workspace,state,workflow_id)')
            # Recovery is lease-aware; another API instance may still be preparing.

    @staticmethod
    def authorize(auth, permission, roles=("admin",)):
        if (auth.get("decision") != "allow" or permission not in auth.get("permissions", []) or
                not set(auth.get("roles", [])).intersection(roles) or not all(auth.get("subject", {}).values())):
            raise LifecycleFailure("OPERATION_NOT_AUTHORIZED", "The current session cannot perform this lifecycle operation.", 403)

    def operation(self, db, workspace, auth, kind, key, workflow_id, expected, fingerprint):
        if not isinstance(key, str) or not re.fullmatch(r"[a-zA-Z0-9_-]{8,128}", key):
            raise LifecycleFailure("INVALID_IDEMPOTENCY_KEY", "Use a retry key of 8-128 safe characters.", 400)
        row = db.execute("SELECT fingerprint, document FROM lifecycle_operations WHERE workspace=? AND subject=? AND idempotency_key=?", (workspace, auth["subject"]["subject_id"], key)).fetchone()
        if row:
            if row[0] != fingerprint:
                raise LifecycleFailure("IDEMPOTENCY_KEY_REUSED", "This retry key belongs to another lifecycle request.")
            return json.loads(row[1]), True
        document = dict(operation_id=identifier("op_"), workspace_id=workspace, workflow_id=workflow_id,
                        subject_id=auth["subject"]["subject_id"], idempotency_key=key,
                        expected_release_id=expected, kind=kind, state="preparing", error_code=None)
        db.execute("INSERT INTO lifecycle_operations VALUES (?, ?, ?, ?, ?, ?)",
                   (workspace, document["operation_id"], document["subject_id"], key, fingerprint, json.dumps(document)))
        return document, False

    @staticmethod
    def save_operation(db, operation):
        db.execute("UPDATE lifecycle_operations SET document=? WHERE operation_id=? AND workspace=?",
                   (json.dumps(operation), operation["operation_id"], operation["workspace_id"]))

    def record_failure(self, request, auth, kind, failure):
        """Persist a safe terminal result after a mutation transaction rolls back."""
        payload = request.get("payload", {}) if isinstance(request, dict) else {}
        key = request.get("idempotency_key") if isinstance(request, dict) else None
        workflow_id = payload.get("workflow_id")
        if (failure.code == "OPERATION_NOT_AUTHORIZED" or not isinstance(workflow_id, str) or
                not isinstance(key, str) or not re.fullmatch(r"[a-zA-Z0-9_-]{8,128}", key)):
            return
        workspace = auth.get("subject", {}).get("workspace_id")
        if not workspace:
            return
        fingerprint = json_digest({"kind": kind, "payload": payload})
        with self.store.transaction(write=True) as db:
            operation, replay = self.operation(db, workspace, auth, kind, key, workflow_id,
                                               payload.get("expected_release_id"), fingerprint)
            if not replay or operation["state"] == "preparing":
                operation["state"] = "failed"
                operation["error_code"] = failure.code
                self.save_operation(db, operation)
                self.emit(db, workspace, workflow_id, "lifecycle.failed")

    def emit(self, db, workspace, workflow_id, event_type):
        event = dict(workspace_id=workspace, sequence=0, event_id=identifier("overview_"),
                     kind="workflow_deleted" if event_type == "workflow.deleted" else "workflow_updated",
                     workflow_id=workflow_id, overview=None)
        cursor = db.execute("INSERT INTO lifecycle_overview_events(workspace, workflow_id, document) VALUES (?, ?, ?)",
                            (workspace, workflow_id, "{}")).lastrowid
        event["sequence"] = cursor
        db.execute("UPDATE lifecycle_overview_events SET document=? WHERE sequence=?", (json.dumps(event), cursor))
        return event

    def activate(self, request, auth):
        from .activation import activate
        return activate(self, request, auth)

    def _release_for_operation(self, db, operation):
        prepared = db.execute('SELECT document FROM lifecycle_preparations WHERE operation_id=?', (operation['operation_id'],)).fetchone()
        if prepared:
            release_id = json.loads(prepared[0])['release_id']
            row = db.execute('SELECT document FROM lifecycle_releases WHERE workspace=? AND release_id=?', (operation['workspace_id'], release_id)).fetchone()
        else:
            # Compatibility for operations persisted before the preparation ledger.
            row = db.execute("SELECT document FROM lifecycle_releases WHERE workspace=? AND workflow_id=? ORDER BY generation DESC LIMIT 1", (operation["workspace_id"], operation["workflow_id"])).fetchone()
        return json.loads(row[0]) if row else None

    def _normalize_trigger(self, workspace, release_id, workflow_id, raw, index):
        if not isinstance(raw, dict) or any(k in raw for k in ("workspace_id", "release_id", "health")):
            raise LifecycleFailure("INVALID_TRIGGER", "Trigger authority and health are server-owned.", 400)
        delivery, provider = raw.get("delivery"), raw.get("provider_id")
        trigger = dict(binding_id=raw.get("binding_id") or f"bind_{release_id[4:16]}_{index}", workspace_id=workspace,
                       provider_id=provider, resource_id=raw.get("resource_id", "default"), event_type=raw.get("event_type", "event"),
                       delivery=delivery, credential_reference=raw.get("credential_reference", "none"),
                       event_schema=raw.get("event_schema", {"type": "object"}), input_mapping=raw.get("input_mapping", {}),
                       filters=raw.get("filters", {}), timezone=raw.get("timezone"), schedule=raw.get("schedule"),
                       poll_input=raw.get("poll_input", {}),
                       poll_interval_seconds=raw.get("poll_interval_seconds"), baseline_policy=raw.get("baseline_policy", "current_only"), health="preparing")
        if (provider not in SUPPORTED_PROVIDERS or delivery not in {"push", "poll", "schedule"} or
                trigger["baseline_policy"] not in {"current_only", "authorized_backfill"} or
                not isinstance(trigger["event_schema"], dict) or not isinstance(trigger["input_mapping"], dict) or not isinstance(trigger["filters"], dict) or not isinstance(trigger["poll_input"], dict)):
            raise LifecycleFailure("INVALID_TRIGGER", "The trigger configuration is unsupported.", 400)
        Draft202012Validator.check_schema(trigger["event_schema"])
        return trigger

    def ingest(self, binding_id, event, auth=None, signature=None, timestamp=None, checkpoint=None):
        if not isinstance(event, dict):
            raise LifecycleFailure("INVALID_EVENT", "The event payload must be an object.", 400)
        reject_secrets(event)
        with self.store.transaction() as db:
            row = db.execute("SELECT workspace, release_id, workflow_id, state, document FROM lifecycle_triggers WHERE binding_id=?", (binding_id,)).fetchone()
            if not row or row[3] != "ready":
                raise LifecycleFailure("TRIGGER_NOT_ACTIVE", "This trigger binding is not active.", 404)
            workspace, release_id, workflow_id, _, encoded = row
            trigger = json.loads(encoded)
            provider = trigger["provider_id"]
            if provider == "generic_hmac_webhook":
                secret = self.trigger_secrets.get(trigger["credential_reference"])
                if not secret or not isinstance(timestamp, str) or not timestamp.isdigit():
                    raise LifecycleFailure("SOURCE_VERIFICATION_FAILED", "The webhook could not be verified.", 401)
                if abs(self.clock() - int(timestamp)) > 300:
                    raise LifecycleFailure("SOURCE_VERIFICATION_FAILED", "The webhook timestamp is outside the freshness window.", 401)
                expected = hmac.new(secret.encode(), (timestamp + "." + json.dumps(event, sort_keys=True, separators=(",", ":"))).encode(), hashlib.sha256).hexdigest()
                if not isinstance(signature, str) or not hmac.compare_digest(expected, signature):
                    raise LifecycleFailure("SOURCE_VERIFICATION_FAILED", "The webhook could not be verified.", 401)
            else:
                self.authorize(auth or {}, "events.ingest", ("admin", "builder"))
                if auth["subject"]["workspace_id"] != workspace:
                    raise LifecycleFailure("WORKSPACE_MISMATCH", "The event binding belongs to another workspace.", 403)
            if event.get("actor_id", "") == "automation:" + workflow_id or event.get("causation_id", "").startswith("run_"):
                raise LifecycleFailure("SELF_ORIGINATED_EVENT", "Self-originated events are not dispatched.", 202)
            errors = list(Draft202012Validator(trigger["event_schema"]).iter_errors(event))
            if errors:
                raise LifecycleFailure("EVENT_SCHEMA_INVALID", "The event does not match the binding schema.", 400)
            if any(event.get(key) != value for key, value in trigger["filters"].items()):
                return {"accepted": False, "reason": "FILTERED", "duplicate": False, "job": None}
            event_id = event.get("event_id")
            if not isinstance(event_id, str) or not re.fullmatch(r"[a-zA-Z0-9_.:-]{1,128}", event_id):
                event_id = json_digest(event)
            existing = db.execute("SELECT document FROM lifecycle_receipts WHERE workspace=? AND binding_id=? AND event_identity=?", (workspace, binding_id, event_id)).fetchone()
            if existing:
                receipt = json.loads(existing[0])
                job = db.execute("SELECT document FROM lifecycle_jobs WHERE job_id=?", (receipt["job_id"],)).fetchone()
                return {"accepted": True, "duplicate": True, "receipt_id": receipt["receipt_id"], "job": json.loads(job[0])}
            inputs = {name: self._input_value(event, path, trigger) for name, path in trigger["input_mapping"].items()}
            receipt_id, job_id = identifier("receipt_"), identifier("job_")
            identity_id = json.loads(db.execute("SELECT document FROM lifecycle_releases WHERE release_id=?", (release_id,)).fetchone()[0])["automation_identity_id"]
            receipt = dict(receipt_id=receipt_id, binding_id=binding_id, event_identity=event_id,
                           received_at=now_iso(self.clock), job_id=job_id)
            job = dict(job_id=job_id, workspace_id=workspace, release_id=release_id, event_receipt_id=receipt_id,
                       deduplication_key=json_digest([workspace, binding_id, event_id, workflow_id]), automation_identity_id=identity_id,
                       inputs=inputs, state="queued", attempt=0, lease_until=None, causation_id=event.get("causation_id"))
            db.execute("INSERT INTO lifecycle_receipts VALUES (?, ?, ?, ?, ?)", (workspace, receipt_id, binding_id, event_id, json.dumps(receipt)))
            db.execute("INSERT INTO lifecycle_jobs VALUES (?, ?, ?, ?, 'queued', ?, NULL, 0, ?)",
                       (workspace, job_id, release_id, workflow_id, now_iso(self.clock), json.dumps(job)))
            if checkpoint is not None:
                if trigger["delivery"] != "poll" or not isinstance(checkpoint, str):
                    raise LifecycleFailure("INVALID_CHECKPOINT", "Only polling adapters can advance a string checkpoint.", 400)
                self._save_checkpoint(db, workspace, binding_id, checkpoint)
            self.emit(db, workspace, workflow_id, "dispatch.queued")
            return {"accepted": True, "duplicate": False, "receipt_id": receipt_id, "job": job}

    def verify_webhook(self, binding_id, provider_id, raw_body, signature, timestamp=None):
        """Verify provider delivery before parsing or dispatching its event."""
        with self.store.transaction(write=False) as db:
            row = db.execute("SELECT state, document FROM lifecycle_triggers WHERE binding_id=?", (binding_id,)).fetchone()
        if not row or row[0] != "ready":
            raise LifecycleFailure("TRIGGER_NOT_ACTIVE", "This trigger binding is not active.", 404)
        trigger = json.loads(row[1])
        if trigger["provider_id"] != provider_id or trigger["delivery"] != "push":
            raise LifecycleFailure("TRIGGER_DELIVERY_MISMATCH", "This webhook does not match its trigger binding.", 400)
        secret = self.trigger_secrets.get(trigger["credential_reference"])
        if not isinstance(secret, str) or not secret or not isinstance(raw_body, bytes):
            raise LifecycleFailure("SOURCE_VERIFICATION_FAILED", "The webhook could not be verified.", 401)
        if provider_id == "github_webhook":
            expected = "sha256=" + hmac.new(secret.encode(), raw_body, hashlib.sha256).hexdigest()
        elif provider_id == "slack_events":
            if not isinstance(timestamp, str) or not timestamp.isdigit() or abs(self.clock() - int(timestamp)) > 300:
                raise LifecycleFailure("SOURCE_VERIFICATION_FAILED", "The webhook timestamp is outside the freshness window.", 401)
            expected = "v0=" + hmac.new(secret.encode(), b"v0:" + timestamp.encode() + b":" + raw_body, hashlib.sha256).hexdigest()
        else:
            expected = hmac.new(secret.encode(), raw_body, hashlib.sha256).hexdigest()
        if not isinstance(signature, str) or not hmac.compare_digest(expected, signature):
            raise LifecycleFailure("SOURCE_VERIFICATION_FAILED", "The webhook could not be verified.", 401)
        return trigger

    def poll(self, binding_id, changes, cursor, auth):
        """Apply an adapter poll batch with an explicit first-poll baseline policy."""
        self.authorize(auth, "events.ingest", ("admin", "builder"))
        if not isinstance(changes, list) or not isinstance(cursor, str) or not cursor:
            raise LifecycleFailure("INVALID_POLL_BATCH", "Polling requires a change list and stable cursor.", 400)
        with self.store.transaction() as db:
            row = db.execute("SELECT workspace, state, document FROM lifecycle_triggers WHERE binding_id=?", (binding_id,)).fetchone()
            if not row or row[1] != "ready":
                raise LifecycleFailure("TRIGGER_NOT_ACTIVE", "This polling binding is not active.", 404)
            trigger = json.loads(row[2])
            if trigger["delivery"] != "poll":
                raise LifecycleFailure("TRIGGER_DELIVERY_MISMATCH", "This binding is not a polling source.", 400)
            checkpoint = db.execute("SELECT cursor FROM lifecycle_checkpoints WHERE workspace=? AND binding_id=?", (row[0], binding_id)).fetchone()
            if checkpoint is None and trigger["baseline_policy"] == "current_only":
                db.execute("INSERT INTO lifecycle_checkpoints VALUES (?, ?, ?, ?)", (row[0], binding_id, cursor, now_iso(self.clock)))
                return {"baseline": True, "cursor": cursor, "receipts": []}
        receipts = []
        for event in changes:
            receipts.append(self.ingest(binding_id, event, auth))
        # Filtered and duplicate receipts are successful ingestion too. Advance
        # only after the complete batch; failures replay through receipt dedup.
        with self.store.transaction() as db:
            self._save_checkpoint(db, auth['subject']['workspace_id'], binding_id, cursor)
        return {"baseline": False, "cursor": cursor, "receipts": receipts}

    def _save_checkpoint(self, db, workspace, binding_id, cursor):
        # Older project databases key this table by binding_id alone. Avoid
        # naming a composite ON CONFLICT target absent from those databases.
        updated_at = now_iso(self.clock)
        updated = db.execute('UPDATE lifecycle_checkpoints SET cursor=?, updated_at=? WHERE workspace=? AND binding_id=?',
                             (cursor, updated_at, workspace, binding_id))
        if updated.rowcount == 0:
            db.execute('INSERT INTO lifecycle_checkpoints (workspace, binding_id, cursor, updated_at) VALUES (?, ?, ?, ?)',
                       (workspace, binding_id, cursor, updated_at))

    def tick_schedule(self, binding_id, event, scheduled_at, auth):
        """Create one deduplicated receipt for an aware scheduler instant."""
        try:
            instant = datetime.fromisoformat(scheduled_at)
            if instant.tzinfo is None:
                raise ValueError()
        except Exception:
            raise LifecycleFailure("INVALID_SCHEDULE_TICK", "A schedule tick requires a timezone-aware instant.", 400) from None
        with self.store.transaction(write=False) as db:
            row = db.execute("SELECT state, document FROM lifecycle_triggers WHERE binding_id=?", (binding_id,)).fetchone()
            if not row or row[0] != "ready":
                raise LifecycleFailure("TRIGGER_NOT_ACTIVE", "This schedule binding is not active.", 404)
            if json.loads(row[1])["delivery"] != "schedule":
                raise LifecycleFailure("TRIGGER_DELIVERY_MISMATCH", "This binding is not a schedule source.", 400)
        payload = deepcopy(event)
        payload.setdefault("event_id", "schedule:" + scheduled_at)
        return self.ingest(binding_id, payload, auth)

    @staticmethod
    def event_path(path):
        """Parse data access only; never evaluate a provider mapping as code."""
        if path == '':
            return []
        try:
            tree = ast.parse(path, mode='eval')
            if len(list(ast.walk(tree))) > 100:
                raise ValueError()
            def parts(node):
                if isinstance(node, ast.Name) and not node.id.startswith('_'):
                    return [node.id]
                if isinstance(node, ast.Attribute) and not node.attr.startswith('_'):
                    return parts(node.value) + [node.attr]
                if isinstance(node, ast.Subscript) and isinstance(node.slice, ast.Constant):
                    key = node.slice.value
                    if type(key) in (str, int) and not (isinstance(key, str) and key.startswith('_')):
                        return parts(node.value) + [key]
                raise ValueError()
            return parts(tree.body)
        except (ValueError, TypeError, SyntaxError, RecursionError):
            raise LifecycleFailure('EVENT_MAPPING_FAILED', 'Use a data path with literal field names or indexes.', 400) from None

    @classmethod
    def _lookup(cls, value, path):
        current = value
        for part in cls.event_path(path):
            try:
                if not isinstance(current, (dict, list)) or (isinstance(current, list) and type(part) is not int):
                    raise KeyError()
                current = current[part]
            except (KeyError, IndexError, TypeError):
                raise LifecycleFailure("EVENT_MAPPING_FAILED", "A configured input path is absent.", 400)
        return deepcopy(current)

    @classmethod
    def _input_value(cls, event, mapping, trigger):
        if isinstance(mapping, str):
            return cls._lookup(event, mapping)
        if isinstance(mapping, dict) and set(mapping) == {"constant"}:
            constant = mapping["constant"]
            if isinstance(constant, str) and constant == "$trigger.resource_id":
                return trigger["resource_id"]
            if isinstance(constant, (str, int, float, bool, list, dict)) or constant is None:
                return deepcopy(constant)
        raise LifecycleFailure("EVENT_MAPPING_FAILED", "A configured input mapping is unsupported.", 400)

    def lease(self, workspace, limit=10, seconds=30):
        with self.store.transaction() as db:
            now = now_iso(self.clock)
            rows = db.execute("SELECT job_id, document FROM lifecycle_jobs WHERE workspace=? AND (state='queued' OR (state='leased' AND lease_until<?)) AND available_at<=? ORDER BY rowid LIMIT ?", (workspace, now, now, limit)).fetchall()
            jobs = []
            for job_id, encoded in rows:
                job = json.loads(encoded)
                job["state"], job["attempt"] = "leased", job["attempt"] + 1
                job["lease_until"] = (datetime.fromtimestamp(self.clock(), timezone.utc) + timedelta(seconds=seconds)).isoformat()
                db.execute("UPDATE lifecycle_jobs SET state='leased', lease_until=?, attempt=?, document=? WHERE job_id=?", (job["lease_until"], job["attempt"], json.dumps(job), job_id))
                token=uuid4().hex
                db.execute('INSERT INTO lifecycle_job_claims VALUES (?,?) ON CONFLICT(job_id) DO UPDATE SET token=excluded.token',(job_id,token))
                self.leased_tokens[job_id]=token
                jobs.append(job)
            return jobs

    def poll_bindings(self, workspace):
        """Return active polling bindings without credential material."""
        with self.store.transaction(write=False) as db:
            rows = db.execute("SELECT binding_id, document FROM lifecycle_triggers WHERE workspace=? AND state='ready'", (workspace,)).fetchall()
        return [json.loads(encoded) for _binding, encoded in rows if json.loads(encoded).get('delivery') == 'poll']

    def execute_job(self, job_id, runner, max_attempts=3, claim=None):
        from .worker_control import LeaseHeartbeat
        claim=claim or self.leased_tokens.get(job_id)
        def renew():
            with self.store.transaction() as db:
                row=db.execute('SELECT token FROM lifecycle_job_claims WHERE job_id=?',(job_id,)).fetchone()
                current=db.execute('SELECT document FROM lifecycle_jobs WHERE job_id=?',(job_id,)).fetchone()
                if not row or row[0]!=claim or not current:return False
                job=json.loads(current[0])
                if job['state']!='leased':return False
                job['lease_until']=(datetime.fromtimestamp(self.clock(),timezone.utc)+timedelta(seconds=120)).isoformat()
                db.execute('UPDATE lifecycle_jobs SET lease_until=?,document=? WHERE job_id=?',(job['lease_until'],json.dumps(job),job_id))
            return True
        with LeaseHeartbeat(renew,interval=10):
            return self._execute_claimed_job(job_id,runner,max_attempts,claim)

    def _execute_claimed_job(self, job_id, runner, max_attempts, claim):
        with self.store.transaction() as db:
            row = db.execute("SELECT document FROM lifecycle_jobs WHERE job_id=?", (job_id,)).fetchone()
            if not row:
                raise LifecycleFailure("JOB_NOT_FOUND", "The dispatch job was not found.", 404)
            job = json.loads(row[0])
            if job["state"] == "completed":
                return job
            current_claim=db.execute('SELECT token FROM lifecycle_job_claims WHERE job_id=?',(job_id,)).fetchone()
            if not claim or not current_claim or current_claim[0]!=claim:
                raise LifecycleFailure('JOB_LEASE_LOST','This worker no longer owns the dispatch job.')
            if job['state']!='leased':return job
            if not job.get('lease_until') or job['lease_until']<=now_iso(self.clock):
                raise LifecycleFailure('JOB_LEASE_EXPIRED','The dispatch lease expired before execution.')
            release_row = db.execute("SELECT state, document FROM lifecycle_releases WHERE release_id=?", (job["release_id"],)).fetchone()
            identity_row = db.execute("SELECT authority, document FROM lifecycle_identities WHERE identity_id=?", (job["automation_identity_id"],)).fetchone()
            tombstoned = db.execute("SELECT 1 FROM lifecycle_tombstones WHERE workspace=? AND workflow_id=?", (job["workspace_id"], self._job_workflow(db, job_id))).fetchone()
            if not release_row or not identity_row or json.loads(identity_row[1])["active"] is not True or tombstoned:
                return self._finish_job(db, job, "cancelled", "EXECUTION_AUTHORITY_REVOKED",claim)
            release, auth = json.loads(release_row[1]), json.loads(identity_row[0])
            workflow = self.store.get(db, job["workspace_id"], release["revision"]["workflow_id"], release["revision"]["workflow_version"])
            if not workflow or not self.workflows.registry_adapter.review(workflow, auth)["ready"]:
                return self._finish_job(db, job, "failed", "ASSIGNMENT_REVALIDATION_FAILED",claim)
        resolver=getattr(self.workflows,'worker_authenticate',None)
        if resolver:
            fresh=resolver(job['workspace_id'],auth['subject']['subject_id'])
            if fresh is None:
                with self.store.transaction() as db:return self._finish_job(db,job,'cancelled','EXECUTION_AUTHORITY_REVOKED',claim)
            auth=fresh
        request = dict(request_id="req_" + job_id, operation="execute_workflow", idempotency_key=job["deduplication_key"],
                       payload={**release["revision"], "inputs": job["inputs"]})
        run=None
        try:
            run = runner.runtime.create_automation_run(request, auth)
            run = runner.advance(run["run_id"], auth)
            with self.store.transaction() as db:
                job["run_id"] = run["run_id"]
                return self._finish_job(db, job, "completed" if run["status"] not in {"failed", "blocked", "cancelled"} else "failed", None,claim)
        except Exception as exc:
            with self.store.transaction() as db:
                token=db.execute('SELECT token FROM lifecycle_job_claims WHERE job_id=?',(job_id,)).fetchone()
                stored=db.execute('SELECT document FROM lifecycle_jobs WHERE job_id=?',(job_id,)).fetchone()
                if not token or token[0]!=claim or json.loads(stored[0])['state']!='leased':return json.loads(stored[0])
                from .postgres import DatabaseFailure
                import sqlite3
                transient=isinstance(exc,DatabaseFailure) and exc.retryable or isinstance(exc,sqlite3.OperationalError) and getattr(exc,'sqlite_errorcode',0)&255 in (sqlite3.SQLITE_BUSY,sqlite3.SQLITE_LOCKED)
                state='queued' if run is None and transient and job['attempt']<max_attempts else 'dead_letter'
                job["lease_until"] = None
                job["last_error_code"] = "RUNTIME_DISPATCH_FAILED" if transient else "RUNTIME_DISPATCH_UNCERTAIN"
                db.execute("UPDATE lifecycle_jobs SET state=?, lease_until=NULL, available_at=?, document=? WHERE job_id=?",
                           (state, now_iso(self.clock), json.dumps({**job, "state": state}), job_id))
                return {**job, "state": state}

    def _job_workflow(self, db, job_id):
        return db.execute("SELECT workflow_id FROM lifecycle_jobs WHERE job_id=?", (job_id,)).fetchone()[0]

    def _finish_job(self, db, job, state, error, claim=None):
        if claim:
            current=db.execute('SELECT document FROM lifecycle_jobs WHERE job_id=?',(job['job_id'],)).fetchone()
            token=db.execute('SELECT token FROM lifecycle_job_claims WHERE job_id=?',(job['job_id'],)).fetchone()
            if not token or token[0]!=claim or json.loads(current[0])['state']!='leased':return json.loads(current[0])
        job["state"], job["lease_until"] = state, None
        if error:
            job["last_error_code"] = error
        db.execute("UPDATE lifecycle_jobs SET state=?, lease_until=NULL, document=? WHERE job_id=?", (state, json.dumps(job), job["job_id"]))
        self.emit(db, job["workspace_id"], self._job_workflow(db, job["job_id"]), "dispatch." + state)
        return job

    def replay(self, job_id, auth):
        self.authorize(auth, "workflow.execute")
        workspace = auth["subject"]["workspace_id"]
        with self.store.transaction() as db:
            row = db.execute("SELECT document FROM lifecycle_jobs WHERE workspace=? AND job_id=?", (workspace, job_id)).fetchone()
            if not row:
                raise LifecycleFailure("JOB_NOT_FOUND", "The dispatch job was not found.", 404)
            job = json.loads(row[0])
            if job["state"] not in {"failed", "dead_letter"}:
                raise LifecycleFailure("JOB_NOT_REPLAYABLE", "Only failed jobs can be replayed.")
            job.update(state="queued", lease_until=None)
            db.execute("UPDATE lifecycle_jobs SET state='queued', available_at=?, lease_until=NULL, document=? WHERE job_id=?", (now_iso(self.clock), json.dumps(job), job_id))
            return job

    def disable(self, request, auth):
        return self._stop(request, auth, deleting=False)

    def delete(self, request, auth):
        return self._stop(request, auth, deleting=True)

    def _stop(self, request, auth, deleting):
        from .activation import stop
        return stop(self, request, auth, deleting)

    def reconcile_cleanup(self, workspace):
        from .activation import reconcile, reconcile_cleanup
        reconcile(self, workspace)
        return reconcile_cleanup(self, workspace)

    def overview(self, auth, after_sequence=None, cursor=None):
        self.authorize(auth, "workflow.view", ("admin", "builder", "viewer", "approver"))
        workspace = auth["subject"]["workspace_id"]
        with self.store.transaction(write=False) as db:
            if after_sequence is not None:
                rows = db.execute("SELECT document FROM lifecycle_overview_events WHERE workspace=? AND sequence>? ORDER BY sequence LIMIT 200", (workspace, after_sequence)).fetchall()
                items = [json.loads(row[0]) for row in rows]
                return {"items": items, "next_sequence": items[-1]["sequence"] if items else after_sequence, "has_more": len(items) == 200}
            from .workflow_pages import read_page
            page = read_page(self.store, workspace, cursor, connection=db)
            documents = page['items']
            identities = [item['workflow_id'] for item in documents]
            run_summaries = {}
            if identities and self._table(db, "runtime_runs"):
                slots = ','.join('?' for _ in identities)
                rows = db.execute("""SELECT workflow_id, run_id, json_extract(document, '$.status'),
                    (SELECT COUNT(*) FROM json_each(runtime_runs.document, '$.approvals') a
                     WHERE json_extract(a.value, '$.status')='pending')
                    FROM runtime_runs WHERE workspace=? AND workflow_id IN (""" + slots + ") ORDER BY rowid DESC", (workspace, *identities))
                for identity, run_id, status, pending in rows:
                    summary = run_summaries.setdefault(identity, {
                        'latest_run_id': run_id, 'latest_run_status': status,
                        'active_run_count': 0, 'pending_approval_count': 0})
                    summary['active_run_count'] += status in ACTIVE_RUN_STATES
                    summary['pending_approval_count'] += pending
            items = []
            for workflow in documents:
                workflow_id = workflow["workflow_id"]
                if db.execute("SELECT 1 FROM lifecycle_tombstones WHERE workspace=? AND workflow_id=?", (workspace, workflow_id)).fetchone():
                    continue
                release_row = db.execute("SELECT r.document FROM lifecycle_active a JOIN lifecycle_releases r ON r.release_id=a.release_id WHERE a.workspace=? AND a.workflow_id=?", (workspace, workflow_id)).fetchone()
                if release_row is None:
                    release_row = db.execute("SELECT document FROM lifecycle_releases WHERE workspace=? AND workflow_id=? ORDER BY generation DESC LIMIT 1", (workspace, workflow_id)).fetchone()
                release = json.loads(release_row[0]) if release_row else None
                summary = run_summaries.get(workflow_id, {
                    'active_run_count': 0, 'latest_run_id': None,
                    'latest_run_status': None, 'pending_approval_count': 0})
                published_row=db.execute("SELECT MAX(version) FROM revisions WHERE workspace=? AND workflow_id=? AND json_extract(document,'$.status')='published'",(workspace,workflow_id)).fetchone()
                items.append(dict(workflow_id=workflow_id, name=workflow["name"],
                                  draft_version=workflow["version"] if workflow["status"] == "draft" else None,
                                  published_version=published_row[0],
                                  release_id=release["release_id"] if release else None,
                                  activation_state=release["state"] if release else None,
                                  **summary, updated_at=now_iso(self.clock)))
            sequence = db.execute("SELECT COALESCE(MAX(sequence), 0) FROM lifecycle_overview_events WHERE workspace=?", (workspace,)).fetchone()[0]
            return {"items": items, "next_sequence": sequence, "has_more": page['has_more'], "next_cursor": page['next_cursor'], "total": page['total']}

    @staticmethod
    def _table(db, name):
        return bool(db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (name,)).fetchone())

    def get_operation(self, operation_id, auth):
        self.authorize(auth, "workflow.view", ("admin", "builder", "viewer", "approver"))
        with self.store.transaction(write=False) as db:
            row = db.execute("SELECT document FROM lifecycle_operations WHERE workspace=? AND operation_id=?", (auth["subject"]["workspace_id"], operation_id)).fetchone()
            if not row:
                raise LifecycleFailure("OPERATION_NOT_FOUND", "The lifecycle operation was not found.", 404)
            return {"operation": json.loads(row[0])}
