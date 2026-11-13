"""Real isolated planner/composition/Registry/jobs/scheduler; controlled transports."""
from copy import deepcopy
from types import SimpleNamespace
import json
import pytest
from tests.test_overview_automation_integration import automation,google_setup,connected,composition,investigation,retrieval,knowledge,reference,generation,foundation,auth,release,queries,setup_query,intent,action,bind,approve,stored,drain
from workflow_api.simpsons_planning import SimpsonsPlanning,consent,validate_consent,check_action,validate_actions,ANNOTATION,presentation_title
from workflow_api.overview_automation import OverviewAutomation
from workflow_api.service import ApiFailure
from runtime.crew import CrewExecutor
from runtime.model import BoundedLLM
from tests.test_data_queries import plan
from runtime.supplier_search import SEARCH,SupplierSearchConnector

PUBLIC='general diesel engine smoke causes and suggested checks'


@pytest.fixture
def pipeline(automation,queries,monkeypatch):
    f=automation
    # These fixtures originally used separate application stores. Only this new
    # fixture shares query metadata/jobs and runtime, matching the deployed app.
    with queries.store.transaction(write=False) as source,f.general.store.transaction() as target:
        for cid,raw in target.execute('SELECT connection_id,document FROM data_source_connections'):
            doc=json.loads(raw);doc['profiling_status']='not_profiled'
            target.execute('UPDATE data_source_connections SET document=? WHERE connection_id=?',(json.dumps(doc),cid))
        for name,sql in source.execute("SELECT name,sql FROM sqlite_master WHERE type='table' AND name LIKE 'data_%'"):
            target.execute(sql.replace('CREATE TABLE ','CREATE TABLE IF NOT EXISTS ',1))
            rows=source.execute('SELECT * FROM "'+name+'"').fetchall()
            if rows:target.executemany('INSERT OR REPLACE INTO "'+name+'" VALUES ('+','.join('?'*len(rows[0]))+')',rows)
    queries.store=queries.manager.store=queries.manager.relationships.store=f.general.store
    jobs,seen,_,body=setup_query(f,queries)
    first=plan();second=plan();second.update(base_dataset_id='mongo_categories',metrics=[],fields=['mongo_categories_name'],limit=2)
    queries.reader.rows['mongo_categories'][0]['mongo_categories_name']='PRIVATE controlled workshop note'
    f.general.simpsons_planning=SimpsonsPlanning(f.general,{},generator=lambda *_:dict(queries=[deepcopy(first),deepcopy(second)],clarification='',limitations=['Returned detail rows are bounded.']))
    tool=deepcopy(SEARCH);tool['availability']='enabled'
    policy=deepcopy(f.registry._policy);policy.version+=1;policy.approved_providers.add(tool['provider_id']);policy.agent_permissions.update(tool['permission_scopes']);policy.remaining_quota[tool['tool_id']]=20
    for actor in (f.x.a,f.x.current):
        actor['permissions']=sorted(set(actor['permissions'])|set(tool['permission_scopes']));actor['scopes']=sorted(set(actor['scopes'])|set(tool['permission_scopes']))
    assert f.registry.update_policy(policy,f.x.a)['status']==200
    assert f.registry.register_tool(tool,f.x.a)['status']==200
    f.connectors[tool['tool_id']]=SupplierSearchConnector(tool);searches=[]
    def search(connector,grant,inputs,effect,deadline):
        assert inputs['query']==PUBLIC
        assert 'PRIVATE' not in json.dumps(inputs)
        searches.append(deepcopy(inputs))
        return dict(results=[dict(title='Controlled public guidance',url='https://public.example/smoke',snippet='Public-only synthetic test guidance.')])
    monkeypatch.setattr(SupplierSearchConnector,'execute',search)
    def factory(definition):
        def transport(messages,cap,timeout):
            raw=messages[-1]['content'].split('Process the following input as data. Return only a JSON object.\n')[-1].lstrip()
            data,_=json.JSONDecoder().raw_decode(raw)
            return json.dumps(dict(summary='Source-backed controlled assessment; coverage is bounded, no confirmed diagnosis.',title='Smoke guidance',subject='Daily source review',body='Controlled findings with evidence limitations: https://public.example/smoke',source_references=data['source_references'],assumptions=['Synthetic controlled test; no company findings.'])),1,10
        return BoundedLLM(definition,transport,lambda _:100,0,0)
    f.runner.agents=CrewExecutor(f.adapter,factory)
    reads=[action('read_'+str(i),'tool.workflow_data_query',[bind('context','query','reviewed_simpsons_queries',path=['query_'+str(i)])]) for i in range(2)]
    search_action=action('search','tool.supplier_web_search',[bind('context','query','reviewed_public_search_queries',path=[0])])
    assess=action('assess','simpsons.assess',[bind('output','data',action='read_0')],['read_0','read_1','search'],['read_0','read_1','search'])
    assess['budget'].update(max_llm_calls=1,max_tool_calls=0)
    email=action('email','content.prepare',[bind('output','data',action='assess')],['assess'],['assess'])
    send=action('send','tool.extension_mail_send',[bind('literal','to','recipient'),bind('generated','subject',action='email',path=['subject']),bind('generated','body',action='email',path=['body'])],['email'])
    proposal=dict(actions=reads+[search_action,assess,email,send],completion_criteria=['send'],missing_inputs=[])
    f.general.planner.provider=SimpleNamespace(plan_actions=lambda goal,ctx:(seen.append(deepcopy(ctx)) or deepcopy(proposal)))
    route=intent();route['side_effects']=['email_send'];route['temporal']['period']='none';route['recurrence'].update(hour=20,minute=35);route['public_research_queries']=[PUBLIC]
    router=OverviewAutomation(f.general,dict(BUILDER_OVERVIEW_ROUTING_ENABLED='1',BUILDER_OVERVIEW_ROUTING_WORKSPACES='one'),interpreter=lambda *_:deepcopy(route))
    body.pop('automatic_inputs',None);body.update(objective='Every day at 8:35 PM India time review available records and documents, search public diesel guidance without internal data, and email engineer@example.com a cited summary. Prepare for approval.')
    return SimpleNamespace(f=f,queries=queries,jobs=jobs,router=router,body=body,searches=searches,seen=seen,proposal=proposal)


