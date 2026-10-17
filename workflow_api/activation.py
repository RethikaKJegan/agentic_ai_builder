"""Durable activation saga. Provider operations never run in a database transaction."""
from copy import deepcopy
import json
import re
from uuid import uuid4


def _helpers():
    from .lifecycle import LifecycleFailure, identifier, json_digest, now_iso
    return LifecycleFailure, identifier, json_digest, now_iso


def _snapshot(lifecycle, db, workspace, workflow_id, version, expected):
    Failure, _, digest, _ = _helpers()
    if db.execute('SELECT 1 FROM lifecycle_tombstones WHERE workspace=? AND workflow_id=?', (workspace, workflow_id)).fetchone():
        raise Failure('WORKFLOW_DELETED', 'A deleted workflow cannot be published.', 410)
    row = db.execute('SELECT release_id FROM lifecycle_active WHERE workspace=? AND workflow_id=?', (workspace, workflow_id)).fetchone()
    if (row[0] if row else None) != expected:
        raise Failure('RELEASE_CONFLICT', 'The active release changed. Reload before publishing.')
    workflow = lifecycle.store.get(db, workspace, workflow_id, version)
    if not workflow or workflow['status'] != 'published' or workflow.get('metadata', {}).get('validation_state') != 'validated':
        raise Failure('REVISION_NOT_PUBLISHED', 'Activate a validated, approved, published revision.')
    return workflow, digest(workflow)


def _read_preparation(lifecycle, db, operation_id):
    row = db.execute('SELECT document FROM lifecycle_preparations WHERE operation_id=?', (operation_id,)).fetchone()
    return json.loads(row[0]) if row else None


def _save_preparation(lifecycle, db, preparation):
    db.execute('UPDATE lifecycle_preparations SET document=? WHERE operation_id=?', (json.dumps(preparation), preparation['operation_id']))


def cleanup_release(lifecycle, release_id):
    """Idempotent compensation; state remains denied throughout external cleanup."""
    with lifecycle.store.transaction(write=False) as db:
        rows = db.execute("SELECT binding_id, document FROM lifecycle_triggers WHERE release_id=? AND state='cleanup_pending'", (release_id,)).fetchall()
    for binding_id, document in rows:
        try:
            cleaned = lifecycle.adapter.cleanup(json.loads(document)) is True
        except Exception:
            cleaned = False
        if cleaned:
            trigger = json.loads(document)
            trigger['health'] = 'disabled'
            with lifecycle.store.transaction() as db:
                db.execute("UPDATE lifecycle_triggers SET state='disabled', document=? WHERE binding_id=? AND release_id=? AND state='cleanup_pending'", (json.dumps(trigger), binding_id, release_id))
    with lifecycle.store.transaction(write=False) as db:
        pending = db.execute("SELECT 1 FROM lifecycle_triggers WHERE release_id=? AND state='cleanup_pending'", (release_id,)).fetchone()
    return not pending


def abort_preparation(lifecycle, preparation, failure):
    with lifecycle.store.transaction() as db:
        current = _read_preparation(lifecycle, db, preparation['operation_id'])
        if not current or current['state'] == 'succeeded':
            return
        current['state'], current['expires_at'] = 'failed', None
        _save_preparation(lifecycle, db, current)
        row = db.execute('SELECT document FROM lifecycle_operations WHERE operation_id=?', (current['operation_id'],)).fetchone()
        operation = json.loads(row[0])
        operation['state'], operation['error_code'] = 'cleanup_pending', failure.code
        lifecycle.save_operation(db, operation)
        release_row = db.execute('SELECT document FROM lifecycle_releases WHERE release_id=?', (current['release_id'],)).fetchone()
        release = json.loads(release_row[0]);release['state'] = 'failed'
        db.execute("UPDATE lifecycle_releases SET state='failed', document=? WHERE release_id=?", (json.dumps(release), current['release_id']))
        for binding_id, encoded in db.execute('SELECT binding_id, document FROM lifecycle_triggers WHERE release_id=?', (current['release_id'],)).fetchall():
            trigger = json.loads(encoded);trigger['health'] = 'cleanup_pending'
            db.execute("UPDATE lifecycle_triggers SET state='cleanup_pending', document=? WHERE binding_id=?", (json.dumps(trigger), binding_id))
    if cleanup_release(lifecycle, preparation['release_id']):
        with lifecycle.store.transaction() as db:
            row = db.execute('SELECT document FROM lifecycle_operations WHERE operation_id=?', (preparation['operation_id'],)).fetchone()
            operation = json.loads(row[0]);operation['state'] = 'failed'
            lifecycle.save_operation(db, operation)
            lifecycle.emit(db, preparation['workspace'], preparation['workflow_id'], 'release.preparation_failed')


