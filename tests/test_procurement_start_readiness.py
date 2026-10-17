"""Run admission and connector races use generated plans and offline providers."""
import json
from unittest.mock import patch
import pytest
from connector_extension.procurement.store import ProcurementError
from tests import test_integrated_procurement as fixtures


@pytest.fixture
def native():
    context = fixtures.IntegratedTests()
    context.setUp()
    try:
        yield context
    finally:
        context.doCleanups()


def publish(context):
    workflow = context.call('plan_workflow', {
        'objective': 'Procurement RFQ simulation from https://docs.google.com/spreadsheets/d/requirements_book/edit and https://docs.google.com/spreadsheets/d/vendors_book/edit',
        'context': {'execution_input_mode': 'automatic'},
    })['workflow']
    ref = {'workflow_id': workflow['workflow_id'], 'workflow_version': workflow['version']}
    context.call('save_workflow_version', {**ref, 'base_version': 0, 'workflow': workflow})
    context.call('validate_workflow', ref)
    context.call('approve_workflow', {**ref, 'action': 'approve'})
    context.call('approve_workflow', {**ref, 'action': 'publish'})
    return workflow, ref


def activate(context, ref):
    return context.service.lifecycle.activate({'request_id': 'activate_readiness', 'idempotency_key': 'activate_readiness',
        'payload': {**ref, 'triggers': []}}, context.auth)['release']


@pytest.mark.parametrize('state', ['missing', 'disabled', 'wrong_revision', 'other_workspace'])
def test_inactive_start_is_rejected_before_any_run_or_project(native, state):
    workflow, ref = publish(native)
    if state != 'missing':
        release = activate(native, ref)
        if state == 'disabled': release['state'] = 'disabled'
        elif state == 'wrong_revision': release['revision']['workflow_version'] += 1
        with native.service.store.transaction() as db:
            db.execute('UPDATE lifecycle_releases SET document=?, workspace=? WHERE release_id=?',
                (json.dumps(release), 'another_workspace' if state == 'other_workspace' else 'local-workspace', release['release_id']))
    with native.service.store.transaction(write=False) as db:
        before = db.execute('SELECT COUNT(*) FROM runtime_runs').fetchone()[0]
    result = native.service.handle({'request_id': 'inactive_start', 'operation': 'execute_workflow',
        'idempotency_key': 'inactive_start', 'payload': {**ref, 'inputs': {}}}, native.auth)
    assert result['status'] == 409
    assert result['data']['error']['error_code'] == 'PROCUREMENT_WORKFLOW_INACTIVE'
    assert 'Activate' in result['data']['error']['message']
    with native.service.store.transaction(write=False) as db:
        assert db.execute('SELECT COUNT(*) FROM runtime_runs').fetchone()[0] == before
    with pytest.raises(ProcurementError, match='PROCUREMENT_PROJECT_NOT_FOUND'):
        native.procurement.job('local-workspace', workflow['metadata']['procurement_plan']['project_id'])
    assert not native.http.sent


def test_activation_race_preserves_specific_runtime_failure(native):
    _, ref = publish(native)
    activate(native, ref)
    native.service.background_execution = True
    run = native.call('execute_workflow', {**ref, 'inputs': {}})['run']
    with patch.object(native.procurement, 'active', return_value=False):
        result = native.service.runtime_runner.advance(run['run_id'], native.auth)
    assert result['status'] == 'failed'
    events = native.call('list_run_events', {'run_id': run['run_id']})['items']
    assert any(event['event_type'] == 'node.failed' and event['details']['error_code'] == 'PROCUREMENT_WORKFLOW_INACTIVE' for event in events)
    assert not native.http.sent


def test_setup_domain_error_is_not_replaced_by_generic_invocation_failure(native):
    _, ref = publish(native)
    activate(native, ref)
    with patch.object(native.procurement, 'setup', side_effect=ProcurementError('PROCUREMENT_SOURCE_INVALID')):
        run = native.call('execute_workflow', {**ref, 'inputs': {}})['run']
    events = native.call('list_run_events', {'run_id': run['run_id']})['items']
    assert run['status'] == 'failed'
    assert any(event['event_type'] == 'node.failed' and event['details']['error_code'] == 'PROCUREMENT_SOURCE_INVALID' for event in events)
    assert not native.http.sent
