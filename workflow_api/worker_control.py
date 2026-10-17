"""Durable worker-group ownership and observable, graceful local supervision."""
import json
import logging
from threading import Event,Thread
import time
from uuid import uuid4


class WorkerSupervisor:
    def __init__(self,store,workers,role='combined',clock=time.time,ttl=30,shutdown_timeout=180):
        if role not in {'api','worker','combined'}:raise ValueError('Use api, worker or combined process role.')
        self.store,self.workers,self.role,self.clock,self.ttl=store,list(workers),role,clock,ttl
        self.shutdown_timeout=shutdown_timeout
        self.owner='worker_'+uuid4().hex;self.key='builder-live-workers'
        self.stop_event=Event();self.thread=None;self.owned=False
        with store.transaction() as db:
            db.execute('CREATE TABLE IF NOT EXISTS builder_worker_leases (name TEXT PRIMARY KEY, owner TEXT NOT NULL, expires REAL NOT NULL)')
            db.execute('CREATE TABLE IF NOT EXISTS builder_worker_health (worker_id TEXT PRIMARY KEY, role TEXT NOT NULL, state TEXT NOT NULL, heartbeat REAL NOT NULL)')
            db.execute('CREATE TABLE IF NOT EXISTS builder_worker_component_health (worker_id TEXT, name TEXT, document TEXT NOT NULL, PRIMARY KEY(worker_id,name))')

    def acquire(self):
        now=self.clock()
        with self.store.transaction() as db:
            row=db.execute('SELECT owner,expires FROM builder_worker_leases WHERE name=?',(self.key,)).fetchone()
            allowed=row is None or row[0]==self.owner or row[1]<=now
            if allowed:
                db.execute('INSERT INTO builder_worker_leases VALUES (?,?,?) ON CONFLICT(name) DO UPDATE SET owner=excluded.owner,expires=excluded.expires',(self.key,self.owner,now+self.ttl))
            db.execute('INSERT INTO builder_worker_health VALUES (?,?,?,?) ON CONFLICT(worker_id) DO UPDATE SET state=excluded.state,heartbeat=excluded.heartbeat',(self.owner,self.role,'active' if allowed else 'standby',now))
            if allowed:
                for worker in self.workers:
                    state=getattr(worker,'health',None)
                    if isinstance(state,dict):
                        document={key:state[key] for key in ('state','last_success','last_error') if key in state}
                        document['heartbeat']=now
                        db.execute('INSERT INTO builder_worker_component_health VALUES (?,?,?) ON CONFLICT(worker_id,name) DO UPDATE SET document=excluded.document',(self.owner,type(worker).__name__,json.dumps(document)))
        return allowed

    def tick(self):
        if self.role=='api':return False
        acquired=self.acquire()
        if acquired and not self.owned:
            started=[]
            try:
                for worker in self.workers:worker.start();started.append(worker)
                self.owned=True
            except Exception:
                for worker in reversed(started):worker.stop()
                self.release('failed')
                raise
        elif not acquired and self.owned:
            self._stop_workers()
            self.owned=False
        return acquired

    def release(self,state='stopped'):
        with self.store.transaction() as db:
            db.execute('DELETE FROM builder_worker_leases WHERE name=? AND owner=?',(self.key,self.owner))
            db.execute('UPDATE builder_worker_health SET state=?,heartbeat=? WHERE worker_id=?',(state,self.clock(),self.owner))
        self.owned=False

    def start(self):
        if self.role=='api' or (self.thread and self.thread.is_alive()):return
        self.stop_event.clear();self.tick()
        def loop():
            while not self.stop_event.wait(max(1,self.ttl/3)):
                try:self.tick()
                except Exception:
                    logging.getLogger(__name__).warning('Worker coordination unavailable; new work is stopping.')
                    if self.owned:
                        self._stop_workers()
                        self.owned=False
        self.thread=Thread(target=loop,name='builder-worker-supervisor',daemon=True);self.thread.start()

    def _stop_workers(self):
        deadline=time.monotonic()+self.shutdown_timeout
        for worker in self.workers:
            event=getattr(worker,'stop_event',None)
            if event is not None:event.set()
        for worker in reversed(self.workers):worker.stop()
        for worker in self.workers:
            thread=getattr(worker,'thread',None)
            if thread and thread.is_alive():thread.join(timeout=max(0,deadline-time.monotonic()))

    def stop(self):
        self.stop_event.set()
        if self.thread:self.thread.join(timeout=5)
        if self.owned:
            # Retain group ownership during a graceful drain so a standby cannot
            # enter the coordinator while this process finishes existing work.
            self.renew_owned()
            with LeaseHeartbeat(self.renew_owned,interval=max(.1,self.ttl/3)):
                self._stop_workers()
        self.release()

    def renew_owned(self):
        with self.store.transaction() as db:
            cursor=db.execute('UPDATE builder_worker_leases SET expires=? WHERE name=? AND owner=?',(self.clock()+self.ttl,self.key,self.owner))
            if cursor.rowcount:
                db.execute("UPDATE builder_worker_health SET state='stopping',heartbeat=? WHERE worker_id=?",(self.clock(),self.owner))
            return cursor.rowcount==1


def health(store,workspace,clock=time.time):
    with store.transaction(write=False) as db:
        def available(table):
            return db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",(table,)).fetchone() is not None
        workers=[]
        if available('builder_worker_health'):
            workers=[{'role':role,'state':state if heartbeat>=clock()-60 else 'stale','last_heartbeat':heartbeat} for role,state,heartbeat in db.execute('SELECT role,state,heartbeat FROM builder_worker_health').fetchall()]
        components=[]
        if available('builder_worker_component_health'):
            for name,document in db.execute('SELECT name,document FROM builder_worker_component_health').fetchall():
                item=json.loads(document);item['name']=name
                if item.get('heartbeat',0)<clock()-60:item['state']='stale'
                components.append(item)
        dispatch=dict(db.execute('SELECT state,COUNT(*) FROM lifecycle_jobs WHERE workspace=? GROUP BY state',(workspace,)).fetchall()) if available('lifecycle_jobs') else {}
        planning=dict(db.execute('SELECT state,COUNT(*) FROM builder_planning_jobs WHERE workspace=? GROUP BY state',(workspace,)).fetchall()) if available('builder_planning_jobs') else {}
        runtime_available=available('runtime_runs')
        active=db.execute("SELECT COUNT(*) FROM runtime_runs WHERE workspace=? AND json_extract(document,'$.status') IN ('queued','running','paused_for_approval')",(workspace,)).fetchone()[0] if runtime_available else 0
    return {'workers':workers,'components':components,'dispatch':dispatch,'planning':planning,'active_runs':active,'runtime_available':runtime_available,'database':dict(store.metrics)}


class LeaseHeartbeat:
    """Renew an owned durable claim while an already-authorized invocation is in flight."""
    def __init__(self,renew,interval=10):
        self.renew,self.interval=renew,interval;self.stop_event=Event();self.thread=None
    def __enter__(self):
        def loop():
            while not self.stop_event.wait(self.interval):
                try:
                    if self.renew() is False:return
                except Exception:logging.getLogger(__name__).warning('Lease heartbeat unavailable; durable fencing remains in force.')
        self.thread=Thread(target=loop,name='builder-lease-heartbeat',daemon=True);self.thread.start();return self
    def __exit__(self,*_):
        self.stop_event.set()
        if self.thread:self.thread.join(timeout=5)
