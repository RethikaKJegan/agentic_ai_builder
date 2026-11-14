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


@pytest.mark.parametrize('defect,reason',[
    ('web','outside the reviewed Simpsons catalogue'),
    ('source','outside the reviewed Simpsons catalogue'),
    ('field','unavailable field'),
    ('join','unsupported relationship'),
    ('email','Additional properties'),
    ('date','Unrequested business-date filter'),
    ('mode','Aggregate plans output group keys and metrics only'),
])
@pytest.mark.parametrize('corrected',[False,True])
def test_semantic_correction_is_bounded_and_authorized(queries,defect,reason,corrected):
    from tests.test_data_relationships import auth
    actor=auth();catalog=queries.catalogue(actor);good=plan();bad=deepcopy(good)
    if defect in {'web','source'}:bad['base_dataset_id']='public_web_search' if defect=='web' else 'other_tenant'
    elif defect=='field':bad['filters']=[dict(field_id='nonexistent',op='eq',value=1)]
    elif defect=='join':bad['joins']=[dict(relationship_id='fictional',target_dataset_id='mongo_categories')]
    elif defect=='email':bad['email_send']={'to':'someone@example.com'}
    elif defect=='mode':bad['fields']=['pg_lines_qty']
    else:
        # A date value in a string field is also an unrequested date restriction.
        bad.update(base_dataset_id='mongo_categories',fields=['mongo_categories_name'],metrics=[],
            filters=[dict(field_id='mongo_categories_name',op='eq',value='2026-11-13')])
    calls=[]
    def generate(objective,catalog):
        calls.append(deepcopy(objective))
        return dict(queries=[good if corrected and len(calls)==2 else bad],clarification='',limitations=[])
    planner=SimpsonsPlanning(SimpleNamespace(workflow_queries=SimpleNamespace(queries=queries)),{},generator=generate)
    scope=dict(internal_query='Read available complaints.',date_filters=[])
    if corrected:
        result=planner.prepare(actor,scope,catalog)
        assert result['queries']=={'query_0':good}
        # Execute the corrected plan through the existing authorized query API.
        queries.planner.output=result['queries']['query_0']
        saved=queries.plan(actor,{'question':'Read authorized records'})
        assert queries.execute(actor,{'plan_id':saved['plan_id']})['matched_rows']==3
    else:
        with pytest.raises(ApiFailure,match=reason):planner.prepare(actor,scope,catalog)
        assert not queries.reader.calls
    assert len(calls)==2
    assert reason in calls[1]['correction']['message']
    assert calls[1]['internal_intent']==scope


@pytest.mark.parametrize('prompt,period,kind',[
    ('Every day at 8:35 PM India time, summarize available Simpsons complaints.','none','daily'),
    ("Every day at 8:35 PM India time, summarize today's Simpsons complaints.",'today','daily'),
    ('Investigate Simpsons complaints and research public diesel-engine maintenance guidance. Prepare a report.','none','none'),
    ('Every day at 8:35 PM India time, investigate Simpsons engine complaints, research general public diesel-engine troubleshooting guidance, and prepare an evidence-backed email summary for approval. Do not restrict complaints by date.','none','daily'),
    ('Every Monday at 9 AM India time, summarize Simpsons complaints from the previous calendar month.','previous_month','weekly'),
    ('Find all complaints associated with engine serial number X.','none','none'),
    ('Find complaints with operating hours between 0 and 100 inclusive.','none','none'),
])
def test_real_prompt_internal_normalization(prompt,period,kind):
    from workflow_api.simpsons_planning import internal_goal,query_intent
    route=intent();route['business_goal']=prompt;route['temporal'].update(period=period,field_id='complaint_date' if period!='none' else None)
    route['recurrence'].update(kind=kind,hour=9 if kind=='weekly' else 20,minute=0 if kind=='weekly' else 35)
    catalog={'datasets':[{'fields':[{'field_id':'complaint_date'}]}]}
    queries=SimpleNamespace(context=lambda _:({}, {}, {'complaint_date':{'types':['timestamp with time zone']}},{}))
    scope=query_intent(route,None,catalog,queries,{},1794614400,'Asia/Kolkata')
    text=scope['internal_query'].lower()
    assert 'complaints' in text and '8:35' not in text and '9 am' not in text
    assert 'public' not in text and 'email' not in text and 'prepare' not in text
    assert scope['execution_schedule']['kind']==kind
    assert bool(scope['date_filters'])==(period!='none')
    if period=='previous_month':
        assert [p['value'] for p in scope['date_filters']]==['2026-09-30T18:30:00+00:00','2026-10-31T18:30:00+00:00']
    if 'serial number' in prompt:assert internal_goal(prompt)==prompt
    if 'operating hours' in prompt:assert 'between 0 and 100 inclusive' in text


