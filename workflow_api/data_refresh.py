"""Owned automatic metadata scheduling; all cloud I/O remains in leased profiles."""
import json
import time

from .google_connections import GoogleConnections, now
from .service import ApiFailure


class DataRefresh:
    def __init__(self, manager, clock=None):
        self.manager, self.store = manager, manager.store
        self.clock = clock or time.time
        with self.store.transaction() as db:
            db.execute('CREATE TABLE IF NOT EXISTS data_source_refresh (connection_id TEXT PRIMARY KEY, enabled INTEGER NOT NULL, interval_seconds INTEGER NOT NULL, next_check REAL NOT NULL, last_attempt TEXT, last_success TEXT, last_change TEXT, failures INTEGER NOT NULL)')
            db.execute('CREATE TABLE IF NOT EXISTS data_source_auto_jobs (job_id TEXT PRIMARY KEY, connection_id TEXT NOT NULL)')
            for (cid,) in db.execute('SELECT connection_id FROM data_source_connections').fetchall():
                self.ensure(db, cid)

    def ensure(self, db, cid):
        db.execute('INSERT INTO data_source_refresh VALUES (?,1,300,?,NULL,NULL,NULL,0) ON CONFLICT(connection_id) DO NOTHING', (cid, self.clock()+300))

    def view(self, db, cid, doc):
        row = db.execute('SELECT enabled,interval_seconds,next_check,last_attempt,last_success,last_change,failures FROM data_source_refresh WHERE connection_id=?', (cid,)).fetchone()
        if row is None:
            row = (1,300,self.clock()+300,None,None,None,0)
        enabled, interval, due, attempt, success, change, failures = row
        return dict(connection_id=cid, name=doc.get('name',cid), enabled=bool(enabled), interval_seconds=interval,
                    next_check_at=due if enabled and doc['connection_status']!='disconnected' else None,
                    last_attempt_at=attempt, last_success_at=success, last_change_at=change,
                    consecutive_failures=failures, profiling_status=doc.get('profiling_status','ready'),
                    connection_status=doc['connection_status'], metadata_revision=doc['metadata_revision'],
                    last_error_message=doc.get('last_error_message'))

    def get(self, auth):
        workspace, owner = GoogleConnections.identity(auth)
        with self.store.transaction(write=False) as db:
            rows = db.execute('SELECT connection_id,document FROM data_source_connections WHERE workspace=? AND owner=? ORDER BY connection_id', (workspace,owner)).fetchall()
            return dict(version=1, items=[self.view(db,cid,json.loads(raw)) for cid,raw in rows])

    def edit(self, auth, cid, body):
        GoogleConnections.identity(auth, True)
        if (not isinstance(body,dict) or set(body)!={'enabled','interval_seconds'}
                or type(body['enabled']) is not bool or type(body['interval_seconds']) is not int
                or not 60 <= body['interval_seconds'] <= 86400):
            raise ApiFailure('DATA_REFRESH_INVALID','Choose automatic refresh and an interval from 60 to 86400 seconds.',400)
        with self.store.transaction() as db:
            _, doc = self.manager.owned(db,auth,cid)
            self.ensure(db,cid)
            db.execute('UPDATE data_source_refresh SET enabled=?,interval_seconds=?,next_check=? WHERE connection_id=?',
                       (int(body['enabled']),body['interval_seconds'],self.clock()+body['interval_seconds'],cid))
            self.manager.audit(db,auth,cid,'refresh_settings_changed')
        return self.get(auth)

    def schedule(self):
        if not self.manager.cipher:
            return False
        with self.store.transaction() as db:
            rows = db.execute('SELECT c.connection_id,c.secret,c.document FROM data_source_connections c JOIN data_source_refresh r ON r.connection_id=c.connection_id WHERE r.enabled=1 AND r.next_check<=? ORDER BY r.next_check,c.connection_id', (self.clock(),)).fetchall()
            for cid, secret, raw in rows:
                doc = json.loads(raw)
                if not secret or doc['connection_status']=='disconnected':
                    continue
                active = db.execute("SELECT 1 FROM data_source_profile_jobs WHERE connection_id=? AND state IN ('queued','running')", (cid,)).fetchone()
                if active:
                    continue
                # An automatic check preserves credential generation. Its job token
                # and the generation guard still reject obsolete publications.
                job = self.manager.queue(db,doc,invalidate=False)
                self.manager.save(db,doc)
                db.execute('INSERT INTO data_source_auto_jobs VALUES (?,?)',(job,cid))
                db.execute('UPDATE data_source_refresh SET next_check=? WHERE connection_id=?',(self.clock()+60,cid))
                return True
        return False

    def started(self, db, cid):
        self.ensure(db,cid)
        db.execute('UPDATE data_source_refresh SET last_attempt=? WHERE connection_id=?',(now(),cid))

    def finished(self, db, cid, failed, changed):
        enabled, interval, failures = db.execute('SELECT enabled,interval_seconds,failures FROM data_source_refresh WHERE connection_id=?',(cid,)).fetchone()
        failures = min(failures+1,10) if failed else 0
        delay = min(86400,interval*(2**min(failures,8))) if failed else interval
        db.execute('UPDATE data_source_refresh SET next_check=?,failures=? WHERE connection_id=?',(self.clock()+delay,failures,cid))
        if not failed:
            db.execute('UPDATE data_source_refresh SET last_success=? WHERE connection_id=?',(now(),cid))
        if changed:
            db.execute('UPDATE data_source_refresh SET last_change=? WHERE connection_id=?',(now(),cid))