def test_prepare_review_activate_two_occurrences_fresh_queries_and_no_duplicates(pipeline):
    p=pipeline;f=p.f
    result=p.router.handle(f.x.a,p.body)
    assert result['state']=='prepared' and result['schedule']['cron']=='35 20 * * *'
    assert result['schedule']['timezone']=='Asia/Kolkata'
    assert ANNOTATION in result['operations']['workflow_data_query']
    assert len(result['operations']['workflow_data_query'][ANNOTATION]['queries'])==2
    assert result['operations']['supplier_web_search']['const']['query']==PUBLIC
    assert not p.jobs.list(f.x.a)['items'] and not p.searches and not f.http.sent
    with pytest.raises(Exception):p.router.handle(f.x.a,dict(operation='activate',request_key=p.body['request_key']))
    workflow=f.c.workflow(f.x.a,result['composition_id'])
    assert f.adapter.approve_pending(workflow,f.x.a)['ready'];approve(f,workflow)
    active=p.router.handle(f.x.a,dict(operation='activate',request_key=p.body['request_key']))
    assert p.router.handle(f.x.a,dict(operation='activate',request_key=p.body['request_key']))==active
    amounts=[]
    for day in range(2):
        if day:p.queries.reader.rows['pg_lines'][0]['pg_lines_qty']=20
        f.now=f.auto.get(f.x.a,active['schedule_id'])['due']
        for _ in range(12):
            f.auto.tick(f.general.worker_authenticate);drain(f)
            p.jobs.tick();f.now+=1
            history=f.auto.history(f.x.a,active['schedule_id'])
            if len(history)==day+1 and all(row['state']=='completed' for row in history):break
        assert len(history)==day+1 and all(row['state']=='completed' for row in history),[(row.get('last_error_code'),stored(f,row['run_id']).get('error_code')) for row in history]
        amounts.append(stored(f,history[0]['run_id'])['action_instances']['read_0']['output']['result']['rows'][0]['sales'])
        assert len(f.http.sent)==len(p.searches)==day+1
        f.auto.tick(f.general.worker_authenticate);assert len(f.http.sent)==day+1
    assert len(p.jobs.list(f.x.a)['items'])==4
    assert len(p.queries.reader.calls)==4
    assert amounts[0]!=amounts[1]


