"""Deterministic failures at real transaction/transport boundaries; no live effects."""
from contextlib import contextmanager
from copy import deepcopy
import json
import time

import pytest

from runtime import RuntimeFailure
from runtime.graph import GraphRunner
from connector_extension.common import EffectJournal
from tests import test_runtime as graph_fixtures
from tests import test_dynamic_delegation as delegation_fixtures
from tests import test_delegated_tools as tool_fixtures


class SimulatedCrash(BaseException):
    """Bypass normal adapter exception handling, as a terminated process would."""


@pytest.fixture
def tool_run():
    f = graph_fixtures.ToolGraphTests()
    f.setUp()
    try:
        f.configure()
        f.now = time.time()
        f.runtime.clock = lambda: f.now
        f.run_id = f.queue()
        paused = f.graph.advance(f.run_id, f.auth)
        f.graph.decide(f.decision(paused, 'approved'), f.approver())
        yield f
    finally:
        f.doCleanups()


def stored(f):
    with f.store.transaction(write=False) as db:
        return deepcopy(f.runtime.load(db, f.run_id, f.auth))


def after_intent(monkeypatch, f, callback):
    """Interrupt immediately after the actual node.started transaction commits."""
    transaction, event = f.store.transaction, f.runtime.event
    armed = False
    fired = False

    def observe(db, run, kind, details):
        nonlocal armed
        event(db, run, kind, details)
        if kind == 'node.started' and details['node_id'] == 'send_email':
            armed = True

    @contextmanager
    def boundary(*args, **kwargs):
        nonlocal fired
        with transaction(*args, **kwargs) as db:
            yield db
        if armed and not fired:
            fired = True
            callback(transaction)

    monkeypatch.setattr(f.runtime, 'event', observe)
    monkeypatch.setattr(f.store, 'transaction', boundary)


@pytest.mark.parametrize('interruption', ['cancel', 'expire', 'revoke'])
def test_committed_intent_is_revalidated_before_external_dispatch(tool_run, monkeypatch, interruption):
    f = tool_run
    def interrupt(transaction):
        if interruption == 'expire':
            f.now += 121
        elif interruption == 'revoke':
            f.workflows.registry.update_approval_evidence({}, f.auth)
        else:
            with transaction() as db:
                run = f.runtime.load(db, f.run_id, f.auth)
                f.runtime.transition(db, run, 'cancelled')
    after_intent(monkeypatch, f, interrupt)
    result = f.graph.advance(f.run_id, f.auth)
    assert not f.invocations
    assert result['status'] == {'cancel': 'cancelled', 'expire': 'running', 'revoke': 'blocked'}[interruption]
    if interruption == 'expire':
        assert f.graph.advance(f.run_id, f.auth)['status'] == 'blocked'
        assert stored(f)['error_code'] == 'UNKNOWN_INVOCATION_RESULT'


def test_expired_worker_cannot_checkpoint_a_delayed_external_result(tool_run):
    f = tool_run
    invoke = f.connector.invoke
    def delayed(*args):
        output = invoke(*args)
        f.now += 121
        return output
    f.connector.invoke = delayed
    f.graph.advance(f.run_id, f.auth)
    run = stored(f)
    assert run['node_states']['send_email'] == 'executing'
    assert 'send_email' not in run['outputs']
    usage = deepcopy(run['usage'])
    blocked = f.graph.advance(f.run_id, f.auth)
    assert blocked['status'] == 'blocked'
    assert stored(f)['usage'] == usage
    assert len(f.invocations) == 1
    assert stored(f)['node_states']['start'] == 'completed'


@pytest.mark.parametrize('interruption', ['cancel', 'takeover', 'expire'])
def test_delegated_failure_cannot_mutate_state_after_ownership_loss(interruption):
    f = delegation_fixtures.DynamicDelegationTests()
    f.setUp()
    try:
        f.now = time.time()
        f.runtime.clock = lambda: f.now
        executor = f.executor()
        def failed(agent, inputs, invocation):
            with f.store.transaction() as db:
                row = db.execute('SELECT document FROM runtime_runs').fetchone()
                run = json.loads(row[0])
                if interruption == 'cancel':
                    f.runtime.transition(db, run, 'cancelled')
                elif interruption == 'takeover':
                    run['worker'] = 'replacement_worker'
                    f.runtime.save(db, run)
                else:
                    f.now += 121
            raise RuntimeFailure('MODEL_INVOCATION_FAILED', 'Controlled transport failure.')
        executor.invoke = failed
        result, events = f.run_case(executor=executor)
        with f.store.transaction(write=False) as db:
            run = f.runtime.load(db, result['run_id'], f.auth)
        assert 'failed' not in run.get('delegation_states', {}).values()
        assert not any(e['event_type'] == 'node.failed' for e in events)
        assert run['status'] == ('cancelled' if interruption == 'cancel' else 'running')
    finally:
        f.doCleanups()


