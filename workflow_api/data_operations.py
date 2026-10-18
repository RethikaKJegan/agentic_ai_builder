"""Owned prepared CRUD, encrypted recovery evidence and durable no-replay claims."""
import json
import re
import secrets
import time
from pathlib import Path

from jsonschema import Draft202012Validator

from .data_operation_tools import registered_grant, tool_definition
from .data_relationships import fingerprint
from .data_selection import dataset_label
from .data_write_adapter import WriteAdapter, RolledBack, UncertainWrite, fail, public_record, pack
from .data_source_adapters import CloudAdapters
from .google_connections import GoogleConnections
from .service import ApiFailure

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = json.loads((ROOT/'shared/contracts/data-sources/operations-v1.schema.json').read_text())


def validate(kind, value):
    validator = Draft202012Validator({'$defs': SCHEMA['$defs'], '$ref': '#/$defs/'+kind})
    if list(validator.iter_errors(value)):
        fail('The database operation does not match its supported contract.')


class DataOperations:
    def __init__(self, manager, resolve=None, adapter=None, workflow_authorize=None):
        self.manager, self.store, self.env = manager, manager.store, manager.env
        self.resolve = resolve
        self.workflow_authorize = workflow_authorize
        self.adapter = adapter or WriteAdapter(getattr(manager, 'adapter', None) or CloudAdapters(self.env))
        with self.store.transaction() as db:
            db.execute('CREATE TABLE IF NOT EXISTS data_write_operations (operation_id TEXT PRIMARY KEY, workspace TEXT NOT NULL, owner TEXT NOT NULL, retry_key TEXT NOT NULL, request_hash TEXT NOT NULL, state TEXT NOT NULL, created REAL NOT NULL, expires REAL NOT NULL, recovery_until REAL NOT NULL, started REAL, token TEXT, secret TEXT, summary TEXT NOT NULL, recovery_of TEXT UNIQUE, UNIQUE(workspace,owner,retry_key))')
            db.execute('CREATE TABLE IF NOT EXISTS data_write_audit (event_id TEXT PRIMARY KEY, workspace TEXT NOT NULL, owner TEXT NOT NULL, operation_id TEXT NOT NULL, step_index INTEGER NOT NULL, tool_id TEXT NOT NULL, state TEXT NOT NULL, matched INTEGER NOT NULL, affected INTEGER NOT NULL, created REAL NOT NULL)')
            db.execute('CREATE TABLE IF NOT EXISTS database_workflow_operations (operation_id TEXT PRIMARY KEY, workspace TEXT NOT NULL, owner TEXT NOT NULL, run_id TEXT NOT NULL, workflow_id TEXT NOT NULL, version INTEGER NOT NULL, invocation TEXT NOT NULL, request_hash TEXT NOT NULL, UNIQUE(workspace,owner,run_id,invocation))')

    @staticmethod
    def identity(auth, write=False):
        if auth.get('decision') != 'allow':
            fail('Current database operation authority is denied.', 'DATA_WRITE_AUTHORITY_CHANGED', 403)
        identity = GoogleConnections.identity(auth, True)
        GoogleConnections.identity(auth)
        if write and ('workflow.approve' not in auth.get('permissions', []) or not {'admin', 'approver'} & set(auth.get('roles', []))):
            fail('Writes require an authenticated human with operation and approval permissions.', 'DATA_WRITE_APPROVAL_REQUIRED', 403)
        return identity

    def current(self, auth):
        workspace, owner = GoogleConnections.identity(auth)
        current = self.resolve(workspace, owner) if self.resolve else auth
        if not current or current.get('subject') != auth['subject']:
            fail('Current database operation authority is unavailable.', 'DATA_WRITE_AUTHORITY_CHANGED', 403)
        return current

    def policy(self):
        path = self.env.get('BUILDER_DATA_WRITE_POLICY_FILE')
        if not path:
            return {'targets': []}
        try:
            file = Path(path)
            raw = (file if file.is_absolute() else ROOT/file).read_text()
            if len(raw.encode()) > 65536:
                raise ValueError()
            policy = json.loads(raw)
            validate('policy', policy)
            identities = [(t['workspace_id'], t['subject_id'], t['connection_id'], t['dataset_id']) for t in policy['targets']]
            if len(set(identities)) != len(identities):
                raise ValueError()
            return policy
        except Exception:
            fail('The server database operation policy is invalid. No target is enabled.', 'DATA_WRITE_SETUP_REQUIRED', 503)

    def context(self, auth, step):
        workspace, owner = self.identity(auth, step['action'] != 'read')
        scope = 'workspace:read' if step['action'] == 'read' else 'workspace:write'
        if scope not in auth.get('scopes', []):
            fail('The current source-operation scope is not granted.', 'DATA_WRITE_SCOPE_DENIED', 403)
        policy = self.policy()
        target = next((t for t in policy['targets'] if (t['workspace_id'], t['subject_id'], t['connection_id'], t['dataset_id']) ==
                       (workspace, owner, step['connection_id'], step['dataset_id'])), None)
        if not target or step['action'] not in target['operations']:
            fail('This exact dataset operation is not enabled by server policy.', 'DATA_WRITE_TARGET_DENIED', 403)
        with self.store.transaction(write=False) as db:
            secret, connection = self.manager.owned(db, auth, step['connection_id'])
            row = db.execute('SELECT document FROM data_source_snapshots WHERE connection_id=? AND revision=?',
                             (step['connection_id'], connection['metadata_revision'])).fetchone()
        if not secret or connection['connection_status'] != 'connected' or connection.get('profiling_status', 'ready') != 'ready' or not row:
            fail('The source is disconnected or lacks ready current metadata.', 'DATA_WRITE_STALE', 409)
        dataset = next((d for d in json.loads(row[0])['datasets'] if d['dataset_id'] == step['dataset_id']), None)
        if not dataset:
            fail('The dataset is outside current metadata.', 'DATA_WRITE_STALE', 409)
        fields = self.adapter.fields(dataset)
        if (set(target['identity_fields']) & set(target['writable_fields']) or
                not set(target['identity_fields'] + target['writable_fields']) <= set(fields)):
            fail('Configured fields do not match the current catalog.', 'DATA_WRITE_SETUP_REQUIRED', 503)
        self.adapter.inputs(dataset, target, step)
        self.manager.configured()
        try:
            config = json.loads(self.manager.cipher.decrypt(secret.encode()))
        except Exception:
            fail('Source credentials are unavailable.', 'DATA_WRITE_SETUP_REQUIRED', 503)
        context_hash = fingerprint([policy, connection['generation'], connection['metadata_revision'], dataset])
        return dict(dataset=dataset, target=target, config=config, context_hash=context_hash,
                    label=dataset_label({**dataset, 'connection': connection}))

    def cleanup(self, db):
        now = time.time()
        db.execute('UPDATE data_write_operations SET secret=NULL WHERE recovery_until<=? AND secret IS NOT NULL', (now,))
        db.execute('DELETE FROM data_write_operations WHERE created<? AND state<>?', (now-30*86400, 'running'))
        db.execute('DELETE FROM database_workflow_operations WHERE operation_id NOT IN (SELECT operation_id FROM data_write_operations)')

    def row(self, db, auth, operation_id):
        identity = self.identity(auth)
        if not isinstance(operation_id, str) or not re.fullmatch(r'dbop_[a-f0-9]{32}', operation_id):
            fail('Database operation not found.', 'DATA_WRITE_NOT_FOUND', 404)
        row = db.execute('SELECT state,secret,summary,started,token,recovery_of FROM data_write_operations WHERE operation_id=? AND workspace=? AND owner=?', (operation_id, *identity)).fetchone()
        if not row:
            fail('Database operation not found.', 'DATA_WRITE_NOT_FOUND', 404)
        return row

    def document(self, row):
        if not row[1]:
            fail('Encrypted operation evidence expired. Reconciliation must be performed independently.', 'DATA_WRITE_EXPIRED', 410)
        return json.loads(self.manager.cipher.decrypt(row[1].encode()))

    def get(self, auth, operation_id, details=True):
        with self.store.transaction() as db:
            self.cleanup(db)
            row = self.row(db, auth, operation_id)
            value = json.loads(row[2])
            recovery = db.execute('SELECT operation_id FROM data_write_operations WHERE recovery_of=?', (operation_id,)).fetchone()
            origin = db.execute('SELECT run_id,workflow_id FROM database_workflow_operations WHERE operation_id=?', (operation_id,)).fetchone()
        value.update(preview_available=False, recovery_operation_id=recovery[0] if recovery else None)
        if origin:
            value.update(workflow_run_id=origin[0], workflow_id=origin[1])
        if value['state'] == 'prepared' and value['expires_at'] <= time.time():
            value['state'] = 'expired'
        if value['state'] == 'running' and row[3] and row[3]+180 < time.time():
            value['state'] = 'uncertain'
        if details and row[1]:
            payload = self.document(row)
            try:
                for step in payload['steps']:
                    self.guard(auth, step)
                value['preview_available'] = True
                for summary, step in zip(value['steps'], payload['steps']):
                    allowed = set(step['target']['identity_fields'] + step['target']['writable_fields'])
                    summary.update(identity=step['request']['identity'], values=step['request']['values'],
                                   unset_fields=step['request']['unset_fields'])
                    for name in ('before', 'after'):
                        record = public_record(step.get(name))
                        summary[name] = {k: v for k, v in record.items() if k in allowed} if record is not None else None
            except ApiFailure:
                pass
        validate('operation', value)
        return value

    def status(self, auth):
        workspace, owner = self.identity(auth)
        policy = self.policy()
        targets = []
        for target in policy['targets']:
            if (target['workspace_id'], target['subject_id']) != (workspace, owner):
                continue
            for action in target['operations']:
                # Catalog discovery does not require a fabricated key value.
                with self.store.transaction(write=False) as db:
                    _, connection = self.manager.owned(db, auth, target['connection_id'])
                    row = db.execute('SELECT document FROM data_source_snapshots WHERE connection_id=? AND revision=?',
                                     (target['connection_id'], connection['metadata_revision'])).fetchone()
                dataset = next((d for d in json.loads(row[0])['datasets'] if d['dataset_id'] == target['dataset_id']), None) if row else None
                if not dataset or connection['connection_status'] != 'connected':
                    break
                entry = next((t for t in targets if t['dataset_id'] == dataset['dataset_id'] and t['connection_id'] == target['connection_id']), None)
                if entry is None:
                    entry = dict(connection_id=target['connection_id'], dataset_id=target['dataset_id'],
                                 label=dataset_label({**dataset, 'connection': connection}), engine=connection['engine'],
                                 identity_fields=target['identity_fields'], writable_fields=target['writable_fields'], operations=[])
                    targets.append(entry)
                try:
                    self.identity(auth, action != 'read')
                    if ('workspace:read' if action == 'read' else 'workspace:write') in auth.get('scopes', []):
                        entry['operations'].append(action)
                except ApiFailure:
                    pass
        with self.store.transaction() as db:
            self.cleanup(db)
            rows = db.execute('SELECT operation_id FROM data_write_operations WHERE workspace=? AND owner=? ORDER BY created DESC LIMIT 20', (workspace, owner)).fetchall()
        return dict(configured=bool(policy['targets']), targets=[t for t in targets if t['operations']],
                    items=[self.get(auth, r[0], details=False) for r in rows],
                    tools=[{k: v for k, v in tool_definition(engine, action).items() if k in ('tool_id', 'provider_id', 'capability', 'approval_required')}
                           for engine in ('postgresql', 'mongodb') for action in ('create', 'read', 'update', 'delete')])

    def read(self, auth, body):
        validate('read', body)
        step = dict(body, action='read', values={}, unset_fields=[])
        context = self.context(auth, step)
        operation_id = 'dbread_'+secrets.token_hex(16)
        registered_grant(auth, context['config']['engine'], 'read', body['connection_id'], body['dataset_id'], operation_id, 0)
        audit_step = dict(tool_id=tool_definition(context['config']['engine'], 'read')['tool_id'], state='running', matched_records=0, affected_records=0)
        workspace, owner = self.identity(auth)
        with self.store.transaction() as db:
            count = db.execute("SELECT count(*) FROM data_write_audit WHERE workspace=? AND owner=? AND tool_id=? AND state='running' AND created>?", (workspace, owner, audit_step['tool_id'], time.time()-60)).fetchone()[0]
            if count >= 20:
                fail('This database tool reached its per-minute limit.', 'DATA_WRITE_LIMIT', 429)
            self.audit(db, auth, operation_id, 0, audit_step)
        try:
            record = self.adapter.read(context['config'], context['dataset'], context['target'], step)
            self.guard(auth, dict(request=step, context_hash=context['context_hash']))
        except Exception:
            with self.store.transaction() as db:
                audit_step['state'] = 'failed'
                self.audit(db, auth, operation_id, 0, audit_step)
            raise
        allowed = set(context['target']['identity_fields'] + context['target']['writable_fields'])
        values = public_record(record)
        with self.store.transaction() as db:
            self.manager.audit(db, auth, body['connection_id'], 'point_record_read')
            audit_step.update(state='succeeded', matched_records=int(record is not None))
            self.audit(db, auth, operation_id, 0, audit_step)
        return dict(record={k: v for k, v in values.items() if k in allowed} if values is not None else None, matched_records=int(record is not None), label=context['label'])

    def guard(self, auth, step):
        context = self.context(self.current(auth), step['request'])
        if context['context_hash'] != step['context_hash']:
            fail('Source metadata, credentials or policy changed. Prepare a fresh operation.', 'DATA_WRITE_STALE', 409)
        return context

    def prepare(self, auth, body, key, expected=None, recovery_of=None, workflow_origin=None):
        workspace, owner = self.identity(auth, True)
        validate('prepare', body)
        if not isinstance(key, str) or not re.fullmatch(r'[A-Za-z0-9_-]{8,128}', key):
            fail('A stable 8–128 character Idempotency-Key is required.')
        request_hash, retry_key = fingerprint([body, recovery_of]), fingerprint(key)
        with self.store.transaction() as db:
            self.cleanup(db)
            prior = db.execute('SELECT operation_id,request_hash FROM data_write_operations WHERE workspace=? AND owner=? AND retry_key=?', (workspace, owner, retry_key)).fetchone()
        if prior:
            if prior[1] != request_hash:
                fail('This idempotency key belongs to a different intent.', 'DATA_WRITE_IDEMPOTENCY_CONFLICT', 409)
            return self.get(auth, prior[0])
        payload, seen = dict(steps=[]), set()
        operation_id = 'dbop_'+secrets.token_hex(16)
        now = time.time()
        summary = dict(operation_id=operation_id, state='prepared', created_at=now, expires_at=now+600,
                       recovery_until=now+86400, recovery_of=recovery_of, recovery_operation_id=None,
                       preview_available=False, steps=[])
        for index, request in enumerate(body['steps']):
            context = self.context(auth, request)
            identity, _ = self.adapter.inputs(context['dataset'], context['target'], request)
            unique = fingerprint([request['connection_id'], request['dataset_id'], pack(identity, context['config']['engine'])])
            if unique in seen:
                fail('Each group step must target a distinct record identity.')
            seen.add(unique)
            before = self.adapter.read(context['config'], context['dataset'], context['target'], request)
            self.adapter.expected(before, before, request['action'])
            if expected is not None and fingerprint(before) != fingerprint(expected[index]):
                fail('A committed after-image changed; guarded recovery cannot proceed.', 'DATA_WRITE_CONFLICT', 409)
            if request['action'] == 'delete':
                if not set(before or {}) <= set(context['target']['identity_fields'] + context['target']['writable_fields']):
                    fail('Deletion recovery requires all record fields to be permitted.')
                inverse = dict(request, action='create', values={k: v for k, v in public_record(before).items() if k not in request['identity']})
                self.adapter.inputs(context['dataset'], context['target'], inverse)
            if request['action'] == 'update':
                restore = {k: v for k, v in public_record(before).items() if k in set(request['values']) | set(request['unset_fields'])}
                self.adapter.inputs(context['dataset'], context['target'], dict(request, values=restore,
                                   unset_fields=[k for k in set(request['values']) | set(request['unset_fields']) if k not in before]))
            stored = dict(request=request, before=before, after=None, target=context['target'], context_hash=context['context_hash'])
            self.guard(auth, stored)
            payload['steps'].append(stored)
            summary['steps'].append(dict(action=request['action'], connection_id=request['connection_id'], dataset_id=request['dataset_id'], label=context['label'],
                                         tool_id=tool_definition(context['config']['engine'], request['action'])['tool_id'],
                                         state='pending', matched_records=0, affected_records=0, error_code=None))
        for step in payload['steps']:
            self.guard(auth, step)
        with self.store.transaction() as db:
            prior = db.execute('SELECT operation_id,request_hash FROM data_write_operations WHERE workspace=? AND owner=? AND retry_key=?', (workspace, owner, retry_key)).fetchone()
            recovery = db.execute('SELECT operation_id FROM data_write_operations WHERE recovery_of=?', (recovery_of,)).fetchone() if recovery_of else None
            if prior:
                if prior[1] != request_hash:
                    fail('This idempotency key belongs to a different intent.', 'DATA_WRITE_IDEMPOTENCY_CONFLICT', 409)
                operation_id = prior[0]
            elif recovery:
                operation_id = recovery[0]
            else:
                count = db.execute('SELECT count(*) FROM data_write_operations WHERE workspace=? AND owner=? AND recovery_until>?', (workspace, owner, now)).fetchone()[0]
                if count >= 100:
                    fail('The daily retained operation capacity is full.', 'DATA_WRITE_LIMIT', 429)
                secret = self.manager.cipher.encrypt(json.dumps(payload).encode()).decode()
                db.execute('INSERT INTO data_write_operations VALUES (?,?,?,?,?,?,?,?,?,NULL,NULL,?,?,?)',
                           (operation_id, workspace, owner, retry_key, request_hash, 'prepared', now, now+600, now+86400, secret, json.dumps(summary), recovery_of))
            if workflow_origin:
                origin = (operation_id, workspace, owner, *workflow_origin)
                existing = db.execute('SELECT operation_id,workspace,owner,run_id,workflow_id,version,invocation,request_hash FROM database_workflow_operations WHERE operation_id=?', (operation_id,)).fetchone()
                if existing and existing != origin:
                    fail('This operation already belongs to another workflow invocation.', 'DATABASE_WORKFLOW_REPLAY', 409)
                if not existing:
                    db.execute('INSERT INTO database_workflow_operations VALUES (?,?,?,?,?,?,?,?)', origin)
        return self.get(auth, operation_id)

    def audit(self, db, auth, operation_id, index, step):
        workspace, owner = self.identity(auth)
        db.execute('INSERT INTO data_write_audit VALUES (?,?,?,?,?,?,?,?,?,?)', (secrets.token_hex(16), workspace, owner,
                   operation_id, index, step['tool_id'], step['state'], step['matched_records'], step['affected_records'], time.time()))

    def execute(self, auth, operation_id, body):
        validate('execute', body)
        workspace, owner = self.identity(auth, True)
        if self.workflow_authorize is not None:
            self.workflow_authorize(operation_id)
        token = secrets.token_hex(16)
        with self.store.transaction() as db:
            row = self.row(db, auth, operation_id)
            linked = db.execute('SELECT operation_id FROM database_workflow_operations WHERE operation_id=?', (operation_id,)).fetchone()
            if linked and self.workflow_authorize is None:
                fail('This operation requires approval and execution through its originating workflow.', 'DATABASE_WORKFLOW_APPROVAL', 403)
            if row[0] != 'prepared':
                value = json.loads(row[2])
                value['preview_available'] = False
                if row[0] == 'running' and row[3] and row[3]+180 < time.time():
                    value['state'] = 'uncertain'
                return value
            summary = json.loads(row[2])
            if summary['expires_at'] <= time.time():
                fail('The prepared operation expired.', 'DATA_WRITE_EXPIRED', 410)
            payload = self.document(row)
            running = db.execute("SELECT count(*) FROM data_write_operations WHERE state='running' AND started>?", (time.time()-180,)).fetchone()[0]
            if running >= 4:
                fail('Database operation concurrency is full.', 'DATA_WRITE_LIMIT', 429)
            summary['state'] = 'running'
            db.execute("UPDATE data_write_operations SET state='running',started=?,token=?,summary=? WHERE operation_id=?", (time.time(), token, json.dumps(summary), operation_id))
        deadline = time.monotonic()+90
        def guard(step):
            if time.monotonic() >= deadline:
                fail('The operation deadline elapsed before commit.', 'DATA_WRITE_TIMEOUT', 409)
            return self.guard(auth, step)

        for index, step in enumerate(payload['steps']):
            public = summary['steps'][index]
            step_deadline = min(deadline, time.monotonic()+30)
            def source_guard():
                if time.monotonic() >= step_deadline:
                    fail('The tool deadline elapsed before commit.', 'DATA_WRITE_TIMEOUT', 409)
                return guard(step)
            try:
                context = source_guard()
                current = self.current(auth)
                registered_grant(current, context['config']['engine'], public['action'], public['connection_id'], public['dataset_id'], operation_id, index)
                with self.store.transaction() as db:
                    count = db.execute("SELECT count(*) FROM data_write_audit WHERE workspace=? AND owner=? AND tool_id=? AND state='running' AND created>?", (workspace, owner, public['tool_id'], time.time()-60)).fetchone()[0]
                    if count >= 20:
                        fail('This database tool reached its per-minute limit.', 'DATA_WRITE_LIMIT', 429)
                    self.audit(db, auth, operation_id, index, dict(public, state='approved'))
                    public['state'] = 'running'
                    db.execute('UPDATE data_write_operations SET summary=? WHERE operation_id=? AND token=?', (json.dumps(summary), operation_id, token))
                    self.audit(db, auth, operation_id, index, public)
                result = self.adapter.mutate(context['config'], context['dataset'], context['target'], step['request'], step['before'], source_guard)
                step['after'] = result['after']
                public.update(state='succeeded', matched_records=result['matched_records'], affected_records=result['affected_records'])
            except UncertainWrite:
                public.update(state='uncertain', error_code='DATA_WRITE_UNCERTAIN')
            except (RolledBack, ApiFailure) as exc:
                public.update(state='failed', error_code=exc.code)
            # A storage publication failure after source commit deliberately leaves
            # the durable running claim. It must not become a retryable failure.
            if public['state'] != 'succeeded':
                summary['state'] = 'uncertain' if public['state'] == 'uncertain' else ('partial' if any(s['state'] == 'succeeded' for s in summary['steps']) else 'failed')
            elif index == len(payload['steps'])-1:
                summary['state'] = 'succeeded'
            with self.store.transaction() as db:
                db.execute('UPDATE data_write_operations SET state=?,secret=?,summary=? WHERE operation_id=? AND token=?',
                           (summary['state'], self.manager.cipher.encrypt(json.dumps(payload).encode()).decode(), json.dumps(summary), operation_id, token))
                self.audit(db, auth, operation_id, index, public)
            if public['state'] != 'succeeded':
                break
        return self.get(auth, operation_id)

    def recover(self, auth, operation_id, key):
        self.identity(auth, True)
        with self.store.transaction(write=False) as db:
            row = self.row(db, auth, operation_id)
            existing = db.execute('SELECT operation_id FROM data_write_operations WHERE recovery_of=?', (operation_id,)).fetchone()
        if existing:
            return self.get(auth, existing[0])
        if row[0] not in ('succeeded', 'partial') or row[5]:
            fail('Only known committed original operations can be compensated; uncertain effects require independent reconciliation.', 'DATA_WRITE_RECOVERY_BLOCKED', 409)
        summary = json.loads(row[2])
        if summary['recovery_until'] <= time.time():
            fail('The encrypted recovery window expired.', 'DATA_WRITE_EXPIRED', 410)
        payload = self.document(row)
        requests, expected = [], []
        for step, outcome in reversed(list(zip(payload['steps'], summary['steps']))):
            if outcome['state'] != 'succeeded' or outcome['affected_records'] == 0:
                continue
            self.guard(auth, step)
            original = step['request']
            inverse = dict(original, action={'create': 'delete', 'update': 'update', 'delete': 'create'}[original['action']], values={}, unset_fields=[])
            if original['action'] == 'delete':
                inverse['values'] = {k: v for k, v in public_record(step['before']).items() if k not in original['identity']}
            elif original['action'] == 'update':
                changed = set(original['values']) | set(original['unset_fields'])
                inverse['values'] = {k: v for k, v in public_record(step['before']).items() if k in changed}
                inverse['unset_fields'] = sorted(changed - set(step['before']))
            requests.append(inverse)
            expected.append(step['after'])
        if not requests:
            fail('No known committed step is available for compensation.', 'DATA_WRITE_RECOVERY_BLOCKED', 409)
        return self.prepare(auth, dict(steps=requests), key, expected=expected, recovery_of=operation_id)
