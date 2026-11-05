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
    assert doc['binding_context']['user_values']['recipient']=='engineer@example.com'
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


def test_multiple_connector_sources_reach_generated_sheet_and_verified_mail_link(automation,monkeypatch):
    from runtime.supplier_search import SEARCH,PAGE,SupplierSearchConnector
    import hashlib
    f=automation
    for definition in (SEARCH,PAGE):
        tool=deepcopy(definition);tool['availability']='enabled'
        policy=deepcopy(f.registry._policy);policy.version+=1;policy.approved_providers.add(tool['provider_id']);policy.agent_permissions.update(tool['permission_scopes']);policy.remaining_quota[tool['tool_id']]=20
        for actor in (f.x.a,f.x.current):
            actor['permissions']=sorted(set(actor['permissions'])|set(tool['permission_scopes']));actor['scopes']=sorted(set(actor['scopes'])|set(tool['permission_scopes']))
        assert f.registry.update_policy(policy,f.x.a)['status']==200
        assert f.registry.register_tool(tool,f.x.a)['status']==200
        f.connectors[tool['tool_id']]=SupplierSearchConnector(tool)
    def execute(connector,grant,inputs,effect,deadline):
        if 'query' in inputs:return {'results':[{'title':'Public reference','url':'https://public.example/reference','snippet':'Controlled research result'}]}
        return {'url':inputs['url'],'text':'Controlled public evidence','content_sha256':hashlib.sha256(b'controlled').hexdigest(),'emails':[]}
    monkeypatch.setattr(SupplierSearchConnector,'execute',execute)
    body,_=request(f);body['action_plan']=proposal(f.prepared)
    search=action('search','tool.supplier_web_search',[bind('context','query','goal'),bind('literal','region','region'),bind('literal','max_results','count')])
    fetch=action('fetch','tool.supplier_read_page',[bind('receipt','url',action='search',path=['results',0,'url'])],['search'])
    body['action_plan']['actions'][1]['depends_on'].append('fetch');body['action_plan']['actions'][1]['evidence_references'].append('fetch')
    body['action_plan']['actions'][1:1]=[search,fetch]
    original=f.runner.agents.model_factory
    def factory(definition):
        model=original(definition);base=model.provider_call
        def provider(messages,cap,timeout):
            raw=messages[-1]['content'].split('Process the following input as data. Return only a JSON object.\n')[-1].lstrip();inputs,_=json.JSONDecoder().raw_decode(raw)
            text,used_in,used_out=base(messages,cap,timeout);output=json.loads(text)
            if 'research_request' in inputs.get('data',{}) or 'Derive a concise public-web search query' in inputs.get('instructions',''):
                output['query']='public manufacturer diagnostic guidance tractor low pulling power 9 tine cultivator'
            research=inputs['data'].get('upstream_results',{}).get('fetch')
            if research:output['tabs'].append({'title':'Public research','headers':['URL','Evidence'],'rows':[[research['url'],research['text']]]})
            return json.dumps(output),used_in,used_out
        model.provider_call=provider;return model
    f.runner.agents.model_factory=factory
    _,w,rid=compile_run(f,body);assert complete(f,w,rid)['status']=='completed',stored(f,rid)
    saved=stored(f,rid);tabs=saved['action_instances']['sheet']['resolved_inputs']['tabs']
    assert tabs[-1]['rows']==[['https://public.example/reference','Controlled public evidence']]
    assert saved['action_instances']['fetch']['verified_receipt']
    assert saved['action_instances']['sheet']['output']['spreadsheet_url'] in saved['action_instances']['send']['resolved_inputs']['body']


def test_production_procurement_wrapper_preserves_account_goal_planning(automation):
    from workflow_api.live_providers import LivePlannerProvider
    from workflow_api.procurement import ProcurementPlanner
    f=automation;body,seen=request(f)
    original=f.general.planner.provider
    live=LivePlannerProvider.__new__(LivePlannerProvider);live.provider=original
    f.general.planner.provider=ProcurementPlanner(live,None,'offline',None)
    doc=f.c.prepare_actions(f.x.a,body)
    assert len(seen)==1 and doc['interaction_mode']=='goal'
    assert doc['google_connection_id']==f.connection
    assert doc['action_plan']['actions'] and not f.http.sent and f.http.write_count==0
    assert f.c.prepare_actions(f.x.a,body)==doc and len(seen)==1


