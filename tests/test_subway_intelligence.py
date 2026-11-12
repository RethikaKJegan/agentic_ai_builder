"""Subway Phase 1 acceptance: synthetic rows, real API/Registry/CrewAI/runtime.

The saved ontology is repository evidence. All operational rows and model outputs
in this module are isolated fixtures, not observations of live Subway behavior.
"""
from copy import deepcopy
from datetime import datetime
from types import SimpleNamespace
import json
import sqlite3
import hashlib
import hmac
import time
import pytest
from fastapi.testclient import TestClient

from tests.test_subway_full_queries import engine,installed,AUTH,plan,field
from tests.test_connected_action_plans import action,bind
from workflow_api.subway_queries import definition,install,SELECTION
from workflow_api.subway_onboarding import build_package
from workflow_api.business_knowledge_model import digest
from workflow_api.service import WorkflowService,ApiFailure
from workflow_api.registry_adapter import RegistryAdapter
from workflow_api.main import create_app
from workflow_api.overview_automation import OverviewAutomation
from runtime import RuntimeService
from runtime.graph import GraphRunner
from runtime.crew import CrewExecutor
from runtime.model import BoundedLLM
from registry import RegistryService,WorkspacePolicy


def selection(q,labels,fields=(),relationships=(),clarification=''):
    c=q.catalog(AUTH)
    return dict(dataset_ids=[d['dataset_id'] for d in c['datasets'].values() if d['label'] in labels],
        field_ids=list(fields),relationship_ids=list(relationships),
        measure_basis='Explicit requested measure; synthetic acceptance rows only.',clarification=clarification)


def route(selected,**changes):
    result=dict(intent_type='population',business_goal='Read the requested records and engine metrics.',entity_scope='population',
        side_effects=[],missing_requirements=[],recurrence=dict(kind='none',hour=None,minute=0,weekdays=[],timezone=None,date=None,month_day=None),
        temporal=dict(period='none',field_id=None,days=1),subway_selection=deepcopy(selected))
    result.update(changes)
    return result


