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
        self.health={"state":"starting","last_success":None,"last_error":None}

    def tick(self):
        lifecycle = self.service.lifecycle
        runner = self.service.runtime_runner
        if runner is None:
            return {"polled": 0, "queued": 0, "dispatched": 0}
        polled = queued = dispatched = 0
        # Poll bindings are workspace scoped and the worker uses fresh auth.
        with lifecycle.store.transaction(write=False) as db:
            workspaces = {row[0] for row in db.execute("SELECT DISTINCT workspace FROM lifecycle_triggers UNION SELECT DISTINCT workspace FROM lifecycle_preparations").fetchall()}
        for workspace in workspaces:
            if self.stop_event.is_set():break
            lifecycle.reconcile_cleanup(workspace)
            auth = self.authenticate(workspace, "local-builder")
            if not auth:
                continue
            for binding in lifecycle.poll_bindings(workspace):
                if self.stop_event.is_set():break
                binding_id = binding["binding_id"]
                now = time.time()
                if now - self.last_polled.get(binding_id, 0) < binding.get("poll_interval_seconds", self.interval):
                    continue
                with lifecycle.store.transaction(write=False) as db:
                    row = db.execute("SELECT cursor FROM lifecycle_checkpoints WHERE workspace=? AND binding_id=?", (workspace, binding_id)).fetchone()
                cursor = row[0] if row else None
                try:
                    source = self.poll_source or getattr(self.service, 'trigger_poller', None)
                    if source is None:
                        continue
                    changes, next_cursor = source(binding, cursor)
                    result = lifecycle.poll(binding_id, changes, next_cursor, auth)
                    with lifecycle.store.transaction() as db:
                        row = db.execute("SELECT document FROM lifecycle_triggers WHERE binding_id=?", (binding_id,)).fetchone()
                        if row:
                            import json
                            trigger = json.loads(row[0])
                            recovered = trigger.get('health') != 'ready'
                            trigger['health'] = 'ready'
                            trigger.pop('last_error_code', None)
                            db.execute("UPDATE lifecycle_triggers SET document=? WHERE binding_id=?", (json.dumps(trigger), binding_id))
                            if recovered:
                                workflow = db.execute('SELECT workflow_id FROM lifecycle_triggers WHERE binding_id=?', (binding_id,)).fetchone()[0]
                                lifecycle.emit(db, workspace, workflow, 'trigger.ready')
                    self.last_polled[binding_id] = now
                    polled += 1
                    queued += sum(1 for receipt in result.get('receipts', []) if receipt.get('accepted') is True and not receipt.get('duplicate'))
                except Exception as exc:
                    # Retry on the next interval and preserve only a stable,
                    # redacted error code for operational diagnosis.
                    code = getattr(exc, 'code', None) or 'POLL_FAILED'
                    with lifecycle.store.transaction() as db:
                        row = db.execute("SELECT document FROM lifecycle_triggers WHERE binding_id=?", (binding_id,)).fetchone()
                        if row:
                            import json
                            trigger = json.loads(row[0])
                            trigger['health'] = 'error'
                            trigger['last_error_code'] = str(code)
                            db.execute("UPDATE lifecycle_triggers SET document=? WHERE binding_id=?", (json.dumps(trigger), binding_id))
                            workflow = db.execute('SELECT workflow_id FROM lifecycle_triggers WHERE binding_id=?', (binding_id,)).fetchone()[0]
                            lifecycle.emit(db, workspace, workflow, 'trigger.error')
                    self.last_polled[binding_id] = now
                    continue
            for _ in range(10):
                if self.stop_event.is_set():break
                jobs=lifecycle.lease(workspace,limit=1,seconds=120)
                if not jobs:break
                lifecycle.execute_job(jobs[0]["job_id"], runner)
                dispatched += 1
        self.health={"state":"ready","last_success":time.time(),"last_error":None}
        return {"polled": polled, "queued": queued, "dispatched": dispatched}

    def start(self):
        if self.thread and self.thread.is_alive():
            return
        self.stop_event.clear()
        self.thread = Thread(target=self._loop, name="builder-trigger-scheduler", daemon=True)
        self.thread.start()

    def _loop(self):
        while not self.stop_event.is_set():
            try:self.tick()
            except Exception:
                import logging
                self.health['state'],self.health['last_error']='error','TRIGGER_WORKER_FAILED'
                logging.getLogger(__name__).warning('Trigger worker failed; durable jobs retained.')
            self.stop_event.wait(self.interval)

    def stop(self):
        self.stop_event.set()
        if self.thread:
            self.thread.join(timeout=5)
