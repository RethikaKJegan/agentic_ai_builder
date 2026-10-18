"""Durable owned query jobs, fenced attempts and encrypted temporary results."""
from __future__ import annotations

import json
import logging
import re
import time
from pathlib import Path
from jsonschema import Draft202012Validator
from threading import Event, Thread, Lock
from uuid import uuid4

from .data_query_control import QueryExecutionControl
from .data_relationships import fingerprint
from .google_connections import GoogleConnections, now
from .service import ApiFailure

ACTIVE = ('validating', 'running', 'finalizing', 'cancel_requested')
TERMINAL = ('succeeded', 'failed', 'cancelled')
COLUMNS = ('job_id', 'workspace', 'owner', 'retry_key', 'plan_id', 'state', 'token', 'lease_until',
           'attempts', 'created', 'updated', 'deadline', 'plan_expires', 'document', 'progress',
           'error_code', 'error_message', 'result_secret', 'result_expires')
SELECT = ','.join(COLUMNS)
ACTIVE_SQL = "('validating','running','finalizing','cancel_requested')"
UNFINISHED_SQL = "('queued','validating','running','finalizing','cancel_requested')"


def failure(code, message, status=409):
    raise ApiFailure(code, message, status)


def identity(auth):
    GoogleConnections.identity(auth)
    return GoogleConnections.identity(auth, True)


def progress_value(stage='Waiting for execution capacity'):
    return dict(stage=stage, completed_fragments=0, transferred_rows=0, transferred_bytes=0)


