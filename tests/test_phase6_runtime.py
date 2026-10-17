"""Real persistence/authority tests; all providers are offline fixtures."""
from copy import deepcopy
import json
from types import SimpleNamespace
import pytest
from fastapi.testclient import TestClient
from tests import test_runtime as fixtures
from runtime.service import RuntimeFailure
from runtime.history import query_options
from workflow_api.main import create_app, COOKIE

@pytest.fixture
def context():
    fixture=fixtures.RuntimeFixture();fixture.setUp()
    try:yield fixture
    finally:fixture.doCleanups()


def seed(context, count=6):
    ids=[]
    for i in range(count):
        request=context.request();request['idempotency_key']='phase6_run_key_'+str(i)
        result=context.runtime.create_run(request,context.auth);ids.append(result['run_id'])
        with context.store.transaction() as db:
            run=context.runtime.load(db,result['run_id'],context.auth)
            run['created_at']=1700000000+i
            if i%2:run['status']='failed'
            context.runtime.save(db,run)
    return ids


def test_run_keyset_filter_before_limit_and_workspace_isolation(context):
    ids=seed(context)
    first=context.runtime.list_runs(context.auth,limit=1,status='queued')
    assert first['items'][0]['run_id']==ids[4] and first['total']==3 and first['has_more']
    second=context.runtime.list_runs(context.auth,limit=2,status='queued',cursor=first['next_cursor'])
    assert [r['run_id'] for r in second['items']]==[ids[2],ids[0]]
    assert not second['has_more'] and second['next_cursor'] is None
    assert not context.runtime.list_runs(context.auth,workflow_id='unknown')['items']
    filtered=context.runtime.list_runs(context.auth,from_date='2023-11-14T22:13:23Z',to_date='2023-11-14T22:13:24Z')
    assert {r['run_id'] for r in filtered['items']}=={ids[3],ids[4]}
    foreign=deepcopy(context.auth);foreign['subject']['workspace_id']='other'
    assert context.runtime.list_runs(foreign)['total']==0
    assert context.runtime.list_runs(context.auth,limit=3,cursor='0')['items']==[]


def test_sequence_pages_resume_deduplicate_and_do_not_modify_evidence(context):
    run_id=seed(context,1)[0]
    with context.store.transaction() as db:
        run=context.runtime.load(db,run_id,context.auth)
        for i in range(5):context.runtime.event(db,run,'node.started',{'node_id':'n_'+str(i)})
    seen=[];after=0
    for _ in range(4):
        page=context.runtime.events(run_id,context.auth,limit=2,after_sequence=after)
        seen.extend(page['items']);after=seen[-1]['details']['recorded_sequence']
        if not page['has_more']:break
        assert page['next_cursor']==str(after)
    assert len(seen)==6 and len({e['event_id'] for e in seen})==6
    assert not context.runtime.events(run_id,context.auth,after_sequence=after)['items']
    with context.store.transaction(write=False) as db:
        assert all('recorded_sequence' not in json.loads(row[0])['details'] for row in db.execute('SELECT document FROM runtime_events'))
    foreign=deepcopy(context.auth);foreign['subject']['workspace_id']='other'
    with pytest.raises(RuntimeFailure):context.runtime.events(run_id,foreign)


@pytest.mark.parametrize('query,kind',[({'limit':'0'},'runs'),({'cursor':'-1'},'runs'),({'limit':'501'},'events'),({'after_sequence':'nan'},'events'),({'secret':'x'},'monitoring')])
def test_invalid_queries_fail_closed(query,kind):
    with pytest.raises(RuntimeFailure):query_options(query,kind)


def test_monitoring_aggregates_and_pages_without_loading_all_workflows(context):
    seed(context)
    # Monitoring must not decode all latest workflow documents.
    original=context.store.list
    context.store.list=lambda *_:(_ for _ in ()).throw(AssertionError('unbounded workflow read'))
    try:
        result=context.runtime.monitoring(context.auth,limit=1)
        assert result['runs']['total']==6 and result['runs']['failed']==3
        assert result['events']==6 and len(result['latest'])==6
        assert result['policies'][0]['scope']=='workspace:local-workspace'
        assert result['policies'][0]['enforcement']=='approved_revision'
    finally:context.store.list=original


def test_http_history_preserves_envelope_auth_and_validates_filters(context):
    ids=seed(context);context.workflows.runtime_runner=SimpleNamespace(runtime=context.runtime)
    app=create_app(context.workflows,dev_auth=True,roles=['admin'],start_workers=False)
    with TestClient(app) as client:
        response=client.get('/session');client.cookies.set(COOKIE,response.cookies[COOKIE],path='/')
        result=client.get('/runs?limit=1&status=queued',headers={'X-Request-ID':'req_phase6_http'})
        assert result.status_code==200 and result.json()['request_id']=='req_phase6_http'
        assert result.headers['cache-control']=='no-store'
        assert result.json()['data']['total']==3 and len(result.json()['data']['items'])==1
        assert client.get('/runs?limit=0').status_code==400
        assert client.get('/runs/'+ids[0]+'/events?limit=1').status_code==200
        assert client.get('/monitoring?source_cursor=-1').status_code==400
        app.state.workflow_auth['permissions']=[]
        assert client.get('/runs').status_code==403
        assert client.get('/monitoring').status_code==403
        client.cookies.clear();assert client.get('/runs').status_code==401