def test_procurement_connected_planning_preserves_provider_failure():
    from planner.errors import PlannerFailure
    from workflow_api.procurement import ProcurementPlanner
    calls=[]
    def fail(objective,context):
        calls.append((objective,context))
        raise PlannerFailure('MODEL_UNAVAILABLE','Controlled provider failure')
    provider=ProcurementPlanner(SimpleNamespace(plan_actions=fail),None,'offline',None)
    with pytest.raises(PlannerFailure) as caught:provider.plan_actions('Goal',{'capabilities':{}})
    assert caught.value.code=='MODEL_UNAVAILABLE'
    assert calls==[('Goal',{'capabilities':{}})]


@pytest.mark.parametrize('fault',['target','source','type'])
def test_generated_binding_is_corrected_once_before_any_execution(automation,fault):
    f=automation;body,_=request(f);seen=[]
    good=proposal(f.prepared);bad=deepcopy(good)
    binding=bad['actions'][1]['bindings'][0]
    if fault=='target':binding['target']=['undeclared']
    elif fault=='source':binding['path']=['output','records']
    else:binding['path']=['version_id']
    def plan(goal,context):
        seen.append(deepcopy(context));return bad if len(seen)==1 else good
    f.general.planner.provider=SimpleNamespace(plan_actions=plan)
    doc=f.c.prepare_actions(f.x.a,body)
    assert len(seen)==2 and doc['planning']['model_calls']==2
    assert doc['google_connection_id']==body['google_connection_id']
    assert seen[1]['validation_feedback']['error_code']=='ACTION_BINDING_INVALID'
    assert ['data'] in seen[1]['binding_paths']['content.prepare']['input']
    assert ['data','complaints'] not in seen[1]['binding_paths']['content.prepare']['input']
    assert not f.http.sent and f.http.write_count==0
    assert f.c.prepare_actions(f.x.a,body)==doc and len(seen)==2


def test_persistently_invalid_generated_binding_stops_after_one_correction(automation):
    f=automation;body,_=request(f);seen=[];bad=proposal(f.prepared)
    bad['actions'][1]['bindings'][0]['target']=['undeclared']
    def plan(goal,context):seen.append(context);return deepcopy(bad)
    f.general.planner.provider=SimpleNamespace(plan_actions=plan)
    with pytest.raises(RuntimeFailure) as caught:f.c.prepare_actions(f.x.a,body)
    assert caught.value.code=='ACTION_BINDING_INVALID' and len(seen)==2
    assert caught.value.binding_issue['side']=='target'
    assert not f.http.sent and f.http.write_count==0
    with f.general.store.transaction(write=False) as db:
        assert not db.execute('SELECT 1 FROM business_compositions WHERE request_key=?',(body['request_key'],)).fetchone()


def test_explicit_invalid_plan_is_not_silently_replanned(automation):
    f=automation;body,seen=request(f);body['action_plan']=proposal(f.prepared)
    body['action_plan']['actions'][1]['bindings'][0]['path']=['invented']
    with pytest.raises(RuntimeFailure) as caught:f.c.prepare_actions(f.x.a,body)
    assert caught.value.code=='ACTION_BINDING_INVALID' and not seen
    assert not f.http.sent and f.http.write_count==0


def test_binding_correction_keeps_recipient_authority_checks(automation):
    f=automation;body,_=request(f);seen=[]
    bad=proposal(f.prepared);bad['actions'][1]['bindings'][0]['target']=['undeclared']
    unsafe=proposal(f.prepared)
    unsafe['actions'][-1]['bindings'][0]=bind('generated','to',action='email',path=['body'])
    def plan(goal,context):seen.append(context);return deepcopy(bad if len(seen)==1 else unsafe)
    f.general.planner.provider=SimpleNamespace(plan_actions=plan)
    with pytest.raises(RuntimeFailure) as caught:f.c.prepare_actions(f.x.a,body)
    assert caught.value.code=='ACTION_AUTHORITY_DENIED' and len(seen)==2
    assert not f.http.sent and f.http.write_count==0