@pytest.fixture
def subway(engine,tmp_path):
    previous,rows=engine;auth=deepcopy(AUTH)
    auth['permissions']=sorted(set(auth['permissions'])|{'workflow.view','workflow.validate','workflow.approve','workflow.publish','runs.view'})
    auth['scopes'].append('tools.read')
    tool=definition()
    policy=WorkspacePolicy('client-subway',agent_permissions={'workflow.read_input','tools.read'},
        approved_providers={tool['provider_id']},remaining_quota={'subway_query':100})
    registry=RegistryService(policy)
    assert registry.register_tool(tool,auth)['status']==200
    adapter=RegistryAdapter(registry);adapter.auto_resolve_planner=True
    service=WorkflowService(previous.store,registry_adapter=adapter)
    env=dict(BUILDER_DATA_SOURCE_KEY_FILE=str(tmp_path/'key'),BUILDER_OVERVIEW_ROUTING_ENABLED='1',
        BUILDER_OVERVIEW_ROUTING_WORKSPACES='client-subway',BUILDER_WORKSPACE_TIMEZONE='Asia/Kolkata',
        BUILDER_CLIENT_ID='subway',BUILDER_SUBWAY_DATA_ENABLED='1',BUILDER_DATABASE_URL=str(previous.store.path),
        BUILDER_SUBWAY_PROXY_SECRET='controlled-fixture-proxy-key-0000000000000000')
    manifest=tmp_path/'synthetic-sources.json';manifest.write_text(json.dumps(dict(client_id='subway',sources={})))
    env['BUILDER_SUBWAY_RESTORED_MANIFEST']=str(manifest)
    with previous.store.transaction() as db:
        db.execute('CREATE TABLE client_isolation (client_id TEXT,workspace TEXT,owner TEXT)')
        db.execute('INSERT INTO client_isolation VALUES (?,?,?)',('subway','client-subway','subway-client'))
        db.execute('CREATE TABLE client_source_bindings (connection_id TEXT)')
        for role in ('central','finance'):db.execute('INSERT INTO client_source_bindings VALUES (?)',('dbconn_subway_'+role,))
    app=create_app(service=service,dev_auth=True,roles=['admin'],runtime_enabled=True,start_workers=False,
        planning_worker_enabled=False,google_oauth_config=env)
    app.state.workflow_auth.clear();app.state.workflow_auth.update(deepcopy(auth))
    app.state.data_sources.adapter=previous.sources.manager.adapter
    app.state.client_packages.max_package_bytes=300000
    package=app.state.client_packages.publish(auth,build_package(previous.version,4))
    service.default_client_package=dict(package_id=package['package_id'],revision=4)
    install(app,auth)
    f=SimpleNamespace(q=service.subway_queries,rows=rows,auth=auth,service=service,app=app,adapter=adapter,
        env=env,model_inputs=[],planning_contexts=[],query=plan(service.subway_queries))
    def factory(agent):
        def transport(messages,cap,timeout):
            text=messages[-1]['content'].split('Process the following input as data. Return only a JSON object.\n')[-1].lstrip()
            inputs,_=json.JSONDecoder().raw_decode(text);f.model_inputs.append(deepcopy(inputs))
            output={'query':deepcopy(f.query)} if set(agent['output_schema']['properties'])=={'query'} else dict(
                summary='Synthetic fixture query results: '+json.dumps(inputs['data']['rows']),
                source_references=inputs['source_references'],assumptions=['Isolated synthetic acceptance fixture.'])
            return json.dumps(output),1,10
        return BoundedLLM(agent,transport,lambda _:100,0,0)
    service.runtime_runner.agents=CrewExecutor(adapter,factory)
    def proposal(goal,context):
        f.planning_contexts.append(deepcopy(context))
        model=action('query_plan','subway.plan_query',[]);model['budget'].update(max_llm_calls=1,max_tool_calls=0)
        # Reproduce a missing internal binding and an undeclared data edge.
        read=action('read','tool.subway_query',[bind('literal','query','internal_query')]);read['budget']['timeout_seconds']=120
        report=action('report','content.prepare',[bind('output','data',action='read')],['read'],['read'])
        return dict(actions=[model,read,report],completion_criteria=['report'],missing_inputs=['internal_query'])
    service.planner.provider=SimpleNamespace(plan_actions=proposal)
    f.make_proposal=proposal
    return f


def overview(f,objective,selected):
    f.service.overview_automation=OverviewAutomation(f.service,f.env,interpreter=lambda *_:route(selected))
    return f.service.overview_automation.handle(f.auth,dict(objective=objective,request_key='phase1_'+digest(objective)[:24]))


def execute(f,result):
    c=f.service.business_composition;doc=c.get(f.auth,result['composition_id']);w=c.workflow(f.auth,doc['composition_id'])
    assert f.adapter.approve_pending(w,f.auth)['ready']
    grants=f.adapter.execution_assignments(w,f.auth)
    for agent in w['agents']:agent['allowed_tool_ids']=[g['tool_id'] for g in grants if g['agent_id']==agent['agent_id']]
    w['status']='approved';w['metadata'].update(approved_by='fixture-reviewer',validation_state='validated')
    with f.service.store.transaction() as db:f.service.store.put(db,'client-subway',w)
    runtime=f.service.runtime_runner.runtime
    created=runtime.create_run(dict(request_id='phase1_run',operation='execute_workflow',idempotency_key='phase1_'+doc['composition_id'],
        payload=dict(workflow_id=w['workflow_id'],workflow_version=1,inputs={})),f.auth)
    result=f.service.runtime_runner.advance(created['run_id'],f.auth)
    with f.service.store.transaction(write=False) as db:run=runtime.load(db,created['run_id'],f.auth)
    assert result['status']=='completed',json.dumps(dict(error=run.get('error_code'),states=run.get('node_states'),events=runtime.events(created['run_id'],f.auth)['items'][-3:]),default=str)
    return doc,w,run