def test_approval_projection_requires_gate_role_permission_and_workspace_scope():
    f=fixtures.GraphTests();f.setUp()
    try:
        f.approval_graph();runner=f.runner();paused=runner.advance(f.queue(),f.auth)
        approver=f.approver();valid=f.runtime.get_run(paused['run_id'],approver)['approvals'][0]
        assert valid['required_roles']==['approver'] and valid['allowed_decisions']==['approved','rejected']
        for update in [{'roles':['viewer']},{'permissions':['runs.view']},{'scopes':[]}]:
            denied=approver|update
            assert f.runtime.get_run(paused['run_id'],denied)['approvals'][0]['allowed_decisions']==[]
            with pytest.raises(RuntimeFailure):runner.decide(f.decision(paused,'approved'),denied)
        assert f.runtime.get_run(paused['run_id'],approver)['status']=='paused_for_approval'
    finally:f.doCleanups()

@pytest.fixture
def lifecycle():
    from tests import test_lifecycle as lifecycle_fixtures
    f=lifecycle_fixtures.LifecycleTests();f.setUp()
    try:yield f
    finally:f.tearDown();f.doCleanups()


def test_missing_webhook_secret_cannot_activate_and_failure_is_durable(lifecycle):
    f=lifecycle;f.service.lifecycle.trigger_secrets={}
    with pytest.raises(Exception) as caught:f.activate(triggers=[f.trigger('generic_hmac_webhook','push')])
    assert caught.value.code=='TRIGGER_CONFIGURATION_REQUIRED'
    with f.service.store.transaction(write=False) as db:
        assert db.execute('SELECT COUNT(*) FROM lifecycle_active').fetchone()[0]==0
        assert json.loads(db.execute('SELECT document FROM lifecycle_operations').fetchone()[0])['state']=='failed'


def test_provider_preparation_requires_installed_connector_resource_and_current_grants(lifecycle):
    from workflow_api.trigger_sources import ProviderTriggerSource
    f=lifecycle;source=ProviderTriggerSource(f.service,{})
    binding=f.trigger('google_sheets','poll')
    with pytest.raises(Exception) as caught:source.validate_configuration(binding,f.workflow,f.auth)
    assert caught.value.code=='TRIGGER_CONFIGURATION_REQUIRED'
    source.connectors['google_sheets_read_rows']=object()
    with pytest.raises(Exception) as caught:source.validate_configuration(binding,f.workflow,f.auth)
    assert caught.value.code=='ASSIGNMENT_REVALIDATION_FAILED'
    from unittest.mock import patch
    with patch.object(f.service.registry_adapter,'execution_assignments',return_value=[{'tool_id':'google_sheets_read_rows'}]):
        binding['resource_id']='configured_default'
        with pytest.raises(Exception) as caught:source.validate_configuration(binding,f.workflow,f.auth)
        assert caught.value.code=='TRIGGER_CONFIGURATION_REQUIRED'


def test_readiness_pages_show_active_exact_policy_and_disabled_triggers(lifecycle):
    f=lifecycle
    first=f.activate(triggers=[f.trigger('fake_poll','poll','binding_a'),f.trigger('fake_poll','poll','binding_b')])
    later=deepcopy(f.workflow);later['version']=2;later['agents']=[]
    with f.service.store.transaction() as db:f.service.store.put(db,'local-workspace',later)
    data=f.runtime.monitoring(f.auth,limit=1)
    assert data['policies'][0]['version']==1 and data['policies'][0]['enforcement']=='active_release'
    assert data['sources'][0]['preparation_succeeded'] and data['sources'][0]['release_state']=='active'
    more=f.runtime.monitoring(f.auth,limit=1,source_cursor=data['source_next_cursor'])
    assert more['sources'][0]['binding_id']!=data['sources'][0]['binding_id']
    request={'idempotency_key':'phase6_disable_123','payload':{'workflow_id':f.workflow['workflow_id'],'expected_release_id':first['release']['release_id']}}
    f.service.lifecycle.disable(request,f.auth)
    disabled=f.runtime.monitoring(f.auth)
    assert all(s['release_state']=='disabled' and not s['preparation_succeeded'] for s in disabled['sources'])


def test_historical_approvals_keep_their_own_gate_roles():
    f=fixtures.GraphTests();f.setUp()
    try:
        f.approval_graph()
        f.workflow['nodes'].append({'node_id':'review_second','kind':'approval','label':'Second review','approval_gate_id':'gate_second'})
        f.workflow['edges'][1]['target']='review_second'
        f.workflow['edges'].append({'edge_id':'second_finish','source':'review_second','target':'finish','outcome':'approved'})
        f.workflow['approval_gates'].append({'approval_gate_id':'gate_second','approver_roles':['admin'],'on_reject':'stop','timeout_seconds':60})
        f.put();runner=f.runner();first=runner.advance(f.queue(),f.auth)
        runner.decide(f.decision(first,'approved'),f.approver())
        second=runner.advance(first['run_id'],f.auth)
        projected=f.runtime.get_run(second['run_id'],f.approver())['approvals']
        assert projected[0]['required_roles']==['approver'] and projected[0]['status']=='approved'
        assert projected[1]['required_roles']==['admin'] and projected[1]['allowed_decisions']==[]
        replay=runner.decide(f.decision(first,'approved'),f.approver())
        assert replay['status']=='paused_for_approval' and replay['approvals'][-1]['status']=='pending'
    finally:f.doCleanups()