def test_connected_planner_transport_enforces_shape_and_declared_capabilities():
    from planner.provider import OpenAIStructuredOutputProvider
    from jsonschema import Draft202012Validator
    calls=[]
    client=SimpleNamespace(responses=SimpleNamespace(create=lambda **kwargs: calls.append(kwargs) or SimpleNamespace(status='completed',output_text='{}')))
    p=OpenAIStructuredOutputProvider(client=client,model='controlled')
    p.plan_actions('Prepare report',{'capabilities':{'content.prepare':{}},'binding_context':{}})
    transport=calls[0]['text']['format']
    assert transport['type']=='json_schema' and transport['strict'] is True
    schema=transport['schema'];Draft202012Validator.check_schema(schema)
    item=action('report','content.prepare',[bind('context','data','source')])
    item.pop('expected_output_schema',None)
    valid={'actions':[item],'completion_criteria':['report'],'missing_inputs':[]}
    assert not list(Draft202012Validator(schema).iter_errors(valid))
    invalid=deepcopy(valid);invalid['actions'][0]['capability_id']='invented.tool'
    assert list(Draft202012Validator(schema).iter_errors(invalid))
    invalid=deepcopy(valid);invalid['actions'][0]['bindings'][0]['target']='data.records'
    assert list(Draft202012Validator(schema).iter_errors(invalid))
    def strict(node):
        if isinstance(node,list):
            for item in node:strict(item)
        elif isinstance(node,dict):
            assert 'oneOf' not in node and 'uniqueItems' not in node and 'const' not in node
            if node.get('type')=='object':
                assert node['additionalProperties'] is False
                assert set(node['required'])==set(node['properties'])
            for item in node.values():strict(item)
    strict(schema)


def test_goal_content_coalesces_whole_dependencies_without_losing_evidence(automation):
    f=automation;body,_=request(f);plan=proposal(f.prepared)
    read=deepcopy(plan['actions'][0]);read['action_id']='another_read'
    plan['actions'].insert(1,read)
    analysis=next(a for a in plan['actions'] if a['action_id']=='analysis')
    analysis['depends_on'].append('another_read')
    analysis['bindings'].append(bind('output','data',action='another_read'))
    body['action_plan']=plan
    doc,w,rid=compile_run(f,body)
    normalized=next(a for a in doc['action_plan']['actions'] if a['action_id']=='analysis')
    assert len(normalized['bindings'])==1 and normalized['depends_on']==['read','another_read']
    assert complete(f,w,rid)['status']=='completed'
    assert stored(f,rid)['action_instances']['another_read']['state']=='completed'


def test_goal_exact_duplicates_are_removed_but_conflicting_recipient_assignments_fail(automation):
    f=automation;body,_=request(f);body['action_plan']=proposal(f.prepared)
    send=body['action_plan']['actions'][-1]
    send['bindings'].append(deepcopy(send['bindings'][0]))
    doc=f.c.prepare_actions(f.x.a,body)
    assert len(doc['action_plan']['actions'][-1]['bindings'])==3
    body['request_key']='conflicting_recipient_001';body['user_values']={'another':'other@example.com'}
    send['bindings'].append(bind('literal','to','another'))
    with pytest.raises(RuntimeFailure) as caught:f.c.prepare_actions(f.x.a,body)
    assert caught.value.code=='ACTION_BINDING_INVALID'
    assert caught.value.binding_issue['overlaps']==['to']
    assert not f.http.sent and f.http.write_count==0


def test_email_the_summary_to_me_uses_account_and_resolves_literal_alias(automation):
    f=automation;body,_=request(f,'Investigate complaint C123. Email the summary to me using my selected Google account.')
    plan=proposal(f.prepared)
    plan['actions'][-1]['bindings'][0]['key']='selected_account_email'
    plan['missing_inputs']=['selected_account_email literal user_values key for the selected Google account recipient','selected_account_email']
    f.general.planner.provider=SimpleNamespace(plan_actions=lambda *args:deepcopy(plan))
    doc=f.c.prepare_actions(f.x.a,body)
    assert doc['binding_context']['user_values']['recipient']=='owner@example.com'
    assert doc['binding_context']['user_values']['complaint_id']=='C123'
    assert doc['action_plan']['missing_inputs']==[]
    assert doc['action_plan']['actions'][-1]['bindings'][0]['key']=='recipient'
    assert not f.http.sent and f.http.write_count==0


