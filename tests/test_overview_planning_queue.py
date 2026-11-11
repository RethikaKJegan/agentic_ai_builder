"""Overview handoff through the existing durable planning queue, no model calls."""
from copy import deepcopy
import pytest
from tests.test_google_connections import setup as google_setup
from tests.test_overview_automation import intent
from workflow_api.main import create_app
from workflow_api.service import WorkflowService,ApiFailure
from runtime.service import RuntimeFailure


@pytest.fixture
def queued(google_setup):
    manager,env=google_setup
    service=WorkflowService(manager.store)
    app=create_app(service=service,dev_auth=True,roles=['admin'],start_workers=False,planning_worker_enabled=False,google_oauth_config=env)
    router=service.overview_automation
    router.env=dict(BUILDER_OVERVIEW_ROUTING_ENABLED='1',BUILDER_OVERVIEW_ROUTING_WORKSPACES='local-workspace')
    seen=[];router.interpreter=lambda *args:seen.append(args) or intent('event')
    auth=app.state.workflow_auth;jobs=app.state.planning_jobs
    body=dict(operation='prepare',objective='When a new mapped record arrives, notify the manager.',request_key='overview_queue_request')
    request=dict(operation='plan_workflow',request_id='req_overview_queue',idempotency_key=body['request_key'],payload=dict(objective=body['objective'],context={'praxi_overview_request_v1':body}))
    return service,router,auth,jobs,body,request,seen


def test_existing_queue_saves_owner_scope_and_reuses_one_interpretation(queued):
    service,router,auth,jobs,body,request,seen=queued
    job=jobs.submit(request,auth)
    assert jobs.submit(request,auth)['job_id']==job['job_id'] and not seen
    assert router.handle(auth,dict(operation='get',request_key=body['request_key']))['state']=='planning'
    assert jobs.tick()
    done=jobs.get(job['job_id'],auth)
    assert done['state']=='succeeded' and done['result']['data']['state']=='unsupported'
    assert router.handle(auth,dict(operation='get',request_key=body['request_key']))['state']=='unsupported'
    assert len(seen)==1
    foreign=deepcopy(auth);foreign['subject']['subject_id']='other'
    with pytest.raises(ApiFailure):jobs.get(job['job_id'],foreign)


def test_cancelled_queue_never_interprets_or_activates(queued):
    service,router,auth,jobs,body,request,seen=queued
    job=jobs.submit(request,auth);jobs.cancel(job['job_id'],auth)
    assert not jobs.tick() and not seen
    assert router.handle(auth,dict(operation='get',request_key=body['request_key']))['state']=='cancelled'
    with pytest.raises(ApiFailure) as error:router.handle(auth,dict(operation='activate',request_key=body['request_key']))
    assert error.value.code=='OVERVIEW_NOT_READY'


def test_cancellation_during_inert_planning_discards_queue_result_and_denies_activation(queued):
    service,router,auth,jobs,body,request,seen=queued
    job=jobs.submit(request,auth)
    def cancel(*_):
        jobs.cancel(job['job_id'],auth)
        return intent('event')
    router.interpreter=cancel
    assert jobs.tick()
    assert jobs.get(job['job_id'],auth)==dict(job_id=job['job_id'],state='cancelled',result=None)
    assert router.saved(auth,body['request_key']) is not None
    assert router.handle(auth,dict(operation='get',request_key=body['request_key']))['state']=='cancelled'
    with pytest.raises(ApiFailure):router.handle(auth,dict(operation='activate',request_key=body['request_key']))


@pytest.mark.parametrize('mutation',['disabled','objective','key','activate'])
def test_queue_revalidates_feature_and_immutable_request(mutation,queued):
    service,router,auth,jobs,body,request,seen=queued
    if mutation=='objective':request['payload']['context']['praxi_overview_request_v1']['objective']='Different goal'
    if mutation=='key':request['payload']['context']['praxi_overview_request_v1']['request_key']='different_key'
    if mutation=='activate':request['payload']['context']['praxi_overview_request_v1']['operation']='activate'
    job=jobs.submit(request,auth)
    if mutation=='disabled':router.env={}
    assert jobs.tick()
    result=jobs.get(job['job_id'],auth)
    assert result['state']=='failed' and not seen
    assert result['result']['data']['error']['error_code']=='OVERVIEW_ROUTING_UNAVAILABLE'


def test_queue_preserves_typed_business_clarifications(queued):
    service,router,auth,jobs,body,request,seen=queued
    def missing(*_):
        error=RuntimeFailure('ACTION_INPUT_REQUIRED','Select a report destination.',422)
        error.required_inputs={'spreadsheet_id':{'type':'string'}}
        raise error
    router.handle=missing
    job=jobs.submit(request,auth);assert jobs.tick()
    error=jobs.get(job['job_id'],auth)['result']['data']['error']
    assert error['error_code']=='ACTION_INPUT_REQUIRED'
    assert error['details']=={'required_inputs':{'spreadsheet_id':{'type':'string'}}}
