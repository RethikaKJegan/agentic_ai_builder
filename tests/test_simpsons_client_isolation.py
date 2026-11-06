"""Dedicated-client transport through real provisioning, retrieval and workflow APIs."""
from copy import deepcopy
import hashlib
import hmac
import json
from pathlib import Path
import time

from fastapi.testclient import TestClient
import pytest

from scripts.provision_simpsons_client import provision
from tests.test_business_retrieval import retrieval, knowledge, reference, generation, foundation, auth
from workflow_api.client_isolation import ClientIsolation, CLIENT, WORKSPACE, OWNER, HEADER
from workflow_api.main import create_app, COOKIE
from workflow_api.service import WorkflowService, ApiFailure
from workflow_api.storage import WorkflowStore
from planner import PlannerService
from tests.test_business_planning import GroundedProvider

SECRET = 'isolated-proxy-test-key-with-at-least-32-characters'


def assertion(expires=None, client=CLIENT, secret=SECRET):
    payload = f'{client}.{expires or int(time.time()) + 60}.{"a" * 48}'
    return payload + '.' + hmac.new(secret.encode(), payload.encode(), hashlib.sha256).hexdigest()


@pytest.fixture
def isolated(retrieval, tmp_path):
    x = retrieval
    source = Path(x.f.store.path)
    target = tmp_path / 'simpsons' / 'app.sqlite3'
    target_key = target.parent / 'source.key'
    source_key = Path(x.manager.env['BUILDER_DATA_SOURCE_KEY_FILE'])
    with x.f.store.transaction() as db:
        for cid in ['service', 'quality']:
            saved = json.loads(db.execute('SELECT document FROM data_source_connections WHERE connection_id=?', (cid,)).fetchone()[0])
            saved.update(generation=1, profiling_status='ready', database=cid, host='fixture.invalid', schemas=[], mode='direct', description='Simpsons test source')
            db.execute('UPDATE data_source_connections SET document=? WHERE connection_id=?', (json.dumps(saved), cid))
            snapshot = json.loads(db.execute('SELECT document FROM data_source_snapshots WHERE connection_id=? AND revision=1', (cid,)).fetchone()[0])
            for dataset in snapshot['datasets']:
                dataset.update(database=cid, schema=None, kind='collection', indexes=[], constraints=[], sample_count=1, discovery_method='sampled')
                for field in dataset['fields']:
                    field.update(field_id=cid + ':' + dataset['dataset_id'] + ':' + field['name'], discovery_method='sampled')
            snapshot.update(warnings=[], coverage='sampled')
            db.execute('UPDATE data_source_snapshots SET document=? WHERE connection_id=?', (json.dumps(snapshot), cid))
        db.execute('INSERT INTO knowledge_sources VALUES (?,?,?,?)', ('one', 'simpsons-context', json.dumps({'title': 'Simpsons engines', 'content': 'Company-specific engine service context'}), 'now'))
        db.execute('INSERT INTO knowledge_sources VALUES (?,?,?,?)', ('one', 'foreign-context', json.dumps({'title': 'Other company private context'}), 'now'))
    report = provision(source, target, source_key, target_key, ('one', 'alice'), ['service', 'quality'], ['simpsons-context'])
    env = dict(BUILDER_CLIENT_ID=CLIENT, BUILDER_SIMPSONS_PROXY_SECRET=SECRET,
               BUILDER_DATABASE_URL=str(target), BUILDER_DATA_SOURCE_KEY_FILE=str(target_key))
    service = WorkflowService(WorkflowStore(target), PlannerService(GroundedProvider()))
    service.registry_adapter.service._policy.workspace_id = WORKSPACE
    app = create_app(service, database=target, roles=['admin', 'approver'], runtime_enabled=True,
                     planning_available=True, start_workers=False, planning_worker_enabled=False,
                     google_oauth_config=env)
    return x, app, env, report