def activate(lifecycle, request, auth):
    Failure, identifier, digest, now_iso = _helpers()
    from registry.safety import reject_secrets
    lifecycle.authorize(auth, 'workflow.publish')
    payload, key = request.get('payload', {}), request.get('idempotency_key')
    workflow_id, version, expected = payload.get('workflow_id'), payload.get('workflow_version'), payload.get('expected_release_id')
    triggers = payload.get('triggers', [])
    if not isinstance(workflow_id, str) or type(version) is not int or not isinstance(triggers, list) or len(triggers) > 64:
        raise Failure('INVALID_REQUEST', 'Activation requires an exact revision and at most 64 trigger bindings.', 400)
    reject_secrets(payload)
    workspace = auth['subject']['workspace_id']
    fingerprint = digest({'kind': 'activate_release', 'payload': payload})
    if not isinstance(key,str) or not re.fullmatch(r'[a-zA-Z0-9_-]{8,128}',key):
        raise Failure('INVALID_IDEMPOTENCY_KEY','Use a retry key of 8-128 safe characters.',400)
    with lifecycle.store.transaction(write=False) as db:
        existing=db.execute('SELECT fingerprint,document FROM lifecycle_operations WHERE workspace=? AND subject=? AND idempotency_key=?',(workspace,auth['subject']['subject_id'],key)).fetchone()
        if existing:
            if existing[0]!=fingerprint:
                raise Failure('IDEMPOTENCY_KEY_REUSED','This retry key belongs to another lifecycle request.')
            operation=json.loads(existing[1])
            if operation['state'] in {'failed','cleanup_pending'}:
                raise Failure(operation.get('error_code') or 'ACTIVATION_FAILED','This activation did not complete. Inspect its operation and cleanup state.')
            return {'operation':operation,'release':lifecycle._release_for_operation(db,operation)}
        # The first snapshot is read-only and short. Reservation revalidates it.
        workflow, workflow_digest = _snapshot(lifecycle, db, workspace, workflow_id, version, expected)
    validator = getattr(lifecycle.workflows, 'configuration_validator', None)
    if validator:
        validator(workflow)
    triggers = triggers or deepcopy(workflow.get('metadata', {}).get('trigger_templates', []))
    if len(triggers) > 64:
        raise Failure('INVALID_REQUEST', 'A release supports at most 64 trigger bindings.', 400)
    review = lifecycle.workflows.registry_adapter.review(workflow, auth)
    if not review['ready']:
        raise Failure('ASSIGNMENT_REVALIDATION_FAILED', 'Registry grants are not currently authorized.', 403)
    grants = lifecycle.workflows.registry_adapter.execution_assignments(workflow, auth)
    preparation = None
    with lifecycle.store.transaction() as db:
        operation, replay = lifecycle.operation(db, workspace, auth, 'activate_release', key, workflow_id, expected, fingerprint)
        if replay:
            if operation['state'] in {'failed', 'cleanup_pending'}:
                raise Failure(operation.get('error_code') or 'ACTIVATION_FAILED', 'This activation did not complete. Inspect its operation and cleanup state.')
            return {'operation': operation, 'release': lifecycle._release_for_operation(db, operation)}
        current, current_digest = _snapshot(lifecycle, db, workspace, workflow_id, version, expected)
        if current_digest != workflow_digest:
            raise Failure('REVISION_CONFLICT', 'The published revision changed during activation.')
        release_id, identity_id = identifier('rel_'), identifier('auto_')
        generation = db.execute('SELECT COALESCE(MAX(generation),0)+1 FROM lifecycle_releases WHERE workspace=? AND workflow_id=?', (workspace, workflow_id)).fetchone()[0]
        identity = dict(identity_id=identity_id, subject_id='automation:' + workflow_id, workspace_id=workspace,
                        scopes=['workflow.execute','trigger.dispatch'], policy_version=max([g.get('policy_version',1) for g in grants] or [1]), active=False)
        authority = deepcopy(auth);authority['subject'] = {'subject_id': identity['subject_id'], 'workspace_id': workspace}
        authority['_registry_assignment_subject'], authority['_registry_approval_auth'] = deepcopy(auth['subject']), deepcopy(auth)
        authority['roles'] = ['admin'];authority['permissions'] = sorted(set(authority['permissions']) | {'workflow.execute','runs.view'})
        bindings = [lifecycle._normalize_trigger(workspace, release_id, workflow_id, raw, index) for index,raw in enumerate(triggers)]
        release = dict(release_id=release_id,workspace_id=workspace,revision=dict(workflow_id=workflow_id,workflow_version=version),state='preparing',generation=generation,
                       automation_identity_id=identity_id,agent_versions={i['agent_id']:i.get('agent_version',1) for i in review['items']},
                       tool_versions={i['tool_id']:i.get('tool_version',1) for i in review['items'] if i.get('tool_id')},policy_version=identity['policy_version'],
                       trigger_binding_ids=[b['binding_id'] for b in bindings],created_at=now_iso(lifecycle.clock))
        db.execute('INSERT INTO lifecycle_releases VALUES (?,?,?,?,?,?,?)', (workspace,release_id,workflow_id,version,generation,'preparing',json.dumps(release)))
        db.execute('INSERT INTO lifecycle_identities VALUES (?,?,?,?)', (workspace,identity_id,json.dumps(authority),json.dumps(identity)))
        for binding in bindings:
            db.execute('INSERT INTO lifecycle_triggers VALUES (?,?,?,?,?,?,?)', (workspace,binding['binding_id'],release_id,workflow_id,'preparing',None,json.dumps(binding)))
        preparation = dict(operation_id=operation['operation_id'],workspace=workspace,workflow_id=workflow_id,release_id=release_id,owner=uuid4().hex,
                           workflow_digest=workflow_digest,review_digest=digest(review),state='preparing',expires_at=lifecycle.clock()+1800)
        db.execute('INSERT INTO lifecycle_preparations VALUES (?,?,?)', (operation['operation_id'],workspace,json.dumps(preparation)))
    try:
        for binding in bindings:
            trigger_validator = getattr(lifecycle.workflows, 'trigger_configuration_validator', None)
            if trigger_validator:
                trigger_validator(binding, workflow, auth)
            if binding['provider_id'] == 'generic_hmac_webhook' and not lifecycle.trigger_secrets.get(binding.get('credential_reference')):
                raise Failure('TRIGGER_CONFIGURATION_REQUIRED', 'Configure the server webhook signing secret before activation.', 400)
            reference = lifecycle.adapter.prepare(deepcopy(binding))
            with lifecycle.store.transaction() as db:
                current = _read_preparation(lifecycle,db,preparation['operation_id'])
                if current['state'] != 'preparing' or current['owner'] != preparation['owner']:
                    raise Failure('ACTIVATION_INTERRUPTED','The activation preparation is no longer owned by this operation.')
                binding['health'] = 'ready'
                db.execute("UPDATE lifecycle_triggers SET provider_reference=?, document=? WHERE binding_id=? AND release_id=? AND state='preparing'", (reference,json.dumps(binding),binding['binding_id'],release_id))
        if validator:
            validator(workflow)
        lifecycle.authorize(auth,'workflow.publish')
        refreshed = lifecycle.workflows.registry_adapter.review(workflow,auth)
        if not refreshed['ready'] or digest(refreshed) != preparation['review_digest']:
            raise Failure('ASSIGNMENT_REVALIDATION_FAILED','Registry policy or authorization changed during preparation.',403)
        with lifecycle.store.transaction() as db:
            current = _read_preparation(lifecycle,db,preparation['operation_id'])
            if current['state'] != 'preparing' or current['owner'] != preparation['owner'] or current['expires_at'] <= lifecycle.clock():
                raise Failure('ACTIVATION_INTERRUPTED','The activation preparation expired or changed.')
            _, current_digest = _snapshot(lifecycle,db,workspace,workflow_id,version,expected)
            if current_digest != preparation['workflow_digest']:
                raise Failure('REVISION_CONFLICT','The published revision changed during preparation.')
            # Registry review is in-memory validation, not a connector/network call.
            if digest(lifecycle.workflows.registry_adapter.review(workflow,auth)) != preparation['review_digest']:
                raise Failure('ASSIGNMENT_REVALIDATION_FAILED','Registry policy changed before activation.',403)
            release['state'],identity['active'] = 'active',True
            db.execute("UPDATE lifecycle_releases SET state='active',document=? WHERE release_id=?",(json.dumps(release),release_id))
            db.execute('UPDATE lifecycle_identities SET document=? WHERE identity_id=?',(json.dumps(identity),identity_id))
            db.execute("UPDATE lifecycle_triggers SET state='ready' WHERE release_id=? AND state='preparing'",(release_id,))
            db.execute('INSERT INTO lifecycle_active VALUES (?,?,?) ON CONFLICT(workspace,workflow_id) DO UPDATE SET release_id=excluded.release_id',(workspace,workflow_id,release_id))
            if expected:
                for table,key,field in [('lifecycle_releases','release_id','state'),('lifecycle_triggers','binding_id','health')]:
                    for identity_key,encoded in db.execute(f'SELECT {key},document FROM {table} WHERE release_id=?',(expected,)).fetchall():
                        previous=json.loads(encoded);previous[field]='disabled'
                        db.execute(f"UPDATE {table} SET state='disabled',document=? WHERE {key}=?",(json.dumps(previous),identity_key))
            operation['state']='succeeded';lifecycle.save_operation(db,operation)
            current['state'],current['expires_at']='succeeded',None;_save_preparation(lifecycle,db,current)
            lifecycle.emit(db,workspace,workflow_id,'release.activated')
        return {'operation':operation,'release':release}
    except Exception as exc:
        failure=exc if isinstance(exc,Failure) else Failure('PROVIDER_ACTIVATION_FAILED','Provider registration failed.',502)
        abort_preparation(lifecycle,preparation,failure)
        raise failure from None


