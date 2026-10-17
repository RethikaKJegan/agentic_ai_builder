"""Bounded, workspace-scoped runtime reads. Cursors are positions, never authority."""
from datetime import datetime, timezone
import json
import re
from .service import RuntimeFailure, TRANSITIONS

ROLES = {'admin', 'builder', 'viewer', 'approver'}
TERMINAL = {'completed', 'failed', 'blocked', 'rejected', 'cancelled'}


def integer(value, minimum=0, maximum=9223372036854775807):
    if isinstance(value, bool) or not re.fullmatch(r'[0-9]{1,19}', str(value)):
        raise RuntimeFailure('INVALID_REQUEST', 'Use a valid non-negative history cursor or limit.', 400)
    result = int(value)
    if not minimum <= result <= maximum:
        raise RuntimeFailure('INVALID_REQUEST', 'History cursor or limit is outside the supported range.', 400)
    return result


def query_options(query, kind):
    allowed = {'limit', 'after_sequence'} if kind == 'events' else {'limit', 'cursor', 'workflow_id', 'status', 'from_date', 'to_date', 'pending_only'}
    if kind == 'monitoring':
        allowed = {'limit', 'source_cursor', 'policy_cursor'}
    if set(query) - allowed - {'request_id'}:
        raise RuntimeFailure('INVALID_REQUEST', 'This history filter is unsupported.', 400)
    result = {key: value for key, value in query.items() if key in allowed}
    for name in {'limit', 'cursor', 'after_sequence', 'source_cursor', 'policy_cursor'} & result.keys():
        result[name] = integer(result[name], 1 if name == 'limit' else 0, 500 if name == 'limit' else 9223372036854775807)
    if 'pending_only' in result:
        if result['pending_only'] not in {'true', 'false'}:
            raise RuntimeFailure('INVALID_REQUEST', 'Use true or false for pending approvals.', 400)
        result['pending_only'] = result['pending_only'] == 'true'
    return result


def public_run(runtime, db, run, auth):
    result = runtime.public(run)
    for key in ('created_at', 'finished_at'):
        if isinstance(run.get(key), (int, float)):
            result[key] = run[key]
    workflow = None
    gates_by_approval = {}
    if result['approvals']:
        for encoded, in db.execute("SELECT document FROM runtime_events WHERE workspace=? AND run_id=? AND json_extract(document,'$.event_type')='approval.pending' ORDER BY sequence", (run['workspace_id'], run['run_id'])):
            details = json.loads(encoded).get('details', {})
            gates_by_approval[details.get('approval_id')] = details.get('node_id')
    for approval in result['approvals']:
        if workflow is None:
            workflow = runtime.store.get(db, run['workspace_id'], run['workflow_id'], run['workflow_version']) or {}
        context = run.get('approval_context', {})
        node_id = gates_by_approval.get(approval['approval_id'])
        node = next((n for n in workflow.get('nodes', []) if n['node_id'] == node_id), None)
        gate_id = node.get('approval_gate_id') if node else context.get('gate_id') if approval['status'] == 'pending' else None
        gate = next((g for g in workflow.get('approval_gates', []) if g['approval_gate_id'] == gate_id), None)
        roles = gate['approver_roles'] if gate else []
        approval['required_roles'] = roles
        eligible = (gate and auth.get('decision') == 'allow' and 'workflow.approve' in auth.get('permissions', [])
                    and bool(set(auth.get('roles', [])) & set(roles))
                    and bool(set(auth.get('scopes', [])) & {'workspace:read', 'workspace:write'}))
        if not eligible or approval['status'] != 'pending':
            approval['allowed_decisions'] = []
    return result


def date_value(value, end=False):
    try:
        parsed = datetime.fromisoformat(value.replace('Z', '+00:00'))
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.timestamp()
    except (ValueError, TypeError, OverflowError):
        raise RuntimeFailure('INVALID_REQUEST', 'Use an ISO date or timestamp for run filters.', 400) from None


