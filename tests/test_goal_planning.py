"""Account + goal acceptance with real Registry/runtime and controlled provider effects."""
from copy import deepcopy
from types import SimpleNamespace
import json
import pytest
from tests.test_connected_action_plans import (connected,composition,investigation,retrieval,knowledge,reference,generation,foundation,auth,release,proposal,compile_run,complete,stored,action,bind)
from tests.test_durable_automation import automation,google_setup
from workflow_api.capability_contracts import catalogue
from workflow_api.business_preparation import retrieval_tool_definition
from runtime.service import RuntimeFailure


def request(f,goal=None,key='account_goal_001'):
    seen=[]
    def plan(goal,ctx):seen.append(deepcopy(ctx));return proposal(f.prepared)
    f.general.planner.provider=SimpleNamespace(plan_actions=plan)
    return dict(objective=goal or 'Investigate complaint C123, create a findings Sheet and email engineer@example.com its verified link.',request_key=key,business_request={},automatic_inputs=True,google_connection_id=f.connection),seen


def test_account_and_goal_generates_internal_inputs_and_runs_actual_report_and_mail(automation):
    f=automation;body,seen=request(f)
    doc,w,rid=compile_run(f,body)
    assert doc['interaction_mode']=='goal' and seen
    assert doc['google_connection_id']==f.connection
    assert doc['binding_context']['user_values']=={'recipient':'engineer@example.com'}
    assert doc['selected_tools']['sheet']['definition']['allowed_destinations']
    sheet=next(a for a in doc['action_plan']['actions'] if a['action_id']=='sheet')
    assert {b['target'][0]:b['kind'] for b in sheet['bindings']}=={'project_id':'configuration','creation_key':'configuration','title':'generated','tabs':'generated'}
    assert f.http.write_count==0 and not f.http.sent
    result=complete(f,w,rid)
    assert result['status']=='completed',stored(f,rid)
    saved=stored(f,rid)
    inputs=saved['action_instances']['sheet']['resolved_inputs']
    assert inputs['project_id'].startswith('goal_') and inputs['creation_key'].startswith('action_')
    assert inputs['tabs'][0]['rows'] and saved['action_instances']['sheet']['verified_receipt']
    assert f.http.write_count==1 and len(f.http.sent)==1
    assert saved['action_instances']['sheet']['output']['spreadsheet_url'] in saved['action_instances']['send']['resolved_inputs']['body']
    assert f.c.prepare_actions(f.x.a,body)==doc
    f.runner.advance(rid,f.x.a);assert f.http.write_count==1 and len(f.http.sent)==1


def test_unstated_recipient_becomes_a_business_question_not_technical_setup(automation):
    f=automation;body,_=request(f,'Investigate complaint C123, create a report Sheet and email its findings to the assigned engineer.')
    with pytest.raises(RuntimeFailure) as caught:f.c.prepare_actions(f.x.a,body)
    assert caught.value.code=='ACTION_INPUT_REQUIRED'
    assert set(caught.value.required_inputs)=={'recipient'}
    assert not f.http.sent and f.http.write_count==0


def test_email_me_resolves_only_the_owned_selected_account(automation):
    f=automation;body,_=request(f,'Investigate complaint C123, create a report Sheet and email me its verified link.')
    doc=f.c.prepare_actions(f.x.a,body)
    assert doc['binding_context']['user_values']['recipient']=='owner@example.com'
    assert doc['google_connection_id']==f.connection


def test_automatic_google_request_never_uses_legacy_account_fallback(automation):
    f=automation;body,_=request(f);body.pop('google_connection_id')
    with pytest.raises(RuntimeFailure) as caught:f.c.prepare_actions(f.x.a,body)
    assert caught.value.code=='GOOGLE_CONNECTION_REQUIRED'
    assert not f.http.sent and f.http.write_count==0


def test_distinct_report_actions_get_distinct_stable_creation_keys(automation):
    f=automation;body,_=request(f);body['action_plan']=proposal(f.prepared)
    second=deepcopy(body['action_plan']['actions'][2]);second['action_id']='another_report'
    body['action_plan']['actions'].insert(3,second)
    doc=f.c.prepare_actions(f.x.a,body)
    def key(a):
        binding=next(b for b in a['bindings'] if b['target']==['creation_key'])
        return doc['binding_context']['configuration'][binding['key']]
    sheets=[a for a in doc['action_plan']['actions'] if a['capability_id']=='tool.extension_sheets_create_report']
    assert len({key(a) for a in sheets})==2
    assert f.c.prepare_actions(f.x.a,body)==doc


