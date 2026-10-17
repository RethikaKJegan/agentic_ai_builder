"""Owned, encrypted cloud connections and durable leased metadata profiling."""
from __future__ import annotations

import hashlib
import json
import secrets
import time
from pathlib import Path
from threading import Event, Thread

from cryptography.fernet import Fernet

from .data_relationships import DataRelationships
from .data_source_adapters import CloudAdapters, configuration, safe_failure
from .google_connections import GoogleConnections, now
from .service import ApiFailure

ROOT = Path(__file__).resolve().parents[1]


def changes(previous, current):
    before = {d['dataset_id']: d for d in (previous or {}).get('datasets', [])}
    after = {d['dataset_id']: d for d in current['datasets']}
    result = {'added': [], 'removed': [], 'changed': []}
    for key in sorted(after.keys() - before.keys()): result['added'].append(after[key]['name'])
    for key in sorted(before.keys() - after.keys()): result['removed'].append(before[key]['name'])
    for key in sorted(before.keys() & after.keys()):
        a, b = before[key], after[key]
        af, bf = {f['name']:f for f in a['fields']}, {f['name']:f for f in b['fields']}
        for field in sorted(bf.keys() - af.keys()): result['added'].append(b['name']+'.'+field)
        for field in sorted(af.keys() - bf.keys()): result['removed'].append(b['name']+'.'+field)
        for field in sorted(af.keys() & bf.keys()):
            shape = lambda f:{k:v for k,v in f.items() if k not in {'present_in_samples'}}
            if shape(af[field]) != shape(bf[field]): result['changed'].append(b['name']+'.'+field)
        if a.get('indexes') != b.get('indexes') or a.get('constraints') != b.get('constraints') or a.get('validation_schema_json') != b.get('validation_schema_json'):
            result['changed'].append(b['name']+' (indexes, constraints or validation)')
    return result