def test_analysis_task_identity_and_context_are_server_owned_in_goal_mode(automation):
    f=automation;body,_=request(f);plan=proposal(f.prepared)
    report=action('report','business.report',[bind('context','task_id','binding_context',path=['validated_context','goal']),bind('context','context','binding_context',path=['validated_context'])],['read'],['read'])
    report['budget'].update(max_llm_calls=1,max_tool_calls=0)
    plan['actions'].insert(1,report)
    body['action_plan']=plan
    doc=f.c.prepare_actions(f.x.a,body)
    result=next(a for a in doc['action_plan']['actions'] if a['action_id']=='report')
    assert {b['target'][0]:b['kind'] for b in result['bindings']}=={'task_id':'configuration','context':'context'}
    assert doc['binding_context']['configuration']['analysis_task_report']=='report'
    assert doc['binding_context']['validated_context']['analysis_context_report']['goal']==body['objective']
    assert not f.http.sent and f.http.write_count==0


def test_real_model_namespace_and_content_metadata_bindings_are_canonical(automation):
    f=automation;body,_=request(f);plan=proposal(f.prepared)
    content=plan['actions'][1]
    content['bindings'].extend([bind('literal','instructions','summary_instructions'),bind('output','source_references',action='read',path=['version_id'])])
    plan['actions'][-1]['bindings'][0]=bind('context','to','user_values',path=['recipient'])
    plan['missing_inputs']=['user_values.complaint_id','summary_instructions']
    f.general.planner.provider=SimpleNamespace(plan_actions=lambda *args:deepcopy(plan))
    doc=f.c.prepare_actions(f.x.a,body)
    assert len(doc['action_plan']['actions'][1]['bindings'])==1
    assert doc['action_plan']['actions'][-1]['bindings'][0]==bind('literal','to','recipient')
    assert doc['action_plan']['missing_inputs']==[]
    assert not f.http.sent and f.http.write_count==0


def test_content_transport_constrains_actual_reference_tokens_without_relabelling():
    from runtime.crew import content_response_schema
    from workflow_api.action_plans import CONTENT_INPUT,CONTENT_OUTPUT
    from jsonschema import Draft202012Validator
    definition={'input_schema':CONTENT_INPUT,'output_schema':CONTENT_OUTPUT}
    schema=content_response_schema(definition,{'source_references':['read_complaint']})
    assert schema['properties']['source_references']['items']['enum']==['read_complaint']
    assert set(schema['required'])==set(schema['properties'])
    from runtime.model_protocol import closed_payload
    assert closed_payload(schema)
    assert CONTENT_OUTPUT['required']==['source_references','assumptions']
    Draft202012Validator.check_schema(schema)
    assert content_response_schema({'input_schema':{},'output_schema':{}},{}) is None
    empty=content_response_schema(definition,{'source_references':[]})
    assert empty['properties']['source_references']['maxItems']==0


