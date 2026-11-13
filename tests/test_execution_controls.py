"""Execution-path safety checks; real isolated store, controlled adapters only."""
from copy import deepcopy
from threading import Event, Thread
import time
import pytest
from tests import test_runtime as fixtures
from runtime import RuntimeService, RuntimeFailure
from runtime.graph import GraphRunner


@pytest.fixture
def context():
    fixture = fixtures.RetryTests()
    fixture.setUp()
    fixture.configure()
    try:
        yield fixture
    finally:
        fixture.doCleanups()


def test_cancel_during_model_fences_result_and_survives_restart(context):
    started, release = Event(), Event()
    def invoke(*args):
        started.set()
        release.wait(5)
        return {'category': 'support', 'confidence': 1}
    context.graph.agents.invoke = invoke
    run = context.runtime.create_run(context.request(), context.auth)
    result = []
    worker = Thread(target=lambda: result.append(context.graph.advance(run['run_id'], context.auth)))
    worker.start()
    assert started.wait(3)
    before = time.monotonic()
    try:
        context.runtime.cancel_run(run['run_id'], context.auth)
        worker.join(2)
        assert not worker.is_alive()
        assert time.monotonic() - before < 2
        assert result[0]['status'] == 'cancelled'
        restarted = RuntimeService(context.workflows)
        assert GraphRunner(restarted).advance(run['run_id'], context.auth)['status'] == 'cancelled'
    finally:
        release.set()
        worker.join(3)
    assert 'classify' not in context.runtime.get_run(run['run_id'], context.auth).get('outputs', {})


def test_cancel_requires_owner_or_admin_and_tenant(context):
    run = context.runtime.create_run(context.request(), context.auth)
    other = deepcopy(context.auth)
    other['roles'] = ['builder']
    other['subject']['subject_id'] = 'other'
    with pytest.raises(RuntimeFailure) as failure:
        context.runtime.cancel_run(run['run_id'], other)
    assert failure.value.code == 'SUBJECT_MISMATCH'
    other['subject']['workspace_id'] = 'foreign'
    with pytest.raises(RuntimeFailure) as failure:
        context.runtime.cancel_run(run['run_id'], other)
    assert failure.value.status == 404
    assert context.runtime.cancel_run(run['run_id'], context.auth)['status'] == 'cancelled'
    assert context.runtime.cancel_run(run['run_id'], context.auth)['status'] == 'cancelled'


def test_model_timeout_stops_execution_without_waiting_for_adapter(context):
    body = context.runtime.governance.get(context.auth)
    context.auth['permissions'].append('workflow.edit')
    context.auth['scopes'].append('workspace:write')
    body['policy']['model_timeout_seconds'] = 1
    context.runtime.governance.update(context.auth, dict(revision=body['revision'], policy=body['policy']))
    release = Event()
    def invoke(*args):
        release.wait(5)
        return {'category': 'support', 'confidence': 1}
    context.graph.agents.invoke = invoke
    run = context.runtime.create_run(context.request(), context.auth)
    try:
        before = time.monotonic()
        result = context.graph.advance(run['run_id'], context.auth)
        assert time.monotonic() - before < 3
        assert result['status'] == 'blocked'
        with context.store.transaction(write=False) as db:
            saved = context.runtime.load(db, run['run_id'], context.auth)
        assert saved['error_code'] == 'MODEL_TIMEOUT'
    finally:
        release.set()


def test_deadline_does_not_reset_after_restart(context):
    run = context.runtime.create_run(context.request(), context.auth)
    with context.store.transaction() as db:
        saved = context.runtime.load(db, run['run_id'], context.auth)
        saved['created_at'] -= context.workflow['execution_policy']['limits']['timeout_seconds'] + 1
        context.runtime.save(db, saved)
    restarted = RuntimeService(context.workflows)
    assert GraphRunner(restarted).advance(run['run_id'], context.auth)['status'] == 'blocked'
    assert not context.attempts


def save_policy(context, **changes):
    context.auth['permissions'] = list(set(context.auth['permissions']) | {'workflow.edit'})
    context.auth['scopes'] = list(set(context.auth['scopes']) | {'workspace:write'})
    body = context.runtime.governance.get(context.auth)
    body['policy'].update(changes)
    return context.runtime.governance.update(context.auth, dict(revision=body['revision'], policy=body['policy']))


@pytest.fixture
def tool_context(request):
    fixture = fixtures.ToolGraphTests()
    fixture.setUp()
    fixture.configure(**getattr(request, 'param', {}))
    try:
        yield fixture
    finally:
        fixture.doCleanups()