@pytest.mark.parametrize('boundary', [
    'before_intent', 'after_intent', 'during_call', 'after_effect',
    'before_journal_receipt', 'after_journal_receipt', 'after_checkpoint',
])
def test_restart_at_external_effect_boundaries(tool_run, monkeypatch, tmp_path, boundary):
    f = tool_run
    monkeypatch.setenv('BUILDER_RUNTIME_LEASE_SECONDS', '30')
    journal = EffectJournal(tmp_path)
    effects = []
    transaction = f.store.transaction
    journal_connection = journal.connection
    event = f.runtime.event
    checkpointed = False
    receipt_pending = False

    def observe(db, run, kind, details):
        nonlocal checkpointed
        if boundary == 'before_intent' and kind == 'node.started' and details['node_id'] == 'send_email':
            raise SimulatedCrash()
        event(db, run, kind, details)
        if boundary == 'after_checkpoint' and kind == 'node.completed' and details['node_id'] == 'send_email':
            checkpointed = True

    @contextmanager
    def crash_after_checkpoint(*args, **kwargs):
        with transaction(*args, **kwargs) as db:
            yield db
        if checkpointed:
            raise SimulatedCrash()

    @contextmanager
    def crash_before_receipt(*args, **kwargs):
        if receipt_pending:
            raise SimulatedCrash()
        with journal_connection(*args, **kwargs) as db:
            yield db

    def action():
        nonlocal receipt_pending
        if boundary == 'during_call':
            raise SimulatedCrash()
        effects.append('provider_accepted')
        if boundary == 'after_effect':
            raise SimulatedCrash()
        receipt_pending = boundary == 'before_journal_receipt'
        return {'message_id': 'controlled_receipt'}

    def invoke(binding, params, effect):
        result = journal.perform(binding['tool_id'], effect, params, action)
        if boundary == 'after_journal_receipt':
            raise SimulatedCrash()
        return result

    with monkeypatch.context() as patch:
        patch.setattr(f.connector, 'invoke', invoke)
        patch.setattr(f.runtime, 'event', observe)
        if boundary == 'after_intent':
            after_intent(patch, f, lambda _: (_ for _ in ()).throw(SimulatedCrash()))
        if boundary == 'after_checkpoint':
            patch.setattr(f.store, 'transaction', crash_after_checkpoint)
        if boundary == 'before_journal_receipt':
            patch.setattr(journal, 'connection', crash_before_receipt)
        with pytest.raises(SimulatedCrash):
            f.graph.advance(f.run_id, f.auth)

    before = stored(f)
    f.now += 31
    # Recreate the runtime and runner over the same store, never reuse local state.
    from runtime import RuntimeService
    f.runtime = RuntimeService(f.workflows, clock=lambda: f.now)
    f.connector.invoke = invoke
    f.graph = GraphRunner(f.runtime, connectors={'smtp_send_email': f.connector})
    result = f.graph.advance(f.run_id, f.auth)
    after = stored(f)
    safe = boundary in ('before_intent', 'after_checkpoint')
    assert result['status'] == ('completed' if safe else 'blocked')
    assert len(effects) == (0 if boundary in ('after_intent', 'during_call') else 1)
    assert after['workflow_digest'] == before['workflow_digest']
    assert after['approval_evidence'] == before['approval_evidence']
    if boundary != 'before_intent':
        assert after['usage'] == before['usage']
    if boundary == 'after_checkpoint':
        assert after['outputs']['send_email'] == before['outputs']['send_email']
        assert after['node_invocations']['send_email'] == before['node_invocations']['send_email']
    if not safe:
        assert after['error_code'] == 'UNKNOWN_INVOCATION_RESULT'
        assert 'send_email' not in after['outputs']
        assert f.graph.advance(f.run_id, f.auth)['status'] == 'blocked'


