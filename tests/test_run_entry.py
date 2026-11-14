"""Manual Run preflight and human approval; both tenant scopes, no provider writes."""
from copy import deepcopy
import json
from pathlib import Path
import pytest
from planner import PlannerService
from planner.provider import RuleBasedStructuredOutputProvider
from workflow_api.storage import WorkflowStore
from workflow_api.service import WorkflowService,ApiFailure
from workflow_api.run_entry import start,resume_pending
from runtime import RuntimeService
from runtime.graph import GraphRunner
from runtime.service import RuntimeFailure,digest

@pytest.fixture(params=['client-simpsons','client-subway'])
def run_context(tmp_path,request):
    service=WorkflowService(WorkflowStore(tmp_path/'run.sqlite3'),PlannerService(RuleBasedStructuredOutputProvider()))
    service.runtime_runner=GraphRunner(RuntimeService(service));service.background_execution=True
    auth=dict(subject=dict(workspace_id=request.param,subject_id='owner'),roles=['admin'],permissions=['workflow.view','workflow.edit','workflow.validate','workflow.approve','workflow.execute','runs.view','tools.read','tools.assign'],scopes=['workspace:read','workspace:write'],decision='allow')
    service.worker_authenticate=lambda workspace,owner:deepcopy(auth) if (workspace,owner)==(request.param,'owner') else None
    workflow=json.loads((Path(__file__).parents[1]/'shared/contracts/examples/workflows/support-triage.json').read_text())
    workflow.update(status='draft',agents=[],tools=[],conditions=[],approval_gates=[],inputs=[],outputs=[],nodes=[dict(node_id='start',kind='trigger',label='Start'),dict(node_id='finish',kind='output',label='Finish')],edges=[dict(edge_id='next',source='start',target='finish')])
    workflow['execution_policy']['allow_external_writes']=False
    workflow['metadata']={'workspace_id':request.param}
    with service.store.transaction() as db:service.store.put(db,request.param,workflow)
    req=dict(request_id='manual_run',operation='execute_workflow',idempotency_key='run_intent_123456',payload=dict(workflow_id=workflow['workflow_id'],workflow_version=workflow['version'],inputs={}))
    return service,workflow,auth,req

def get(s,w,a):
    with s.store.transaction(write=False) as db:return s.store.get(db,a['subject']['workspace_id'],w['workflow_id'],w['version'])
def count(s):
    with s.store.transaction(write=False) as db:return db.execute('SELECT count(*) FROM runtime_runs').fetchone()[0]
def approve(s,w,a):
    result=s.handle(dict(request_id='human_review',operation='approve_workflow',idempotency_key='human_decision_123',payload=dict(workflow_id=w['workflow_id'],workflow_version=w['version'],action='approve')),a)
    assert result['status']==200,result

def test_run_checks_draft_and_waits_for_real_human_approval(run_context):
    s,w,a,r=run_context
    with pytest.raises(ApiFailure) as error:start(s,r,a)
    assert error.value.code=='WORKFLOW_APPROVAL_REQUIRED'
    document=get(s,w,a);assert document['status']=='validated'
    assert document['metadata']['validation_report']['ready']
    assert 'approved_by' not in document['metadata'];assert count(s)==0
    approve(s,w,a)
    resumed=resume_pending(s,w['workflow_id'],w['version'],a)
    assert len(resumed)==1 and count(s)==1
    assert start(s,r,a)['run_id']==resumed[0]['run_id']
    assert s.runtime_runner.advance(resumed[0]['run_id'],a)['status']=='completed'
    assert count(s)==1

def test_missing_inputs_does_not_create_run_or_request_approval(run_context):
    s,w,a,r=run_context;w['inputs']=[dict(name='recipient',type='string',required=True,description='Selected recipient')]
    with s.store.transaction() as db:s.store.put(db,a['subject']['workspace_id'],w)
    with pytest.raises(ApiFailure) as error:start(s,r,a)
    assert error.value.code=='INVALID_INPUT' and error.value.field=='inputs.recipient'
    assert 'recipient' in str(error.value)
    assert count(s)==0;assert get(s,w,a)['status']=='draft'