@pytest.mark.parametrize('restriction', ['read_only', 'restricted_tools'])
def test_protected_tool_denied_before_transport(tool_context, restriction):
    c = tool_context
    save_policy(c, **{restriction: True if restriction == 'read_only' else ['smtp_send_email']})
    run_id = c.queue()
    assert c.graph.advance(run_id, c.auth)['status'] == 'paused_for_approval'
    c.graph.decide(c.decision(c.runtime.get_run(run_id, c.auth), 'approved'), c.approver())
    result = c.graph.advance(run_id, c.auth)
    assert result['status'] == 'blocked'
    assert not c.invocations
    errors = [e['details'].get('error_code') for e in c.runtime.events(run_id, c.auth)['items']]
    assert ('READ_ONLY_VIOLATION' if restriction == 'read_only' else 'TOOL_RESTRICTED') in errors


def test_restriction_added_after_approval_blocks_existing_run(tool_context):
    c = tool_context
    run_id = c.queue()
    c.graph.advance(run_id, c.auth)
    c.graph.decide(c.decision(c.runtime.get_run(run_id, c.auth), 'approved'), c.approver())
    save_policy(c, read_only=True)
    assert c.graph.advance(run_id, c.auth)['status'] == 'blocked'
    assert not c.invocations


def test_policy_snapshot_cannot_be_relaxed_for_existing_run(context):
    save_policy(context, read_only=True, limits={'max_llm_calls': 0})
    run = context.runtime.create_run(context.request(), context.auth)
    save_policy(context, read_only=False, limits={})
    assert context.graph.advance(run['run_id'], context.auth)['status'] == 'blocked'
    assert context.attempts == 0
    with context.store.transaction(write=False) as db:
        saved = context.runtime.load(db, run['run_id'], context.auth)
        assert context.runtime.governance.effective(saved, db)['read_only']


def test_unauthorized_policy_edits_and_stale_revision(context):
    body = context.runtime.governance.get(context.auth)
    with pytest.raises(RuntimeFailure):
        context.runtime.governance.update(context.auth, {'revision': 0, 'policy': body['policy']})
    save_policy(context, read_only=True)
    with pytest.raises(RuntimeFailure) as failure:
        context.runtime.governance.update(context.auth, {'revision': 0, 'policy': body['policy']})
    assert failure.value.code == 'POLICY_CONFLICT'
    other = deepcopy(context.auth)
    other['subject']['workspace_id'] = 'other'
    assert not context.runtime.governance.get(other)['policy']['read_only']


def test_workspace_policy_adds_exact_action_review_without_new_workflow(tool_context):
    c = tool_context
    c.workflow['agents'][0]['approval_requirements'] = []
    c.workflows.registry_adapter.agents[c.workflow['agents'][0]['agent_id']]['definition']['approval_requirements'] = []
    c.workflow['approval_gates'] = []
    c.workflow['nodes'] = [n for n in c.workflow['nodes'] if n['node_id'] in {'start', 'send_email', 'finish'}]
    c.workflow['edges'] = [dict(edge_id='start_send',source=c.workflow['nodes'][0]['node_id'],target='send_email'),dict(edge_id='send_finish',source='send_email',target='finish')]
    save_policy(c, require_action_approval=True)
    run_id = c.queue()
    pending = c.graph.advance(run_id, c.auth)
    assert pending['status'] == 'paused_for_approval'
    assert pending['approvals'][0]['resolved_payload']['to'] == 'approved@example.com'
    assert not c.invocations
    c.graph.decide(c.decision(pending, 'approved'), c.approver())
    result = c.graph.advance(run_id, c.auth)
    assert result['status'] == 'completed', [(e['event_type'],e['details'].get('error_code')) for e in c.runtime.events(run_id,c.auth)['items']][-3:]
    assert len(c.invocations) == 1
    assert c.graph.advance(run_id, c.auth)['status'] == 'completed'
    assert len(c.invocations) == 1


def test_expired_approved_action_never_calls_transport(tool_context):
    c = tool_context
    run_id = c.queue()
    pending = c.graph.advance(run_id, c.auth)
    c.graph.decide(c.decision(pending, 'approved'), c.approver())
    with c.store.transaction() as db:
        run = c.runtime.load(db, run_id, c.auth)
        run['approval_context']['expires_at'] = c.runtime.clock() - 1
        c.runtime.save(db, run)
    assert c.graph.advance(run_id, c.auth)['status'] == 'blocked'
    assert not c.invocations