def reconcile(lifecycle,workspace):
    Failure,_,_,_=_helpers()
    with lifecycle.store.transaction(write=False) as db:
        preparations=[json.loads(row[0]) for row in db.execute("SELECT document FROM lifecycle_preparations WHERE workspace=? AND json_extract(document,'$.state')='preparing'",(workspace,)).fetchall()]
    repaired=[]
    for preparation in preparations:
        if preparation['state']=='preparing' and preparation['expires_at']<=lifecycle.clock():
            abort_preparation(lifecycle,preparation,Failure('ACTIVATION_INTERRUPTED','Activation was interrupted.'))
            repaired.append(preparation['operation_id'])
    return repaired


def stop(lifecycle,request,auth,deleting):
    Failure,_,digest,now_iso=_helpers()
    from .lifecycle import ACTIVE_RUN_STATES
    permission,kind=('workflow.delete','delete_workflow') if deleting else ('workflow.publish','disable_release')
    lifecycle.authorize(auth,permission)
    payload,key=request.get('payload',{}),request.get('idempotency_key')
    workflow_id,expected=payload.get('workflow_id'),payload.get('expected_release_id')
    if deleting and payload.get('confirmed') is not True:
        raise Failure('DELETE_CONFIRMATION_REQUIRED','Confirm deletion explicitly.',400)
    workspace=auth['subject']['workspace_id'];fingerprint=digest({'kind':kind,'payload':payload})
    with lifecycle.store.transaction() as db:
        operation,replayed=lifecycle.operation(db,workspace,auth,kind,key,workflow_id,expected,fingerprint)
        if replayed:
            return {'operation':operation}
        row=db.execute('SELECT release_id FROM lifecycle_active WHERE workspace=? AND workflow_id=?',(workspace,workflow_id)).fetchone()
        active_id=row[0] if row else None
        if deleting and active_id is None and expected is not None:
            row=db.execute('SELECT release_id FROM lifecycle_releases WHERE workspace=? AND workflow_id=? ORDER BY generation DESC LIMIT 1',(workspace,workflow_id)).fetchone()
            active_id=row[0] if row else None
        if expected!=active_id:
            raise Failure('RELEASE_CONFLICT','The active release changed. Reload before continuing.')
        if active_id:
            row=db.execute('SELECT document FROM lifecycle_releases WHERE release_id=?',(active_id,)).fetchone()
            release=json.loads(row[0]);release['state']='deleting' if deleting else 'disabled'
            db.execute('UPDATE lifecycle_releases SET state=?,document=? WHERE release_id=?',(release['state'],json.dumps(release),active_id))
            for binding_id,encoded in db.execute('SELECT binding_id,document FROM lifecycle_triggers WHERE release_id=?',(active_id,)).fetchall():
                trigger=json.loads(encoded);trigger['health']='cleanup_pending'
                db.execute("UPDATE lifecycle_triggers SET state='cleanup_pending',document=? WHERE binding_id=?",(json.dumps(trigger),binding_id))
            db.execute('DELETE FROM lifecycle_active WHERE workspace=? AND workflow_id=?',(workspace,workflow_id))
        rows=db.execute("SELECT job_id,document FROM lifecycle_jobs WHERE workspace=? AND workflow_id=? AND state IN ('queued','leased')",(workspace,workflow_id)).fetchall()
        for job_id,encoded in rows:
            job=json.loads(encoded);job['state'],job['lease_until']='cancelled',None
            db.execute("UPDATE lifecycle_jobs SET state='cancelled',lease_until=NULL,document=? WHERE job_id=?",(json.dumps(job),job_id))
        if deleting:
            db.execute('INSERT INTO lifecycle_tombstones VALUES (?,?,?,?) ON CONFLICT(workspace,workflow_id) DO UPDATE SET cleanup_state=excluded.cleanup_state',(workspace,workflow_id,now_iso(lifecycle.clock),'pending' if active_id else 'complete'))
            identities=db.execute('SELECT identity_id,document FROM lifecycle_identities WHERE workspace=?',(workspace,)).fetchall()
            release_ids={json.loads(r[0])['automation_identity_id'] for r in db.execute('SELECT document FROM lifecycle_releases WHERE workspace=? AND workflow_id=?',(workspace,workflow_id)).fetchall()}
            for identity_id,encoded in identities:
                if identity_id not in release_ids:continue
                identity=json.loads(encoded);identity['active']=False
                db.execute('UPDATE lifecycle_identities SET document=? WHERE identity_id=?',(json.dumps(identity),identity_id))
            if lifecycle.workflows.runtime_runner is not None and lifecycle._table(db,'runtime_runs'):
                runtime=lifecycle.workflows.runtime_runner.runtime
                for encoded, in db.execute('SELECT document FROM runtime_runs WHERE workspace=? AND workflow_id=?',(workspace,workflow_id)).fetchall():
                    run=json.loads(encoded)
                    if run['status'] in ACTIVE_RUN_STATES:runtime.transition(db,run,'cancelled')
        operation['state']='cleanup_pending' if active_id else 'succeeded';lifecycle.save_operation(db,operation)
        lifecycle.emit(db,workspace,workflow_id,'workflow.deleted' if deleting else 'release.disabled')
    cleaned=not active_id or cleanup_release(lifecycle,active_id)
    if cleaned and active_id:
        with lifecycle.store.transaction() as db:
            operation['state']='succeeded';lifecycle.save_operation(db,operation)
            if deleting:db.execute("UPDATE lifecycle_tombstones SET cleanup_state='complete' WHERE workspace=? AND workflow_id=?",(workspace,workflow_id))
    return {'operation':operation}


