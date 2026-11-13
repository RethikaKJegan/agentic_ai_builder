"""Use workspace restrictions for existing planning and read-only domain jobs.

No execution authority is granted here. Each owning service still validates its
identity, source contracts, checkpoints and cancellation state.
"""
from contextvars import ContextVar
from copy import deepcopy
import json
import time
from .execution_control import guarded_call, _provider_request, model_limits_required, policy_resolver, request_method, retry_reserver
from .service import RuntimeFailure, digest

_operation = ContextVar('runtime_controlled_operation', default=False)


def controlled_operation(service, auth, identifier, invoke, *, active=None, resources=None, created_at=None):
    runtime = getattr(getattr(service, 'runtime_runner', None), 'runtime', None)
    if runtime is None or _operation.get() or active is None and request_method.get() in {'GET', 'HEAD'}:
        return invoke()
    control = runtime.governance
    workspace, owner = auth['subject']['workspace_id'], auth['subject']['subject_id']
    operation_key = digest(identifier)
    with runtime.store.transaction() as db:
        db.execute('CREATE TABLE IF NOT EXISTS runtime_operation_controls (workspace TEXT, owner TEXT, operation_key TEXT, document TEXT NOT NULL, PRIMARY KEY(workspace,owner,operation_key))')
        row = db.execute('SELECT document FROM runtime_operation_controls WHERE workspace=? AND owner=? AND operation_key=?', (workspace, owner, operation_key)).fetchone()
        if row:
            initial = json.loads(row[0])
        else:
            initial = dict(created_at=created_at if created_at is not None else runtime.clock(), policy=control.read(db, workspace)['policy'], usage={})
            db.execute('INSERT INTO runtime_operation_controls VALUES (?,?,?,?)', (workspace, owner, operation_key, json.dumps(initial)))

    def load(db):
        return json.loads(db.execute('SELECT document FROM runtime_operation_controls WHERE workspace=? AND owner=? AND operation_key=?', (workspace, owner, operation_key)).fetchone()[0])

    def policy(db, current):
        return control.intersect(current['policy'], control.read(db, workspace)['policy'])

    def check():
        if active is not None:
            active()
        authority = auth
        if authenticate := getattr(runtime, 'authenticate_current', None):
            authority = authenticate(workspace, owner)
            if authority is None or authority['subject'] != auth['subject']:
                raise RuntimeFailure('OPERATION_NOT_AUTHORIZED', 'Current operation authority is unavailable.', 403)
        if authority.get('decision') != 'allow':
            raise RuntimeFailure('OPERATION_NOT_AUTHORIZED', 'Current operation authority is unavailable.', 403)
        with runtime.store.transaction(write=False) as db:
            current = load(db)
            effective = policy(db, current)
        seconds = min(effective['limits'].get('timeout_seconds', 86400), effective['step_timeout_seconds'] or 86400)
        if runtime.clock() - current['created_at'] >= seconds:
            raise RuntimeFailure('RUN_TIMEOUT', 'The original operation duration is exhausted.')
        restricted = set(effective['restricted_sources'])
        def visit(value):
            if isinstance(value, dict):
                for key, item in value.items():
                    if key in {'source_id', 'connection_id', 'dataset_id', 'data_source_id', 'binding_id'} and isinstance(item, str) and item in restricted:
                        raise RuntimeFailure('SOURCE_RESTRICTED', 'A selected source is restricted by workspace policy.', 403)
                    visit(item)
            elif isinstance(value, list):
                for item in value:visit(item)
        visit(resources)
        return effective

    def model_request(send, arguments):
        effective = check()
        options = deepcopy(arguments)
        input_reservation = len(json.dumps(options, ensure_ascii=False).encode()) + 1024
        with runtime.store.transaction() as db:
            current = load(db)
            effective = policy(db, current)
            usage = current['usage']
            calls = usage.get('llm_calls', 0)
            if calls >= effective['limits'].get('max_llm_calls', float('inf')):
                raise RuntimeFailure('GOVERNANCE_BUDGET_EXHAUSTED', 'The operation model-call limit is exhausted.')
            cap = options.get('max_output_tokens')
            if 'max_tokens' in effective['limits']:
                remaining = effective['limits']['max_tokens'] - usage.get('tokens', 0) - input_reservation
                if remaining < 1:
                    raise RuntimeFailure('GOVERNANCE_BUDGET_EXHAUSTED', 'The operation token limit is exhausted.')
                cap = min(cap, remaining) if cap is not None else remaining
                options['max_output_tokens'] = cap
            usage['llm_calls'] = calls + 1
            reservation = input_reservation + (cap or 0)
            usage['tokens'] = usage.get('tokens', 0) + reservation
            db.execute('UPDATE runtime_operation_controls SET document=? WHERE workspace=? AND owner=? AND operation_key=?', (json.dumps(current), workspace, owner, operation_key))
        remaining_seconds = effective['limits'].get('timeout_seconds', 86400) - (runtime.clock() - initial['created_at'])
        options['timeout'] = min(options.get('timeout', 180), effective['model_timeout_seconds'] or 180, remaining_seconds)
        result = guarded_call(check, lambda: send(options), timeout=options['timeout'], timeout_code='MODEL_TIMEOUT')
        observed = getattr(result, 'usage', None)
        if observed is not None:
            used = getattr(observed, 'input_tokens', None), getattr(observed, 'output_tokens', None)
            if all(type(v) is int and v >= 0 for v in used):
                with runtime.store.transaction() as db:
                    current = load(db)
                    current['usage']['tokens'] = max(0, current['usage']['tokens'] - reservation + sum(used))
                    db.execute('UPDATE runtime_operation_controls SET document=? WHERE workspace=? AND owner=? AND operation_key=?', (json.dumps(current), workspace, owner, operation_key))
                if 'max_tokens' in effective['limits'] and current['usage']['tokens'] > effective['limits']['max_tokens']:
                    raise RuntimeFailure('GOVERNANCE_BUDGET_EXHAUSTED', 'Provider usage exceeded the operation token allowance.')
        return result

    def resolve_policy():
        with runtime.store.transaction(write=False) as db:
            return policy(db, load(db))
    def reserve_correction():
        check()
        with runtime.store.transaction() as db:
            current = load(db)
            effective = policy(db, current)
            limit = effective['limits'].get('max_retries')
            if limit is None:
                return
            used = current['usage'].get('retries', 0)
            if used >= limit:
                raise RuntimeFailure('GOVERNANCE_BUDGET_EXHAUSTED', 'The configured correction/retry limit is exhausted.')
            current['usage']['retries'] = used + 1
            db.execute('UPDATE runtime_operation_controls SET document=? WHERE workspace=? AND owner=? AND operation_key=?', (json.dumps(current), workspace, owner, operation_key))
    retry_marker = retry_reserver.set(reserve_correction)
    policy_marker = policy_resolver.set(resolve_policy)
    marker = _operation.set(True)
    limits_marker = model_limits_required.set('max_tokens' in initial['policy']['limits'])
    provider_marker = _provider_request.set(model_request)
    try:
        effective = check()
        remaining = effective['limits'].get('timeout_seconds', 86400) - (runtime.clock() - initial['created_at'])
        return guarded_call(check, invoke, timeout=min(remaining, effective['step_timeout_seconds'] or remaining), timeout_code='RUN_TIMEOUT')
    finally:
        retry_reserver.reset(retry_marker)
        policy_resolver.reset(policy_marker)
        model_limits_required.reset(limits_marker)
        _provider_request.reset(provider_marker)
        _operation.reset(marker)