@pytest.mark.parametrize('problem',['ontology','binding'])
def test_invalid_configuration_never_queues_run(run_context,problem):
    s,w,a,r=run_context
    if problem=='ontology':w['metadata']['unresolved_requirements']=['Mandatory ontology mapping is unavailable.']
    else:w['edges'][0]['target']='missing_task'
    with s.store.transaction() as db:s.store.put(db,a['subject']['workspace_id'],w)
    with pytest.raises(ApiFailure):start(s,r,a)
    assert count(s)==0;assert 'approved_by' not in get(s,w,a)['metadata']

def test_simultaneous_different_keys_coalesce_only_same_owner_inputs(run_context):
    s,w,a,r=run_context
    with pytest.raises(ApiFailure):start(s,r,a)
    approve(s,w,a)
    first=start(s,r,a);second=start(s,{**r,'idempotency_key':'another_run_key_123'},a)
    assert first['run_id']==second['run_id'];assert count(s)==1

def test_changed_revision_and_foreign_tenant_are_blocked(run_context):
    s,w,a,r=run_context
    with pytest.raises(ApiFailure):start(s,r,a)
    document=get(s,w,a);document['nodes'][-1]['label']='Changed after Run requested'
    with s.store.transaction() as db:s.store.put(db,a['subject']['workspace_id'],document)
    # A former request cannot become authority for the changed plan.
    approve(s,w,a)
    assert resume_pending(s,w['workflow_id'],w['version'],a)==[]
    foreign=deepcopy(a);foreign['subject']['workspace_id']='foreign'
    with pytest.raises(ApiFailure):start(s,r,foreign)
    assert count(s)==0

def test_exact_preflight_revision_rechecked_under_runtime_transaction(run_context):
    s,w,a,r=run_context
    with pytest.raises(ApiFailure):start(s,r,a)
    approve(s,w,a);document=get(s,w,a);expected=digest(document)
    document['nodes'][-1]['label']='Concurrent edit'
    with s.store.transaction() as db:s.store.put(db,a['subject']['workspace_id'],document)
    with pytest.raises((ApiFailure,RuntimeFailure)):s.runtime_runner.runtime.create_run(r,a,expected_digest=expected,coalesce=True)
    assert count(s)==0

def test_execution_permission_rechecked_when_approval_arrives(run_context):
    s,w,a,r=run_context
    with pytest.raises(ApiFailure):start(s,r,a)
    approve(s,w,a);revoked=deepcopy(a);revoked['permissions'].remove('workflow.execute')
    s.worker_authenticate=lambda *_:revoked
    assert resume_pending(s,w['workflow_id'],w['version'],a)==[];assert count(s)==0

def test_removed_public_validate_routes(run_context):
    from fastapi.testclient import TestClient
    from workflow_api.main import create_app,COOKIE
    s,w,a,r=run_context
    with TestClient(create_app(s,dev_auth=True,roles=['admin'],start_workers=False)) as client:
        session=client.get('/session');client.cookies.set(COOKIE,session.cookies[COOKIE],path='/')
        assert client.post('/workflows/'+w['workflow_id']+'/validate',json={}).status_code==404
        assert client.post('/business-ontology/v1/investigations/plans/'+w['workflow_id']+'/validate',json={}).status_code==404


def test_repeated_pending_clicks_cannot_repeat_a_fast_completed_run(run_context):
    s,w,a,r=run_context;second={**r,'idempotency_key':'second_click_before_review'}
    for request in (r,second):
        with pytest.raises(ApiFailure) as pending:start(s,request,a)
        assert pending.value.code=='WORKFLOW_APPROVAL_REQUIRED'
    approve(s,w,a);resumed=resume_pending(s,w['workflow_id'],w['version'],a)
    assert len({run['run_id'] for run in resumed})==1 and count(s)==1
    first=resumed[0];assert s.runtime_runner.advance(first['run_id'],a)['status']=='completed'
    assert start(s,second,a)['run_id']==first['run_id'];assert count(s)==1
    assert resume_pending(s,w['workflow_id'],w['version'],a)==[]