def test_worker_expires_approval_wait_using_original_run_budget(tool_context):
    c = tool_context
    save_policy(c, limits={'timeout_seconds': 1})
    run_id = c.queue()
    assert c.graph.advance(run_id, c.auth)['status'] == 'paused_for_approval'
    with c.store.transaction() as db:
        run = c.runtime.load(db, run_id, c.auth)
        run['created_at'] -= 2
        c.runtime.save(db, run)
    c.runtime.expire_runs()
    assert c.runtime.get_run(run_id, c.auth)['status'] == 'blocked'
    assert not c.invocations


def test_operation_model_budget_persists_and_blocks_before_provider(context):
    from runtime.operation_control import controlled_operation
    from runtime.execution_control import controlled_response
    from types import SimpleNamespace
    context.workflows.runtime_runner = context.graph
    save_policy(context, limits={'max_llm_calls': 1})
    calls = []
    provider = SimpleNamespace(responses=SimpleNamespace(create=lambda **kwargs: calls.append(kwargs) or SimpleNamespace(output_text='ok')))
    def execute():
        return controlled_response(provider, model='configured-model', input=[], max_output_tokens=10, timeout=2)
    controlled_operation(context.workflows, context.auth, 'stable_planning_job', execute)
    with pytest.raises(RuntimeFailure) as failure:
        controlled_operation(context.workflows, context.auth, 'stable_planning_job', execute)
    assert failure.value.code == 'GOVERNANCE_BUDGET_EXHAUSTED'
    assert len(calls) == 1


def test_operation_cancellation_prevents_later_model_requests(context):
    from runtime.operation_control import controlled_operation
    from runtime.execution_control import controlled_response
    from types import SimpleNamespace
    context.workflows.runtime_runner = context.graph
    cancelled, entered, release, finished = Event(), Event(), Event(), Event()
    calls = []
    def active():
        if cancelled.is_set():
            raise RuntimeFailure('EXECUTION_STOPPED', 'Stopped')
    provider = SimpleNamespace(responses=SimpleNamespace(create=lambda **kwargs: calls.append(kwargs) or SimpleNamespace(output_text='ok')))
    def execute():
        entered.set()
        release.wait(5)
        try:
            controlled_response(provider, model='configured-model', input=[], timeout=2)
        finally:
            finished.set()
    errors = []
    def run():
        try:
            controlled_operation(context.workflows, context.auth, 'cancellable_planning_job', execute, active=active)
        except RuntimeFailure as exc:
            errors.append(exc.code)
    worker = Thread(target=run)
    worker.start()
    assert entered.wait(3)
    cancelled.set()
    worker.join(2)
    try:
        assert not worker.is_alive()
        assert errors == ['EXECUTION_STOPPED']
    finally:
        release.set()
        assert finished.wait(2)
    assert not calls


def test_policy_and_stop_apis_require_trusted_session(context):
    from fastapi.testclient import TestClient
    from workflow_api.main import create_app, COOKIE
    context.workflows.runtime_runner = context.graph
    app = create_app(context.workflows, dev_auth=True, roles=['admin'], runtime_enabled=True, start_workers=False, planning_worker_enabled=False)
    with TestClient(app) as client:
        assert client.get('/governance/policy').status_code == 401
        session = client.get('/session')
        client.cookies.set(COOKIE, session.cookies[COOKIE], path='/')
        response = client.get('/governance/policy')
        assert response.status_code == 200
        body = {k:response.json()['data'][k] for k in ('revision','policy')}
        body['policy']['read_only'] = True
        assert client.put('/governance/policy', json=body).status_code == 200
        assert client.put('/governance/policy', json=body).status_code == 409
        run = context.runtime.create_run(context.request(), context.auth)
        stopped = client.post('/runs/' + run['run_id'] + '/cancel', json={})
        assert stopped.status_code == 200
        assert stopped.json()['data']['run']['status'] == 'cancelled'
        assert client.get('/runs/' + run['run_id']).json()['data']['run']['safety']['cancellation']['reason'] == 'user_requested'