def test_one_time_mixed_scope_preserves_original_goal_and_public_action(pipeline):
    p=pipeline;route=p.router.interpreter('',{})
    route['intent_type']='one_time';route['recurrence'].update(kind='none',hour=None)
    route['business_goal']='Investigate Simpsons complaints and research public diesel-engine maintenance guidance. Prepare a report.'
    p.router.interpreter=lambda *_:deepcopy(route)
    seen=[]
    original=p.f.general.simpsons_planning.generator
    p.f.general.simpsons_planning.generator=lambda goal,catalog:(seen.append(deepcopy(goal)) or original(goal,catalog))
    p.body['objective']=route['business_goal']
    result=p.router.prepare_intent(p.f.x.a,p.body)
    assert result['result']['state']=='prepared' and result['intent']['schedule'] is None
    assert len(result['intent']['simpsons_queries']['queries'])==2
    assert 'public' not in seen[0]['internal_query']
    assert seen[0]['excluded_workflow_intents']['public_research']==[PUBLIC]
    assert result['intent']['route']['side_effects']==['email_send']
    assert p.body['objective']==route['business_goal']
    assert not p.searches and not p.f.http.sent


@pytest.mark.parametrize('period',['today','previous_month'])
@pytest.mark.parametrize('count',[1,2])
def test_dated_preliminary_handoff_uses_existing_relative_binding(pipeline,period,count):
    from workflow_api.temporal_queries import resolve,window
    p=pipeline
    with p.queries.store.transaction() as db:
        raw=db.execute("SELECT document FROM data_source_snapshots WHERE connection_id='pg'").fetchone()[0]
        snapshot=json.loads(raw)
        snapshot['datasets'][0]['fields'].append(dict(field_id='pg_lines_created',name='created',types=['timestamp with time zone'],nullable=True))
        db.execute("UPDATE data_source_snapshots SET document=? WHERE connection_id='pg'",(json.dumps(snapshot),))
    p.queries.manager.relationships.request(p.f.x.a);p.queries.manager.relationships.tick()
    route=p.router.interpreter('',{});route['temporal'].update(period=period,field_id='pg_lines_created')
    p.router.interpreter=lambda *_:deepcopy(route)
    def generator(scope,catalog):
        first=plan();first['filters']=deepcopy(scope['date_filters'])
        second=plan();second.update(base_dataset_id='mongo_categories',metrics=[],fields=['mongo_categories_name'])
        return dict(queries=[first,second][:count],clarification='',limitations=[])
    p.f.general.simpsons_planning.generator=generator
    result=p.router.prepare_intent(p.f.x.a,p.body)
    if count==2:
        assert result['result']['state']=='clarification'
        assert 'per-query relative-date bindings' in result['result']['questions'][0]
        assert result['intent'] is None
    else:
        prepared=result['intent'];assert prepared['temporal_pin']['period']==period
        due=prepared['schedule']['next_due']+32*86400
        resolved=resolve(prepared['query'],prepared['temporal_pin'],due)
        assert [f['value'] for f in resolved['filters']]==list(window(period,'Asia/Kolkata',due))
        assert resolved['metrics']==prepared['query']['metrics']
    assert not p.jobs.list(p.f.x.a)['items'] and not p.searches and not p.f.http.sent