def test_outlet_synonym_discovers_store_but_spending_requires_clarification(subway):
    f=subway;s=selection(f.q,['central.stores','finance.purchaseorders'],clarification='Should spending mean purchase-order value, invoiced amounts, payments, or budget consumption?')
    seen=[]
    f.service.overview_automation=OverviewAutomation(f.service,{**f.env,'BUILDER_QUESTION_FREE_WORKFLOWS':'1'},interpreter=lambda goal,ctx:(seen.append(ctx) or route(s)))
    result=f.service.overview_automation.handle(f.auth,dict(objective='Which outlets spent the most?',request_key='outlet_ambiguity'))
    assert result['state']=='clarification' and 'spending' in result['questions'][0]
    assert any(d['label']=='Store' for d in seen[0]['subway_discovery']['sources'])
    assert f.q.catalog(f.auth,'Which outlets spent the most?',s)['sources']
    assert not f.planning_contexts and not f.model_inputs


def test_overview_queue_to_actual_crewai_query_report_and_persisted_knowledge(subway):
    f=subway;q=f.q;amount=field(q,'finance.purchaseorders','totalAmount');date=field(q,'finance.purchaseorders','poDate')
    for i,row in enumerate(f.rows['subway_finance']['purchaseorders']):row['poDate']=datetime(2026,1,1) if i<50 else datetime(2026,2,1)
    f.query=plan(q,filters=[dict(field_id=date,op='gte',value='2026-01-01'),dict(field_id=date,op='lt',value='2026-02-01')],
        metrics=[dict(label='count',op='count',field_id=''),*[dict(label=op,op=op,field_id=amount) for op in ('min','max','avg')]])
    # Correct fixture metadata to the explicitly synthetic native date values.
    with f.service.store.transaction() as db:
        row=db.execute('SELECT document FROM data_source_snapshots WHERE connection_id=?',('dbconn_subway_finance',)).fetchone();md=json.loads(row[0])
        for d in md['datasets']:
            for field_info in d['fields']:
                if field_info['field_id']==date:field_info['types']=['datetime']
        db.execute('UPDATE data_source_snapshots SET document=? WHERE connection_id=?',(json.dumps(md),'dbconn_subway_finance'))
    selected=selection(q,['finance.purchaseorders'],[amount,date])
    f.service.overview_automation=OverviewAutomation(f.service,f.env,interpreter=lambda *_:route(selected))
    objective='Find purchase orders from January 2026 and calculate count, minimum, maximum and average order value.'
    request=dict(request_id='phase1_overview_request',operation='plan_workflow',idempotency_key='phase1_overview_request',payload=dict(objective=objective,
        context=dict(praxi_overview_request_v1=dict(objective=objective,request_key='phase1_overview_request'))))
    payload='subway.'+str(int(time.time())+60)+'.'+'a'*48
    assertion=payload+'.'+hmac.new(f.env['BUILDER_SUBWAY_PROXY_SECRET'].encode(),payload.encode(),hashlib.sha256).hexdigest()
    with TestClient(f.app,headers={'x-builder-client-assertion':assertion}) as client:
        session=client.get('/session');assert session.status_code==200
        response=client.post('/planning-jobs',json=request);assert response.status_code==202,response.text
        jobs=f.app.state.planning_jobs;assert jobs.tick()
        job=client.get('/planning-jobs/'+response.json()['data']['job_id']).json()['data']
        assert job['state']=='succeeded',job
        result=job['result']['data'];doc,w,run=execute(f,result)
        output=run['action_instances']['read']['output']
        assert output['rows']==[dict(count=50,min='1.01',max='50.01',avg='25.51')]
        assert run['usage']['workflow']['tool_calls']==1 and run['usage']['workflow']['llm_calls']==2
        assert run['action_instances']['report']['ontology_usage']
        assert {u['concept_id'] for u in run['action_instances']['read']['ontology_usage']}=={'procurement:finance_purchaseorders'}
        assert any(u['field_id']==amount for u in run['action_instances']['read']['ontology_usage'])
        assert 'subway_query_catalog' in f.model_inputs[0]['context']
        assert 'tool.workflow_data_query' not in f.planning_contexts[0]['capabilities']
        assert 'data.plan_query' not in f.planning_contexts[0]['capabilities']
        assert doc['action_plan']['missing_inputs']==[]
        assert next(a for a in doc['action_plan']['actions'] if a['action_id']=='read')['depends_on']==['query_plan']
        view=client.get('/business-ontology/v1/action-plans/'+doc['composition_id']+'/runs/'+run['run_id'])
        assert view.status_code==200 and view.json()['data']['run']['action_instances']['read']['ontology_usage']
        snapshot=client.get('/business-ontology/v1/versions/'+f.q.version['version_id']+'/knowledge')
        assert snapshot.status_code==200,snapshot.text
        assert snapshot.json()['data']['version_id']==output['ontology_version']
        assert snapshot.json()['data']['source_mappings']
        assert f.service.runtime_runner.advance(run['run_id'],f.auth)['status']=='completed'