def reconcile_cleanup(lifecycle,workspace):
    with lifecycle.store.transaction(write=False) as db:
        rows=db.execute("SELECT DISTINCT release_id FROM lifecycle_triggers WHERE workspace=? AND state='cleanup_pending'",(workspace,)).fetchall()
        before={r[0] for r in db.execute("SELECT binding_id FROM lifecycle_triggers WHERE workspace=? AND state='cleanup_pending'",(workspace,)).fetchall()}
    if not rows:return []
    for release_id, in rows:cleanup_release(lifecycle,release_id)
    with lifecycle.store.transaction() as db:
        remaining={r[0] for r in db.execute("SELECT binding_id FROM lifecycle_triggers WHERE workspace=? AND state='cleanup_pending'",(workspace,)).fetchall()}
        for encoded, in db.execute('SELECT document FROM lifecycle_operations WHERE workspace=?',(workspace,)).fetchall():
            operation=json.loads(encoded)
            if operation['state']!='cleanup_pending':continue
            if db.execute("SELECT 1 FROM lifecycle_triggers WHERE workspace=? AND workflow_id=? AND state='cleanup_pending'",(workspace,operation['workflow_id'])).fetchone():continue
            operation['state']='failed' if operation.get('error_code') else 'succeeded';lifecycle.save_operation(db,operation)
            db.execute("UPDATE lifecycle_tombstones SET cleanup_state='complete' WHERE workspace=? AND workflow_id=?",(workspace,operation['workflow_id']))
    return sorted(before-remaining)