def test_identity_route_does_not_prepare_population_queries(pipeline):
    p=pipeline;route=p.router.interpreter('',{})
    route.update(intent_type='investigation',entity_scope='identified_case',side_effects=[],business_goal='Find all complaints associated with engine serial number X.')
    route['recurrence'].update(kind='none',hour=None)
    p.router.interpreter=lambda *_:deepcopy(route)
    p.f.general.simpsons_planning.generator=lambda *_:pytest.fail('Identity investigation entered population planner')
    p.body['objective']=route['business_goal']
    assert 'simpsons_queries' not in p.router.prepare_intent(p.f.x.a,p.body)['intent']


def test_correction_respects_existing_retry_budget(queries,monkeypatch):
    from tests.test_data_relationships import auth
    actor=auth();calls=[]
    bad=plan();bad['base_dataset_id']='fictional'
    planner=SimpsonsPlanning(SimpleNamespace(workflow_queries=SimpleNamespace(queries=queries)),{},
        generator=lambda *_:(calls.append(True) or dict(queries=[bad],clarification='',limitations=[])))
    def deny():raise ApiFailure('BUDGET_EXHAUSTED','No correction budget remains.',403)
    monkeypatch.setattr('runtime.execution_control.reserve_retry',deny)
    with pytest.raises(ApiFailure,match='No correction budget remains'):
        planner.prepare(actor,dict(internal_query='Read complaints',date_filters=[]),queries.catalogue(actor))
    assert len(calls)==1 and not queries.reader.calls


def test_real_router_paraphrase_excludes_public_synthesis_from_internal_scope():
    from workflow_api.simpsons_planning import internal_goal
    goal = 'Investigate engine complaints without a date restriction and synthesize findings with general public diesel-engine troubleshooting guidance.'
    assert internal_goal(goal) == 'Investigate engine complaints without a date restriction'
    assert internal_goal('Investigate complaints and combine general internal evidence.') == 'Investigate complaints combine general internal evidence.'


@pytest.mark.parametrize('position',['fields','group_by','filter','sort'])
def test_catalog_schema_rejects_unavailable_identifiers(queries,position):
    from jsonschema import Draft202012Validator
    from workflow_api.simpsons_planning import model_schema
    from tests.test_data_relationships import auth
    catalog=queries.catalogue(auth());catalog['relationships']=[]
    query=plan();query.update(metrics=[],fields=['pg_lines_qty'],order_by=[],group_by=[])
    good=dict(queries=[query],clarification='',limitations=[])
    validator=Draft202012Validator(model_schema(catalog))
    assert validator.is_valid(good)
    if position=='fields':query['fields']=['invented']
    elif position=='group_by':query.update(fields=[],group_by=['invented'],metrics=[dict(op='count',expression='',label='count')])
    elif position=='filter':query['filters']=[dict(field_id='invented',op='eq',value=1)]
    else:query['order_by']=[dict(column='invented',direction='asc')]
    assert not validator.is_valid(good)


