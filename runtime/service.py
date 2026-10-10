"""Durable execution boundary; persisted data never supplies authority."""
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
import re
import time
from uuid import uuid4

from jsonschema import Draft202012Validator
from registry.contracts import schema, validate
from registry.safety import reject_secrets


class RuntimeFailure(Exception):
    def __init__(self, code, message, status=409):
        super().__init__(message)
        self.code, self.status = code, status


TRANSITIONS = {
    'queued': {'running', 'failed', 'blocked', 'cancelled'},
    'running': {'paused_for_approval', 'completed', 'failed', 'blocked', 'cancelled'},
    'paused_for_approval': {'running', 'rejected', 'failed', 'blocked', 'cancelled'},
    'completed': set(), 'failed': set(), 'rejected': set(), 'blocked': set(), 'cancelled': set(),
}


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, allow_nan=False).encode()).hexdigest()


class RuntimeService:
    """Inject trusted current auth into every worker invocation, never from storage."""
    def __init__(self, workflows, clock=time.time, observer=None):
        self.observer = observer
        self.workflows, self.store, self.clock = workflows, workflows.store, clock
        with self.store.transaction() as db:
            db.execute('CREATE TABLE IF NOT EXISTS runtime_runs (workspace TEXT, run_id TEXT PRIMARY KEY, workflow_id TEXT, version INTEGER, subject TEXT, retry_key TEXT, fingerprint TEXT, document TEXT NOT NULL, UNIQUE(workspace, subject, retry_key))')
            db.execute('CREATE TABLE IF NOT EXISTS runtime_trace_exports (observer TEXT, sequence INTEGER, PRIMARY KEY(observer, sequence))')
            db.execute('CREATE TABLE IF NOT EXISTS runtime_events (sequence INTEGER PRIMARY KEY AUTOINCREMENT, workspace TEXT, run_id TEXT, document TEXT NOT NULL)')

    @staticmethod
    def authorize(auth, permission, roles):
        # Lifecycle-only context is not part of the canonical auth contract.
        # It remains available for exact Registry assignment reconstruction.
        validate({k: v for k, v in auth.items() if k not in
                  {'_registry_assignment_subject', '_registry_approval_auth'}}, 'auth')
        if (auth['decision'] != 'allow' or permission not in auth['permissions'] or
                not set(auth['roles']) & set(roles) or not all(auth['subject'].values())):
            raise RuntimeFailure('OPERATION_NOT_AUTHORIZED', 'The current subject cannot perform this runtime operation.', 403)

    def revision(self, db, workflow_id, version, auth, allow_superseded=False):
        self.authorize(auth, 'workflow.execute', {'admin', 'builder'})
        workspace = auth['subject']['workspace_id']
        if not isinstance(workflow_id, str) or type(version) is not int or version < 1:
            raise RuntimeFailure('INVALID_REVISION', 'An exact workflow ID and version are required.', 400)
        document = self.store.get(db, workspace, workflow_id, version)
        if document is None:
            raise RuntimeFailure('WORKFLOW_NOT_FOUND', 'The workflow revision was not found.', 404)
        if (document['status'] not in {'approved', 'published'} or
                document['metadata'].get('validation_state') != 'validated' or
                not document['metadata'].get('approved_by') or
                document['metadata'].get('workspace_id') != workspace):
            raise RuntimeFailure('REVISION_NOT_APPROVED', 'Execution requires a reviewed, approved revision.')
        # A newer draft does not change this approved revision. A newer approved
        # revision supersedes manual execution until the release contract is reviewed.
        rows = db.execute('SELECT document FROM revisions WHERE workspace=? AND workflow_id=? AND version>?', (workspace, workflow_id, version)).fetchall()
        if not allow_superseded and any(json.loads(row[0])['status'] in {'approved', 'published'} for row in rows):
            raise RuntimeFailure('STALE_REVISION', 'A newer approved revision exists.')
        self.workflows.validate_document(document)
        reject_secrets(document)
        grants = self.workflows.registry_adapter.execution_assignments(document, auth)
        actual = {(g['agent_id'], g['tool_id']) for g in grants}
        expected = {(a['agent_id'], t) for a in document['agents'] for t in a['allowed_tool_ids']}
        if actual != expected:
            raise RuntimeFailure('ASSIGNMENT_MISMATCH', 'Approved tools do not match current exact registry grants.', 403)
        # A release keeps grants bound to its publisher while recording the
        # automation subject on the run. Manual runs retain exact caller binding.
        assignment_subject = auth['subject']['subject_id']
        if allow_superseded:
            assignment_subject = self.workflows.registry_adapter._assignment_auth(auth)['subject']['subject_id']
        for grant in grants:
            if (grant['authorization_state'] != 'authorized' or
                    grant['subject_id'] != assignment_subject or grant['workspace_id'] != workspace or
                    grant['workflow_id'] != workflow_id or grant['workflow_version'] != version):
                raise RuntimeFailure('ASSIGNMENT_MISMATCH', 'An assignment is outside this execution binding.', 403)
        return document, grants

    @staticmethod
    def validate_inputs(workflow, inputs):
        if not isinstance(inputs, dict):
            raise RuntimeFailure('INVALID_INPUT', 'Execution inputs must be an object.', 400)
        fields = workflow['inputs']
        contract = {'type': 'object', 'properties': {f['name']: {'type': f['type']} for f in fields},
                    'required': [f['name'] for f in fields if f['required']], 'additionalProperties': False}
        if list(Draft202012Validator(contract).iter_errors(inputs)):
            raise RuntimeFailure('INVALID_INPUT', 'Execution inputs do not satisfy workflow fields.', 400)
        reject_secrets(inputs)

    def create_run(self, request, auth):
        return self._create_run(request, auth, allow_superseded=False)

    def create_automation_run(self, request, auth):
        """Trusted lifecycle entry point for a job pinned to an immutable release."""
        return self._create_run(request, auth, allow_superseded=True)

    def _create_run(self, request, auth, allow_superseded):
        self.authorize(auth, 'workflow.execute', {'admin', 'builder'})
        key = request.get('idempotency_key')
        if not isinstance(key, str) or not re.fullmatch(r'[a-zA-Z0-9_-]{8,128}', key):
            raise RuntimeFailure('INVALID_IDEMPOTENCY_KEY', 'Use a retry key of 8–128 safe characters.', 400)
        payload = request['payload']
        if set(payload) - {'workflow_id', 'workflow_version', 'inputs'}:
            raise RuntimeFailure('INVALID_REQUEST', 'Execution payload contains unsupported fields.', 400)
        fingerprint = digest(payload)
        workspace, subject = auth['subject']['workspace_id'], auth['subject']['subject_id']
        with self.store.transaction() as db:
            # Authorize even retries; an idempotent result is not a fresh grant.
            workflow, _ = self.revision(db, payload.get('workflow_id'), payload.get('workflow_version'), auth, allow_superseded)
            self.validate_inputs(workflow, payload.get('inputs', {}))
            row = db.execute('SELECT fingerprint, document FROM runtime_runs WHERE workspace=? AND subject=? AND retry_key=?', (workspace, subject, digest(key))).fetchone()
            if row:
                if row[0] != fingerprint:
                    raise RuntimeFailure('IDEMPOTENCY_KEY_REUSED', 'The retry key identifies different execution inputs.')
                return self.public(json.loads(row[1]))
            run = dict(run_id='run_' + uuid4().hex, workflow_id=workflow['workflow_id'], workflow_version=workflow['version'],
                       status='queued', approvals=[], workflow_digest=digest(workflow), workspace_id=workspace, subject_id=subject,
                       inputs=deepcopy(payload.get('inputs', {})), outputs={}, node_states={}, edge_states={}, usage={},
                       created_at=self.clock(), correlation_id='corr_' + uuid4().hex, trace_reference='trace_' + uuid4().hex,
                       request_id=request['request_id'], release_bound=allow_superseded)
            db.execute('INSERT INTO runtime_runs VALUES (?, ?, ?, ?, ?, ?, ?, ?)',
                       (workspace, run['run_id'], run['workflow_id'], run['workflow_version'], subject, digest(key), fingerprint, json.dumps(run)))
            self.event(db, run, 'run.queued', {'status': 'queued'})
            return self.public(run)

    @staticmethod
    def public(run):
        return {key: deepcopy(run[key]) for key in ('run_id', 'workflow_id', 'workflow_version', 'status', 'approvals', 'correlation_id', 'trace_reference')}

    def load(self, db, run_id, auth, permission='runs.view'):
        self.authorize(auth, permission, {'admin', 'builder', 'viewer', 'approver'} if permission == 'runs.view' else {'admin', 'builder'})
        row = db.execute('SELECT document FROM runtime_runs WHERE workspace=? AND run_id=?', (auth['subject']['workspace_id'], run_id)).fetchone()
        if row is None:
            raise RuntimeFailure('RUN_NOT_FOUND', 'The run was not found in this workspace.', 404)
        return json.loads(row[0])

    def event(self, db, run, event_type, details):
        # Details are application-created metadata, never provider/input content.
        reject_secrets(details)
        event = dict(event_id='evt_' + uuid4().hex, run_id=run['run_id'], workflow_id=run['workflow_id'],
                     workflow_version=run['workflow_version'], timestamp=datetime.fromtimestamp(self.clock(), timezone.utc).isoformat(),
                     source='runtime', event_type=event_type, details={**details, 'correlation_id': run['correlation_id'], 'trace_reference': run['trace_reference']})
        Draft202012Validator(schema('run_status')['properties']['run_event']).validate(event)
        db.execute('INSERT INTO runtime_events(workspace, run_id, document) VALUES (?, ?, ?)', (run['workspace_id'], run['run_id'], json.dumps(event)))

    def transition(self, db, run, target):
        if target not in TRANSITIONS[run['status']]:
            raise RuntimeFailure('INVALID_RUN_TRANSITION', 'The requested run transition is not legal.')
        run['status'] = target
        self.event(db, run, 'run.' + target, {'status': target})
        self.save(db, run)

    @staticmethod
    def save(db, run):
        reject_secrets(run)
        db.execute('UPDATE runtime_runs SET document=? WHERE run_id=? AND workspace=?', (json.dumps(run), run['run_id'], run['workspace_id']))

    def get_run(self, run_id, auth):
        with self.store.transaction() as db:
            return self.public(self.load(db, run_id, auth))

    def list_runs(self, auth, limit=100, status=None):
        self.authorize(auth, 'runs.view', {'admin', 'builder', 'viewer', 'approver'})
        workspace = auth['subject']['workspace_id']
        with self.store.transaction() as db:
            rows = db.execute('SELECT document FROM runtime_runs WHERE workspace=? ORDER BY rowid DESC LIMIT ?', (workspace, min(max(int(limit), 1), 500))).fetchall()
        items = [self.public(json.loads(row[0])) for row in rows]
        if status:
            items = [item for item in items if item['status'] == status]
        return {'items': items, 'total': len(items), 'has_more': len(items) >= min(max(int(limit), 1), 500), 'next_cursor': None}

    def list_approvals(self, auth, pending_only=False, limit=100):
        self.authorize(auth, 'runs.view', {'admin', 'builder', 'viewer', 'approver'})
        workspace = auth['subject']['workspace_id']
        with self.store.transaction() as db:
            rows = db.execute('SELECT document FROM runtime_runs WHERE workspace=? ORDER BY rowid DESC LIMIT ?', (workspace, min(max(int(limit), 1), 500))).fetchall()
        items = []
        for row in rows:
            run = json.loads(row[0])
            for approval in run.get('approvals', []):
                if not pending_only or approval.get('status') == 'pending':
                    items.append({**approval, 'run_id': run['run_id']})
        return {'items': items, 'total': len(items), 'has_more': False, 'next_cursor': None}

    def events(self, run_id, auth):
        with self.store.transaction() as db:
            self.load(db, run_id, auth)
            items = [json.loads(row[0]) for row in db.execute('SELECT document FROM runtime_events WHERE workspace=? AND run_id=? ORDER BY sequence', (auth['subject']['workspace_id'], run_id))]
            return dict(items=items, total=len(items), has_more=False, next_cursor=None)

    def monitoring(self, auth):
        """Return workspace-scoped counters and safe trace references."""
        self.authorize(auth, 'runs.view', {'admin', 'builder', 'viewer', 'approver'})
        workspace = auth['subject']['workspace_id']
        with self.store.transaction() as db:
            runs = [json.loads(row[0]) for row in db.execute('SELECT document FROM runtime_runs WHERE workspace=? ORDER BY rowid DESC', (workspace,))]
            event_count = db.execute('SELECT COUNT(*) FROM runtime_events WHERE workspace=?', (workspace,)).fetchone()[0]
            audit = [json.loads(row[0]) for row in db.execute('SELECT document FROM runtime_events WHERE workspace=? ORDER BY sequence DESC LIMIT 30', (workspace,))]
            sources = []
            if db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='lifecycle_triggers'").fetchone():
                for workflow_id, state, document in db.execute('SELECT workflow_id, state, document FROM lifecycle_triggers WHERE workspace=?', (workspace,)):
                    trigger = json.loads(document)
                    checkpoint = db.execute('SELECT updated_at FROM lifecycle_checkpoints WHERE workspace=? AND binding_id=?', (workspace, trigger['binding_id'])).fetchone()
                    sources.append(dict(workflow_id=workflow_id, binding_id=trigger['binding_id'], provider_id=trigger['provider_id'],
                                        state=state, health=trigger.get('health', state), error_code=trigger.get('last_error_code'),
                                        baseline_ready=checkpoint is not None, last_successful_poll=checkpoint[0] if checkpoint else None))
            policies = []
            for workflow in self.store.list(db, workspace):
                if workflow['status'] not in {'approved', 'published'}:
                    continue
                policies.append(dict(workflow_id=workflow['workflow_id'], version=workflow['version'],
                                     action_approval_required=bool(workflow.get('approval_gates')),
                                     agents=[{key: agent.get(key) for key in ('agent_id', 'guardrails', 'limits', 'approval_requirements')}
                                             for agent in workflow['agents']]))
        usage = {'llm_calls': 0, 'tool_calls': 0, 'tokens': 0, 'retries': 0, 'estimated_cost_usd': 0}
        for run in runs:
            # Workflow counters already include each per-agent reservation.
            counters = run.get('usage', {}).get('workflow', {})
            for key in usage:
                usage[key] += counters.get(key, 0)
        by_status = {status: sum(r['status'] == status for r in runs) for status in ('queued', 'running', 'paused_for_approval', 'completed', 'failed', 'blocked', 'rejected', 'cancelled')}
        durations = [max(0, (r.get('finished_at', r.get('created_at', self.clock())) - r.get('created_at', self.clock()))) for r in runs if isinstance(r.get('finished_at'), (int, float))]
        return {'runs': {'total': len(runs), 'active': sum(r['status'] in {'queued', 'running', 'paused_for_approval'} for r in runs),
                         'completed': sum(r['status'] == 'completed' for r in runs), 'failed': sum(r['status'] in {'failed', 'blocked'} for r in runs)},
                'status_breakdown': by_status, 'duration_seconds': {'count': len(durations), 'avg': sum(durations) / len(durations) if durations else 0},
                'events': event_count, 'usage': usage,
                'sources': sources, 'policies': policies,
                'audit': [{key: event.get(key) for key in ('event_id', 'event_type', 'run_id', 'timestamp')} for event in audit],
                'latest': [self.public(run) for run in runs[:20]]}

    def export_traces(self, observer_id='default', limit=100):
        """Export committed events. Export failure never permits a side effect.

        Export is at least once on a crash after delivery, with event_id for
        consumer deduplication. No uncommitted run events reach the exporter.
        """
        if self.observer is None:
            return 0
        with self.store.transaction() as db:
            rows = db.execute('SELECT sequence, document FROM runtime_events WHERE sequence NOT IN (SELECT sequence FROM runtime_trace_exports WHERE observer=?) ORDER BY sequence LIMIT ?', (observer_id, limit)).fetchall()
        exported = 0
        for sequence, document in rows:
            try:
                self.observer.export(json.loads(document))
            except Exception:
                break
            with self.store.transaction() as db:
                db.execute('INSERT OR IGNORE INTO runtime_trace_exports VALUES (?, ?)', (observer_id, sequence))
            exported += 1
        return exported