def test_cancel_inflight_tool_preserves_unknown_outcome_and_prevents_replay(tool_context):
    c = tool_context
    started, release = Event(), Event()
    def invoke(*args):
        started.set()
        release.wait(5)
        return {'message_id': 'late_provider_receipt'}
    c.connector.invoke = invoke
    run_id = c.queue()
    pending = c.graph.advance(run_id, c.auth)
    c.graph.decide(c.decision(pending, 'approved'), c.approver())
    results = []
    worker = Thread(target=lambda: results.append(c.graph.advance(run_id, c.auth)))
    worker.start()
    assert started.wait(3)
    try:
        c.runtime.cancel_run(run_id, c.auth)
        worker.join(2)
        assert not worker.is_alive()
        assert results[0]['status'] == 'cancelled'
        assert c.runtime.get_run(run_id, c.auth)['safety']['uncertain_effects'][0]['outcome'] == 'unknown'
        assert c.graph.advance(run_id, c.auth)['status'] == 'cancelled'
    finally:
        release.set()
        worker.join(3)


def test_restricted_source_is_rejected_on_actual_tool_path(tool_context):
    c = tool_context
    c.workflow['metadata']['source_context'] = {'source_id': 'restricted_source'}
    save_policy(c, restricted_sources=['restricted_source'])
    run_id = c.queue()
    pending = c.graph.advance(run_id, c.auth)
    c.graph.decide(c.decision(pending, 'approved'), c.approver())
    assert c.graph.advance(run_id, c.auth)['status'] == 'blocked'
    assert not c.invocations
    errors = [e['details'].get('error_code') for e in c.runtime.events(run_id, c.auth)['items']]
    assert 'SOURCE_RESTRICTED' in errors


def test_worker_blocks_revoked_identity_without_reconstructing_grants(context):
    from runtime.worker import RuntimeWorker
    run = context.runtime.create_run(context.request(), context.auth)
    RuntimeWorker(context.graph, lambda *_: None).drain()
    saved = context.runtime.get_run(run['run_id'], context.auth)
    assert saved['status'] == 'blocked'
    assert saved['safety']['error_code'] == 'EXECUTION_AUTHORITY_REVOKED'
    assert context.attempts == 0


def test_identical_external_action_on_another_node_reuses_durable_receipt(tool_context):
    c = tool_context
    c.workflow['agents'][0]['approval_requirements'] = []
    c.workflows.registry_adapter.agents[c.workflow['agents'][0]['agent_id']]['definition']['approval_requirements'] = []
    c.workflow['approval_gates'] = []
    c.workflow['nodes'] = [n for n in c.workflow['nodes'] if n['node_id'] in {'start', 'send_email', 'finish'}]
    second = deepcopy(next(n for n in c.workflow['nodes'] if n['node_id'] == 'send_email'))
    second['node_id'] = 'send_again'
    c.workflow['nodes'].insert(-1, second)
    c.workflow['edges'] = [dict(edge_id='a',source='start',target='send_email'),dict(edge_id='b',source='send_email',target='send_again'),dict(edge_id='c',source='send_again',target='finish')]
    save_policy(c, require_action_approval=True)
    run_id = c.queue()
    first = c.graph.advance(run_id, c.auth)
    assert first['status'] == 'paused_for_approval'
    c.graph.decide(c.decision(first, 'approved'), c.approver())
    second = c.graph.advance(run_id, c.auth)
    assert second['status'] == 'paused_for_approval'
    assert len(c.invocations) == 1
    c.graph.decide(c.decision(second, 'approved'), c.approver())
    assert c.graph.advance(run_id, c.auth)['status'] == 'completed'
    assert len(c.invocations) == 1
    with c.store.transaction(write=False) as db:
        assert db.execute("SELECT COUNT(*) FROM runtime_action_effects WHERE state='completed'").fetchone()[0] == 1


@pytest.fixture
def delegation_context():
    from tests.test_dynamic_delegation import DynamicDelegationTests
    fixture = DynamicDelegationTests()
    fixture.setUp()
    try:
        yield fixture
    finally:
        fixture.doCleanups()


def test_delegation_budget_blocks_child_before_spawn(delegation_context):
    c = delegation_context
    save_policy(c, limits={'max_delegation_calls': 0})
    result, events = c.run_case()
    assert result['status'] == 'blocked'
    assert not c.called
    assert not [e for e in events if e['event_type'] == 'agent.spawned']


def test_real_crewai_call_cancels_before_later_delegation(delegation_context):
    from runtime.crew import CrewExecutor
    from runtime.model import BoundedLLM
    import json
    c = delegation_context
    entered, release, finished = Event(), Event(), Event()
    def factory(agent):
        def provider(*args):
            entered.set()
            release.wait(5)
            finished.set()
            return json.dumps({'action':'finish','reason':'Offline transport result.','output':{'summary':'Test'}}),1,1
        return BoundedLLM(agent, provider, lambda _: 10, 0, 0)
    runner = GraphRunner(c.runtime, agents=CrewExecutor(c.workflows.registry_adapter, factory))
    run = c.runtime.create_run(c.request(), c.auth)
    results = []
    worker = Thread(target=lambda: results.append(runner.advance(run['run_id'], c.auth)))
    worker.start()
    assert entered.wait(4)
    try:
        c.runtime.cancel_run(run['run_id'], c.auth)
        worker.join(3)
        assert not worker.is_alive()
        assert results[0]['status'] == 'cancelled'
        assert not [e for e in c.runtime.events(run['run_id'], c.auth)['items'] if e['event_type'] == 'agent.spawned']
    finally:
        release.set()
        assert finished.wait(2)