def test_operator_recovery_view_is_read_only_and_does_not_authorize_replay(tool_run):
    f = tool_run
    def uncertain(*args):
        f.invocations.append('attempt')
        raise RuntimeFailure('SMTP_DELIVERY_UNCERTAIN', 'Controlled unknown outcome.')
    f.connector.invoke = uncertain
    assert f.graph.advance(f.run_id, f.auth)['status'] == 'blocked'
    before = stored(f)
    writes = f.store.metrics['writes']
    report = f.runtime.recovery.inspect(f.run_id, f.auth)
    assert f.store.metrics['writes'] == writes
    assert report['required_action'] == 'operator_reconciliation'
    assert report['automatic_replay_allowed'] is False
    assert report['uncertain_invocations'] == [dict(node_id='send_email',
        invocation_id=before['node_invocations']['send_email'], tool_id='smtp_send_email',
        effect_reference=f.run_id + ':send_email', outcome='unknown',
        required_action='verify_provider_and_connector_journal')]
    assert report['consumed_usage'] == before['usage']
    assert stored(f) == before
    assert f.graph.advance(f.run_id, f.auth)['status'] == 'blocked'
    assert len(f.invocations) == 1
    other = deepcopy(f.auth)
    other['subject']['workspace_id'] = 'another_customer'
    with pytest.raises(RuntimeFailure) as missing:
        f.runtime.recovery.inspect(f.run_id, other)
    assert missing.value.code == 'RUN_NOT_FOUND'
    other = deepcopy(f.auth)
    other['permissions'].remove('runs.view')
    with pytest.raises(RuntimeFailure) as denied:
        f.runtime.recovery.inspect(f.run_id, other)
    assert denied.value.status == 403


def test_recovery_endpoint_requires_auth_and_rejects_mutation_flags(tool_run):
    from fastapi.testclient import TestClient
    from workflow_api.main import create_app, COOKIE
    f = tool_run
    f.workflows.runtime_runner = f.graph
    with TestClient(create_app(f.workflows, dev_auth=True, roles=['admin'],
                               start_workers=False, planning_worker_enabled=False)) as client:
        url = '/runs/' + f.run_id + '/recovery'
        assert client.get(url).status_code == 401
        session = client.get('/session')
        client.cookies.set(COOKIE, session.cookies[COOKIE], path='/')
        assert client.get(url).json()['data']['run_id'] == f.run_id
        assert client.get(url + '?confirmed_success=true').status_code == 400
        assert client.get('/runs/unknown_run/recovery').status_code == 404


@pytest.mark.parametrize('invalid', ['unknown_timeout', 'missing_timeout_path', 'timeout_on_tool', 'missing_error_path'])
def test_unsupported_failure_control_is_rejected_before_execution(tool_run, invalid):
    from planner.errors import PlannerFailure
    from workflow_api.service import WorkflowService
    workflow = deepcopy(tool_run.workflow)
    review = next(n for n in workflow['nodes'] if n['node_id'] == 'review')
    tool = next(n for n in workflow['nodes'] if n['node_id'] == 'send_email')
    if invalid == 'unknown_timeout':
        review['configuration'] = {'on_timeout': 'repeat_forever'}
    elif invalid == 'missing_timeout_path':
        review['configuration'] = {'on_timeout': 'branch', 'timeout_outcome': 'missing'}
    elif invalid == 'timeout_on_tool':
        tool['configuration']['on_timeout'] = 'retry'
    else:
        tool['configuration']['error_outcome'] = 'missing'
    with pytest.raises(PlannerFailure) as denied:
        WorkflowService.validate_document(workflow)
    assert denied.value.code == 'UNSUPPORTED_EXECUTION_CONFIGURATION'


