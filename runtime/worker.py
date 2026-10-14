"""Worker polling uses fresh server authentication, never stored roles/scopes."""
import json
from threading import Event, Thread


class RuntimeWorker:
    def __init__(self, runner, authenticate, interval=1):
        self.runner, self.authenticate, self.interval = runner, authenticate, interval
        self.stop_event = Event()
        self.thread = None

    def drain(self):
        runtime = self.runner.runtime
        with runtime.store.transaction(write=False) as db:
            rows = db.execute('SELECT document FROM runtime_runs ORDER BY rowid').fetchall()
        advanced = []
        for row in rows:
            run = json.loads(row[0])
            if run['status'] not in {'queued', 'running', 'paused_for_approval'}:
                continue
            # Authentication adapters may reject expired/revoked identities. The
            # worker does not reconstruct executable authority from run records.
            try:
                auth = self.authenticate(run['workspace_id'], run['subject_id'])
                if auth is None or auth['subject'] != dict(workspace_id=run['workspace_id'], subject_id=run['subject_id']):
                    continue
                advanced.append(self.runner.advance(run['run_id'], auth))
            except Exception:
                continue
        runtime.export_traces()
        return advanced

    def start(self):
        if self.thread and self.thread.is_alive():
            return
        self.stop_event.clear()
        def loop():
            while not self.stop_event.is_set():
                self.drain()
                self.stop_event.wait(self.interval)
        self.thread = Thread(target=loop, name='builder-runtime-worker', daemon=True)
        self.thread.start()

    def stop(self):
        self.stop_event.set()
        if self.thread:
            self.thread.join(timeout=5)