def test_revoked_account_stops_before_planning_or_effects(automation):
    f=automation;body,seen=request(f);f.manager.disconnect(f.x.a,f.connection)
    with pytest.raises(Exception) as caught:f.c.prepare_actions(f.x.a,body)
    assert caught.value.code=='GOOGLE_RECONNECT_REQUIRED' and not seen
    assert not f.http.sent and f.http.write_count==0


def test_registry_connector_catalogue_has_no_fixed_provider_or_count_allowlist(composition):
    f=composition;policy=deepcopy(f.registry._policy);policy.version+=1
    tools=[];connectors={}
    class Read:
        external_write=False
    for i in range(40):
        d=deepcopy(retrieval_tool_definition());d.update(tool_id=f'custom_lookup_{i}',capability=f'custom.lookup_{i}',input_schema={'type':'object'},output_schema={'type':'object'})
        policy.remaining_quota[d['tool_id']]=100
        tools.append({'tool_id':d['tool_id'],'definition':d});connectors[d['tool_id']]=Read()
    assert f.registry.update_policy(policy,f.x.a)['status']==200
    for record in tools:assert f.registry.register_tool(record['definition'],f.x.a)['status']==200
    contracts=catalogue(None,f.c.tools(f.x.a),connectors)
    assert {f'tool.custom_lookup_{i}' for i in range(40)}<=set(contracts)
    assert all(contracts[f'tool.custom_lookup_{i}']['side_effect']=='read' for i in range(40))
    assert not any(k.startswith('tool.custom_') for k in catalogue(None,tools,{}))


def test_live_provider_exposes_connected_planner_without_legacy_generation():
    from workflow_api.live_providers import LivePlannerProvider
    provider=LivePlannerProvider.__new__(LivePlannerProvider);seen=[]
    provider.provider=SimpleNamespace(plan_actions=lambda objective,context:seen.append((objective,context)) or {'actions':[]})
    assert provider.plan_actions('Goal',{'capabilities':{'custom':{}}})=={'actions':[]}
    assert seen==[('Goal',{'capabilities':{'custom':{}}})]


def test_new_registered_connector_executes_without_frontend_or_capability_allowlist(connected):
    f=connected;definition=deepcopy(retrieval_tool_definition())
    definition.update(tool_id='custom_service_lookup',capability='custom.service.lookup',input_schema={'type':'object','additionalProperties':False,'required':['query'],'properties':{'query':{'type':'string'}}},output_schema={'type':'object','additionalProperties':False,'required':['value'],'properties':{'value':{'type':'string'}}})
    policy=deepcopy(f.registry._policy);policy.version+=1;policy.remaining_quota[definition['tool_id']]=10
    assert f.registry.update_policy(policy,f.x.a)['status']==200
    assert f.registry.register_tool(definition,f.x.a)['status']==200
    calls=[]
    class CustomRead:
        external_write=False;retry_safe=True;timeout=1
        def reservation(self,grant):return {'tool_calls':1,'estimated_cost_usd':0}
        def invoke(self,grant,inputs,effect):calls.append(inputs);return {'value':'Actual controlled service receipt'}
    f.connectors[definition['tool_id']]=CustomRead()
    req=dict(objective='Retrieve an authorized custom service record.',request_key='custom_service_goal',automatic_inputs=True,user_values={'query':'existing record'},action_plan=dict(actions=[action('lookup','tool.custom_service_lookup',[bind('literal','query','query')])],completion_criteria=['lookup'],missing_inputs=[]))
    _,w,rid=compile_run(f,req)
    assert f.runner.advance(rid,f.x.a)['status']=='completed',stored(f,rid)
    receipt=stored(f,rid)['action_instances']['lookup']
    assert receipt['verified_receipt'] and receipt['output']['value']=='Actual controlled service receipt'
    assert calls==[{'query':'existing record'}]


def test_public_planning_error_preserves_typed_business_questions(tmp_path):
    from fastapi.testclient import TestClient
    from workflow_api.main import create_app
    app=create_app(database=tmp_path/'goal-api.sqlite',dev_auth=True,roles=['admin'],runtime_enabled=True,start_workers=False,planning_worker_enabled=False)
    def need_recipient(*args):
        error=RuntimeFailure('ACTION_INPUT_REQUIRED','An email recipient is required.',422)
        error.required_inputs={'recipient':{'type':'string','format':'email'}}
        raise error
    app.state.workflow_service.business_composition.prepare_actions=need_recipient
    client=TestClient(app);client.get('/session');client.cookies.set('builder_dev_session',client.cookies.get('builder_dev_session'),path='/')
    response=client.post('/business-ontology/v1/action-plans',json={'objective':'Email findings'})
    assert response.status_code==422
    error=response.json()['data']['error']
    assert error['error_code']=='ACTION_INPUT_REQUIRED'
    assert error['details']=={'required_inputs':{'recipient':{'type':'string','format':'email'}}}