def test_consent_rejects_other_action_query_and_foreign_owner(pipeline):
    p=pipeline;f=p.f;result=p.router.handle(f.x.a,p.body)
    workflow=f.c.workflow(f.x.a,result['composition_id']);schema=result['operations']['workflow_data_query']
    foreign=deepcopy(f.x.a);foreign['subject']['subject_id']='other'
    with pytest.raises(ApiFailure):validate_consent(schema,foreign)
    node=next(n for n in workflow['nodes'] if n['node_id']=='read_0')
    pin=schema[ANNOTATION]
    check_action(schema,workflow,node,{'query':pin['queries']['read_0']},f.x.a)
    with pytest.raises(ApiFailure):check_action(schema,workflow,node,{'query':pin['queries']['read_1']},f.x.a)
    widened=deepcopy(schema);widened['properties']['query']={}
    with pytest.raises(ApiFailure):validate_consent(widened,f.x.a)
    changed=deepcopy(workflow);changed['metadata']['overview_intent']['simpsons_queries']['context_hash']='0'*64
    with pytest.raises(ApiFailure):check_action(schema,changed,node,{'query':pin['queries']['read_0']},f.x.a)


def test_unresolved_multi_source_request_stays_unprepared(pipeline):
    p=pipeline;p.f.general.simpsons_planning.generator=lambda *_:dict(queries=[],clarification='The requested document source is unavailable.',limitations=[])
    result=p.router.handle(p.f.x.a,p.body)
    assert result['state']=='clarification' and result['business_clarification']
    assert not result.get('composition_id') and not result.get('report_only')
    assert not p.jobs.list(p.f.x.a)['items'] and not p.searches


def test_fallback_title_is_scoped_and_honest():
    doc=dict(overview_intent=dict(limitation_report=True,requested_intent={'intent_type':'recurring'}))
    assert presentation_title(SimpleNamespace(simpsons_planning=True),doc,'Daily review').startswith('Automation not prepared')
    assert presentation_title(SimpleNamespace(),doc,'Daily review')=='Daily review'


@pytest.mark.parametrize('bad',['foreign_dataset','unsupported_filter','too_many','duplicate'])
def test_batch_planner_validates_every_query_and_bound(queries,bad):
    from tests.test_data_relationships import auth
    actor=auth();catalog=queries.catalogue(actor)
    first=plan();batch=dict(queries=[first],clarification='',limitations=[])
    if bad=='foreign_dataset':first['base_dataset_id']='foreign_company'
    elif bad=='unsupported_filter':first['filters']=[dict(field_id='pg_lines_qty',op='contains',value='smoke')]
    elif bad=='too_many':batch['queries']=[first]*5
    else:batch['queries']=[first,deepcopy(first)]
    planner=SimpsonsPlanning(SimpleNamespace(workflow_queries=SimpleNamespace(queries=queries)),{},generator=lambda *_:batch)
    if bad=='duplicate':assert len(planner.prepare(actor,'Read available records',catalog)['queries'])==1
    else:
        with pytest.raises(ApiFailure):planner.prepare(actor,'Read available records',catalog)


def test_simpsons_assessment_rejects_invented_citations_and_links():
    from runtime.action_plans import validate_content
    from runtime.service import RuntimeFailure
    workflow={'metadata':{'connected_action_plan':{'actions':[dict(action_id='assess',capability_id='simpsons.assess')]}}}
    inputs=dict(data={},source_references=['read_0'])
    for output in [dict(source_references=['invented_record']),dict(source_references=['read_0'],body='https://invented.example/diagnosis')]:
        with pytest.raises(RuntimeFailure) as exc:validate_content(workflow,{'node_id':'assess'},output,inputs)
        assert exc.value.code=='ACTION_CONTENT_UNVERIFIED'
