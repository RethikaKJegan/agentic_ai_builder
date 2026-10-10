"""Acceptance coverage for workflow operations v2 and durable event dispatch."""
from copy import deepcopy
import hashlib
import hmac
import json
from pathlib import Path
import tempfile
import unittest

from jsonschema import Draft202012Validator

from runtime import RuntimeService
from runtime.graph import GraphRunner
from workflow_api.lifecycle import LifecycleFailure, TriggerAdapter
from workflow_api.service import WorkflowService
from workflow_api.storage import WorkflowStore


ROOT = Path(__file__).resolve().parents[1]


class RecordingAdapter(TriggerAdapter):
    def __init__(self, fail_at=None, cleanup=True):
        self.prepared, self.cleaned, self.fail_at, self.cleanup_result = [], [], fail_at, cleanup

    def prepare(self, trigger):
        if self.fail_at == len(self.prepared):
            raise LifecycleFailure("PROVIDER_ACTIVATION_FAILED", "Provider registration failed.", 502, True)
        self.prepared.append(trigger["binding_id"])
        return super().prepare(trigger)

    def cleanup(self, trigger):
        self.cleaned.append(trigger["binding_id"])
        return self.cleanup_result


class LifecycleTests(unittest.TestCase):
    def setUp(self):
        (ROOT / ".local/tests").mkdir(parents=True, exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(dir=ROOT / ".local/tests")
        self.path = Path(self.temp.name) / "lifecycle.sqlite3"
        self.now = 1_800_000_000
        self.adapter = RecordingAdapter()
        self.service = WorkflowService(WorkflowStore(self.path), lifecycle_adapter=self.adapter,
                                       trigger_secrets={"cred_webhook": "test-only-signing-key"}, clock=lambda: self.now)
        self.runtime = RuntimeService(self.service, clock=lambda: self.now)
        self.runner = GraphRunner(self.runtime)
        self.service.runtime_runner = self.runner
        self.workflow = json.loads((ROOT / "shared/contracts/examples/workflows/support-triage.json").read_text())
        self.workflow.update(status="published", version=1)
        self.workflow["outputs"] = []
        self.workflow["metadata"] = {"workspace_id": "local-workspace", "validation_state": "validated", "approved_by": "owner"}
        with self.service.store.transaction() as db:
            self.service.store.put(db, "local-workspace", self.workflow)
        self.auth = dict(subject=dict(subject_id="owner", workspace_id="local-workspace"), roles=["admin"],
                         permissions=["workflow.view", "workflow.publish", "workflow.delete", "workflow.execute", "events.ingest", "runs.view"],
                         scopes=["workspace:read", "workspace:write"], decision="allow")

    def tearDown(self):
        self.temp.cleanup()

    def trigger(self, provider="fake_push", delivery="push", binding_id="binding_main"):
        return dict(binding_id=binding_id, provider_id=provider, resource_id="resource_1", event_type="request.created",
                    delivery=delivery, credential_reference="cred_webhook" if provider == "generic_hmac_webhook" else "none",
                    event_schema={"type": "object", "properties": {"event_id": {"type": "string"}, "body": {"type": "string"}},
                                  "required": ["event_id", "body"], "additionalProperties": False},
                    input_mapping={"request_text": "body"}, filters={}, timezone="UTC" if delivery == "schedule" else None,
                    schedule="*/5 * * * *" if delivery == "schedule" else None,
                    poll_interval_seconds=60 if delivery == "poll" else None, baseline_policy="current_only")

    def activate(self, key="activate_key_1234", expected=None, triggers=None, version=1):
        request = dict(request_id="req_activate", idempotency_key=key,
                       payload=dict(workflow_id=self.workflow["workflow_id"], workflow_version=version,
                                    expected_release_id=expected, triggers=triggers if triggers is not None else [self.trigger()]))
        return self.service.lifecycle.activate(request, self.auth)

    def test_first_publish_deduplicated_event_dispatch_and_overview(self):
        activated = self.activate()
        self.assertEqual(activated["release"]["state"], "active")
        self.assertEqual(self.activate(), activated)
        contract = json.loads((ROOT / "shared/contracts/workflow-operations-v2.json").read_text())
        Draft202012Validator(contract["$defs"]["release"]).validate(activated["release"])
        first = self.service.lifecycle.ingest("binding_main", {"event_id": "event_1", "body": "Please help"}, self.auth)
        duplicate = self.service.lifecycle.ingest("binding_main", {"event_id": "event_1", "body": "Please help"}, self.auth)
        self.assertFalse(first["duplicate"])
        self.assertTrue(duplicate["duplicate"])
        self.assertEqual(first["job"]["job_id"], duplicate["job"]["job_id"])
        leased = self.service.lifecycle.lease("local-workspace")
        self.assertEqual(len(leased), 1)
        completed = self.service.lifecycle.execute_job(leased[0]["job_id"], self.runner)
        self.assertEqual(completed["state"], "completed")
        overview = self.service.lifecycle.overview(self.auth)
        self.assertEqual(overview["items"][0]["release_id"], activated["release"]["release_id"])
        self.assertEqual(overview["items"][0]["latest_run_status"], "completed")
        events = self.service.lifecycle.overview(self.auth, 0)
        self.assertEqual([event["sequence"] for event in events["items"]], sorted(event["sequence"] for event in events["items"]))
        for event in events["items"]:
            Draft202012Validator(contract).validate(event)
        run = self.runtime.get_run(completed["run_id"], self.auth)
        run_events = self.runtime.events(completed["run_id"], self.auth)["items"]
        evidence = dict(kind="deterministic-local-lifecycle-acceptance", release_id=activated["release"]["release_id"],
                        receipt_id=first["receipt_id"], dispatch_job_id=completed["job_id"], run_id=run["run_id"],
                        correlation_id=run["correlation_id"], trace_reference=run["trace_reference"],
                        run_event_ids=[item["event_id"] for item in run_events], overview_sequences=[item["sequence"] for item in events["items"]])
        target = ROOT / ".local/lifecycle-review/evidence.json"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(evidence, indent=2) + "\n")

    def test_republish_is_atomic_and_old_job_retains_release(self):
        first = self.activate()
        old_job = self.service.lifecycle.ingest("binding_main", {"event_id": "old", "body": "Old"}, self.auth)["job"]
        second_workflow = deepcopy(self.workflow)
        second_workflow["version"] = 2
        with self.service.store.transaction() as db:
            self.service.store.put(db, "local-workspace", second_workflow)
        second_trigger = self.trigger(binding_id="binding_second")
        second = self.activate("activate_key_5678", first["release"]["release_id"], [second_trigger], 2)
        self.assertNotEqual(first["release"]["release_id"], second["release"]["release_id"])
        self.assertEqual(old_job["release_id"], first["release"]["release_id"])
        new_job = self.service.lifecycle.ingest("binding_second", {"event_id": "new", "body": "New"}, self.auth)["job"]
        self.assertEqual(new_job["release_id"], second["release"]["release_id"])
        jobs = self.service.lifecycle.lease("local-workspace")
        self.assertEqual({job["release_id"] for job in jobs}, {first["release"]["release_id"], second["release"]["release_id"]})
        for job in jobs:
            self.assertEqual(self.service.lifecycle.execute_job(job["job_id"], self.runner)["state"], "completed")

    def test_activation_failure_compensates_and_conflict_preserves_active_release(self):
        first = self.activate()
        self.adapter.fail_at = len(self.adapter.prepared) + 1
        with self.assertRaisesRegex(LifecycleFailure, "Provider registration failed"):
            self.activate("failed_activate_1234", first["release"]["release_id"],
                          [self.trigger(binding_id="prepared_one"), self.trigger(binding_id="fails_two")])
        self.assertIn("prepared_one", self.adapter.cleaned)
        with self.assertRaisesRegex(LifecycleFailure, "active release changed"):
            self.activate("conflict_key_1234", None, [], 1)
        self.assertEqual(self.service.lifecycle.overview(self.auth)["items"][0]["release_id"], first["release"]["release_id"])

    def test_poll_checkpoint_schedule_timezone_and_restart_reconciliation(self):
        poll = self.activate(triggers=[self.trigger("fake_poll", "poll", "poll_binding")])
        baseline = self.service.lifecycle.poll("poll_binding", [{"event_id": "historical", "body": "Old"}], "cursor_1", self.auth)
        self.assertTrue(baseline["baseline"])
        self.assertEqual(baseline["receipts"], [])
        dispatched = self.service.lifecycle.poll("poll_binding", [{"event_id": "poll_1", "body": "Changed"}], "cursor_2", self.auth)
        self.assertFalse(dispatched["baseline"])
        with self.service.store.transaction() as db:
            self.assertEqual(db.execute("SELECT cursor FROM lifecycle_checkpoints WHERE binding_id='poll_binding'").fetchone()[0], "cursor_2")
        restarted = WorkflowService(WorkflowStore(self.path), clock=lambda: self.now)
        self.assertEqual(restarted.lifecycle.overview(self.auth)["items"][0]["release_id"], poll["release"]["release_id"])
        with self.assertRaisesRegex(LifecycleFailure, "IANA timezone"):
            self.activate("bad_timezone_1234", poll["release"]["release_id"],
                          [{**self.trigger("fake_schedule", "schedule", "schedule_bad"), "timezone": "Mars/Olympus"}])
        self.service.lifecycle.disable(dict(request_id="disable_poll", idempotency_key="disable_poll_1234",
            payload=dict(workflow_id=self.workflow["workflow_id"], expected_release_id=poll["release"]["release_id"])), self.auth)
        scheduled = self.activate("schedule_key_1234", None, [self.trigger("fake_schedule", "schedule", "schedule_binding")])
        tick = self.service.lifecycle.tick_schedule("schedule_binding", {"body": "Tick"}, "2027-01-15T08:05:00+00:00", self.auth)
        self.assertEqual(tick["job"]["release_id"], scheduled["release"]["release_id"])
        with self.assertRaisesRegex(LifecycleFailure, "timezone-aware"):
            self.service.lifecycle.tick_schedule("schedule_binding", {"body": "Tick"}, "2027-01-15T08:10:00", self.auth)

    def test_signed_real_webhook_rejects_invalid_and_accepts_fresh_signature(self):
        self.activate(triggers=[self.trigger("generic_hmac_webhook", "push", "webhook_binding")])
        event = {"event_id": "webhook_1", "body": "Authenticated delivery"}
        timestamp = str(self.now)
        canonical = json.dumps(event, sort_keys=True, separators=(",", ":"))
        signature = hmac.new(b"test-only-signing-key", (timestamp + "." + canonical).encode(), hashlib.sha256).hexdigest()
        with self.assertRaisesRegex(LifecycleFailure, "could not be verified"):
            self.service.lifecycle.ingest("webhook_binding", event, signature="bad", timestamp=timestamp)
        self.assertTrue(self.service.lifecycle.ingest("webhook_binding", event, signature=signature, timestamp=timestamp)["accepted"])
        self.now += 301
        with self.assertRaisesRegex(LifecycleFailure, "freshness window"):
            self.service.lifecycle.ingest("webhook_binding", {**event, "event_id": "late"}, signature=signature, timestamp=timestamp)

    def test_disable_delete_tombstone_and_cleanup_failure_are_safe(self):
        active = self.activate()
        queued = self.service.lifecycle.ingest("binding_main", {"event_id": "queued", "body": "Queued"}, self.auth)["job"]
        disabled = self.service.lifecycle.disable(dict(request_id="req_disable", idempotency_key="disable_key_1234",
            payload=dict(workflow_id=self.workflow["workflow_id"], expected_release_id=active["release"]["release_id"])), self.auth)
        self.assertEqual(disabled["operation"]["state"], "succeeded")
        with self.service.store.transaction() as db:
            self.assertEqual(db.execute("SELECT state FROM lifecycle_jobs WHERE job_id=?", (queued["job_id"],)).fetchone()[0], "cancelled")
        active = self.activate("reactivate_key_1234", None, [self.trigger(binding_id="binding_reactivated")], 1)
        pending_run = self.runtime.create_run(dict(request_id="req_pending_delete", operation="execute_workflow",
            idempotency_key="pending_delete_1234", payload=dict(workflow_id=self.workflow["workflow_id"], workflow_version=1,
                                                                  inputs={"request_text": "Pending"})), self.auth)
        self.adapter.cleanup_result = False
        request = dict(request_id="req_delete", idempotency_key="delete_key_1234",
                       payload=dict(workflow_id=self.workflow["workflow_id"], expected_release_id=active["release"]["release_id"], confirmed=True))
        deleted = self.service.lifecycle.delete(request, self.auth)
        self.assertEqual(deleted["operation"]["state"], "cleanup_pending")
        self.assertEqual(self.service.lifecycle.delete(request, self.auth), deleted)
        self.assertEqual(self.runtime.get_run(pending_run["run_id"], self.auth)["status"], "cancelled")
        self.assertEqual(self.service.lifecycle.overview(self.auth)["items"], [])
        self.adapter.cleanup_result = True
        self.assertEqual(self.service.lifecycle.reconcile_cleanup("local-workspace"), ["binding_reactivated"])
        with self.assertRaisesRegex(LifecycleFailure, "deleted workflow"):
            self.activate("after_delete_1234", None, [], 1)

    def test_invalid_duplicate_self_event_leases_and_dead_letter_replay(self):
        self.activate()
        other = deepcopy(self.auth)
        other["subject"] = {"subject_id": "other", "workspace_id": "other-workspace"}
        with self.assertRaisesRegex(LifecycleFailure, "another workspace"):
            self.service.lifecycle.ingest("binding_main", {"event_id": "cross", "body": "Cross"}, other)
        self.assertEqual(self.service.lifecycle.overview(other)["items"], [])
        with self.assertRaisesRegex(LifecycleFailure, "does not match"):
            self.service.lifecycle.ingest("binding_main", {"event_id": "invalid"}, self.auth)
        with self.assertRaisesRegex(LifecycleFailure, "Self-originated"):
            self.service.lifecycle.ingest("binding_main", {"event_id": "self", "body": "x", "actor_id": "automation:" + self.workflow["workflow_id"]}, self.auth)
        job = self.service.lifecycle.ingest("binding_main", {"event_id": "retry", "body": "Retry"}, self.auth)["job"]
        leased = self.service.lifecycle.lease("local-workspace", seconds=1)[0]
        self.now += 2
        self.assertEqual(self.service.lifecycle.lease("local-workspace")[0]["job_id"], leased["job_id"])
        class BrokenRunner:
            class BrokenRuntime:
                def create_automation_run(self, *_args):
                    raise RuntimeError("provider detail must be redacted")
            runtime = BrokenRuntime()
        failed = self.service.lifecycle.execute_job(job["job_id"], BrokenRunner(), max_attempts=2)
        self.assertEqual(failed["state"], "dead_letter")
        replayed = self.service.lifecycle.replay(job["job_id"], self.auth)
        self.assertEqual(replayed["state"], "queued")
        self.assertNotIn("provider detail", json.dumps(replayed))

    def test_v2_http_routes_and_authenticated_sequence_resume(self):
        from fastapi.testclient import TestClient
        from workflow_api.main import COOKIE, create_app
        with TestClient(create_app(self.service, dev_auth=True, roles=["admin"], runtime_enabled=True)) as client:
            session = client.get("/session")
            client.cookies.set(COOKIE, session.cookies[COOKIE], path="/")
            body = dict(request_id="req_http_activate", operation="activate_release", idempotency_key="http_activate_1234",
                        payload=dict(workflow_id=self.workflow["workflow_id"], workflow_version=1,
                                     expected_release_id=None, triggers=[self.trigger("generic_hmac_webhook", "push", "http_webhook")]))
            activated = client.post(f"/workflows/{self.workflow['workflow_id']}/releases", json=body)
            self.assertEqual(activated.status_code, 200, activated.json())
            release_id = activated.json()["data"]["release"]["release_id"]
            event = {"event_id": "http_event_1", "body": "Signed HTTP event"}
            timestamp = str(self.now)
            canonical = json.dumps(event, sort_keys=True, separators=(",", ":"))
            signature = hmac.new(b"test-only-signing-key", (timestamp + "." + canonical).encode(), hashlib.sha256).hexdigest()
            delivery = client.post("/trigger-bindings/http_webhook/events", headers={"X-Builder-Timestamp": timestamp,
                "X-Builder-Signature": signature}, json={"request_id": "req_http_event", "operation": "ingest_trigger_event",
                                                               "payload": {"event": event}})
            self.assertEqual(delivery.status_code, 200, delivery.json())
            self.assertEqual(delivery.json()["data"]["job"]["release_id"], release_id)
            overview = client.get("/workflow-overview").json()["data"]
            self.assertEqual(overview["items"][0]["release_id"], release_id)
            stream = client.get("/workflow-overview/events?after_sequence=0", headers={"Accept": "text/event-stream"})
            self.assertEqual(stream.status_code, 200)
            self.assertIn("id: 1", stream.text)
            resumed = client.get(f"/workflow-overview/events?after_sequence={overview['next_sequence']}").json()["data"]
            self.assertEqual(resumed["items"], [])


if __name__ == "__main__":
    unittest.main()