def runs(runtime, auth, limit=100, status=None, cursor=None, workflow_id=None, from_date=None, to_date=None, pending_only=False):
    runtime.authorize(auth, 'runs.view', ROLES)
    limit = integer(limit, 1, 500)
    clauses, values = ['workspace=?'], [auth['subject']['workspace_id']]
    if status:
        if status not in TRANSITIONS:
            raise RuntimeFailure('INVALID_REQUEST', 'Choose a supported run status.', 400)
        clauses.append("json_extract(document,'$.status')=?"); values.append(status)
    if workflow_id:
        if not isinstance(workflow_id, str) or len(workflow_id) > 256:
            raise RuntimeFailure('INVALID_REQUEST', 'Use a valid workflow filter.', 400)
        clauses.append('workflow_id=?'); values.append(workflow_id)
    for value, operator in [(from_date, '>='), (to_date, '<=')]:
        if value:
            clauses.append("CAST(json_extract(document,'$.created_at') AS DOUBLE PRECISION)" + operator + '?')
            values.append(date_value(value))
    if from_date and to_date and date_value(from_date) > date_value(to_date):
        raise RuntimeFailure('INVALID_REQUEST', 'The start date must precede the end date.', 400)
    if pending_only:
        # Pending approval runs remain visible even if their gate has expired;
        # the decision endpoint owns expiration and rejects stale decisions.
        clauses.append("json_extract(document,'$.status')='paused_for_approval'")
    base = ' AND '.join(clauses)
    with runtime.store.transaction(write=False) as db:
        total = db.execute('SELECT COUNT(*) FROM runtime_runs WHERE ' + base, values).fetchone()[0]
        if cursor is not None:
            clauses.append('rowid<?'); values.append(integer(cursor))
        rows = db.execute('SELECT rowid,document FROM runtime_runs WHERE ' + ' AND '.join(clauses) + ' ORDER BY rowid DESC LIMIT ?', (*values, limit + 1)).fetchall()
        page = rows[:limit]
        items = [public_run(runtime, db, json.loads(row[1]), auth) for row in page]
    more = len(rows) > limit
    return dict(items=items, total=total, has_more=more, next_cursor=str(page[-1][0]) if more else None)


def events(runtime, run_id, auth, limit=100, after_sequence=0):
    limit, after = integer(limit, 1, 500), integer(after_sequence)
    with runtime.store.transaction(write=False) as db:
        runtime.load(db, run_id, auth)
        values = (auth['subject']['workspace_id'], run_id, after)
        rows = db.execute('SELECT sequence,document FROM runtime_events WHERE workspace=? AND run_id=? AND sequence>? ORDER BY sequence LIMIT ?', (*values, limit + 1)).fetchall()
        total = db.execute('SELECT COUNT(*) FROM runtime_events WHERE workspace=? AND run_id=? AND sequence>?', values).fetchone()[0]
    items = []
    for sequence, encoded in rows[:limit]:
        event = json.loads(encoded)
        event['details'] = {**event.get('details', {}), 'recorded_sequence': sequence}
        items.append(event)
    more = len(rows) > limit
    return dict(items=items, total=total, has_more=more, next_cursor=str(rows[limit - 1][0]) if more else None)