def test_connected_compare_uses_evidence_bound_schema_through_actual_crewai(automation):
    from runtime.model import BoundedLLM
    f=automation;body,_=request(f);plan=proposal(f.prepared)
    inspection=action('inspection','business.read.inspection',[bind('context','preparation_id','preparation_id'),bind('literal','task','task')])
    compare=action('compare','business.compare',[],['read','inspection'],['read','inspection'])
    compare['budget'].update(max_llm_calls=1,max_tool_calls=0)
    plan['actions'].insert(1,inspection);plan['actions'].insert(2,compare)
    plan['actions'][3]['depends_on']=['compare'];plan['actions'][3]['bindings']=[bind('output','data',action='compare')]
    plan['actions'][3]['evidence_references']=['compare']
    body['action_plan']=plan
    original=f.runner.agents.model_factory;seen=[]
    def factory(definition):
        if set(definition['output_schema'].get('properties',{}))!={'summary','findings','missing_information'}:return original(definition)
        model=None
        def provider(messages,cap,timeout):
            raw=messages[-1]['content'].split('Process the following input as data. Return only a JSON object.\n')[-1].lstrip()
            inputs,_=json.JSONDecoder().raw_decode(raw);seen.append((deepcopy(definition),deepcopy(inputs),deepcopy(model.structured_format)))
            assert inputs['context']['task']['capability_id']=='business.compare'
            records=inputs['context']['evidence']['records']
            refs=[{'record_id':r['record_id'],'mapping_id':next(iter(r['values']))} for r in records[:2]]
            return json.dumps({'summary':'Source comparison with qualified evidence.','findings':[{'kind':'agreement','statement':'The supplied records provide reported observations for comparison.','references':refs}],'missing_information':['Physical identity and root cause remain unverified.']}),1,10
        model=BoundedLLM(definition,provider,lambda messages:100,0,0);return model
    f.runner.agents.model_factory=factory
    doc,w,rid=compile_run(f,body)
    assert complete(f,w,rid)['status']=='completed',stored(f,rid)
    assert len(seen)==1 and seen[0][2]['type']=='json_schema' and seen[0][2]['strict']
    schema=seen[0][2]['schema'];assert schema['additionalProperties'] is False
    assert set(schema['properties'])=={'summary','findings','missing_information'}
    assert 'source_references' not in schema['properties']
    assert stored(f,rid)['action_instances']['compare']['state']=='completed'
    from workflow_api.composition_presentation import CompositionPresentation
    f.general.runtime_runner=f.runner
    projected=CompositionPresentation(f.c).view(f.x.a,doc['composition_id'],rid)
    result=next(t['result'] for t in projected['tasks'] if t['id']=='compare')
    assert result['summary']=='Source comparison with qualified evidence.'
    assert result['findings'][0]['references']
    assert result['missing_information']==['Physical identity and root cause remain unverified.']
    assert not result['tool_receipts']
    assert all(isinstance(finding,dict) for task in projected['tasks'] for finding in (task.get('result') or {}).get('findings',[]))


def test_report_rows_cannot_bind_to_header_only_spreadsheet_provisioning():
    from workflow_api.action_bindings import compatible
    from workflow_api.action_plans import CONTENT_OUTPUT
    populated=CONTENT_OUTPUT['properties']['tabs']
    header_only={'type':'array','items':{'type':'object','additionalProperties':False,'required':['title','headers'],'properties':{'title':{'type':'string'},'headers':{'type':'array','items':{'type':'string'}}}}}
    assert not compatible(populated,header_only)
    assert compatible(populated,populated)


def test_report_row_validation_gets_one_bounded_model_correction():
    from runtime.action_plans import validate_content_tables
    from shared.llm_feedback import correct_once
    workflow={'metadata':{'connected_action_plan':{'actions':[{'action_id':'content','capability_id':'content.prepare'}]}}}
    node={'node_id':'content'};seen=[]
    def invoke(feedback):
        seen.append(feedback)
        output={'tabs':[{'headers':['Finding','Complaint','Inspection'],'rows':[['Reported',None,'Source']] if feedback else [['Reported','Source']]}]}
        validate_content_tables(workflow,node,output)
        return output
    result=correct_once(invoke,lambda feedback:None)
    assert len(seen)==2 and seen[1]['field']=='tabs/rows'
    assert 'middle columns' in seen[1]['hint']
    assert result['tabs'][0]['rows']==[['Reported',None,'Source']]
    calls=[]
    def invalid(feedback):
        calls.append(feedback)
        validate_content_tables(workflow,node,{'tabs':[{'headers':['One','Two'],'rows':[['Only one']]}]})
    with pytest.raises(RuntimeFailure):correct_once(invalid,lambda feedback:None)
    assert len(calls)==2


@pytest.mark.parametrize('query_binding',[bind('context','query','goal'),bind('context','query','research_request',path=['objective'])])
def test_long_research_goal_gets_query_preparation_not_full_prompt_dispatch(query_binding):
    from workflow_api.goal_inputs import research_queries
    from workflow_api.action_plans import content_contract
    from runtime.supplier_search import SEARCH
    objective='Research tractor low pulling power using primary manufacturer sources. '+('Keep findings qualified. '*30)+'Email me the findings.'
    contracts={'content.prepare':content_contract(),'search':{'supported_operation':'research.search','input_schema':SEARCH['input_schema'],'output_schema':SEARCH['output_schema']}}
    context={'validated_context':{'goal':objective,'research_request':{'objective':objective}},'configuration':{},'user_values':{},'evidence':{}}
    actions=[action('search','search',[deepcopy(query_binding)])]
    research_queries(actions,contracts,context)
    assert len(actions)==2 and actions[0]['capability_id']=='content.prepare'
    assert actions[1]['bindings'][0]['kind']=='generated'
    assert actions[1]['bindings'][0]['path']==['query']
    assert actions[0]['action_id'] in actions[1]['depends_on']
    assert context['validated_context']['research_request']=={'objective':objective}
    assert 'private complaint identifiers' in actions[0]['instructions']
    assert content_contract()['output_schema']['properties']['query']['maxLength']<=SEARCH['input_schema']['properties']['query']['maxLength']
    research_queries(actions,contracts,context)
    assert len(actions)==2