@pytest.mark.parametrize('interruption', ['cancel', 'takeover', 'expire'])
def test_delegated_tool_failure_cannot_commit_after_ownership_loss(interruption):
    f = tool_fixtures.DelegatedToolTests()
    f.setUp()
    try:
        f.now = time.time()
        f.runtime.clock = lambda: f.now
        calls = []
        def failed(*args):
            calls.append('attempt')
            with f.store.transaction() as db:
                run = json.loads(db.execute('SELECT document FROM runtime_runs').fetchone()[0])
                if interruption == 'cancel':
                    f.runtime.transition(db, run, 'cancelled')
                elif interruption == 'takeover':
                    run['worker'] = 'replacement_worker'
                    f.runtime.save(db, run)
                else:
                    f.now += 121
            raise RuntimeFailure('CONNECTOR_TIMEOUT', 'Controlled failure.')
        f.connector.invoke = failed
        result, events = f.execute()
        with f.store.transaction(write=False) as db:
            run = f.runtime.load(db, result['run_id'], f.auth)
        assert calls == ['attempt']
        assert 'failed' not in run.get('delegation_states', {}).values()
        assert not any(e['event_type'] == 'node.failed' for e in events)
        report = f.runtime.recovery.inspect(result['run_id'], f.auth)
        tool = report['uncertain_invocations'][0]
        assert tool['effect_reference'] == result['run_id'] + ':' + tool['invocation_id']
    finally:
        f.doCleanups()


def test_recovery_view_distinguishes_denial_before_invocation(tool_run):
    f = tool_run
    f.connector.timeout = 121
    assert f.graph.advance(f.run_id, f.auth)['status'] == 'blocked'
    report = f.runtime.recovery.inspect(f.run_id, f.auth)
    assert not f.invocations
    assert report['uncertain_invocations'] == []
    assert report['not_invoked'][0]['outcome'] == 'not_invoked'
    assert report['required_action'] == 'review_failure'


@pytest.mark.parametrize('elapsed,reason', [(61, 'AGENT_TIMEOUT'), (121, 'RUN_TIMEOUT')])
def test_late_response_cannot_complete_after_execution_deadline(tool_run, elapsed, reason):
    f = tool_run
    invoke = f.connector.invoke
    def delayed(*args):
        output = invoke(*args)
        f.now += elapsed
        # Model a healthy lease heartbeat during a transport that overruns its
        # declared deadline. Ownership alone must not extend execution budgets.
        with f.store.transaction() as db:
            run = f.runtime.load(db, f.run_id, f.auth)
            run['lease_until'] = f.now + 120
            f.runtime.save(db, run)
        return output
    f.connector.invoke = delayed
    assert f.graph.advance(f.run_id, f.auth)['status'] == 'blocked'
    run = stored(f)
    assert run['error_code'] == 'POST_INVOCATION_REVALIDATION_FAILED'
    assert 'send_email' not in run['outputs']
    events = f.runtime.events(f.run_id, f.auth)['items']
    assert any(e['event_type'] == 'invocation.revalidation_failed' and e['details']['error_code'] == reason for e in events)
    assert len(f.invocations) == 1


@pytest.mark.parametrize('interruption', ['cancel', 'takeover', 'expire'])
def test_delegated_usage_settlement_is_fenced(interruption):
    f = delegation_fixtures.DynamicDelegationTests()
    f.setUp()
    try:
        f.now = time.time()
        f.runtime.clock = lambda: f.now
        executor = f.executor()
        def accounted(agent, inputs, invocation, schema):
            if agent['agent_id'] == 'master_agent':
                return f.decision(inputs), {'llm_calls': 1, 'tokens': 1}
            with f.store.transaction() as db:
                run = json.loads(db.execute('SELECT document FROM runtime_runs').fetchone()[0])
                if interruption == 'cancel':
                    f.runtime.transition(db, run, 'cancelled')
                elif interruption == 'takeover':
                    run['worker'] = 'replacement_worker'
                    f.runtime.save(db, run)
                else:
                    f.now += 121
            return {'facts': inputs['task']}, {'llm_calls': 1, 'tokens': 1}
        executor.invoke_accounted = accounted
        result, events = f.run_case(executor=executor)
        with f.store.transaction(write=False) as db:
            run = f.runtime.load(db, result['run_id'], f.auth)
        assert run['usage']['research_agent']['tokens'] == 10
        assert not any(e['event_type'] == 'budget.settled' and e['details']['agent_id'] == 'research_agent' for e in events)
        assert run['status'] == ('cancelled' if interruption == 'cancel' else 'running')
    finally:
        f.doCleanups()
