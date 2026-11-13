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
        # Trusted launcher policy, never accepted from workflow metadata/inputs.
        self.enforce_usage_budgets = True
        self.workflows, self.store, self.clock = workflows, workflows.store, clock
        with self.store.transaction() as db:
            db.execute('CREATE TABLE IF NOT EXISTS runtime_runs (workspace TEXT, run_id TEXT PRIMARY KEY, workflow_id TEXT, version INTEGER, subject TEXT, retry_key TEXT, fingerprint TEXT, document TEXT NOT NULL, UNIQUE(workspace, subject, retry_key))')
            db.execute('CREATE INDEX IF NOT EXISTS runtime_runs_workspace_workflow ON runtime_runs(workspace, workflow_id)')
            db.execute("CREATE INDEX IF NOT EXISTS runtime_runs_pending ON runtime_runs(json_extract(document,'$.status')) WHERE json_extract(document,'$.status') IN ('queued','running','paused_for_approval')")
            db.execute('CREATE TABLE IF NOT EXISTS runtime_trace_exports (observer TEXT, sequence INTEGER, PRIMARY KEY(observer, sequence))')
            db.execute('CREATE TABLE IF NOT EXISTS runtime_events (sequence INTEGER PRIMARY KEY AUTOINCREMENT, workspace TEXT, run_id TEXT, document TEXT NOT NULL)')
            db.execute('CREATE INDEX IF NOT EXISTS runtime_events_workspace_run_sequence ON runtime_events(workspace,run_id,sequence)')
            db.execute('CREATE TABLE IF NOT EXISTS runtime_action_effects (workspace TEXT, run_id TEXT, action_key TEXT, state TEXT NOT NULL, reference TEXT NOT NULL, document TEXT NOT NULL, PRIMARY KEY(workspace,run_id,action_key))')
        from .memory import WorkingMemory, ExperienceMemory
        from .recovery import RecoveryService
        self.working_memory = WorkingMemory(self)
        self.experience_memory = ExperienceMemory(self)
        self.recovery = RecoveryService(self)
        from .governance import GovernancePolicy
        self.governance = GovernancePolicy(self)

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
        if db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='lifecycle_tombstones'").fetchone() and db.execute('SELECT 1 FROM lifecycle_tombstones WHERE workspace=? AND workflow_id=?',(workspace,workflow_id)).fetchone():
            raise RuntimeFailure('WORKFLOW_DELETED','Deleted workflows cannot execute.',410)
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
        selection=document.get('metadata',{}).get('ontology_selection_id')
        if selection:
            ontology=getattr(getattr(getattr(self.workflows,'database_workflows',None),'manager',None),'ontology_foundation',None)
            if ontology is None:raise RuntimeFailure('ONTOLOGY_UNAVAILABLE','Ontology service unavailable.',503)
            try:ontology.validate_selection(db,auth,selection)
            except Exception as exc:
                from workflow_api.service import ApiFailure
                if isinstance(exc,ApiFailure):raise RuntimeFailure(exc.code,str(exc),exc.status) from None
                raise
        from workflow_api.business_preparation import verify_workflow_pin
        from workflow_api.service import ApiFailure
        try:
            verify_workflow_pin(db,auth,document)
            from workflow_api.business_composition import verify_composition
            verify_composition(db,auth,document)
        except ApiFailure as exc:raise RuntimeFailure(exc.code,str(exc),exc.status) from None
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

    def execution_revision(self, db, run, auth):
        approved, grants = self.revision(db, run['workflow_id'], run['workflow_version'], auth, run.get('release_bound', False))
        if digest(approved) != run['workflow_digest']:
            raise RuntimeFailure('REVISION_CHANGED', 'The approved revision changed after execution was queued.')
        from workflow_api.workflow_adaptive import effective
        workflow = effective(run, approved)
        self.governance.check_run(db, run, workflow)
        return workflow, grants

    def create_run(self, request, auth, *, on_created=None):
        # Trusted in-process persistence hook; never accepted from an API payload.
        return self._create_run(request, auth, allow_superseded=False, on_created=on_created)

    def create_automation_run(self, request, auth, *, on_created=None):
        """Trusted lifecycle entry point for a job pinned to an immutable release."""
        return self._create_run(request, auth, allow_superseded=True, on_created=on_created)

    def _create_run(self, request, auth, allow_superseded, on_created=None):
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
                existing = json.loads(row[1])
                if on_created is not None:on_created(db, deepcopy(existing))
                return self.public(existing)
            if controls:=getattr(self,'resource_controls',None):controls.admit(db,workspace)
            if validator := getattr(self, 'execution_validator', None):
                validator(workflow, auth, db)
            run = dict(run_id='run_' + uuid4().hex, workflow_id=workflow['workflow_id'], workflow_version=workflow['version'],
                       status='queued', approvals=[], workflow_digest=digest(workflow), workspace_id=workspace, subject_id=subject,
                       inputs=deepcopy(payload.get('inputs', {})), outputs={}, node_states={}, edge_states={}, usage={},
                       created_at=self.clock(), correlation_id='corr_' + uuid4().hex, trace_reference='trace_' + uuid4().hex,
                       request_id=request['request_id'], release_bound=allow_superseded)
            run['governance_policy'] = self.governance.read(db, workspace)
            from workflow_api.workflow_adaptive import initialize
            initialize(run, workflow)
            previous=db.execute("SELECT document FROM runtime_runs WHERE workspace=? AND subject=? AND workflow_id=? AND version=? AND json_extract(document,'$.status') IN ('failed','blocked') ORDER BY rowid DESC LIMIT 1",(workspace,subject,workflow['workflow_id'],workflow['version'])).fetchone()
            if previous:
                from .recovery import failure_feedback
                hints=failure_feedback(json.loads(previous[0]))
                if hints:run['previous_failure_feedback']=hints
            selection=workflow.get('metadata',{}).get('ontology_selection_id')
            if selection:
                ontology=self.workflows.database_workflows.manager.ontology_foundation
                ontology.bind(db,auth,selection,workflow['workflow_id'],workflow['version'],run['run_id'])
            db.execute('INSERT INTO runtime_runs VALUES (?, ?, ?, ?, ?, ?, ?, ?)',
                       (workspace, run['run_id'], run['workflow_id'], run['workflow_version'], subject, digest(key), fingerprint, json.dumps(run)))
            self.event(db, run, 'run.queued', {'status': 'queued'})
            if on_created is not None:on_created(db, deepcopy(run))
            return self.public(run)

    @staticmethod
    def public(run):
        result = {key: deepcopy(run[key]) for key in ('run_id', 'workflow_id', 'workflow_version', 'status', 'approvals', 'correlation_id', 'trace_reference')}
        if run.get('adaptive'):
            a = run['adaptive']
            result['adaptive'] = {k:deepcopy(a[k]) for k in ('objective','status','revision','turns','assessment','pending_wait','decisions','revisions','blocker','deterministic_limitations') if k in a}
        return result

    def expire_runs(self):
        """Expire queued, active and approval-waiting work, including live leases."""
        with self.store.transaction() as db:
            rows = db.execute("SELECT document FROM runtime_runs WHERE json_extract(document,'$.status') IN ('queued','running','paused_for_approval')").fetchall()
            for row in rows:
                run = json.loads(row[0])
                workflow = self.store.get(db, run['workspace_id'], run['workflow_id'], run['workflow_version'])
                if not workflow:
                    continue
                try:
                    self.check_deadlines(run, workflow)
                except RuntimeFailure as error:
                    run['error_code'] = error.code
                    run['lease_until'] = 0
                    for approval in run.get('approvals', []):
                        if approval['status'] == 'pending':
                            approval.update(status='timed_out', allowed_decisions=[])
                    self.event(db, run, 'run.timeout', dict(error_code=error.code))
                    self.transition(db, run, 'blocked')

    def cancel_run(self, run_id, auth):
        with self.store.transaction() as db:
            run = self.load(db, run_id, auth, 'workflow.execute')
            if run['subject_id'] != auth['subject']['subject_id'] and 'admin' not in auth['roles']:
                raise RuntimeFailure('SUBJECT_MISMATCH', 'Only the execution owner or an administrator can stop this run.', 403)
            if run['status'] in {'queued', 'running', 'paused_for_approval'}:
                run['cancellation'] = dict(requested_at=self.clock(), requested_by=auth['subject']['subject_id'], reason='user_requested')
                for approval in run.get('approvals', []):
                    if approval['status'] == 'pending':
                        approval.update(status='rejected', allowed_decisions=[])
                run['lease_until'] = 0
                self.event(db, run, 'run.cancellation_requested', dict(actor_id=auth['subject']['subject_id'], reason='user_requested'))
                self.transition(db, run, 'cancelled')
            return self.public(run)

    def _record_revoked_invocation(self, run_id, auth, worker, claim_token):
        # Trusted invocation bookkeeping must survive revocation of the actor.
        # The opaque worker/claim token still fences which invocation may stop.
        with self.store.transaction() as db:
            row = db.execute('SELECT document FROM runtime_runs WHERE workspace=? AND subject=? AND run_id=?',
                (auth['subject']['workspace_id'], auth['subject']['subject_id'], run_id)).fetchone()
            if row is None:
                return
            current = json.loads(row[0])
            owns = (current['status'] in {'queued', 'running'} and current.get('adaptive', {}).get('claim', {}).get('token') == claim_token) if claim_token else self.owns_execution(current, worker)
            if owns:
                current['error_code'] = 'OPERATION_NOT_AUTHORIZED'
                current['lease_until'] = 0
                self.event(db, current, 'runtime.denied', dict(error_code='OPERATION_NOT_AUTHORIZED'))
                self.transition(db, current, 'blocked')

    def invoke_guarded(self, run_id, auth, worker, invoke, *, agent=None, kind='model', adapter=None, reference=None, claim_token=None, tool_node=None, effect_schema=None):
        from .execution_control import guarded_call, model_limits_required, policy_resolver, retry_reserver
        def check():
            current_auth = auth
            if authenticate := getattr(self, 'authenticate_current', None):
                current_auth = authenticate(auth['subject']['workspace_id'], auth['subject']['subject_id'])
                if current_auth is None or current_auth['subject'] != auth['subject']:
                    raise RuntimeFailure('OPERATION_NOT_AUTHORIZED', 'Execution authority was revoked.', 403)
            with self.store.transaction(write=False) as db:
                run = self.load(db, run_id, current_auth, 'workflow.execute')
                owns = (run['status'] in {'queued', 'running'} and run.get('adaptive', {}).get('claim', {}).get('token') == claim_token) if claim_token else self.owns_execution(run, worker)
                if not owns:
                    raise RuntimeFailure('EXECUTION_STOPPED', 'Execution was stopped or its lease changed.')
                workflow, _ = self.execution_revision(db, run, current_auth)
                self.check_deadlines(run, workflow, agent)
                self.governance.check_run(db, run, workflow)
                if tool_node is not None:
                    from .graph import GraphRunner
                    self.governance.check_tool(run, workflow, tool_node, adapter, {}, GraphRunner.params(tool_node, run, workflow, now=self.clock()))
            return run, workflow
        try:
            run, workflow = check()
        except RuntimeFailure as error:
            if error.code == 'OPERATION_NOT_AUTHORIZED':
                self._record_revoked_invocation(run_id, auth, worker, claim_token)
            raise
        timeout = self.governance.invocation_timeout(run, workflow, agent, kind)
        if kind == 'tool':
            timeout = min(timeout, getattr(adapter, 'timeout', float('inf')))
        cancel_method = getattr(adapter, 'cancel_invocation', None)
        cancel = (lambda: cancel_method(reference)) if callable(cancel_method) else None
        original_invoke = invoke
        action_key = None
        if kind == 'tool' and getattr(adapter, 'external_write', False):
            from .graph import GraphRunner
            params = GraphRunner.params(tool_node, run, workflow, now=self.clock())
            action_key = digest(dict(tool_id=tool_node['tool_id'], params=params, workflow_digest=run['workflow_digest']))
            def invoke():
                check()
                with self.store.transaction() as db:
                    row = db.execute('SELECT state,document FROM runtime_action_effects WHERE workspace=? AND run_id=? AND action_key=?', (run['workspace_id'], run_id, action_key)).fetchone()
                    if row:
                        if row[0] == 'completed':
                            receipt = json.loads(row[1])
                            if digest(receipt['output']) != receipt['output_sha256']:
                                raise RuntimeFailure('ACTION_RECEIPT_INVALID', 'The saved action receipt changed.')
                            return receipt['output']
                        raise RuntimeFailure('ACTION_OUTCOME_UNKNOWN', 'This exact action was already submitted. Reconcile its provider outcome before retrying.')
                    db.execute('INSERT INTO runtime_action_effects VALUES (?,?,?,?,?,?)', (run['workspace_id'], run_id, action_key, 'submitted', reference, '{}'))
                output = original_invoke()
                if effect_schema is None or list(Draft202012Validator(effect_schema).iter_errors(output)):
                    raise RuntimeFailure('ACTION_EFFECT_UNVERIFIED', 'The submitted action did not return a valid receipt.')
                reject_secrets(output)
                with self.store.transaction() as db:
                    db.execute('UPDATE runtime_action_effects SET state=?,document=? WHERE workspace=? AND run_id=? AND action_key=? AND reference=?', ('completed', json.dumps(dict(output=output, output_sha256=digest(output))), run['workspace_id'], run_id, action_key, reference))
                    stored = json.loads(db.execute('SELECT document FROM runtime_runs WHERE workspace=? AND run_id=?', (run['workspace_id'], run_id)).fetchone()[0])
                    stored['uncertain_effects'] = [item for item in stored.get('uncertain_effects', []) if item.get('effect_reference') != reference]
                    self.event(db, stored, 'action.receipt_recorded', dict(effect_reference=reference, action_key=action_key, outcome='confirmed'))
                    self.save(db, stored)
                return output
        def reserve_correction():
            if 'max_retries' not in self.governance.effective(run)['limits']:
                return
            check()
            with self.store.transaction() as db:
                saved = self.load(db, run_id, auth, 'workflow.execute')
                owns = (saved['status'] in {'queued', 'running'} and saved.get('adaptive', {}).get('claim', {}).get('token') == claim_token) if claim_token else self.owns_execution(saved, worker)
                if not owns:
                    raise RuntimeFailure('EXECUTION_STOPPED', 'The run no longer owns this correction.')
                reviewed, _ = self.execution_revision(db, saved, auth)
                from .graph import GraphRunner
                GraphRunner(self).reserve(db, saved, reviewed, agent, {'retries': 1})
                self.save(db, saved)
        retry_marker = retry_reserver.set(reserve_correction)
        policy_marker = policy_resolver.set(lambda: self.governance.effective(run))
        marker = model_limits_required.set('max_tokens' in self.governance.effective(run)['limits'])
        try:
            return guarded_call(check, invoke, timeout=timeout, timeout_code=kind.upper() + '_TIMEOUT', cancel=cancel)
        except RuntimeFailure as error:
            if error.code == 'OPERATION_NOT_AUTHORIZED':
                self._record_revoked_invocation(run_id, auth, worker, claim_token)
            # Preserve unknown external outcomes even after cancellation fenced the worker.
            if getattr(adapter, 'external_write', False):
                with self.store.transaction() as db:
                    stored = json.loads(db.execute('SELECT document FROM runtime_runs WHERE workspace=? AND run_id=?', (run['workspace_id'], run_id)).fetchone()[0])
                    receipt = db.execute('SELECT state,reference FROM runtime_action_effects WHERE workspace=? AND run_id=? AND action_key=?', (run['workspace_id'], run_id, action_key)).fetchone()
                    if not receipt or receipt[0] == 'completed':
                        raise
                    original_reference = receipt[1]
                    self.event(db, stored, 'action.reconciliation_required', dict(error_code=error.code, effect_reference=original_reference, outcome='unknown'))
                    if not any(item.get('effect_reference') == original_reference for item in stored.get('uncertain_effects', [])):
                        stored.setdefault('uncertain_effects', []).append(dict(effect_reference=original_reference, outcome='unknown'))
                    self.save(db, stored)
            raise
        finally:
            retry_reserver.reset(retry_marker)
            policy_resolver.reset(policy_marker)
            model_limits_required.reset(marker)

    def owns_execution(self, run, worker):
        """An owner token is executable authority only while its lease is live."""
        return (run['status'] == 'running' and run.get('worker') == worker
                and run.get('lease_until', 0) > self.clock())

    def check_deadlines(self, run, workflow, agent=None):
        now = self.clock()
        policy = self.governance.effective(run)
        limit = min(workflow['execution_policy']['limits']['timeout_seconds'], policy['limits'].get('timeout_seconds', float('inf')))
        if now - run['created_at'] >= limit:
            raise RuntimeFailure('RUN_TIMEOUT', 'The workflow duration budget is exhausted.')
        if agent and now - run.get('agent_started_at', {}).get(agent['agent_id'], now) >= agent['limits']['timeout_seconds']:
            raise RuntimeFailure('AGENT_TIMEOUT', 'The agent execution duration budget is exhausted.')

    def load(self, db, run_id, auth, permission='runs.view'):
        self.authorize(auth, permission, {'admin', 'builder', 'viewer', 'approver'} if permission == 'runs.view' else {'admin', 'builder'})
        row = db.execute('SELECT document FROM runtime_runs WHERE workspace=? AND run_id=?' + (' FOR UPDATE' if getattr(db,'write',False) else ''), (auth['subject']['workspace_id'], run_id)).fetchone()
        if row is None:
            raise RuntimeFailure('RUN_NOT_FOUND', 'The run was not found in this workspace.', 404)
        return json.loads(row[0])

    def event(self, db, run, event_type, details):
        # Details are application-created metadata, never provider/input content.
        reject_secrets(details)
        event = dict(event_id='evt_' + uuid4().hex, run_id=run['run_id'], workflow_id=run['workflow_id'],
                     workflow_version=run['workflow_version'], timestamp=datetime.fromtimestamp(self.clock(), timezone.utc).isoformat(),
                     source='runtime', event_type=event_type, details={**details, 'correlation_id': run['correlation_id'], 'trace_reference': run['trace_reference'], 'workspace_id': run['workspace_id'], 'actor_id': details.get('actor_id', run['subject_id'])})
        Draft202012Validator(schema('run_status')['properties']['run_event']).validate(event)
        db.execute('INSERT INTO runtime_events(workspace, run_id, document) VALUES (?, ?, ?)', (run['workspace_id'], run['run_id'], json.dumps(event)))

    def transition(self, db, run, target):
        if target not in TRANSITIONS[run['status']]:
            raise RuntimeFailure('INVALID_RUN_TRANSITION', 'The requested run transition is not legal.')
        run['status'] = target
        if target in {'completed', 'failed', 'blocked', 'cancelled', 'rejected'}:
            run['finished_at'] = self.clock()
        if run.get('adaptive',{}).get('kind')=='workflow-investigation' and target in {'failed','blocked','cancelled','rejected'}:
            run['adaptive']['status']=target
        if target in {'completed','failed','blocked','cancelled','rejected'}:
            from .recovery import evaluate_run
            workflow = self.store.get(db, run['workspace_id'], run['workflow_id'], run['workflow_version']) or {'nodes': []}
            run['outcome_evaluation'] = evaluate_run(run, workflow, self.clock())
            if graph:=getattr(self.workflows,'account_graph',None):graph.record_execution(db,run,workflow)
        self.event(db, run, 'run.' + target, {'status': target})
        self.save(db, run)

    @staticmethod
    def save(db, run):
        reject_secrets(run)
        db.execute('UPDATE runtime_runs SET document=? WHERE run_id=? AND workspace=?', (json.dumps(run), run['run_id'], run['workspace_id']))

    def get_run(self, run_id, auth):
        with self.store.transaction(write=False) as db:
            from .history import public_run
            return public_run(self, db, self.load(db, run_id, auth), auth)

    def list_runs(self, auth, limit=100, status=None, **filters):
        from .history import runs
        return runs(self, auth, limit=limit, status=status, **filters)

    def list_approvals(self, auth, pending_only=False, limit=100):
        self.authorize(auth, 'runs.view', {'admin', 'builder', 'viewer', 'approver'})
        workspace = auth['subject']['workspace_id']
        with self.store.transaction(write=False) as db:
            rows = db.execute('SELECT document FROM runtime_runs WHERE workspace=? ORDER BY rowid DESC LIMIT ?', (workspace, min(max(int(limit), 1), 500))).fetchall()
        items = []
        for row in rows:
            run = json.loads(row[0])
            for approval in run.get('approvals', []):
                if not pending_only or approval.get('status') == 'pending':
                    items.append({**approval, 'run_id': run['run_id']})
        return {'items': items, 'total': len(items), 'has_more': False, 'next_cursor': None}

    def events(self, run_id, auth, limit=100, after_sequence=0):
        from .history import events
        return events(self, run_id, auth, limit, after_sequence)

    def monitoring(self, auth, **options):
        from .history import monitoring
        return monitoring(self, auth, **options)

    def export_traces(self, observer_id='default', limit=100):
        """Export committed events. Export failure never permits a side effect.

        Export is at least once on a crash after delivery, with event_id for
        consumer deduplication. No uncommitted run events reach the exporter.
        """
        if self.observer is None:
            return 0
        with self.store.transaction(write=False) as db:
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