def test_explicit_primary_calendar_schedule_is_bound_without_technical_form():
    from workflow_api.goal_inputs import calendar_context,calendar_bindings
    context={'validated_context':{}};goal='Prepare a 30-minute review on 10 November 2026 at 10:00 AM Asia/Kolkata in my selected Google account primary calendar.'
    calendar_context(context,goal,True)
    assert context['validated_context']['calendar_event_start']=={'dateTime':'2026-11-10T10:00:00+05:30','timeZone':'Asia/Kolkata'}
    assert context['validated_context']['calendar_event_end']['dateTime']=='2026-11-10T10:30:00+05:30'
    contracts={'create':{'supported_operation':'calendar.create'}}
    actions=[{'capability_id':'create','bindings':[{'target':['event','summary'],'kind':'generated'}]}]
    calendar_bindings(actions,contracts,context,set())
    assert {tuple(b['target']) for b in actions[0]['bindings']}=={('calendar_id',),('event','summary'),('event','start'),('event','end')}
    original=deepcopy(actions);calendar_bindings(actions,contracts,context,set());assert actions==original
    custom={'capability_id':'create','bindings':[{'target':['calendar_id'],'kind':'literal','key':'chosen_calendar'},{'target':['event'],'kind':'literal','key':'exact_event'}]}
    original=deepcopy(custom);calendar_bindings([custom],contracts,context,set());assert custom==original


@pytest.mark.parametrize('goal',[
    'Create an event in my primary calendar.',
    'Prepare a 30-minute review on 2026-11-10 at 10:00 AM.',
    'Prepare a 30-minute review on 2026-02-30 at 10:00 AM Asia/Kolkata.',
    'Prepare a 30-minute review on 2026-11-10 at 25:00 Asia/Kolkata.',
    'Prepare a 30-minute review on 2026-11-01 at 01:30 AM America/New_York.',
])
def test_calendar_defaults_do_not_invent_or_accept_ambiguous_times(goal):
    from workflow_api.goal_inputs import calendar_context
    context={'validated_context':{}};calendar_context(context,goal,True)
    assert 'calendar_event_start' not in context['validated_context']
    other={'validated_context':{}};calendar_context(other,'30-minute review on 2026-11-10 at 10:00 AM Asia/Kolkata primary calendar.',False)
    assert not other['validated_context']


def test_account_goal_calendar_runs_with_explicit_schedule_and_exact_approval(automation):
    from tests.test_durable_automation import add_scopes
    f=automation;add_scopes(f.manager,f.connection,['calendar.events'])
    body,_=request(f,'Prepare a 30-minute review of complaint C123 on 10 November 2026 at 10:00 AM Asia/Kolkata in my selected Google account primary calendar.')
    plan=proposal(f.prepared);plan['actions']=plan['actions'][:2]
    event=action('review','tool.extension_calendar_create',[bind('generated','event.summary',action='analysis',path=['title']),bind('generated','event.description',action='analysis',path=['summary'])],['analysis'])
    plan['actions'].append(event);plan['completion_criteria']=['review'];body['action_plan']=plan
    doc,w,rid=compile_run(f,body)
    pending=f.runner.advance(rid,f.x.a);assert pending['status']=='paused_for_approval',stored(f,rid)
    payload=pending['approvals'][-1]['resolved_payload']
    assert payload['calendar_id']=='primary'
    assert payload['event']['start']['dateTime']=='2026-11-10T10:00:00+05:30'
    assert payload['event']['end']['dateTime']=='2026-11-10T10:30:00+05:30'
    assert not f.http.events
    assert complete(f,w,rid)['status']=='completed',stored(f,rid)
    assert len(f.http.events)==1