@pytest.mark.parametrize('position',['fields','group_by','filter','sort','expression'])
def test_correction_identifies_field_dataset_and_allowed_alternatives(queries,position):
    from tests.test_data_relationships import auth
    actor=auth();catalog=queries.catalogue(actor);bad=plan();calls=[]
    if position=='fields':bad['fields']=['invented']
    elif position=='group_by':bad['group_by']=['invented']
    elif position=='filter':bad['filters']=[dict(field_id='invented',op='eq',value=1)]
    elif position=='sort':bad.update(metrics=[],fields=['pg_lines_qty'],order_by=[dict(column='invented',direction='asc')])
    else:bad['metrics'][0]['expression']='invented * 2'
    def generate(scope,catalog):
        calls.append(deepcopy(scope))
        return dict(queries=[bad],clarification='',limitations=[])
    planner=SimpsonsPlanning(SimpleNamespace(workflow_queries=SimpleNamespace(queries=queries)),{},generator=generate)
    scope=dict(internal_query='Review complaints without date restriction',date_filters=[])
    with pytest.raises(ApiFailure,match='unavailable field'):planner.prepare(actor,scope,catalog)
    assert len(calls)==2 and not queries.reader.calls
    correction=calls[1]['correction'];details=correction['details']
    assert details['datasets']==['pg_lines']
    assert details['invalid_references'][0]['field_id']=='invented'
    assert 'pg_lines_qty' in json.dumps(details['allowed_fields'])
    assert details['query_mode'] in ('detail','aggregate')
    assert correction['requirements']==scope


@pytest.mark.parametrize('text,initial,expected',[
    ('Prepare an email summary for my review.',[],False),
    ('Prepare an email summary for my review.',['email_send'],False),
    ('Email me the findings after I approve them.',[],True),
    ('Every day at 8:35 PM India time, review complaints and email me findings after approval.',[],True),
    ('Prepare a report. Do not email me.',[],False),
    ('Send the report to Slack after approval.',[],False),
    ('Deliver the summary to a shared drive.',[],False),
    ('Email me a draft; no external writes.',['email_send'],False),
])
def test_simpsons_delivery_intent_does_not_grant_draft_sending(text,initial,expected):
    from workflow_api.simpsons_planning import normalize_intent
    route=intent();route['side_effects']=initial
    result=normalize_intent(route,text)
    assert ('email_send' in result['side_effects']) is expected
    assert route['side_effects']==initial
    if expected:assert result['recipient_mode']=='selected_account'


@pytest.mark.parametrize('name,day',[('Monday',1),('Wednesday',3),('Sunday',0)])
def test_simpsons_named_weekly_day_preserves_exact_cron_day(name,day):
    from workflow_api.simpsons_planning import normalize_intent
    route=intent();route['recurrence'].update(kind='weekdays',weekdays=[day])
    result=normalize_intent(route,'Every '+name+' at 9 AM India time, summarize complaints.')
    assert result['recurrence']['kind']=='weekly'
    assert result['recurrence']['weekdays']==[day]
    assert route['recurrence']['kind']=='weekdays'


def test_simpsons_named_weekly_days_keep_all_reviewed_days():
    from workflow_api.simpsons_planning import normalize_intent
    route=intent();route['recurrence'].update(kind='weekdays',weekdays=[1,3])
    result=normalize_intent(route,'Every Monday and Wednesday at 9 AM, summarize complaints.')
    assert result['recurrence']['kind']=='weekly'
    assert result['recurrence']['weekdays']==[1,3]


@pytest.mark.parametrize('with_relationships',[False,True])
def test_large_catalog_enum_respects_individual_provider_string_budget(with_relationships):
    from workflow_api.simpsons_planning import model_schema
    fields=[dict(field_id='field_'+str(i).zfill(32),name='Field '+str(i),types=['number']) for i in range(600)]
    catalog=dict(datasets=[dict(dataset_id='authorized',fields=fields)],relationships=[dict(relationship_id='reviewed')] if with_relationships else [])
    schema=model_schema(catalog)
    def enums(value):
        if isinstance(value,dict):
            if 'enum' in value:yield value['enum']
            for child in value.values():yield from enums(child)
        elif isinstance(value,list):
            for child in value:yield from enums(child)
    values=list(enums(schema))
    assert sum(map(len,values))<=1000
    assert all(len(e)<=250 or sum(len(v) for v in e if isinstance(v,str))<=15000 for e in values)
    assert {f['field_id'] for f in fields}<=set(v for e in values for v in e)