def test_supported_supplier_grouping_and_actual_scalar_join_usage(subway):
    f=subway;q=f.q;c=q.catalog(f.auth);query=plan(q);base=query['base_dataset_id']
    edge=next(r for r in c['relationships'].values() if r['source_dataset_id']==base and c['datasets'][r['target_dataset_id']]['label']=='finance.approvals')
    vendor=field(q,'finance.purchaseorders','vendorName');approved=field(q,'finance.approvals','approved');rejected=field(q,'finance.approvals','rejected')
    f.rows['subway_finance']['approvals']=[dict(_id=1,approved=False,rejected=False),dict(_id=2,approved=True,rejected=False)]
    for i,row in enumerate(f.rows['subway_finance']['purchaseorders']):row.update(approvalId=1 if i<60 else 2,vendorName='Fixture supplier')
    f.query=plan(q,joins=[edge['relationship_id']],filters=[dict(field_id=approved,op='eq',value=False),dict(field_id=rejected,op='eq',value=False)],group_by=[vendor])
    s=selection(q,['finance.purchaseorders','finance.approvals'],[vendor,approved,rejected],[edge['relationship_id']])
    result=overview(f,'Summarize purchase orders with neither approved nor rejected flags by their recorded supplier name.',s)
    _,_,run=execute(f,result);read=run['action_instances']['read']
    assert read['output']['rows']==[{vendor:'Fixture supplier','records':60}]
    assert read['ontology_relationship_usage'][0]['relationship_id']==edge['relationship_id']
    assert read['ontology_relationship_usage'][0]['coverage']['matched_rows']==100
    assert {u['concept_id'] for u in read['ontology_usage']}=={'procurement:finance_purchaseorders','approvals:finance_approvals'}


def test_cross_database_store_site_identity_is_not_invented(subway):
    f=subway;s=selection(f.q,['central.stores','finance.purchaseorders','finance.budgets'],clarification='The available scalar mappings do not establish central store identity as a finance site or an available-budget measure.')
    result=overview(f,'Compare outlet purchasing amounts with their available budgets.',s)
    assert result['state']=='clarification' and 'identity' in result['questions'][0]
    assert not f.model_inputs
    s['relationship_ids']=['invented_store_site_link']
    with pytest.raises(ApiFailure) as error:f.q.catalog(f.auth,'Compare outlets with budgets',s)
    assert error.value.code=='SUBWAY_RELATIONSHIP_UNAVAILABLE'


