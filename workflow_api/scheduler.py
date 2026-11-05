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
        if not getattr(service,'worker_authenticate',None):service.worker_authenticate=authenticate
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
        automation=getattr(self.service,'automation',None)
        if automation:automation.tick(self.authenticate)
        # Poll bindings are workspace scoped and the worker uses fresh auth.
        with lifecycle.store.transaction(write=False) as db:
            workspaces = {row[0] for row in db.execute("SELECT DISTINCT workspace FROM lifecycle_triggers UNION SELECT DISTINCT workspace FROM lifecycle_preparations UNION SELECT DISTINCT workspace FROM lifecycle_jobs").fetchall()}
        for workspace in workspaces:
            if self.stop_event.is_set():break
            lifecycle.reconcile_cleanup(workspace)
            auth = self.authenticate(workspace, "local-builder")
            bindings=lifecycle.poll_bindings(workspace) if auth else []
            for binding in bindings:
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


class CronSchedule:
    """Five-field cron, evaluated on UTC minutes through an IANA timezone.

    DST gaps have no occurrence; repeated wall-clock minutes have distinct UTC
    occurrences. Day-of-month and weekday use standard cron OR semantics.
    """
    def __init__(self,expression,zone):
        from zoneinfo import ZoneInfo
        from .lifecycle import LifecycleFailure
        try:
            self.zone=ZoneInfo(zone)
            fields=expression.split()
            if len(fields)!=5:raise ValueError()
            self.values=[];self.wild=[]
            for text,(lo,hi) in zip(fields,[(0,59),(0,23),(1,31),(1,12),(0,7)]):
                self.wild.append(text=='*');values=set()
                for part in text.split(','):
                    raw,*step=part.split('/');stride=int(step[0]) if step else 1
                    if len(step)>1 or stride<1:raise ValueError()
                    if raw=='*':start,end=lo,hi
                    elif '-' in raw:start,end=map(int,raw.split('-'))
                    else:start=int(raw);end=hi if step else start
                    if not lo<=start<=end<=hi:raise ValueError()
                    values.update(range(start,end+1,stride))
                self.values.append(values)
            if 7 in self.values[4]:self.values[4].add(0);self.values[4].remove(7)
        except Exception:
            raise LifecycleFailure('INVALID_SCHEDULE','Supply a valid five-field cron expression and IANA timezone.',422) from None

    def next(self,after):
        from datetime import datetime,timezone
        from .lifecycle import LifecycleFailure
        stamp=(int(after)//60+1)*60
        for _ in range(366*24*60*5):
            d=datetime.fromtimestamp(stamp,timezone.utc).astimezone(self.zone)
            minute,hour,dom,month,dow=self.values
            day=d.day in dom;weekday=(d.weekday()+1)%7 in dow
            matches=(day and weekday) if self.wild[2] or self.wild[4] else (day or weekday)
            if d.minute in minute and d.hour in hour and d.month in month and matches:return stamp
            stamp+=60
        raise LifecycleFailure('INVALID_SCHEDULE','No occurrence within the bounded five-year horizon.',422)
