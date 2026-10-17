"""Phase 1 regression checks; isolated storage and offline planner only."""
from copy import deepcopy
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import time
from unittest.mock import patch

from fastapi.testclient import TestClient
import pytest

from planner import PlannerService
from planner.provider import RuleBasedStructuredOutputProvider
from workflow_api.main import create_app, COOKIE
from workflow_api.live_providers import create_configured_app
from workflow_api.planning_jobs import PlanningJobs
from workflow_api.security import origins, PUBLIC_ORIGIN
from workflow_api.service import ApiFailure, WorkflowService
from workflow_api.storage import WorkflowStore


@pytest.fixture
def service(tmp_path):
    return WorkflowService(WorkflowStore(tmp_path / 'phase1.sqlite3'), PlannerService(RuleBasedStructuredOutputProvider()))


def test_origins_trim_and_reject_scheme_host_port_mismatches(service):
    app = create_app(service, dev_auth=True, ui_origins='  http://localhost:3000 , http://127.0.0.1:3001  ')
    with TestClient(app) as client:
        for origin in ['http://localhost:3000', 'http://127.0.0.1:3001']:
            assert client.get('/session', headers={'Origin': origin}).status_code == 200
        for origin in ['https://localhost:3000', 'http://localhost:3001', 'http://localhost:3000.evil.example', 'null', PUBLIC_ORIGIN]:
            response = client.get('/session', headers={'Origin': origin})
            assert response.status_code == 403
            assert response.json()['data']['error']['error_code'] == 'ORIGIN_NOT_AUTHORIZED'
        assert app.state.allowed_origins == {'http://localhost:3000', 'http://127.0.0.1:3001'}


@pytest.mark.parametrize('origin', ['*', 'https://example.com/path', 'https://user:pass@example.com', 'https://example.com?query=1', 'https://example.com#x', 'https://example.com:bad', 'https://example.com:0', 'null', ''])
def test_invalid_origin_configuration_fails(origin):
    with pytest.raises(ValueError):
        origins(origin, production=True)


def test_public_origin_explicitly_supported_for_future_production():
    assert origins('  ' + PUBLIC_ORIGIN + '  ', production=True) == {PUBLIC_ORIGIN}
    assert origins(None, production=True) == {PUBLIC_ORIGIN}
    with pytest.raises(ValueError):
        origins('http://praxi.bellcorpstudio.com', production=True)


@pytest.mark.parametrize('enabled', [True, False])
def test_production_fails_closed_until_deferred_login_is_implemented(service, enabled):
    with pytest.raises(ValueError, match='Google Workspace'):
        create_app(service, dev_auth=enabled, environment_name='production')


def test_live_launcher_requires_explicit_local_auth_before_writing_provider_files():
    with patch('workflow_api.live_providers.registry_configuration') as config:
        for env in [{}, {'BUILDER_ENVIRONMENT': 'production'}, {'BUILDER_ENVIRONMENT': 'development'}]:
            with pytest.raises(ValueError):
                create_configured_app(env)
        config.assert_not_called()


def test_development_sessions_reject_remote_hosts_and_cross_site(service):
    app = create_app(service, dev_auth=True)
    with TestClient(app, base_url=PUBLIC_ORIGIN) as client:
        assert client.get('/session').status_code == 403
    with TestClient(app) as client:
        assert client.get('/session', headers={'Sec-Fetch-Site': 'cross-site'}).status_code == 403


def test_expired_and_missing_cookie_are_401_and_errors_keep_ids(service):
    with TestClient(create_app(service, dev_auth=True)) as client:
        for value in ['', 'expired']:
            response = client.get('/workflows', headers={'Cookie': f'{COOKIE}={value}', 'X-Request-ID': 'req_phase1', 'X-Correlation-ID': 'corr_phase1'})
            assert response.status_code == 401
            assert response.json()['data']['error']['request_id'] == 'req_phase1'
            assert response.headers['x-request-id'] == 'req_phase1'
            assert response.headers['x-correlation-id'] == 'corr_phase1'
            assert response.headers['cache-control'] == 'no-store'
            assert response.headers['x-builder-service'] == 'workflow-api'


def test_launcher_passes_merged_origins_to_fastapi(tmp_path):
    # Stop immediately after create_app: no providers, workers or credentials accessed.
    class Configured(Exception): pass
    with patch('workflow_api.live_providers.registry_configuration', return_value={}), \
         patch('workflow_api.procurement.configuration', return_value=None), \
         patch('workflow_api.live_providers.model_configuration', return_value=('offline', {}, {})), \
         patch('workflow_api.live_providers.private_write'), \
         patch('workflow_api.live_providers.create_app', side_effect=Configured) as factory:
        with pytest.raises(Configured):
            create_configured_app({'BUILDER_ENVIRONMENT': 'test', 'BUILDER_DEV_AUTH': '1', 'BUILDER_UI_ORIGINS': '  http://localhost:3100  '})
        assert factory.call_args.kwargs['ui_origins'] == {'http://localhost:3100'}
        assert factory.call_args.kwargs['environment_name'] == 'test'