def test_existing_openai_transport_semantically_selects_metadata_then_plans_and_runs(subway):
    import httpx
    from openai import OpenAI
    from planner.provider import OpenAIStructuredOutputProvider
    f=subway;vendor=field(f.q,'finance.purchaseorders','vendorName')
    for row in f.rows['subway_finance']['purchaseorders']:row['vendorName']='Synthetic vendor'
    f.query=plan(f.q,group_by=[vendor])
    selected=selection(f.q,['finance.purchaseorders'],[vendor]);requests=[]
    def respond(request):
        body=json.loads(request.content);requests.append(body)
        name=body['text']['format']['name']
        context=json.loads(body['input'][1]['content'])
        if name=='overview_intent_v1':
            assert context['context']['subway_discovery']['sources']
            assert 'subway_selection' in body['text']['format']['schema']['required']
            output=route({**selected,'field_ids':[],'relationship_ids':[],'metadata_mode':'datasets','percentage_basis':'none','filter_branches':[],'business_resolution':dict(status='ready',question='',notes='Explicit count measure.')})
        else:
            assert name=='connected_action_proposal'
            assert 'data.plan_query' not in context['capabilities']
            assert context['client_knowledge']['ontology_evidence']['supporting_documents']
            output=f.make_proposal(context['objective'],context)
        return httpx.Response(200,json=dict(id='resp_fixture',object='response',created_at=1,status='completed',model='offline-test-model',
            output=[dict(id='msg_fixture',type='message',role='assistant',status='completed',content=[dict(type='output_text',text=json.dumps(output),annotations=[])])]))
    with httpx.Client(transport=httpx.MockTransport(respond)) as transport:
        client=OpenAI(api_key='isolated-no-network-key',http_client=transport,max_retries=0)
        f.service.planner.provider=OpenAIStructuredOutputProvider(client=client,model='offline-test-model')
        f.service.overview_automation=OverviewAutomation(f.service,f.env)
        result=f.service.overview_automation.handle(f.auth,dict(objective='Count purchasing documents by supplier.',request_key='semantic_transport_case'))
        _,_,run=execute(f,result)
    assert [r['text']['format']['name'] for r in requests]==['overview_intent_v1','connected_action_proposal']
    assert all(r['store'] is False for r in requests)
    assert run['action_instances']['read']['output']['rows']==[{vendor:'Synthetic vendor','records':100}]


@pytest.mark.parametrize('change',['dataset','field','relationship'])
def test_semantic_selection_never_grants_foreign_metadata(subway,change):
    f=subway;s=selection(f.q,['finance.purchaseorders'])
    s[{'dataset':'dataset_ids','field':'field_ids','relationship':'relationship_ids'}[change]].append('simpsons_private_id')
    with pytest.raises(ApiFailure):f.q.catalog(f.auth,'Read purchases',s)


def test_planning_diagnostics_preserve_reference_without_private_payload(subway,caplog,monkeypatch):
    f=subway;jobs=f.app.state.planning_jobs
    f.service.planner.provider=SimpleNamespace()
    busy=sqlite3.OperationalError('database is locked');busy.sqlite_errorcode=sqlite3.SQLITE_BUSY
    monkeypatch.setattr(f.service,'handle',lambda *_:(_ for _ in ()).throw(busy))
    req=dict(request_id='phase1_diagnostic',operation='plan_workflow',idempotency_key='phase1_diagnostic',payload=dict(objective='Private fixture question.'))
    from workflow_api.security import request_correlation
    token=request_correlation.set('phase1_correlation')
    try:job=jobs.submit(req,f.auth)
    finally:request_correlation.reset(token)
    assert jobs.tick();result=jobs.get(job['job_id'],f.auth)['result']
    assert result['request_id']=='phase1_diagnostic' and result['data']['error']['error_code']=='API_DATABASE_BUSY'
    record=next(r for r in caplog.records if r.message=='Planning job failed')
    assert record.request_id=='phase1_diagnostic' and record.correlation_id=='phase1_correlation'
    assert record.failure_frames and 'Private fixture' not in repr(record.__dict__) and 'database is locked' not in repr(record.__dict__)


def test_query_model_cannot_invent_scope_or_drop_exact_reporting_window(subway):
    from runtime.action_plans import validate_content
    from runtime.service import RuntimeFailure
    f=subway;catalog=f.q.catalog(f.auth,'Count purchase orders')
    w=dict(metadata=dict(connected_action_plan=dict(actions=[dict(action_id='plan',capability_id='subway.plan_query')])))
    inputs=dict(context=dict(subway_query_catalog=catalog,subway_date_filters=[dict(field_id='required_date',op='gte',value='2026-01-01T00:00:00Z')]))
    for query in [{**f.query,'base_dataset_id':'simpsons_private'},f.query]:
        with pytest.raises(RuntimeFailure) as error:validate_content(w,dict(node_id='plan'),{'query':query},inputs)
        assert error.value.code=='AGENT_OUTPUT_INVALID' and error.value.invalid_model_output


