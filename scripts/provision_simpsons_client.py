"""Copy explicit Simpsons definitions and source bindings into a NEW private store.

No network, model, source write, shared history or shared workspace context access.
Run with --help for required paths. The existing application is read-only.
"""
import argparse
import json
import os
from pathlib import Path
import sqlite3
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cryptography.fernet import Fernet
from workflow_api.client_isolation import CLIENT, WORKSPACE, OWNER
from workflow_api.storage import WorkflowStore
from workflow_api.data_sources import DataSources
from workflow_api.business_ontology import BusinessOntology


def provision(source, target, source_key, target_key, scope, connection_ids, knowledge_ids=()):
    source, target, source_key, target_key = map(lambda p: Path(p).resolve(), (source, target, source_key, target_key))
    if target.exists() or target_key.exists() or target == source or source_key == target_key:
        raise ValueError('Use new, separate target database and key paths.')
    if len(set(connection_ids)) != 2:
        raise ValueError('Explicitly select the two Simpsons source connection IDs.')
    # Validate the full selection before creating output. Never infer tenancy from a display name.
    with sqlite3.connect(source.as_uri() + '?mode=ro', uri=True) as original:
        original.execute('PRAGMA query_only=ON')
        original.execute('BEGIN')
        row = original.execute('SELECT document FROM business_ontology_workspaces WHERE workspace=? AND owner=? AND ontology_id=?',
                               (*scope, 'simpson')).fetchone()
        if not row or set(json.loads(row[0])['sources'].values()) != set(connection_ids):
            raise ValueError('The selected sources must exactly match the Simpsons ontology bindings.')
        versions = original.execute('SELECT version_id,document FROM business_ontology_versions WHERE workspace=? AND owner=?', scope).fetchall()
        if not versions or any(set(json.loads(v[1])['workspace']['sources'].values()) != set(connection_ids) for v in versions):
            raise ValueError('Every copied ontology version must bind only the selected Simpsons sources.')
        source_cipher = Fernet(source_key.read_bytes().strip())
        target_key_bytes = Fernet.generate_key()
        target_cipher = Fernet(target_key_bytes)
        selected = []
        snapshots = []
        for cid in connection_ids:
            connection = original.execute('SELECT secret,document FROM data_source_connections WHERE workspace=? AND owner=? AND connection_id=?',
                                          (*scope, cid)).fetchone()
            if not connection or not connection[0]:
                raise ValueError('A selected Simpsons source has no usable saved credentials.')
            secret = target_cipher.encrypt(source_cipher.decrypt(connection[0].encode())).decode()
            document = json.loads(connection[1])
            if document['connection_status'] != 'connected':
                raise ValueError('Selected Simpsons sources must be connected.')
            # The document scope, when present, follows the new server-owned scope.
            for field, value in [('workspace_id', WORKSPACE), ('subject_id', OWNER), ('workspace', WORKSPACE), ('owner', OWNER)]:
                if field in document:
                    document[field] = value
            selected.append((cid, WORKSPACE, OWNER, secret, json.dumps(document)))
            current = original.execute('SELECT revision,document FROM data_source_snapshots WHERE connection_id=?', (cid,)).fetchall()
            if not any(revision == document['metadata_revision'] for revision, _ in current):
                raise ValueError('A selected source is missing its pinned metadata snapshot.')
            snapshots.extend((cid, revision, raw) for revision, raw in current)
        knowledge = []
        for kid in knowledge_ids:
            item = original.execute('SELECT source_id,document,updated_at FROM knowledge_sources WHERE workspace=? AND source_id=?', (scope[0], kid)).fetchone()
            if not item:
                raise ValueError('An explicitly selected context document was not found.')
            knowledge.append(item)
        target.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        target_key.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        # Exclusive creation makes concurrent runs fail before any existing artifact is overwritten.
        fd = os.open(target, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        os.close(fd)
        with target_key.open('xb') as handle:
            os.chmod(target_key, 0o600)
            handle.write(target_key_bytes + b'\n')
        store = WorkflowStore(target)
        DataSources(store, {'BUILDER_DATA_SOURCE_KEY_FILE': str(target_key)})
        BusinessOntology(store)
        with store.transaction() as db:
            db.executemany('INSERT INTO data_source_connections VALUES (?,?,?,?,?)', selected)
            db.executemany('INSERT INTO data_source_snapshots VALUES (?,?,?)', snapshots)
            db.execute('INSERT INTO business_ontology_workspaces VALUES (?,?,?,?)', (WORKSPACE, OWNER, 'simpson', row[0]))
            db.executemany('INSERT INTO business_ontology_versions VALUES (?,?,?,?)', [(WORKSPACE, OWNER, vid, raw) for vid, raw in versions])
            for kid, raw, updated in knowledge:
                db.execute('INSERT INTO knowledge_sources(workspace,source_id,document,updated_at) VALUES (?,?,?,?)', (WORKSPACE, kid, raw, updated))
            # Copy only policy revisions pinned by these immutable ontology versions.
            policy_ids = {p['policy_id'] for _, raw in versions for p in json.loads(raw).get('knowledge', {}).get('manifest', {}).get('policy_refs', [])}
            if policy_ids:
                for table in ('business_policy_heads', 'business_policy_versions'):
                    ddl = original.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name=?", (table,)).fetchone()
                    if not ddl:
                        raise ValueError('A pinned business policy table is unavailable.')
                    db.execute(ddl[0])
                keys = set()
                for pid in policy_ids:
                    policy = original.execute('SELECT * FROM business_policy_versions WHERE workspace=? AND owner=? AND policy_id=?', (*scope, pid)).fetchone()
                    if not policy:
                        raise ValueError('A pinned business policy is unavailable.')
                    copied = (WORKSPACE, OWNER, *policy[2:])
                    db.execute('INSERT INTO business_policy_versions VALUES (' + ','.join('?' for _ in copied) + ')', copied)
                    keys.add(policy[3])
                for key in keys:
                    revision = db.execute('SELECT MAX(revision) FROM business_policy_versions WHERE policy_key=?', (key,)).fetchone()[0]
                    db.execute('INSERT INTO business_policy_heads VALUES (?,?,?,?)', (WORKSPACE, OWNER, key, revision))
            # The marker is written last: a failed/partial provisioning can never start a client backend.
            db.execute('CREATE TABLE client_isolation(client_id TEXT PRIMARY KEY,workspace TEXT NOT NULL,owner TEXT NOT NULL)')
            db.execute('CREATE TABLE client_source_bindings(connection_id TEXT PRIMARY KEY)')
            db.executemany('INSERT INTO client_source_bindings VALUES (?)', [(cid,) for cid in connection_ids])
            db.execute('INSERT INTO client_isolation VALUES (?,?,?)', (CLIENT, WORKSPACE, OWNER))
    return dict(client_id=CLIENT, workspace_id=WORKSPACE, subject_id=OWNER,
                source_connections=len(selected), ontology_versions=len(versions), context_documents=len(knowledge),
                shared_histories_copied=0, source_writes=0, model_calls=0)


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source', type=Path, required=True)
    p.add_argument('--target', type=Path, required=True)
    p.add_argument('--source-key', type=Path, required=True)
    p.add_argument('--target-key', type=Path, required=True)
    p.add_argument('--workspace', required=True)
    p.add_argument('--owner', required=True)
    p.add_argument('--connection-id', action='append', required=True)
    p.add_argument('--knowledge-id', action='append', default=[])
    a = p.parse_args()
    try:
        print(json.dumps(provision(a.source, a.target, a.source_key, a.target_key,
                                   (a.workspace, a.owner), a.connection_id, a.knowledge_id), indent=2))
    except Exception:
        raise SystemExit('Provisioning failed. Check the explicit Simpsons bindings, keys and new output paths; no source data was changed.') from None