def test_whole_context_namespace_content_binding_uses_known_values_only():
    from workflow_api.goal_inputs import bind_internal
    from workflow_api.action_plans import content_contract
    context={'validated_context':{'goal':'Public research','selected_account_email':'owner@example.com'},'configuration':{},'user_values':{},'evidence':{}}
    actions=[action('query','content.prepare',[bind('context','data','validated_context')])]
    bind_internal(actions,{'content.prepare':content_contract()},context,{},lambda cid,c:cid,'namespace_test')
    binding=actions[0]['bindings'][0]
    assert binding['key']=='namespace_validated_context' and binding['path']==[]
    assert context['validated_context'][binding['key']]=={'goal':'Public research','selected_account_email':'owner@example.com'}


@pytest.mark.parametrize('kind',['output','generated','receipt'])
def test_goal_materializes_referenced_source_as_direct_dependency(kind):
    from workflow_api.goal_inputs import complete_binding_dependencies
    actions=[{'action_id':'sheet','depends_on':[],'bindings':[]},{'action_id':'verify','depends_on':['sheet'],'bindings':[]},{'action_id':'email','depends_on':['verify'],'bindings':[{'kind':kind,'action_id':'sheet','path':['spreadsheet_url']}]}]
    complete_binding_dependencies(actions)
    assert actions[-1]['depends_on']==['verify','sheet']
    original=deepcopy(actions);complete_binding_dependencies(actions);assert actions==original


def test_goal_missing_direct_receipt_dependency_runs_with_approvals(automation):
    f=automation;body,_=request(f);plan=proposal(f.prepared)
    review=action('review_sheet','content.prepare',[bind('receipt','data',action='sheet')],['sheet'],['sheet'])
    plan['actions'].insert(3,review)
    email=next(a for a in plan['actions'] if a['action_id']=='email')
    email['depends_on']=['analysis','review_sheet']
    body['action_plan']=plan
    doc,w,rid=compile_run(f,body)
    normalized=next(a for a in doc['action_plan']['actions'] if a['action_id']=='email')
    assert normalized['depends_on']==['analysis','review_sheet','sheet']
    assert complete(f,w,rid)['status']=='completed',stored(f,rid)
    assert f.http.write_count==1 and len(f.http.sent)==1
    assert stored(f,rid)['action_instances']['sheet']['output']['spreadsheet_url'] in stored(f,rid)['action_instances']['send']['resolved_inputs']['body']


@pytest.mark.parametrize('invalid',['unknown','cycle','optional','advanced'])
def test_dependency_completion_preserves_invalid_graph_rejection(automation,invalid):
    f=automation;body,_=request(f);plan=proposal(f.prepared)
    email=next(a for a in plan['actions'] if a['action_id']=='email')
    if invalid=='unknown':email['bindings'][1]['action_id']='missing_source'
    if invalid=='cycle':
        sheet=next(a for a in plan['actions'] if a['action_id']=='sheet')
        sheet['bindings'][2]=bind('generated','title',action='email',path=['title'])
    if invalid=='optional':
        sheet=next(a for a in plan['actions'] if a['action_id']=='sheet')
        sheet.update(optional=True,when=dict(binding=bind('literal','enabled','allow_sheet'),equals=True))
        body['user_values']={'allow_sheet':True}
    if invalid=='advanced':
        body['automatic_inputs']=False
        body['user_values']={'task':'complaints','project':'report','creation':'report_one','title':'Report','recipient':'engineer@example.com'}
        email['depends_on']=['analysis']
    body['action_plan']=plan
    with pytest.raises(RuntimeFailure):f.c.prepare_actions(f.x.a,body)
    assert f.http.write_count==0 and not f.http.sent