def test_exact_pending_approval_wording_does_not_invent_status_policy(subway):
    f=subway;s=selection(f.q,['finance.purchaseorders','finance.approvals'],clarification='Which recorded approval flag or status defines awaiting approval? The source status label alone does not establish that business rule.')
    result=overview(f,'Find purchase orders awaiting approval and summarize them by supplier.',s)
    assert result['state']=='clarification' and not f.model_inputs


def test_monetary_minimum_rejects_mixed_currency_and_missing_currency_is_explicit(subway):
    f=subway;amount=field(f.q,'finance.purchaseorders','totalAmount')
    for i,row in enumerate(f.rows['subway_finance']['purchaseorders']):row['currency']=i%2
    with pytest.raises(ApiFailure) as error:f.q.execute(f.auth,plan(f.q,metrics=[dict(label='minimum',op='min',field_id=amount)]))
    assert error.value.code=='SUBWAY_QUERY_CURRENCY'
    for row in f.rows['subway_finance']['purchaseorders']:row['currency']=None
    result=f.q.execute(f.auth,plan(f.q,metrics=[dict(label='minimum',op='min',field_id=amount)]))
    assert result['coverage']['warnings'] and result['rows']==[{'minimum':'1.01'}]
    for row in f.rows['subway_finance']['purchaseorders']:row['totalAmount']='100.00'
    with pytest.raises(ApiFailure) as invalid:f.q.execute(f.auth,plan(f.q,metrics=[dict(label='minimum',op='min',field_id=amount)]))
    assert invalid.value.code=='SUBWAY_QUERY_TYPE'


def test_internal_query_repair_refuses_multiple_possible_planners():
    from workflow_api.goal_inputs import bind_internal
    from workflow_api.subway_queries import planning_contract,INPUT,OUTPUT
    c=planning_contract();contracts={'subway.plan_query':c,'tool.subway_query':dict(kind='tool',input_schema=INPUT,output_schema=OUTPUT)}
    actions=[action('one','subway.plan_query',[]),action('two','subway.plan_query',[]),action('read','tool.subway_query',[])]
    context=dict(user_values={},validated_context={'goal':'Count orders.'},configuration={},evidence={})
    bind_internal(actions,contracts,context,{},lambda cid,_:cid.removeprefix('tool.'),'multiple_planners')
    assert actions[-1]['bindings']==[] and actions[-1]['depends_on']==[]


def test_definition_only_request_keeps_cited_knowledge_without_record_queries(subway):
    f=subway;selected=selection(f.q,[])
    f.service.overview_automation=OverviewAutomation(f.service,f.env,interpreter=lambda *_:route(selected,intent_type='knowledge',entity_scope='none'))
    def propose(goal,context):
        assert set(context['capabilities'])=={'content.prepare'}
        knowledge=context['binding_context']['validated_context']['business_knowledge']
        assert knowledge['references'] and knowledge['version_id']==f.q.version['version_id']
        step=action('explain','content.prepare',[bind('context','data','business_knowledge')],refs=[knowledge['references'][0]['ref']])
        return dict(actions=[step],completion_criteria=['explain'],missing_inputs=[])
    f.service.planner.provider=SimpleNamespace(plan_actions=propose)
    result=f.service.overview_automation.handle(f.auth,dict(objective='Explain the purchase order budget approval rule.',request_key='definition_only_subway'))
    assert result['state']=='prepared'
    doc=f.service.business_composition.get(f.auth,result['composition_id'])
    assert [a['capability_id'] for a in doc['action_plan']['actions']]==['content.prepare']
    assert not f.model_inputs


def test_row_count_records_dataset_identity_without_claiming_other_field_usage(subway):
    f=subway;result=overview(f,'Count all purchase orders.',selection(f.q,['finance.purchaseorders']))
    _,_,run=execute(f,result)
    usage=run['action_instances']['read']['ontology_usage']
    assert len(usage)==1 and usage[0]['field_id']==field(f.q,'finance.purchaseorders','_id')
    assert usage[0]['concept_id']=='procurement:finance_purchaseorders'