def test_provisioning_copies_only_simpsons_bindings_reencrypts_and_preserves_versions(isolated):
    x, app, env, report = isolated
    assert report['source_connections'] == 2 and report['shared_histories_copied'] == 0
    service = app.state.workflow_service
    assert app.state.workflow_auth['subject'] == {'workspace_id': WORKSPACE, 'subject_id': OWNER}
    with service.store.transaction(write=False) as db:
        assert {r[0] for r in db.execute('SELECT connection_id FROM data_source_connections')} == {'service', 'quality'}
        assert db.execute('SELECT source_id FROM knowledge_sources').fetchall() == [('simpsons-context',)]
        assert not db.execute('SELECT 1 FROM revisions').fetchone()
        encrypted = db.execute("SELECT secret FROM data_source_connections WHERE connection_id='service'").fetchone()[0]
        plain = json.loads(app.state.data_sources.cipher.decrypt(encrypted.encode()))
        assert plain['database'] == 'service'
        original = x.f.version(x.a, x.version)
        copied = app.state.business_ontology.version(app.state.workflow_auth, x.version)
        assert copied == original
    assert ClientIsolation.configured(env).database == Path(service.store.path)
    with service.store.transaction() as db:
        db.execute('CREATE TABLE scoped_automation_fixture(workspace TEXT,owner TEXT)')
        db.execute('INSERT INTO scoped_automation_fixture VALUES (?,?)', (WORKSPACE, 'automation:server-owned-release'))
    assert ClientIsolation.configured(env).subject == app.state.workflow_auth['subject']
    with pytest.raises(ValueError):
        provision(Path(x.f.store.path), Path(service.store.path), Path(x.manager.env['BUILDER_DATA_SOURCE_KEY_FILE']), Path(env['BUILDER_DATA_SOURCE_KEY_FILE']), ('one', 'alice'), ['service', 'quality'])


def test_every_route_including_session_rejects_anonymous_dev_cookie_forged_and_expired_identity(isolated):
    _, app, _, _ = isolated
    with TestClient(app) as client:
        for token in ['', assertion(secret='wrong-key'), assertion(expires=int(time.time()) - 1), assertion(client='other'), assertion(expires=int(time.time()) + 1000)]:
            for route in ['/session', '/workflows', '/data-sources', '/business-ontology/v1', '/webhooks/slack']:
                response = client.get(route, headers={HEADER: token, 'Cookie': f'{COOKIE}=anything', 'x-workspace-id': 'local-workspace'})
                assert response.status_code == 401, (route, response.text)
        session = client.get('/session', headers={HEADER: assertion()})
        assert session.status_code == 200
        assert session.json()['data']['mode'] == 'client-isolated'
        assert session.headers['x-builder-client'] == CLIENT
        assert 'set-cookie' not in session.headers


def test_shared_backend_rejects_simpsons_assertions_and_mixed_stores_fail_closed(isolated, tmp_path):
    _, _, env, _ = isolated
    shared = WorkflowService(WorkflowStore(tmp_path / 'shared.sqlite3'))
    with TestClient(create_app(shared, dev_auth=True, start_workers=False)) as client:
        assert client.get('/session', headers={HEADER: assertion()}).status_code == 403
    with pytest.raises(ValueError):
        create_app(shared, google_oauth_config=env)
    with shared.store.transaction() as db:
        db.execute('INSERT INTO workspace_settings VALUES (?,?,?,?)', ('foreign-company', 'secret', '{}', 'now'))
        db.execute('CREATE TABLE client_isolation(client_id,workspace,owner)')
        db.execute('INSERT INTO client_isolation VALUES (?,?,?)', (CLIENT, WORKSPACE, OWNER))
        db.execute('CREATE TABLE client_source_bindings(connection_id)')
        db.executemany('INSERT INTO client_source_bindings VALUES (?)', [('service',), ('quality',)])
    with pytest.raises(ValueError, match='another company'):
        ClientIsolation.configured({**env, 'BUILDER_DATABASE_URL': shared.store.path})