class DataSources:
    def __init__(self, store, env, adapter=None):
        self.store, self.env = store, env
        self.adapter = adapter or CloudAdapters(env)
        self.cipher = None
        keyfile = env.get('BUILDER_DATA_SOURCE_KEY_FILE') or env.get('BUILDER_GOOGLE_KEY_FILE')
        try:
            if keyfile:
                path = Path(keyfile)
                self.cipher = Fernet((path if path.is_absolute() else ROOT/path).read_bytes().strip())
        except (OSError,ValueError): pass
        with store.transaction() as db:
            db.execute('CREATE TABLE IF NOT EXISTS data_source_migrations (version INTEGER PRIMARY KEY)')
            db.execute('INSERT INTO data_source_migrations(version) VALUES (1) ON CONFLICT DO NOTHING')
            db.execute('CREATE TABLE IF NOT EXISTS data_source_connections (connection_id TEXT PRIMARY KEY, workspace TEXT NOT NULL, owner TEXT NOT NULL, secret TEXT, document TEXT NOT NULL)')
            db.execute('CREATE TABLE IF NOT EXISTS data_source_profile_jobs (job_id TEXT PRIMARY KEY, connection_id TEXT NOT NULL, generation INTEGER NOT NULL, state TEXT NOT NULL, token TEXT, lease_until REAL NOT NULL, attempts INTEGER NOT NULL)')
            db.execute('CREATE TABLE IF NOT EXISTS data_source_snapshots (connection_id TEXT NOT NULL, revision INTEGER NOT NULL, document TEXT NOT NULL, PRIMARY KEY(connection_id,revision))')
            db.execute('CREATE TABLE IF NOT EXISTS data_source_audit (event_id TEXT PRIMARY KEY, connection_id TEXT NOT NULL, workspace TEXT NOT NULL, owner TEXT NOT NULL, kind TEXT NOT NULL, created_at TEXT NOT NULL)')

        self.relationships = DataRelationships(store)

    def configured(self):
        if not self.cipher:
            raise ApiFailure('DATA_SOURCE_SETUP_REQUIRED', 'Configure BUILDER_DATA_SOURCE_KEY_FILE with a persistent Fernet key on the backend and worker.', 503)

    def owned(self, db, auth, cid):
        workspace, owner = GoogleConnections.identity(auth)
        row = db.execute('SELECT secret,document FROM data_source_connections WHERE connection_id=? AND workspace=? AND owner=?',(cid,workspace,owner)).fetchone()
        if not row: raise ApiFailure('DATA_SOURCE_NOT_FOUND', 'Database connection not found.', 404)
        return row[0], json.loads(row[1])

    @staticmethod
    def save(db, doc):
        db.execute('UPDATE data_source_connections SET document=? WHERE connection_id=?',(json.dumps(doc),doc['connection_id']))

    @staticmethod
    def audit(db, auth, cid, kind):
        workspace, owner = GoogleConnections.identity(auth)
        db.execute('INSERT INTO data_source_audit VALUES (?,?,?,?,?,?)',('dba_'+secrets.token_hex(16),cid,workspace,owner,kind,now()))

    def list(self, auth):
        workspace, owner = GoogleConnections.identity(auth)
        with self.store.transaction(write=False) as db:
            rows=db.execute('SELECT document FROM data_source_connections WHERE workspace=? AND owner=? ORDER BY connection_id',(workspace,owner)).fetchall()
        return {'configured':bool(self.cipher),'shared_demo_identity':auth['subject']['subject_id']=='local-builder','items':[json.loads(r[0]) for r in rows]}

    def test(self, auth, body):
        GoogleConnections.identity(auth, True)
        config=configuration(body)
        try:self.adapter.test(config)
        except Exception as exc:raise safe_failure(exc) from None
        return {'success':True,'message':'Connection and discovery access verified. Metadata profiling has not run.'}

    @staticmethod
    def queue(db, doc):
        doc['generation'] += 1
        doc['profiling_status']='queued'
        doc['last_error_code']=None
        doc['last_error_message']=None
        doc['updated_at']=now()
        db.execute("UPDATE data_source_profile_jobs SET state='cancelled',token=NULL WHERE connection_id=? AND state IN ('queued','running')",(doc['connection_id'],))
        db.execute('INSERT INTO data_source_profile_jobs VALUES (?,?,?,?,?,?,?)',('dbjob_'+secrets.token_hex(16),doc['connection_id'],doc['generation'],'queued',None,0,0))

    def connect(self, auth, body):
        self.configured()
        workspace, owner=GoogleConnections.identity(auth,True)
        config=configuration(body)
        try:self.adapter.test(config)
        except Exception as exc:raise safe_failure(exc) from None
        cid='dbconn_'+secrets.token_hex(16)
        doc={k:config[k] for k in ('name','engine','database','schemas','description','mode','host')}
        doc.update(connection_id=cid,connection_status='connected',profiling_status='queued',generation=0,metadata_revision=0,created_at=now(),updated_at=now(),last_verified_at=now(),last_profiled_at=None,last_error_code=None,last_error_message=None)
        with self.store.transaction() as db:
            count=db.execute("SELECT COUNT(*) FROM data_source_connections WHERE workspace=? AND owner=? AND secret IS NOT NULL",(workspace,owner)).fetchone()[0]
            if count >= 20:raise ApiFailure('DATA_SOURCE_LIMIT', 'Disconnect an existing database before adding more than 20 connections.',409)
            self.queue(db,doc)
            db.execute('INSERT INTO data_source_connections VALUES (?,?,?,?,?)',(cid,workspace,owner,self.cipher.encrypt(json.dumps(config).encode()).decode(),json.dumps(doc)))
            self.audit(db,auth,cid,'connected')
        return doc

    def credentials(self, auth, cid, body):
        self.configured()
        GoogleConnections.identity(auth, True)
        config = configuration(body)
        with self.store.transaction(write=False) as db:
            _, previous = self.owned(db, auth, cid)
        if any(config[k] != previous[k] for k in ('engine', 'host', 'database')):
            raise ApiFailure('DATA_SOURCE_TARGET_CHANGED', 'Create a new connection when changing its database endpoint.', 409)
        try:self.adapter.test(config)
        except Exception as exc:raise safe_failure(exc) from None
        with self.store.transaction() as db:
            _, doc = self.owned(db, auth, cid)
            if doc['generation'] != previous['generation']:
                raise ApiFailure('DATA_SOURCE_CHANGED', 'Connection changed during verification. Refresh status.', 409)
            doc.update({k:config[k] for k in ('name','schemas','description','mode')})
            doc.update(connection_status='connected', last_verified_at=now())
            self.queue(db, doc)
            db.execute('UPDATE data_source_connections SET secret=? WHERE connection_id=?', (self.cipher.encrypt(json.dumps(config).encode()).decode(), cid))
            self.save(db, doc);self.audit(db, auth, cid, 'credentials_replaced')
        return doc

    def action(self, auth, cid, action):
        GoogleConnections.identity(auth,True)
        with self.store.transaction() as db:
            secret, doc=self.owned(db,auth,cid)
            if action=='disconnect':
                doc.update(connection_status='disconnected',profiling_status='cancelled',generation=doc['generation']+1,updated_at=now(),last_error_code=None,last_error_message=None)
                db.execute('UPDATE data_source_connections SET secret=NULL WHERE connection_id=?',(cid,))
                db.execute("UPDATE data_source_profile_jobs SET state='cancelled',token=NULL WHERE connection_id=? AND state IN ('queued','running')",(cid,))
                self.save(db,doc);self.audit(db,auth,cid,'disconnected')
                self.relationships.enqueue(db,*GoogleConnections.identity(auth))
                return doc
            if not secret:raise ApiFailure('DATA_SOURCE_DISCONNECTED','Connect the database again to use it.',409)
            if action=='refresh-metadata':
                if doc['profiling_status'] in {'queued','running'}:return doc
                self.queue(db,doc);self.save(db,doc);self.audit(db,auth,cid,'refresh_requested')
                return doc
            generation=doc['generation']
        self.configured()
        try:
            config=json.loads(self.cipher.decrypt(secret.encode()))
            self.adapter.test(config)
            failure=None
        except Exception as exc:failure=safe_failure(exc)
        with self.store.transaction() as db:
            current_secret,doc=self.owned(db,auth,cid)
            if not current_secret or doc['generation']!=generation:
                raise ApiFailure('DATA_SOURCE_CHANGED','Connection changed during verification. Refresh its status.',409)
            doc.update(connection_status='authentication_failed' if failure and failure.code=='DATA_SOURCE_ACCESS_DENIED' else 'unreachable' if failure else 'connected',last_verified_at=now(),updated_at=now(),last_error_code=failure.code if failure else None,last_error_message=str(failure) if failure else None)
            self.save(db,doc);self.audit(db,auth,cid,'verification_failed' if failure else 'verified')
        return doc

    def metadata(self,auth,cid):
        with self.store.transaction(write=False) as db:
            _,doc=self.owned(db,auth,cid)
            row=db.execute('SELECT document FROM data_source_snapshots WHERE connection_id=? AND revision=?',(cid,doc['metadata_revision'])).fetchone()
        return {'connection':doc,'snapshot':json.loads(row[0]) if row else None}

    def tick(self):
        # Claim transaction is short. No network I/O holds a database transaction.
        with self.store.transaction() as db:
            row=db.execute("SELECT job_id,connection_id,generation,attempts FROM data_source_profile_jobs WHERE state='queued' OR (state='running' AND lease_until<?) ORDER BY job_id LIMIT 1",(time.time(),)).fetchone()
            if not row:return False
            job,cid,generation,attempts=row
            connection=db.execute('SELECT secret,document FROM data_source_connections WHERE connection_id=?',(cid,)).fetchone()
            if not connection or not connection[0]:
                db.execute("UPDATE data_source_profile_jobs SET state='cancelled' WHERE job_id=?",(job,));return True
            secret,raw=connection;doc=json.loads(raw)
            if doc['generation']!=generation:
                db.execute("UPDATE data_source_profile_jobs SET state='cancelled' WHERE job_id=?",(job,));return True
            token=secrets.token_hex(16)
            db.execute("UPDATE data_source_profile_jobs SET state='running',token=?,lease_until=?,attempts=? WHERE job_id=?",(token,time.time()+180,attempts+1,job))
            doc['profiling_status']='running';self.save(db,doc)
        try:
            self.configured()
            if attempts>=3:raise ApiFailure('DATA_SOURCE_PROFILING_INTERRUPTED','Profiling was repeatedly interrupted. Refresh metadata to retry.',503)
            result=self.adapter.profile(json.loads(self.cipher.decrypt(secret.encode())),cid)
            if len(json.dumps(result).encode())>2_000_000:
                raise ApiFailure('DATA_SOURCE_METADATA_LIMIT','Metadata exceeded the 2 MB snapshot limit. Profile a smaller database/schema selection.',400)
            failure=None
        except Exception as exc:failure=safe_failure(exc);result=None
        with self.store.transaction() as db:
            claim=db.execute('SELECT state,token FROM data_source_profile_jobs WHERE job_id=?',(job,)).fetchone()
            current=db.execute('SELECT secret,document FROM data_source_connections WHERE connection_id=?',(cid,)).fetchone()
            if not claim or claim!=('running',token) or not current or not current[0]:return True
            doc=json.loads(current[1])
            if doc['generation']!=generation:return True
            if failure:
                doc.update(profiling_status='failed',last_error_code=failure.code,last_error_message=str(failure))
                if failure.code=='DATA_SOURCE_ACCESS_DENIED':doc['connection_status']='authentication_failed'
                elif failure.code=='DATA_SOURCE_CONNECTION_FAILED':doc['connection_status']='unreachable'
                state='failed'
            else:
                previous=db.execute('SELECT document FROM data_source_snapshots WHERE connection_id=? AND revision=?',(cid,doc['metadata_revision'])).fetchone()
                result.update(connection_id=cid,engine=doc['engine'],revision=doc['metadata_revision']+1,discovered_at=now(),changes=changes(json.loads(previous[0]) if previous else None,result))
                db.execute('INSERT INTO data_source_snapshots VALUES (?,?,?)',(cid,result['revision'],json.dumps(result)))
                doc.update(connection_status='connected',profiling_status='ready',metadata_revision=result['revision'],last_profiled_at=result['discovered_at'],last_error_code=None,last_error_message=None)
                state='succeeded'
            doc['updated_at']=now();self.save(db,doc)
            db.execute('UPDATE data_source_profile_jobs SET state=?,token=NULL WHERE job_id=?',(state,job))
            row=db.execute('SELECT workspace,owner FROM data_source_connections WHERE connection_id=?',(cid,)).fetchone()
            db.execute('INSERT INTO data_source_audit VALUES (?,?,?,?,?,?)',('dba_'+secrets.token_hex(16),cid,*row,'profile_'+state,now()))
            if not failure:self.relationships.enqueue(db,*row)
        return True


class DataSourceWorker:
    def __init__(self,manager):
        self.manager=manager;self.stop_event=Event();self.thread=None
        self.health={'state':'idle','last_success':None,'last_error':None}

    def start(self):
        if self.thread and self.thread.is_alive():return
        self.stop_event.clear()
        def loop():
            while not self.stop_event.is_set():
                try:
                    worked=self.manager.tick()
                    worked=self.manager.relationships.tick() or worked
                    self.health.update(state='active',last_success=now(),last_error=None)
                except Exception:
                    worked=False;self.health.update(state='failed',last_error='DATA_SOURCE_WORKER_FAILED')
                if not worked:self.stop_event.wait(2)
        self.thread=Thread(target=loop,name='builder-data-source-profiling',daemon=True);self.thread.start()

    def stop(self):
        self.stop_event.set()
        if self.thread:self.thread.join(timeout=5)
