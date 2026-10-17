"""Worker polling uses fresh server authentication, never stored roles/scopes."""
import json
from threading import Event, Thread


class RuntimeWorker:
    def __init__(self, runner, authenticate, interval=1, batch_size=100):
        self.runner, self.authenticate, self.interval = runner, authenticate, interval
        self.batch_size = min(max(int(batch_size),1),1000)
        self.health = {"state":"starting","last_success":None,"last_error":None}
        self.cursor = 0
        self.stop_event = Event()
        self.thread = None

    def drain(self):
        runtime = self.runner.runtime
        with runtime.store.transaction(write=False) as db:
            rows = db.execute("SELECT rowid,document FROM runtime_runs WHERE rowid>? AND json_extract(document,'$.status') IN ('queued','running','paused_for_approval') ORDER BY rowid LIMIT ?",(self.cursor,self.batch_size)).fetchall()
            if not rows:
                self.cursor=0
                rows = db.execute("SELECT rowid,document FROM runtime_runs WHERE rowid>? AND json_extract(document,'$.status') IN ('queued','running','paused_for_approval') ORDER BY rowid LIMIT ?",(self.cursor,self.batch_size)).fetchall()
        advanced = []
        for row in rows:
            if self.stop_event.is_set():break
            self.cursor=row[0]
            run = json.loads(row[1])
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
        import time
        self.health={"state":"ready","last_success":time.time(),"last_error":None}
        return advanced

    def start(self):
        if self.thread and self.thread.is_alive():
            return
        self.stop_event.clear()
        def loop():
            while not self.stop_event.is_set():
                try:self.drain()
                except Exception:
                    import logging
                    self.health['state'],self.health['last_error']='error','RUNTIME_WORKER_FAILED'
                    logging.getLogger(__name__).warning('Runtime worker failed; durable runs retained.')
                self.stop_event.wait(self.interval)
        self.thread = Thread(target=loop, name='builder-runtime-worker', daemon=True)
        self.thread.start()

    def stop(self):
        self.stop_event.set()
        if self.thread:
            self.thread.join(timeout=5)
