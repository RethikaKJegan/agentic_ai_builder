"""Durable polling and dispatch worker for published workflow triggers."""
from threading import Event, Thread
import time


class TriggerScheduler:
    """Poll provider adapters, enqueue rows, and drain lifecycle jobs.

    The scheduler receives all provider access as a server-owned callback. It
    never reads credentials from trigger records or client requests.
    """
    def __init__(self, service, authenticate, poll_source=None, interval=5):
        self.service = service
        self.authenticate = authenticate
        self.poll_source = poll_source
        self.interval = max(1, int(interval))
        self.stop_event = Event()
        self.thread = None
        self.last_polled = {}

    def tick(self):
        lifecycle = self.service.lifecycle
        runner = self.service.runtime_runner
        if runner is None:
            return {"polled": 0, "queued": 0, "dispatched": 0}
        polled = queued = dispatched = 0
        # Poll bindings are workspace scoped and the worker uses fresh auth.
        with lifecycle.store.transaction() as db:
            workspaces = {row[0] for row in db.execute("SELECT DISTINCT workspace FROM lifecycle_triggers WHERE state='ready'").fetchall()}
        for workspace in workspaces:
            auth = self.authenticate(workspace, "local-builder")
            if not auth:
                continue
            for binding in lifecycle.poll_bindings(workspace):
                binding_id = binding["binding_id"]
                now = time.time()
                if now - self.last_polled.get(binding_id, 0) < binding.get("poll_interval_seconds", self.interval):
                    continue
                with lifecycle.store.transaction() as db:
                    row = db.execute("SELECT cursor FROM lifecycle_checkpoints WHERE workspace=? AND binding_id=?", (workspace, binding_id)).fetchone()
                cursor = row[0] if row else None
                try:
                    source = self.poll_source or getattr(self.service, 'trigger_poller', None)
                    if source is None:
                        continue
                    changes, next_cursor = source(binding, cursor)
                    result = lifecycle.poll(binding_id, changes, next_cursor, auth)
                    self.last_polled[binding_id] = now
                    polled += 1
                    queued += len(result.get("receipts", []))
                except Exception:
                    # Provider failures are retried next tick; no partial authority is persisted.
                    continue
            for job in lifecycle.lease(workspace):
                lifecycle.execute_job(job["job_id"], runner)
                dispatched += 1
        return {"polled": polled, "queued": queued, "dispatched": dispatched}

    def start(self):
        if self.thread and self.thread.is_alive():
            return
        self.stop_event.clear()
        self.thread = Thread(target=self._loop, name="builder-trigger-scheduler", daemon=True)
        self.thread.start()

    def _loop(self):
        while not self.stop_event.is_set():
            self.tick()
            self.stop_event.wait(self.interval)

    def stop(self):
        self.stop_event.set()
        if self.thread:
            self.thread.join(timeout=5)