class DataQueryJobs:
    result_ttl = 900
    metadata_ttl = 86400
    lease_seconds = 15
    heartbeat_interval = 1

    def __init__(self, queries, authenticate, *, clock=time.time):
        self.queries, self.manager, self.store = queries, queries.manager, queries.store
        self.authenticate, self.clock = authenticate, clock
        result_contract=json.loads((Path(__file__).resolve().parents[1]/'shared/contracts/data-sources/queries-v1.schema.json').read_text())
        self.result_validator=Draft202012Validator({**result_contract,'oneOf':[{'$ref':'#/$defs/result'}]})
        self.timeout = int(self.manager.env.get('BUILDER_DATA_QUERY_JOB_TIMEOUT_SECONDS', '180'))
        if not 45 <= self.timeout <= 300:
            raise ValueError('Data query job timeout must be between 45 and 300 seconds.')
        self.stop_event, self.wake, self.guard = Event(), Event(), Lock()
        self.threads, self.thread = [], None
        self.health = dict(state='starting')
        with self.store.transaction() as db:
            db.execute('CREATE TABLE IF NOT EXISTS data_query_jobs (job_id TEXT PRIMARY KEY, workspace TEXT NOT NULL, owner TEXT NOT NULL, retry_key TEXT NOT NULL, plan_id TEXT NOT NULL, state TEXT NOT NULL, token TEXT, lease_until REAL NOT NULL, attempts INTEGER NOT NULL, created REAL NOT NULL, updated REAL NOT NULL, deadline REAL NOT NULL, plan_expires REAL NOT NULL, document TEXT NOT NULL, progress TEXT NOT NULL, error_code TEXT, error_message TEXT, result_secret TEXT, result_expires REAL, UNIQUE(workspace,owner,retry_key))')
            db.execute('CREATE INDEX IF NOT EXISTS data_query_job_queue ON data_query_jobs(state,created)')
            db.execute('CREATE INDEX IF NOT EXISTS data_query_job_owner ON data_query_jobs(workspace,owner,created)')

    @staticmethod
    def decode(row):
        return dict(zip(COLUMNS, row)) if row else None

    def owned(self, db, auth, job_id):
        workspace, owner = identity(auth)
        if not isinstance(job_id, str) or not re.fullmatch(r'dqj_[a-f0-9]{32}', job_id):
            failure('DATA_QUERY_JOB_NOT_FOUND', 'Query job not found.', 404)
        row = self.decode(db.execute('SELECT '+SELECT+' FROM data_query_jobs WHERE job_id=? AND workspace=? AND owner=?',
                                    (job_id, workspace, owner)).fetchone())
        if row is None:
            failure('DATA_QUERY_JOB_NOT_FOUND', 'Query job not found.', 404)
        return row

    def public(self, row):
        saved = json.loads(row['document'])
        return dict(job_id=row['job_id'], plan_id=row['plan_id'], state=row['state'], attempt=row['attempts'],
                    created_at=row['created'], updated_at=row['updated'], deadline_at=min(row['deadline'],row['plan_expires']),
                    progress=json.loads(row['progress']), result_expires_at=row['result_expires'],
                    result_available=bool(row['state']=='succeeded' and row['result_secret'] and row['result_expires']>self.clock()),
                    error=dict(code=row['error_code'], message=row['error_message']) if row['error_code'] else None,
                    planned_query={k:v for k,v in saved.items() if k!='context_hash'})

    def maintenance(self, db):
        current = self.clock()
        db.execute('UPDATE data_query_jobs SET result_secret=NULL WHERE result_expires<=? AND result_secret IS NOT NULL', (current,))
        db.execute("DELETE FROM data_query_jobs WHERE state IN ('succeeded','failed','cancelled') AND updated<?", (current-self.metadata_ttl,))
        expired = db.execute('SELECT '+SELECT+" FROM data_query_jobs WHERE state IN "+UNFINISHED_SQL+
                             ' AND (deadline<=? OR plan_expires<=? OR (state<>\'queued\' AND lease_until<=?))', (current,current,current)).fetchall()
        for values in expired:
            row = self.decode(values)
            state, code, message = 'failed', 'DATA_QUERY_INTERRUPTED', 'Query execution was interrupted. Create a fresh query job.'
            if row['state']=='cancel_requested':
                state, code, message = 'cancelled', None, None
            elif row['plan_expires']<=current:
                code,message='DATA_QUERY_STALE','Query plan expired. Create a fresh plan.'
            elif row['deadline']<=current:
                code,message='DATA_QUERY_TIMEOUT','Query job deadline exceeded. No partial answer returned.'
            elif row['attempts']<2:
                state,code,message='queued',None,None
            stage = 'Recovering with fresh source snapshots' if state=='queued' else 'Cancelled' if state=='cancelled' else 'Stopped without results'
            db.execute('UPDATE data_query_jobs SET state=?,token=NULL,lease_until=0,updated=?,progress=?,error_code=?,error_message=?,result_secret=NULL WHERE job_id=?',
                       (state,current,json.dumps(progress_value(stage)),code,message,row['job_id']))

    def submit(self, auth, body, retry_key):
        workspace, owner = identity(auth)
        self.manager.configured()
        if not isinstance(body,dict) or set(body)!={'plan_id'} or not isinstance(body['plan_id'],str):
            failure('DATA_QUERY_INVALID','Supply a saved plan ID.',400)
        if not isinstance(retry_key,str) or not re.fullmatch(r'[A-Za-z0-9_-]{8,128}',retry_key):
            failure('DATA_QUERY_INVALID','Supply an Idempotency-Key of 8–128 letters, digits, underscores or hyphens.',400)
        # Return the same owned job even after the original plan/result expires.
        with self.store.transaction() as db:
            self.maintenance(db)
            old=db.execute('SELECT '+SELECT+' FROM data_query_jobs WHERE workspace=? AND owner=? AND retry_key=?',(workspace,owner,retry_key)).fetchone()
            if old:
                old=self.decode(old)
                if old['plan_id']!=body['plan_id']:
                    failure('IDEMPOTENCY_KEY_REUSED','This query key belongs to a different plan.',409)
                return self.public(old)
            stored=db.execute('SELECT document FROM data_query_plans WHERE plan_id=? AND workspace=? AND owner=?',(body['plan_id'],workspace,owner)).fetchone()
        if not stored:
            failure('DATA_QUERY_NOT_FOUND','Query plan not found.',404)
        saved=json.loads(stored[0])
        self.valid_saved(auth,saved)
        current=self.clock()
        job_id='dqj_'+uuid4().hex
        with self.store.transaction() as db:
            self.maintenance(db)
            old=db.execute('SELECT '+SELECT+' FROM data_query_jobs WHERE workspace=? AND owner=? AND retry_key=?',(workspace,owner,retry_key)).fetchone()
            if old:
                old=self.decode(old)
                if old['plan_id']!=body['plan_id']:failure('IDEMPOTENCY_KEY_REUSED','This query key belongs to a different plan.',409)
                return self.public(old)
            pending=db.execute('SELECT workspace,owner FROM data_query_jobs WHERE state IN '+UNFINISHED_SQL).fetchall()
            live=db.execute('SELECT workspace,owner FROM data_query_jobs WHERE result_secret IS NOT NULL').fetchall()
            if (len(pending)>=100 or sum(w==workspace for w,_ in pending)>=20 or
                sum((w,o)==(workspace,owner) for w,o in pending)>=5 or len(live)>=100 or
                sum((w,o)==(workspace,owner) for w,o in live)>=20):
                failure('DATA_QUERY_BUSY','Query queue or temporary result capacity reached. Wait for existing jobs/results to finish or expire.',429)
            values=(job_id,workspace,owner,retry_key,body['plan_id'],'queued',None,0,0,current,current,current+self.timeout,
                    saved['expires_at'],json.dumps(saved),json.dumps(progress_value()),None,None,None,None)
            db.execute('INSERT INTO data_query_jobs ('+SELECT+') VALUES ('+','.join('?' for _ in COLUMNS)+')',values)
        self.wake.set()
        return self.get(auth,job_id)

    def valid_saved(self, auth, saved):
        identity(auth)
        if saved['expires_at']<=self.clock():
            failure('DATA_QUERY_STALE','Query plan expired. Create a fresh plan.')
        context=self.queries.context(auth)
        if fingerprint(context[0])!=saved['context_hash']:
            failure('DATA_QUERY_STALE','Metadata or relationship review changed. Create a fresh plan.')
        if saved['plan']['clarification']:
            failure('DATA_QUERY_INVALID','Resolve the clarification before execution.',400)
        self.queries.validate(saved['plan'],context)

    def get(self, auth, job_id):
        with self.store.transaction() as db:
            self.maintenance(db)
            return self.public(self.owned(db,auth,job_id))

    def list(self, auth):
        workspace,owner=identity(auth)
        with self.store.transaction() as db:
            self.maintenance(db)
            rows=db.execute('SELECT '+SELECT+' FROM data_query_jobs WHERE workspace=? AND owner=? ORDER BY created DESC,job_id DESC LIMIT 20',(workspace,owner)).fetchall()
        return dict(items=[self.public(self.decode(row)) for row in rows])

    def cancel(self, auth, job_id):
        with self.store.transaction() as db:
            self.maintenance(db)
            row=self.owned(db,auth,job_id)
            if row['state'] not in TERMINAL:
                state='cancelled' if row['state']=='queued' else 'cancel_requested'
                db.execute('UPDATE data_query_jobs SET state=?,updated=?,progress=?,result_secret=NULL WHERE job_id=?',
                           (state,self.clock(),json.dumps(progress_value('Cancelled' if state=='cancelled' else 'Stopping query')),job_id))
        return self.get(auth,job_id)

    def result(self, auth, job_id):
        with self.store.transaction() as db:
            self.maintenance(db)
            row=self.owned(db,auth,job_id)
        if row['state']!='succeeded':
            failure('DATA_QUERY_RESULT_UNAVAILABLE','This job has no completed result.',409)
        if not row['result_secret'] or row['result_expires']<=self.clock():
            failure('DATA_QUERY_RESULT_EXPIRED','The temporary result expired. Create a fresh plan and query job.',410)
        self.valid_result_authority(auth,row)
        try:
            result=json.loads(self.manager.cipher.decrypt(row['result_secret'].encode()).decode())
        except Exception:
            failure('DATA_QUERY_RESULT_UNAVAILABLE','The temporary result could not be read. Check the shared encryption key configuration.',503)
        # A slow read must not return rows after their retention window.
        if row['result_expires']<=self.clock():
            self.get(auth,job_id)
            failure('DATA_QUERY_RESULT_EXPIRED','The temporary result expired.',410)
        return result

    def valid_result_authority(self, auth, row):
        identity(auth)
        saved=json.loads(row['document'])
        # Plan TTL limits execution, not retrieval of an already completed result.
        if fingerprint(self.queries.context(auth)[0])!=saved['context_hash']:
            failure('DATA_QUERY_STALE','Source access, metadata or relationship review changed. Create a fresh plan.')

    def authority(self, row):
        auth=self.authenticate(row['workspace'],row['owner'])
        if auth is None or identity(auth)!=(row['workspace'],row['owner']):
            failure('OPERATION_NOT_AUTHORIZED','Query authority is no longer available.',403)
        return auth

    def claim(self):
        with self.store.transaction() as db:
            self.maintenance(db)
            active=db.execute('SELECT workspace,owner FROM data_query_jobs WHERE state IN '+ACTIVE_SQL).fetchall()
            if len(active)>=4:return None
            waiting=db.execute('SELECT '+SELECT+" FROM data_query_jobs WHERE state='queued' ORDER BY created,job_id LIMIT 100").fetchall()
            for values in waiting:
                row=self.decode(values)
                if (row['workspace'],row['owner']) in active:continue
                stamp=self.clock();token=uuid4().hex
                db.execute("UPDATE data_query_jobs SET state='validating',token=?,lease_until=?,attempts=attempts+1,updated=?,progress=? WHERE job_id=? AND state='queued'",
                           (token,min(stamp+self.lease_seconds,row['deadline'],row['plan_expires']),stamp,json.dumps(progress_value('Rechecking plan and source access')),row['job_id']))
                row.update(state='validating',token=token,attempts=row['attempts']+1)
                return row
        return None

    def check_claim(self, row, current):
        if current is None or current['token']!=row['token'] or current['state'] not in ACTIVE or current['lease_until']<=self.clock():
            failure('DATA_QUERY_LEASE_LOST','This query attempt no longer owns execution.',409)
        if current['state']=='cancel_requested':
            failure('DATA_QUERY_CANCELLED','Query cancellation requested.',409)
        if min(current['deadline'],current['plan_expires'])<=self.clock():
            failure('DATA_QUERY_TIMEOUT','Query execution deadline exceeded.',504)

    def pulse(self, row):
        if self.stop_event.is_set():
            failure('DATA_QUERY_INTERRUPTED','Worker is restarting. No partial result was published.',503)
        with self.store.transaction() as db:
            current=self.decode(db.execute('SELECT '+SELECT+' FROM data_query_jobs WHERE job_id=?',(row['job_id'],)).fetchone())
            self.check_claim(row,current)
            db.execute('UPDATE data_query_jobs SET lease_until=?,updated=? WHERE job_id=? AND token=?',
                       (min(self.clock()+self.lease_seconds,row['deadline'],row['plan_expires']),self.clock(),row['job_id'],row['token']))
        self.authority(row)

    def progress(self, row, stage, fragment=None, *, finalizing=False):
        with self.store.transaction() as db:
            current=self.decode(db.execute('SELECT '+SELECT+' FROM data_query_jobs WHERE job_id=?',(row['job_id'],)).fetchone())
            self.check_claim(row,current)
            value=json.loads(current['progress']);value['stage']=stage[:160]
            if fragment is not None:
                value['completed_fragments']+=1
                value['transferred_rows']+=fragment['transferred_rows']
                value['transferred_bytes']+=fragment['transferred_bytes']
            db.execute('UPDATE data_query_jobs SET state=?,progress=?,updated=? WHERE job_id=? AND token=?',
                       ('finalizing' if finalizing else 'running',json.dumps(value),self.clock(),row['job_id'],row['token']))

    def publish(self, row, result):
        self.pulse(row)
        auth=self.authority(row)
        self.valid_saved(auth,json.loads(row['document']))
        # Bound the complete envelope too, including source/fragment metadata.
        self.result_validator.validate(result)
        payload=json.dumps(result,ensure_ascii=False).encode()
        if len(payload)>2_500_000:
            failure('DATA_QUERY_LIMIT','Complete query response exceeds the temporary result budget.',422)
        encrypted=self.manager.cipher.encrypt(payload).decode()
        with self.store.transaction() as db:
            current=self.decode(db.execute('SELECT '+SELECT+' FROM data_query_jobs WHERE job_id=?',(row['job_id'],)).fetchone())
            self.check_claim(row,current)
            self.authority(row)
            view=self.manager.relationships.get_in_transaction(db,row['workspace'],row['owner'])
            if not view['graph'] or view['stale'] or fingerprint(view['graph'])!=json.loads(row['document'])['context_hash']:
                failure('DATA_QUERY_STALE','Metadata or relationship review changed before result publication.')
            live=db.execute('SELECT workspace,owner FROM data_query_jobs WHERE result_secret IS NOT NULL').fetchall()
            if len(live)>=100 or sum((w,o)==(row['workspace'],row['owner']) for w,o in live)>=20:
                failure('DATA_QUERY_BUSY','Temporary result capacity reached. Wait for existing results to expire.',429)
            stamp=self.clock()
            db.execute("UPDATE data_query_jobs SET state='succeeded',token=NULL,lease_until=0,updated=?,progress=?,result_secret=?,result_expires=?,error_code=NULL,error_message=NULL WHERE job_id=? AND token=?",
                       (stamp,json.dumps({**json.loads(current['progress']),'stage':'Complete'}),encrypted,stamp+self.result_ttl,row['job_id'],row['token']))

    def finish_failure(self, row, error):
        with self.store.transaction() as db:
            current=self.decode(db.execute('SELECT '+SELECT+' FROM data_query_jobs WHERE job_id=?',(row['job_id'],)).fetchone())
            if current is None or current['token']!=row['token'] or current['lease_until']<=self.clock():return
            state,code,message='failed',error.code,str(error)
            if current['state']=='cancel_requested' or code=='DATA_QUERY_CANCELLED':
                state,code,message='cancelled',None,None
            elif code=='DATA_QUERY_INTERRUPTED' and current['attempts']<2 and min(current['deadline'],current['plan_expires'])>self.clock():
                state,code,message='queued',None,None
            stage='Recovering with fresh source snapshots' if state=='queued' else 'Cancelled' if state=='cancelled' else 'Stopped without results'
            db.execute('UPDATE data_query_jobs SET state=?,token=NULL,lease_until=0,updated=?,progress=?,error_code=?,error_message=?,result_secret=NULL WHERE job_id=? AND token=?',
                       (state,self.clock(),json.dumps(progress_value(stage)),code,message,row['job_id'],row['token']))

    def tick(self):
        row=self.claim()
        if row is None:return False
        try:
            with QueryExecutionControl(self,row) as control:
                auth=self.authority(row)
                saved=json.loads(row['document']);self.valid_saved(auth,saved)
                control.progress('Starting read-only query',None)
                remaining=min(row['deadline'],row['plan_expires'])-self.clock()
                result=self.queries.execute(auth,{'plan_id':row['plan_id']},saved_snapshot=saved,deadline=time.monotonic()+max(0,remaining))
                control.check()
                self.progress(row,'Validating complete result',finalizing=True)
                self.publish(row,result)
            self.health=dict(state='ready',last_success=now())
        except ApiFailure as error:
            self.finish_failure(row,error)
            self.health=dict(state='ready',last_error=error.code)
        except Exception:
            self.finish_failure(row,ApiFailure('DATA_QUERY_JOB_FAILED','Query execution failed. Check source access and create a fresh job.',503))
            self.health=dict(state='ready',last_error='DATA_QUERY_JOB_FAILED')
        return True

    def start(self):
        with self.guard:
            if any(t.is_alive() for t in self.threads):return
            self.stop_event.clear();self.health=dict(state='ready')
            def loop():
                while not self.stop_event.is_set():
                    try:worked=self.tick()
                    except Exception:
                        logging.getLogger(__name__).warning('Data query job coordination unavailable; durable jobs retained.')
                        self.health=dict(state='error',last_error='DATA_QUERY_QUEUE_UNAVAILABLE');worked=False
                    if not worked:self.wake.wait(1);self.wake.clear()
            self.threads=[Thread(target=loop,name='builder-data-query-'+str(i),daemon=True) for i in range(4)]
            self.thread=self.threads[0]
            for thread in self.threads:thread.start()

    def stop(self):
        self.stop_event.set();self.wake.set()
        deadline=time.monotonic()+15
        for thread in self.threads:thread.join(timeout=max(0,deadline-time.monotonic()))
        self.health=dict(state='stopped')
