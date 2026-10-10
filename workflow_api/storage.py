"""Transactional local POC revision/idempotency store; no runtime state."""
import json
import sqlite3
from contextlib import contextmanager
from pathlib import Path


class WorkflowStore:
    def __init__(self, path):
        self.path = str(path)
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        with self.transaction() as db:
            db.execute('CREATE TABLE IF NOT EXISTS revisions (workspace TEXT, workflow_id TEXT, version INTEGER, document TEXT NOT NULL, PRIMARY KEY(workspace, workflow_id, version))')
            db.execute('CREATE TABLE IF NOT EXISTS mutations (workspace TEXT, subject TEXT, key TEXT, fingerprint TEXT NOT NULL, response TEXT NOT NULL, PRIMARY KEY(workspace, subject, key))')
            db.execute('CREATE TABLE IF NOT EXISTS workspace_settings (workspace TEXT, key TEXT, value TEXT NOT NULL, updated_at TEXT NOT NULL, PRIMARY KEY(workspace, key))')
            db.execute('CREATE TABLE IF NOT EXISTS knowledge_sources (workspace TEXT, source_id TEXT PRIMARY KEY, document TEXT NOT NULL, updated_at TEXT NOT NULL)')
            db.execute('CREATE TABLE IF NOT EXISTS governance_policies (workspace TEXT, policy_id TEXT PRIMARY KEY, document TEXT NOT NULL, updated_at TEXT NOT NULL)')

    @contextmanager
    def transaction(self):
        db = sqlite3.connect(self.path, timeout=10)
        try:
            db.execute('BEGIN IMMEDIATE')
            yield db
            db.commit()
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()

    @staticmethod
    def get(db, workspace, workflow_id, version=None):
        query = 'SELECT document FROM revisions WHERE workspace=? AND workflow_id=?'
        args = [workspace, workflow_id]
        if version is not None:
            query += ' AND version=?'
            args.append(version)
        row = db.execute(query + ' ORDER BY version DESC LIMIT 1', args).fetchone()
        return json.loads(row[0]) if row else None

    @staticmethod
    def put(db, workspace, workflow):
        db.execute('INSERT OR REPLACE INTO revisions VALUES (?, ?, ?, ?)',
                   (workspace, workflow['workflow_id'], workflow['version'], json.dumps(workflow)))

    @staticmethod
    def list(db, workspace):
        rows = db.execute('SELECT r.document FROM revisions r WHERE r.workspace=? AND r.version=(SELECT MAX(s.version) FROM revisions s WHERE s.workspace=r.workspace AND s.workflow_id=r.workflow_id) ORDER BY r.workflow_id', (workspace,)).fetchall()
        return [json.loads(row[0]) for row in rows]