def test_zero_retry_policy_blocks_model_validation_correction(context):
    from runtime.service import RuntimeFailure
    save_policy(context, limits={'max_retries': 0})
    calls = []
    def invalid(*args):
        calls.append(1)
        raise RuntimeFailure('MODEL_OUTPUT_INVALID_JSON', 'Controlled malformed response.')
    context.graph.agents.invoke = invalid
    run = context.runtime.create_run(context.request(), context.auth)
    assert context.graph.advance(run['run_id'], context.auth)['status'] == 'blocked'
    assert len(calls) == 1


def test_revocation_during_call_is_durable_even_when_original_actor_is_denied(context):
    entered, release = Event(), Event()
    viewer = deepcopy(context.auth)
    def invoke(*args):
        entered.set()
        release.wait(5)
        return {'category': 'support', 'confidence': 1}
    context.graph.agents.invoke = invoke
    context.runtime.authenticate_current = lambda *_: context.auth
    run = context.runtime.create_run(context.request(), context.auth)
    errors = []
    def execute():
        try:
            context.graph.advance(run['run_id'], context.auth)
        except RuntimeFailure as error:
            errors.append(error.code)
    worker = Thread(target=execute)
    worker.start()
    assert entered.wait(3)
    try:
        context.auth['decision'] = 'deny'
        worker.join(3)
        assert not worker.is_alive()
        stopped = context.runtime.get_run(run['run_id'], viewer)
        assert stopped['status'] == 'blocked'
        assert stopped['safety']['error_code'] == 'OPERATION_NOT_AUTHORIZED'
    finally:
        release.set()
        worker.join(3)


@pytest.mark.parametrize('tool_context,deadline_scope', [({}, 'workflow'), ({'agent_timeout': 30}, 'agent')], indirect=['tool_context'])
def test_tool_equal_configured_deadline_runs_with_remaining_time(tool_context, deadline_scope):
    c = tool_context
    if deadline_scope == 'workflow':
        c.workflow['execution_policy']['limits']['timeout_seconds'] = c.connector.timeout
    c.put()
    run_id = c.queue()
    paused = c.graph.advance(run_id, c.auth)
    c.graph.decide(c.decision(paused, 'approved'), c.approver())
    completed = c.graph.advance(run_id, c.auth)
    assert completed['status'] == 'completed', c.runtime.events(run_id, c.auth)
    assert len(c.invocations) == 1


def test_tool_remaining_budget_is_enforced_during_invocation(tool_context):
    c = tool_context
    save_policy(c, tool_timeout_seconds=1)
    release, started = Event(), Event()
    def invoke(*args):
        started.set()
        release.wait(5)
        return {'accepted': True, 'message_id': 'offline_message'}
    c.connector.invoke = invoke
    run_id = c.queue()
    paused = c.graph.advance(run_id, c.auth)
    c.graph.decide(c.decision(paused, 'approved'), c.approver())
    try:
        before = time.monotonic()
        stopped = c.graph.advance(run_id, c.auth)
        assert started.is_set()
        assert time.monotonic() - before < 3
        assert stopped['status'] == 'blocked'
        with c.store.transaction(write=False) as db:
            saved = c.runtime.load(db, run_id, c.auth)
        assert saved['error_code'] == 'TOOL_TIMEOUT'
    finally:
        release.set()


def test_tool_transport_above_registry_maximum_still_rejected(tool_context):
    c = tool_context
    c.connector.timeout += 1
    run_id = c.queue()
    paused = c.graph.advance(run_id, c.auth)
    c.graph.decide(c.decision(paused, 'approved'), c.approver())
    stopped = c.graph.advance(run_id, c.auth)
    assert stopped['status'] == 'blocked'
    assert not c.invocations
    with c.store.transaction(write=False) as db:
        saved = c.runtime.load(db, run_id, c.auth)
    assert saved['error_code'] == 'TOOL_TIMEOUT_EXCEEDED'
