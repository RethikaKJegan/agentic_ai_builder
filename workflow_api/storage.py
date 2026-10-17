"""Transactional local POC revision/idempotency store; no runtime state."""
import json
import sqlite3
import logging
import os
import time
from threading import Lock
from contextlib import contextmanager
from pathlib import Path


def sqlite_category(exc):
    code=getattr(exc,'sqlite_errorcode',0)&255
    if code in (sqlite3.SQLITE_BUSY,sqlite3.SQLITE_LOCKED):return 'contention'
    if code==sqlite3.SQLITE_MISUSE or str(exc).lower() in {
            'cannot start a transaction within a transaction','cannot commit - no transaction is active',
            'cannot rollback - no transaction is active'}:return 'transaction_state'
    return 'database_failure'


class WorkflowStore:
    def __init__(self, path, *, busy_timeout_ms=None):
        self.busy_timeout_ms = int(os.getenv('BUILDER_DATABASE_BUSY_TIMEOUT_MS', '3000')) if busy_timeout_ms is None else busy_timeout_ms
        if type(self.busy_timeout_ms) is not int or not 0 <= self.busy_timeout_ms <= 30000:
            raise ValueError('Database busy timeout must be between 0 and 30000 milliseconds.')
        self.metrics = {'reads': 0, 'writes': 0, 'contention': 0, 'failures': 0, 'slow_transactions': 0}
        self.metrics_lock = Lock()
        self.path = str(path)
        self.database = None
        if self.path.startswith(('postgresql://','postgres://')):
            from .postgres import PostgresDatabase
            self.database = PostgresDatabase(self.path,self.busy_timeout_ms)
        else:
            Path(path).parent.mkdir(parents=True, exist_ok=True)
            with sqlite3.connect(self.path, timeout=self.busy_timeout_ms / 1000) as db:
                db.execute('PRAGMA journal_mode=WAL')
        with self.transaction() as db:
            db.execute('CREATE TABLE IF NOT EXISTS builder_schema_migrations (version INTEGER PRIMARY KEY, applied_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP)')
            version=db.execute('SELECT COALESCE(MAX(version),0) FROM builder_schema_migrations').fetchone()[0]
            if version>1:raise ValueError('The database schema is newer than this application.')
            db.execute('INSERT INTO builder_schema_migrations(version) VALUES (1) ON CONFLICT DO NOTHING')
            db.execute('CREATE TABLE IF NOT EXISTS revisions (workspace TEXT, workflow_id TEXT, version INTEGER, document TEXT NOT NULL, PRIMARY KEY(workspace, workflow_id, version))')
            db.execute('CREATE TABLE IF NOT EXISTS mutations (workspace TEXT, subject TEXT, key TEXT, fingerprint TEXT NOT NULL, response TEXT NOT NULL, PRIMARY KEY(workspace, subject, key))')
            db.execute('CREATE TABLE IF NOT EXISTS workspace_settings (workspace TEXT, key TEXT, value TEXT NOT NULL, updated_at TEXT NOT NULL, PRIMARY KEY(workspace, key))')
            db.execute('CREATE TABLE IF NOT EXISTS knowledge_sources (workspace TEXT, source_id TEXT PRIMARY KEY, document TEXT NOT NULL, updated_at TEXT NOT NULL)')
            db.execute('CREATE TABLE IF NOT EXISTS governance_policies (workspace TEXT, policy_id TEXT PRIMARY KEY, document TEXT NOT NULL, updated_at TEXT NOT NULL)')

    @contextmanager
    def transaction(self, *, write=True):
        if self.database is not None:
            started=time.monotonic()
            try:
                with self.database.transaction(write=write) as connection:
                    yield connection
            except Exception as exc:
                from .postgres import DatabaseFailure
                if isinstance(exc,DatabaseFailure):
                    with self.metrics_lock:self.metrics['contention' if exc.category=='contention' else 'failures']+=1
                raise
            finally:
                with self.metrics_lock:
                    self.metrics['writes' if write else 'reads']+=1
                    if time.monotonic()-started>=1:self.metrics['slow_transactions']+=1
            return
        db = sqlite3.connect(self.path, timeout=self.busy_timeout_ms / 1000)
        started = time.monotonic()
        category = None
        try:
            db.execute(f'PRAGMA busy_timeout={self.busy_timeout_ms}')
            if not write:
                db.execute('PRAGMA query_only=ON')
            db.execute('BEGIN IMMEDIATE' if write else 'BEGIN')
            yield db
            db.commit()
        except Exception as exc:
            db.rollback()
            code = getattr(exc, 'sqlite_errorcode', 0) & 255
            category = sqlite_category(exc) if isinstance(exc,sqlite3.DatabaseError) else None
            logging.getLogger(__name__).warning('Database transaction failed', extra={
                'database_category': category, 'database_code': code, 'transaction_write': write,
                'transaction_seconds': round(time.monotonic() - started, 4)})
            raise
        finally:
            elapsed = time.monotonic() - started
            with self.metrics_lock:
                self.metrics['writes' if write else 'reads'] += 1
                if category:
                    self.metrics['contention' if category == 'contention' else 'failures'] += 1
                if elapsed >= 1:
                    self.metrics['slow_transactions'] += 1
            if elapsed >= 1:
                logging.getLogger(__name__).info('Slow database transaction', extra={
                    'transaction_write': write, 'transaction_seconds': round(elapsed, 4)})
            db.close()

    @staticmethod
    def get(db, workspace, workflow_id, version=None):
        query = 'SELECT document FROM revisions WHERE workspace=? AND workflow_id=?'
        args = [workspace, workflow_id]
        if version is not None:
            query += ' AND version=?'
            args.append(version)
        row = db.execute(query + ' ORDER BY version DESC LIMIT 1' + (' FOR UPDATE' if getattr(db,'write',False) else ''), args).fetchone()
        return json.loads(row[0]) if row else None

    @staticmethod
    def put(db, workspace, workflow):
        db.execute('INSERT OR REPLACE INTO revisions VALUES (?, ?, ?, ?)',
                   (workspace, workflow['workflow_id'], workflow['version'], json.dumps(workflow)))

    @staticmethod
    def list(db, workspace):
        rows = db.execute('SELECT r.document FROM revisions r WHERE r.workspace=? AND r.version=(SELECT MAX(s.version) FROM revisions s WHERE s.workspace=r.workspace AND s.workflow_id=r.workflow_id) ORDER BY r.workflow_id', (workspace,)).fetchall()
        return [json.loads(row[0]) for row in rows]