@pytest.fixture
def planning(service):
    auth = dict(subject=dict(subject_id='planner-user', workspace_id='workspace-a'), roles=['builder'], permissions=['workflow.plan'], scopes=[], decision='allow')
    jobs = PlanningJobs(service, lambda workspace, subject: deepcopy(auth) if (workspace, subject) == ('workspace-a', 'planner-user') else None)
    request = {'request_id': 'req_job', 'operation': 'plan_workflow', 'idempotency_key': 'planning_retry_key', 'payload': {'objective': 'Summarize notes'}}
    return jobs, auth, request


def test_planning_persists_idempotency_and_result_after_recreation(planning):
    jobs, auth, request = planning
    submitted = jobs.submit(request, auth)
    assert submitted['state'] == 'queued'
    restarted = PlanningJobs(jobs.service, jobs.authenticate)
    assert restarted.submit({**request, 'request_id': 'req_retry'}, auth)['job_id'] == submitted['job_id']
    assert restarted.tick()
    completed = restarted.get(submitted['job_id'], auth)
    assert completed['state'] == 'succeeded', completed
    assert completed['result']['data']['workflow']['status'] == 'draft'
    assert jobs.submit(request, auth)['state'] == 'succeeded'
    assert not restarted.tick()


def test_planning_is_workspace_and_subject_scoped(planning):
    jobs, auth, request = planning
    submitted = jobs.submit(request, auth)
    for field in ['subject_id', 'workspace_id']:
        other = deepcopy(auth)
        other['subject'][field] = 'other'
        with pytest.raises(ApiFailure) as failure:
            jobs.get(submitted['job_id'], other)
        assert failure.value.status == 404
        with pytest.raises(ApiFailure):
            jobs.cancel(submitted['job_id'], other)
    denied = {**auth, 'permissions': []}
    with pytest.raises(ApiFailure) as failure:
        jobs.submit(request, denied)
    assert failure.value.status == 403


def test_planning_key_reuse_does_not_overwrite_original(planning):
    jobs, auth, request = planning
    job = jobs.submit(request, auth)
    with pytest.raises(ApiFailure) as failure:
        jobs.submit({**request, 'payload': {'objective': 'Different request'}}, auth)
    assert failure.value.code == 'IDEMPOTENCY_KEY_REUSED'
    assert jobs.get(job['job_id'], auth)['state'] == 'queued'


def test_cancelled_planning_does_not_generate_or_store_late_results(planning):
    jobs, auth, request = planning
    job = jobs.submit(request, auth)
    with patch.object(jobs.service, 'handle') as generate:
        assert jobs.cancel(job['job_id'], auth)['state'] == 'cancelled'
        assert not jobs.tick()
        generate.assert_not_called()
    request['idempotency_key'] = 'cancel_in_flight'
    job = jobs.submit(request, auth)
    original = jobs.service.handle
    def generate_and_cancel(body, authority):
        jobs.cancel(job['job_id'], auth)
        return original(body, authority)
    with patch.object(jobs.service, 'handle', side_effect=generate_and_cancel):
        jobs.tick()
    assert jobs.get(job['job_id'], auth) == {'job_id': job['job_id'], 'state': 'cancelled', 'result': None}


def test_interrupted_planning_is_not_automatically_replayed(planning):
    jobs, auth, request = planning
    job = jobs.submit(request, auth)
    with jobs.store.transaction() as db:
        db.execute("UPDATE builder_planning_jobs SET state='running', lease_until=0 WHERE job_id=?", (job['job_id'],))
    assert not jobs.tick()
    result = jobs.get(job['job_id'], auth)
    assert result['state'] == 'failed'
    assert result['result']['data']['error']['error_code'] == 'PLANNING_INTERRUPTED'


def test_queued_planning_revalidates_authority(planning):
    jobs, auth, request = planning
    job = jobs.submit(request, auth)
    jobs.authenticate = lambda *_: None
    jobs.tick()
    assert jobs.get(job['job_id'], auth)['result']['status'] == 403


def test_async_planning_endpoints_require_session_and_complete(service):
    with TestClient(create_app(service, dev_auth=True)) as client:
        request = {'request_id': 'req_http_job', 'operation': 'plan_workflow', 'idempotency_key': 'http_planning_retry', 'payload': {'objective': 'Summarize notes'}}
        assert client.post('/planning-jobs', json=request).status_code == 401
        session = client.get('/session')
        assert session.json()['data']['planning_jobs_available'] is True
        client.cookies.set(COOKIE, session.cookies[COOKIE], path='/')
        response = client.post('/planning-jobs', json=request)
        assert response.status_code == 202, response.text
        job_id = response.json()['data']['job_id']
        until = time.monotonic() + 10
        while time.monotonic() < until:
            data = client.get('/planning-jobs/' + job_id).json()['data']
            if data['state'] not in {'queued', 'running'}:
                break
            time.sleep(.02)
        assert data['state'] == 'succeeded', data
        assert client.delete('/planning-jobs/' + job_id).json()['data']['state'] == 'succeeded'
