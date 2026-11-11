"""Existing HTTP action-plan boundary, session feature flag and authentication."""
from copy import deepcopy
from fastapi.testclient import TestClient
from tests.test_google_connections import setup as google_setup
from tests.test_overview_automation import intent
from workflow_api.main import create_app,COOKIE
from workflow_api.service import WorkflowService


def test_overview_transport_requires_session_and_never_invents_event_subscription(google_setup):
    manager,env=google_setup;service=WorkflowService(manager.store)
    app=create_app(service=service,dev_auth=True,roles=['admin'],start_workers=False,planning_worker_enabled=False,google_oauth_config=env)
    seen=[]
    router=service.overview_automation
    router.env=dict(BUILDER_OVERVIEW_ROUTING_ENABLED='1',BUILDER_OVERVIEW_ROUTING_WORKSPACES='local-workspace')
    router.interpreter=lambda goal,ctx:seen.append(deepcopy(ctx)) or intent('event')
    request=dict(overview=True,operation='prepare',objective='When a new business record arrives, notify the manager.',request_key='overview_api_event')
    with TestClient(app) as client:
        assert client.post('/business-ontology/v1/action-plans',json=request).status_code==401
        session=client.get('/session');assert session.json()['data']['overview_routing_available'] is True
        client.cookies.set(COOKIE,session.cookies[COOKIE],path='/')
        response=client.post('/business-ontology/v1/action-plans',json=request)
        assert response.status_code==200,response.text
        result=response.json()['data'];assert result['state']=='unsupported' and 'composition_id' not in result
        assert 'event source' in result['questions'][0]
        repeated=client.post('/business-ontology/v1/action-plans',json=request).json()['data']
        # The envelope traces each HTTP attempt independently; the persisted
        # business response and interpretation must remain identical.
        first_trace=result.pop('correlation_id')
        assert repeated.pop('correlation_id')!=first_trace
        assert repeated==result
        assert len(seen)==1 and seen[0]['workspace']==app.state.workflow_auth['subject']
        router.env={}
        assert client.get('/session').json()['data']['overview_routing_available'] is False
        assert client.post('/business-ontology/v1/action-plans',json=request).json()['data']['state']=='legacy'


def test_existing_planning_queue_runs_overview_and_cancellation_is_visible(google_setup):
    manager,env=google_setup;service=WorkflowService(manager.store)
    app=create_app(service=service,dev_auth=True,roles=['admin'],start_workers=False,planning_worker_enabled=False,google_oauth_config=env)
    service.overview_automation.env=dict(BUILDER_OVERVIEW_ROUTING_ENABLED='1',BUILDER_OVERVIEW_ROUTING_WORKSPACES='local-workspace')
    service.overview_automation.interpreter=lambda *_:intent('event')
    with TestClient(app) as client:
        session=client.get('/session');client.cookies.set(COOKIE,session.cookies[COOKIE],path='/')
        request=dict(operation='prepare',objective='Notify me when a new business record arrives.',request_key='queued_overview_request')
        def queued(body):return dict(request_id='overview_queue',operation='plan_workflow',idempotency_key=body['request_key'],payload=dict(objective=body['objective'],context={'praxi_overview_request_v1':body}))
        response=client.post('/planning-jobs',json=queued(request));assert response.status_code<300,response.text
        job=response.json()['data'];assert job['state']=='queued'
        pending=client.post('/business-ontology/v1/action-plans',json=dict(overview=True,operation='get',request_key=request['request_key'])).json()['data']
        assert pending['state']=='planning' and pending['planning_job']['job_id']==job['job_id']
        assert app.state.planning_jobs.tick()
        finished=client.get('/planning-jobs/'+job['job_id']).json()['data'];assert finished['state']=='succeeded'
        assert finished['result']['data']['state']=='unsupported'
        request['request_key']='cancelled_overview_request'
        job=client.post('/planning-jobs',json=queued(request)).json()['data']
        assert client.delete('/planning-jobs/'+job['job_id']).status_code==200
        result=client.post('/business-ontology/v1/action-plans',json=dict(overview=True,operation='get',request_key=request['request_key'])).json()['data']
        assert result['state']=='cancelled' and 'composition_id' not in result
        from runtime.service import RuntimeFailure
        def blocked(*_):
            error=RuntimeFailure('ACTION_INPUT_REQUIRED','Which report should be updated?',422)
            error.required_inputs={'report':{'type':'string'}}
            raise error
        service.overview_automation.handle=blocked
        request['request_key']='missing_report_overview'
        job=client.post('/planning-jobs',json=queued(request)).json()['data']
        assert app.state.planning_jobs.tick()
        failed=client.get('/planning-jobs/'+job['job_id']).json()['data']
        assert failed['state']=='failed'
        assert failed['result']['data']['error']['error_code']=='ACTION_INPUT_REQUIRED'
        assert failed['result']['data']['error']['details']['required_inputs']=={'report':{'type':'string'}}