def test_authenticated_natural_language_retrieval_and_worker_use_only_copied_simpsons_sources(isolated):
    x, app, _, _ = isolated
    authority = app.state.workflow_auth
    # Use the real query/evidence path with controlled company transport, never a remote call.
    retrieval_service = app.state.business_retrieval
    retrieval_service.reader = x.reader
    preview = retrieval_service.preview(authority, dict(question='Show complaints for engine E123.', request_key='simpsons_client_question'))
    result = retrieval_service.execute(authority, preview['request_id'], {})
    assert result and x.reader.calls
    assert {c['database'] for c in x.reader.calls} <= {'service', 'quality'}
    assert app.state.business_sources.resolve(WORKSPACE, OWNER)['subject'] == authority['subject']
    assert app.state.business_sources.resolve('one', 'alice') is None
    for field in ['workspace_id', 'subject_id']:
        foreign = deepcopy(authority)
        foreign['subject'][field] = 'foreign'
        with pytest.raises(ApiFailure):
            retrieval_service.execute(foreign, preview['request_id'], {})
    with TestClient(app) as client:
        client.headers[HEADER] = assertion()
        sources = client.get('/data-sources').json()['data']['items']
        assert {s['connection_id'] for s in sources} == {'service', 'quality'}
        assert client.get('/data-sources/other/metadata').status_code == 404
        planned = client.post('/business-ontology/v1/retrieval/preview', json={
            'question': 'Show complaints for engine E123.', 'request_key': 'simpsons_http_question'})
        assert planned.status_code == 200, planned.text
        request_id = planned.json()['data']['request_id']
        evidence = client.post(f'/business-ontology/v1/retrieval/{request_id}/execute', json={})
        assert evidence.status_code == 200, evidence.text
        assert evidence.json()['data']['records']
        assert {c['database'] for c in x.reader.calls} <= {'service', 'quality'}
        for path in ['/data-sources', '/data-sources/test', '/data-sources/service/credentials']:
            response = client.post(path, json={'uri': 'mongodb://foreign.invalid/another-company'})
            assert response.status_code == 403, response.text


def test_chat_planning_jobs_and_saved_workflow_execute_under_client_identity(isolated):
    _, app, _, _ = isolated
    service = app.state.workflow_service
    with TestClient(app) as client:
        client.headers[HEADER] = assertion()
        request = dict(request_id='req_simpsons_plan', operation='plan_workflow',
                       idempotency_key='simpsons_planning_key_001', payload={'objective': 'Summarize Simpsons engine service notes'})
        submitted = client.post('/planning-jobs', json=request)
        assert submitted.status_code == 202, submitted.text
        assert app.state.planning_jobs.tick()
        job = client.get('/planning-jobs/' + submitted.json()['data']['job_id']).json()['data']
        assert job['state'] == 'succeeded', json.dumps(job)
        document = job['result']['data']['workflow']
        assert document['workflow_id']
        context = service.planner.provider.contexts[-1]
        assert {k['source_id'] for k in context['workspace_knowledge']} == {'simpsons-context'}
        assert context['business_ontology_retrieval']['state'] == 'matched'
        with service.store.transaction(write=False) as db:
            assert {r[0] for r in db.execute('SELECT workspace FROM revisions')} <= {WORKSPACE}
        # Existing runtime path with a deterministic executable graph; no new engine or fake HTTP result.
        document.update(workflow_id='simpsons_execution', version=1, status='draft', agents=[], tools=[], conditions=[], approval_gates=[], metadata={})
        document['nodes'] = [dict(node_id='start', kind='trigger', label='Start'), dict(node_id='finish', kind='output', label='Finish')]
        document['edges'] = [dict(edge_id='start_finish', source='start', target='finish')]
        document['execution_policy']['allow_external_writes'] = False
        document['inputs'], document['outputs'] = [], []
        def operation(path, op, payload, method='post'):
            return getattr(client, method)(path, json=dict(request_id='req_client_operation', operation=op,
                idempotency_key='simpsons_' + op + '_' + payload.get('action', '') + '_001', payload=payload))
        ref = dict(workflow_id=document['workflow_id'], workflow_version=1)
        saved = operation('/workflows/simpsons_execution/versions/1', 'save_workflow_version', {**ref, 'workflow': document, 'base_version': 0}, 'put')
        assert saved.status_code == 200, saved.text
        validated = operation('/workflows/simpsons_execution/validate', 'validate_workflow', ref)
        assert validated.status_code == 200, validated.text
        for action in ['approve', 'publish']:
            response = operation('/workflows/simpsons_execution/approve', 'approve_workflow', {**ref, 'action': action})
            assert response.status_code == 200, response.text
        executed = operation('/workflows/simpsons_execution/execute', 'execute_workflow', {**ref, 'inputs': {}})
        assert executed.status_code == 200, executed.text
        run = executed.json()['data']['run']
        assert run['status'] == 'completed', run
        with service.store.transaction(write=False) as db:
            stored_run = json.loads(db.execute('SELECT document FROM runtime_runs WHERE workspace=? AND run_id=?', (WORKSPACE, run['run_id'])).fetchone()[0])
            assert stored_run['subject_id'] == OWNER and stored_run['workspace_id'] == WORKSPACE
        # Supplying browser authority is rejected at the existing service boundary.
        denied = operation('/workflows/simpsons_execution/validate', 'validate_workflow', {**ref, 'subject': {'workspace_id': 'foreign'}})
        assert denied.status_code == 400