def test_http_run_waits_and_human_approval_resumes_once(run_context):
    from fastapi.testclient import TestClient
    from workflow_api.main import create_app,COOKIE
    s,w,a,r=run_context
    app=create_app(s,dev_auth=True,roles=['admin'],start_workers=False,planning_worker_enabled=False)
    app.state.workflow_auth.clear();app.state.workflow_auth.update(deepcopy(a))
    with TestClient(app) as client:
        session=client.get('/session');client.cookies.set(COOKIE,session.cookies[COOKIE],path='/')
        pending=client.post('/workflows/'+w['workflow_id']+'/execute',json=r)
        assert pending.status_code==409,pending.text
        assert pending.json()['data']['error']['error_code']=='WORKFLOW_APPROVAL_REQUIRED'
        assert count(s)==0
        approval=dict(request_id='http_human_review',operation='approve_workflow',idempotency_key='http_human_review_key',payload=dict(workflow_id=w['workflow_id'],workflow_version=w['version'],action='approve'))
        accepted=client.post('/workflows/'+w['workflow_id']+'/approve',json=approval)
        assert accepted.status_code==200,accepted.text
        assert count(s)==1
        retried=client.post('/workflows/'+w['workflow_id']+'/execute',json=r)
        assert retried.status_code==200,retried.text
        run=retried.json()['data']['run']
        assert s.runtime_runner.advance(run['run_id'],a)['status']=='completed'
        repeated=client.post('/workflows/'+w['workflow_id']+'/approve',json=approval)
        assert repeated.status_code==200,repeated.text
        assert count(s)==1


def test_changed_semantically_reviewed_configuration_requires_fresh_checks(run_context):
    s,w,a,r=run_context
    w['metadata']['original_objective']='Complete the defined steps.'
    s.planner.provider.review_requirements=lambda *_:dict(issues=[],covered_requirements=['Complete the defined steps.'])
    with s.store.transaction() as db:s.store.put(db,a['subject']['workspace_id'],w)
    with pytest.raises(ApiFailure) as pending:start(s,r,a)
    assert pending.value.code=='WORKFLOW_APPROVAL_REQUIRED'
    changed=get(s,w,a);assert changed['metadata']['validation_report']['model_assessment'] is not None
    changed['nodes'][-1]['label']='Changed after semantic review'
    with s.store.transaction() as db:s.store.put(db,a['subject']['workspace_id'],changed)
    result=s.handle(dict(request_id='stale_review',operation='approve_workflow',idempotency_key='stale_review_key_123',payload=dict(workflow_id=w['workflow_id'],workflow_version=w['version'],action='approve')),a)
    assert result['status']==409,result
    assert result['data']['error']['error_code']=='WORKFLOW_READINESS_STALE'
    assert count(s)==0



def test_display_title_does_not_change_the_executable_revision(run_context):
    from workflow_api.workflow_titles import rename
    s,w,a,r=run_context
    rename(s,a,w['workflow_id'],dict(name='Renamed workflow',expected_name=w['name']))
    with pytest.raises(ApiFailure) as pending:start(s,r,a)
    assert pending.value.code=='WORKFLOW_APPROVAL_REQUIRED'
    rename(s,a,w['workflow_id'],dict(name='Another display title',expected_name='Renamed workflow'))
    assert get(s,w,a)['name']==w['name']
    approve(s,w,a);resumed=resume_pending(s,w['workflow_id'],w['version'],a)
    assert len(resumed)==1
    assert start(s,r,a)['run_id']==resumed[0]['run_id']
    assert s.runtime_runner.advance(resumed[0]['run_id'],a)['status']=='completed'
    assert count(s)==1