def monitoring(runtime, auth, limit=50, source_cursor=None, policy_cursor=None):
    runtime.authorize(auth, 'runs.view', ROLES)
    workspace = auth['subject']['workspace_id']; limit = integer(limit, 1, 500)
    source_after = integer(source_cursor or 0)
    policy_after = integer(policy_cursor or 0)
    usage_keys = ['llm_calls', 'tool_calls', 'tokens', 'retries', 'estimated_cost_usd']
    with runtime.store.transaction(write=False) as db:
        counts = db.execute("SELECT json_extract(document,'$.status'),COUNT(*) FROM runtime_runs WHERE workspace=? GROUP BY json_extract(document,'$.status')", (workspace,)).fetchall()
        by_status = {status: 0 for status in TRANSITIONS}; by_status.update(dict(counts))
        sums = ','.join("COALESCE(SUM(CAST(json_extract(document,'$.usage.workflow." + key + "') AS DOUBLE PRECISION)),0)" for key in usage_keys)
        usage = dict(zip(usage_keys, db.execute('SELECT '+sums+' FROM runtime_runs WHERE workspace=?', (workspace,)).fetchone()))
        duration = db.execute("SELECT COUNT(*),COALESCE(AVG(CAST(json_extract(document,'$.finished_at') AS DOUBLE PRECISION)-CAST(json_extract(document,'$.created_at') AS DOUBLE PRECISION)),0) FROM runtime_runs WHERE workspace=? AND json_extract(document,'$.finished_at') IS NOT NULL", (workspace,)).fetchone()
        latest = [runtime.public(json.loads(row[0])) for row in db.execute('SELECT document FROM runtime_runs WHERE workspace=? ORDER BY rowid DESC LIMIT 20', (workspace,))]
        count = db.execute('SELECT COUNT(*) FROM runtime_events WHERE workspace=?', (workspace,)).fetchone()[0]
        audit = [json.loads(row[0]) for row in db.execute('SELECT document FROM runtime_events WHERE workspace=? ORDER BY sequence DESC LIMIT 30', (workspace,))]
        sources, policies = [], []
        if db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='lifecycle_triggers'").fetchone():
            rows = db.execute('SELECT t.rowid,t.workflow_id,t.state,t.document,r.document FROM lifecycle_triggers t JOIN lifecycle_releases r ON r.release_id=t.release_id AND r.workspace=t.workspace WHERE t.workspace=? AND t.rowid>? ORDER BY t.rowid LIMIT ?', (workspace, source_after, limit + 1)).fetchall()
            for position, workflow_id, state, encoded, release_doc in rows[:limit]:
                trigger, release = json.loads(encoded), json.loads(release_doc)
                checkpoint = db.execute('SELECT updated_at FROM lifecycle_checkpoints WHERE workspace=? AND binding_id=?', (workspace, trigger['binding_id'])).fetchone()
                sources.append(dict(workflow_id=workflow_id, binding_id=trigger['binding_id'], provider_id=trigger['provider_id'], state=state,
                    release_state=release['state'], workflow_version=release['revision']['workflow_version'], delivery=trigger['delivery'],
                    event_type=trigger['event_type'], source=trigger['resource_id'], schedule=trigger.get('schedule'), timezone=trigger.get('timezone'),
                    preparation_succeeded=state == 'ready' and trigger.get('health') not in {'preparing','cleanup_pending'},
                    health=trigger.get('health', state), error_code=trigger.get('last_error_code'), baseline_ready=checkpoint is not None,
                    last_successful_poll=checkpoint[0] if checkpoint else None))
            source_more = len(rows) > limit
            source_cursor = str(rows[limit-1][0]) if source_more else None
        else:
            source_more, source_cursor = False, None
        # Only approved/published revisions are enforced candidates. Drafts are
        # explicitly excluded. Read a bounded page, never all workflow documents.
        rows = db.execute("SELECT r.rowid,r.document FROM revisions r WHERE r.workspace=? AND r.rowid>? AND json_extract(r.document,'$.status') IN ('approved','published') AND r.version=(SELECT MAX(x.version) FROM revisions x WHERE x.workspace=r.workspace AND x.workflow_id=r.workflow_id AND json_extract(x.document,'$.status') IN ('approved','published')) ORDER BY r.rowid LIMIT ?", (workspace, policy_after, limit + 1)).fetchall()
        for position, encoded in rows[:limit]:
            workflow = json.loads(encoded)
            active = None
            if db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='lifecycle_active'").fetchone():
                active = db.execute('SELECT r.version,r.document FROM lifecycle_active a JOIN lifecycle_releases r ON r.release_id=a.release_id WHERE a.workspace=? AND a.workflow_id=?', (workspace, workflow['workflow_id'])).fetchone()
            # Effective active policy can be older than the newest draft/publication.
            if active:
                workflow = runtime.store.get(db, workspace, workflow['workflow_id'], active[0])
            policies.append(dict(workflow_id=workflow['workflow_id'], version=workflow['version'], scope='workspace:'+workspace,
                enforcement='active_release' if active else 'approved_revision', policy_version=json.loads(active[1])['policy_version'] if active else None,
                action_approval_required=bool(workflow.get('approval_gates')),
                agents=[{key: agent.get(key) for key in ('agent_id','guardrails','limits','approval_requirements')} for agent in workflow['agents']]))
        policy_more = len(rows) > limit
        policy_cursor = str(rows[limit-1][0]) if policy_more else None
    return dict(runs=dict(total=sum(by_status.values()), active=sum(by_status[s] for s in ('queued','running','paused_for_approval')), completed=by_status['completed'], failed=by_status['failed']+by_status['blocked']),
        status_breakdown=by_status, duration_seconds=dict(count=duration[0],avg=max(0,float(duration[1]))), events=count, usage=usage, latest=latest,
        sources=sources, policies=policies, source_next_cursor=source_cursor, policy_next_cursor=policy_cursor,
        audit=[{key:event.get(key) for key in ('event_id','event_type','run_id','timestamp')} for event in audit])
