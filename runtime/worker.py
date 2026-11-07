"""Worker polling uses fresh server authentication, never stored roles/scopes."""
import json
import time
from concurrent.futures import ThreadPoolExecutor
from itertools import zip_longest
from threading import Event, Thread


class RuntimeWorker:
    def __init__(self, runner, authenticate, interval=1, batch_size=100,concurrency=1,fair=False):
        self.runner, self.authenticate, self.interval = runner, authenticate, interval
        self.batch_size = min(max(int(batch_size),1),1000)
        self.health = {"state":"starting","last_success":None,"last_error":None}
        self.cursor = 0
        if type(concurrency) is not int or not 1<=concurrency<=32:raise ValueError('Worker concurrency must be 1–32.')
        self.concurrency,self.fair=concurrency,fair
        self.workspace_cursor=0
        self.stop_event = Event()
        self.thread = None

    def drain(self):
        runtime = self.runner.runtime
        with runtime.store.transaction(write=False) as db:
            if self.fair:
                workspaces=[r[0] for r in db.execute("SELECT DISTINCT workspace FROM runtime_runs WHERE json_extract(document,'$.status') IN ('queued','running','paused_for_approval') ORDER BY workspace LIMIT 1000").fetchall()]
                if workspaces:
                    offset=self.workspace_cursor%len(workspaces)
                    workspaces=workspaces[offset:]+workspaces[:offset]
                batches=[]
                per_workspace=max(1,self.batch_size//max(1,len(workspaces)))
                for workspace in workspaces[:self.batch_size]:
                    batches.append(db.execute("SELECT rowid,document FROM runtime_runs WHERE workspace=? AND json_extract(document,'$.status') IN ('queued','running','paused_for_approval') AND COALESCE(CAST(json_extract(document,'$.lease_until') AS DOUBLE PRECISION),0)<=? AND COALESCE(CAST(json_extract(document,'$.available_at') AS DOUBLE PRECISION),0)<=? AND (json_extract(document,'$.status')!='paused_for_approval' OR COALESCE(CAST(json_extract(document,'$.approval_context.expires_at') AS DOUBLE PRECISION),0)<=?) ORDER BY rowid LIMIT ?",(workspace,runtime.clock(),runtime.clock(),runtime.clock(),per_workspace)).fetchall())
                rows=[row for group in zip_longest(*batches) for row in group if row is not None]
                self.workspace_cursor+=min(len(workspaces),self.batch_size)
            else:
                rows = db.execute("SELECT rowid,document FROM runtime_runs WHERE rowid>? AND json_extract(document,'$.status') IN ('queued','running','paused_for_approval') ORDER BY rowid LIMIT ?",(self.cursor,self.batch_size)).fetchall()
            if not rows and not self.fair:
                self.cursor=0
                rows = db.execute("SELECT rowid,document FROM runtime_runs WHERE rowid>? AND json_extract(document,'$.status') IN ('queued','running','paused_for_approval') ORDER BY rowid LIMIT ?",(self.cursor,self.batch_size)).fetchall()
        def execute(row):
            if self.stop_event.is_set():return None
            self.cursor=row[0]
            run = json.loads(row[1])
            if run['status'] not in {'queued', 'running', 'paused_for_approval'}:
                return None
            if run.get('available_at',0)>runtime.clock():return None
            if run['status']=='running' and run.get('lease_until',0)>runtime.clock():return None
            if run['status']=='paused_for_approval' and run.get('approval_context',{}).get('expires_at',0)>runtime.clock():return None
            # Authentication adapters may reject expired/revoked identities. The
            # worker does not reconstruct executable authority from run records.
            try:
                auth = self.authenticate(run['workspace_id'], run['subject_id'])
                if auth is None or auth['subject'] != dict(workspace_id=run['workspace_id'], subject_id=run['subject_id']):
                    return None
                return self.runner.advance(run['run_id'], auth)
            except Exception:
                return None
        if self.concurrency==1:
            advanced=[result for row in rows if (result:=execute(row)) is not None]
        else:
            with ThreadPoolExecutor(max_workers=self.concurrency,thread_name_prefix='builder-execution') as pool:
                advanced=[r for r in pool.map(execute,rows) if r is not None]
        runtime.export_traces()
        self.health={"state":"ready","last_success":time.time(),"last_error":None,
                     'selected':len(rows),'advanced':len(advanced),'capacity':self.concurrency}
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