@pytest.mark.parametrize('correct_second',[True,False])
def test_model_authority_binding_gets_one_correction_without_relaxing_validation(automation,correct_second):
    f=automation;body,_=request(f);seen=[]
    def provider(goal,context):
        seen.append(deepcopy(context));plan=proposal(f.prepared)
        if len(seen)==1 or not correct_second:
            send=next(a for a in plan['actions'] if a['action_id']=='send')
            send['bindings'][0]=bind('generated','to',action='email',path=['body'])
        return plan
    f.general.planner.provider=SimpleNamespace(plan_actions=provider)
    if correct_second:
        doc=f.c.prepare_actions(f.x.a,body)
        send=next(a for a in doc['action_plan']['actions'] if a['action_id']=='send')
        assert next(b for b in send['bindings'] if b['target']==['to'])['kind']=='literal'
    else:
        with pytest.raises(RuntimeFailure) as caught:f.c.prepare_actions(f.x.a,body)
        assert caught.value.code=='ACTION_AUTHORITY_DENIED'
    assert len(seen)==2
    issue=seen[1]['validation_feedback']['binding_issue']
    assert issue['action_id']=='send' and issue['path']==['to'] and issue['rule']=='explicit_authority_required'
    assert f.http.write_count==0 and not f.http.sent


@pytest.mark.parametrize('context_count',[1,2])
def test_mixed_whole_context_and_evidence_preserves_all_inputs_through_runtime(automation,context_count):
    f=automation;body,_=request(f);plan=proposal(f.prepared)
    content=next(a for a in plan['actions'] if a['action_id']=='analysis')
    content['bindings'].append(bind('context','data','research_request'))
    if context_count==2:content['bindings'].append(bind('context','data','validated_context'))
    content['depends_on']=[]  # Its output binding still declares the read dependency.
    body['action_plan']=plan
    doc,w,rid=compile_run(f,body)
    normalized=next(a for a in doc['action_plan']['actions'] if a['action_id']=='analysis')
    assert normalized['depends_on']==['read']
    assert len([b for b in normalized['bindings'] if b['target']==['data']])==1
    assert complete(f,w,rid)['status']=='completed',stored(f,rid)
    inputs=stored(f,rid)['action_instances']['analysis']['resolved_inputs']['data']
    assert 'read' in inputs['upstream_results']
    assert inputs['upstream_results']['read']==stored(f,rid)['action_instances']['read']['output']
    if context_count==1:assert inputs['primary']['objective']==body['objective']
    else:
        assert inputs['primary']['contexts']['research_request']['objective']==body['objective']
        assert inputs['primary']['contexts']['namespace_validated_context']['selected_account_email']=='owner@example.com'


def test_redundant_known_research_namespace_is_normalized_without_masking_real_child():
    from workflow_api.goal_inputs import bind_internal
    from workflow_api.action_plans import content_contract
    for nested in [False,True]:
        value={'research_request':{'objective':'Actual nested value'}} if nested else {'objective':'Public research'}
        context={'validated_context':{'goal':'Public research','research_request':value},'configuration':{},'user_values':{},'evidence':{}}
        actions=[action('query','content.prepare',[bind('context','data','research_request',path=['research_request'])])]
        bind_internal(actions,{'content.prepare':content_contract()},context,{},lambda cid,c:cid,'namespace_test')
        assert actions[0]['bindings'][0]['path']==(['research_request'] if nested else [])


@pytest.mark.parametrize('clock,zone',[('10 AM','India time'),('10:00 AM','Indian Standard Time'),('10 AM','Asia/Kolkata'),('22:00','Asia/Kolkata')])
def test_explicit_india_time_and_hour_only_clock(clock,zone):
    from workflow_api.goal_inputs import calendar_context
    context={'validated_context':{}}
    calendar_context(context,f'Schedule a 30-minute review in my primary calendar for 10 November 2026 at {clock} {zone}.',True)
    hour='22' if clock=='22:00' else '10'
    assert context['validated_context']['calendar_event_start']=={'dateTime':f'2026-11-10T{hour}:00:00+05:30','timeZone':'Asia/Kolkata'}
    assert context['validated_context']['calendar_event_end']['dateTime']==f'2026-11-10T{hour}:30:00+05:30'


def test_context_merge_does_not_discard_a_receipt_requirement(automation):
    f=automation;body,_=request(f);plan=proposal(f.prepared)
    email=next(a for a in plan['actions'] if a['action_id']=='email')
    email['bindings'].extend([bind('context','data','research_request'),bind('receipt','data',action='sheet')])
    body['action_plan']=plan
    with pytest.raises(RuntimeFailure) as caught:f.c.prepare_actions(f.x.a,body)
    assert caught.value.code=='ACTION_BINDING_INVALID'
    assert not f.http.sent and f.http.write_count==0