def test_full_configured_backend_and_workers_share_client_identity_without_shared_integrations(isolated):
    from types import SimpleNamespace
    from workflow_api.live_providers import create_configured_app, authenticate
    _, _, env, _ = isolated
    env.update(BUILDER_ENVIRONMENT='test', BUILDER_DEV_AUTH='1', OPENAI_API_KEY='offline-test-key',
               OPENAI_MODEL='offline-model', BUILDER_MODEL_RATES=json.dumps({'offline-model': {'input_per_token': 0, 'output_per_token': 0}}))
    # Constructors only: no lifespan/workers/network calls run during this test.
    # The trusted Registry loader requires repository-local configuration paths.
    from unittest.mock import patch
    from workflow_api.registry_adapter import load_registry_config
    import tempfile
    with tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parents[1] / '.local') as registry_dir:
        original = load_registry_config
        def load(path, **kwargs):
            copied = Path(registry_dir) / 'registry.json'
            copied.write_text(Path(path).read_text())
            return original(copied, **kwargs)
        with patch('workflow_api.main.load_registry_config', side_effect=load):
            app = create_configured_app(env, client=SimpleNamespace(), model_factory=lambda _: None)
    assert app.state.workflow_auth['subject'] == app.state.live_operator_auth['subject'] == {'workspace_id': WORKSPACE, 'subject_id': OWNER}
    service = app.state.workflow_service
    assert authenticate(service, app.state.live_operator_auth, 'local-workspace', 'local-builder') is None
    assert service.worker_authenticate(WORKSPACE, OWNER)['subject'] == app.state.workflow_auth['subject']
    assert 'smtp_send_email' not in service.runtime_runner.connectors
    assert 'google_sheets_read_rows' not in service.runtime_runner.connectors
    assert service.business_preparation is not None


def test_valid_process_lease_does_not_prevent_client_restart(isolated):
    _,app,env,_=isolated
    with app.state.workflow_service.store.transaction() as db:
        db.execute('CREATE TABLE IF NOT EXISTS builder_worker_leases(name TEXT PRIMARY KEY,owner TEXT NOT NULL,expires REAL NOT NULL)')
        db.execute('INSERT INTO builder_worker_leases VALUES (?,?,?)',('builder-live-workers','worker_'+'a'*32,0))
    assert ClientIsolation.configured(env).subject=={'workspace_id':WORKSPACE,'subject_id':OWNER}
    with app.state.workflow_service.store.transaction() as db:
        db.execute('UPDATE builder_worker_leases SET owner=?',('foreign-company',))
    with pytest.raises(ValueError,match='invalid worker lease'):ClientIsolation.configured(env)


def test_session_reports_optional_reply_monitor_availability(isolated):
    _,app,_,_=isolated
    with TestClient(app) as client:
        client.headers[HEADER]=assertion()
        assert client.get('/session').json()['data']['reply_monitor_available'] is False
        from types import SimpleNamespace
        app.state.workflow_service.reply_cases=SimpleNamespace()
        assert client.get('/session').json()['data']['reply_monitor_available'] is True
