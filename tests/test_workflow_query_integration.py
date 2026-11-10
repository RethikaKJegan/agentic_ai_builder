"""Real CrewAI/Registry/graph query→report→Sheets→email, controlled transports."""
from copy import deepcopy
import json
from types import SimpleNamespace
import pytest

from tests.test_goal_planning import (automation,google_setup,connected,composition,investigation,retrieval,knowledge,reference,generation,foundation,auth,release)
from tests.test_connected_action_plans import action,bind,proposal,compile_run,stored,complete
from tests.test_data_queries import queries,plan
from workflow_api.data_query_jobs import DataQueryJobs
from workflow_api.workflow_queries import install
from runtime.crew import CrewExecutor
from runtime.model import BoundedLLM
from runtime import RuntimeService
from runtime.graph import GraphRunner


def setup_query(f,queries,typed_query=None,expected_rows=None):
    jobs=DataQueryJobs(queries,lambda w,o:f.x.a if (w,o)==('one','alice') else None)
    install(f.general,queries,jobs,f.x.a)
    f.connectors['workflow_data_query']=f.general.workflow_queries
    base=proposal(f.prepared)
    prepare=action('query_plan','data.plan_query',[])
    prepare['budget'].update(max_llm_calls=1,max_tool_calls=0)
    read=action('read','tool.workflow_data_query',[bind('output','query',action='query_plan',path=['query'])],['query_plan'])
    base['actions'][:1]=[prepare,read]
    seen=[]
    f.general.planner.provider=SimpleNamespace(plan_actions=lambda goal,ctx:(seen.append(deepcopy(ctx)) or base))
    model_inputs=[]
    def factory(definition):
        def transport(messages,cap,timeout):
            raw=messages[-1]['content'].split('Process the following input as data. Return only a JSON object.\n')[-1].lstrip()
            inputs,_=json.JSONDecoder().raw_decode(raw);model_inputs.append(deepcopy(inputs))
            if set(definition['output_schema']['properties'])=={'query'}:
                assert model.structured_format['name']=='scoped_read_query'
                assert inputs['context']['data_query_catalog']['datasets']
                output={'query':deepcopy(typed_query or plan())}
            else:
                output=dict(source_references=inputs['source_references'],assumptions=[])
                if 'artifact_url' in inputs:output.update(subject='Population statistics',body='Report: '+inputs['artifact_url'])
                else:
                    result=inputs['data']['result']
                    assert result['rows']==(expected_rows or [{'sales':'33.360'}])
                    assert result['matched_rows']>0
                    output.update(title='Population statistics',summary='Validated source metrics: '+json.dumps(result['rows']),tabs=[dict(title='Statistics',headers=['Metric','Value'],rows=[[key,value] for key,value in result['rows'][0].items()])])
            return json.dumps(output),1,10
        model=BoundedLLM(definition,transport,lambda messages:100,0,0)
        return model
    f.runner.agents=CrewExecutor(f.adapter,factory)
    body=dict(objective='Find all complaints and calculate statistics, create a spreadsheet and email engineer@example.com its link.',
        request_key='population_query_goal',business_request={},automatic_inputs=True,google_connection_id=f.connection)
    return jobs,seen,model_inputs,body


def test_no_id_prompt_queries_waits_resumes_and_delivers_with_selected_account(automation,queries):
    f=automation;jobs,seen,inputs,body=setup_query(f,queries)
    doc,w,rid=compile_run(f,body)
    assert 'data.plan_query' in seen[0]['capabilities']
    assert doc['google_connection_id']==f.connection and not doc['action_plan']['missing_inputs']
    first=f.runner.advance(rid,f.x.a)
    assert first['status']=='running',stored(f,rid)
    before=stored(f,rid)
    assert before['action_instances']['read']['state']=='waiting_for_query'
    assert before['usage']['workflow']['llm_calls']==1 and before['usage']['workflow']['tool_calls']==1
    assert jobs.tick()
    # Restart the runtime while the query is waiting; dependencies and budget persist.
    agents=f.runner.agents
    f.runtime=RuntimeService(f.general,clock=lambda:f.now)
    f.runner=GraphRunner(f.runtime,agents=agents,connectors=f.connectors);f.general.runtime_runner=f.runner
    f.now+=2
    result=complete(f,w,rid)
    assert result['status']=='completed',(stored(f,rid),inputs)
    final=stored(f,rid)
    assert final['usage']['workflow']['tool_calls']==3 # query + sheet + mail, no extra poll charge
    assert final['usage']['workflow']['llm_calls']==3 # typed query + report + email
    assert len(jobs.list(f.x.a)['items'])==1 and len(queries.reader.calls)==1
    assert f.http.write_count==1 and len(f.http.sent)==1
    assert final['action_instances']['read']['output']['coverage']['complete_scan']
    assert final['action_instances']['sheet']['output']['spreadsheet_url'] in final['action_instances']['send']['resolved_inputs']['body']
    assert f.runner.advance(rid,f.x.a)['status']=='completed' and len(f.http.sent)==1


def test_worker_crash_after_query_submission_reattaches_without_new_model_or_job(automation,queries):
    f=automation;jobs,seen,inputs,body=setup_query(f,queries)
    _,w,rid=compile_run(f,body);f.runner.advance(rid,f.x.a)
    with f.general.store.transaction() as db:
        run=f.runtime.load(db,rid,f.x.a)
        run['node_states']['read']='executing';run['lease_until']=0;run['available_at']=0
        f.runtime.save(db,run)
    f.now+=2
    again=f.runner.advance(rid,f.x.a)
    assert again['status']=='running',stored(f,rid)
    assert len(jobs.list(f.x.a)['items'])==1
    assert stored(f,rid)['usage']['workflow']==run['usage']['workflow']
    assert jobs.tick()
    f.now+=2
    assert complete(f,w,rid)['status']=='completed',stored(f,rid)


def recurring_query(f,queries):
    from tests.test_connected_action_plans import approve
    jobs,seen,inputs,body=setup_query(f,queries)
    doc=f.c.prepare_actions(f.x.a,body);w=f.c.workflow(f.x.a,doc['composition_id'])
    assert f.adapter.approve_pending(w,f.x.a)['ready'];approve(f,w)
    project=next(b for a in doc['action_plan']['actions'] if a['action_id']=='sheet' for b in a['bindings'] if b['target']==['project_id'])
    project_id=doc['binding_context']['configuration'][project['key']]
    operations={
        'workflow_data_query':dict(type='object',required=['query'],properties={'query':{'const':plan()}}),
        'extension_sheets_create_report':dict(type='object',required=['project_id'],properties={'project_id':{'const':project_id}}),
        'extension_mail_send':dict(type='object',required=['to'],properties={'to':{'const':'engineer@example.com'}})}
    policy=f.auto.authorize(f.x.a,dict(request_key='query_recurring_consent',connection_id=f.connection,operations=operations,purpose='Daily validated report.',content_scope='Exact reviewed query and verified report link.',schedule={'cron':'0 18 * * *','timezone':'Asia/Kolkata'},limits={'max_occurrences':3,'max_actions_per_occurrence':8},expires_at=f.now+7*86400))
    schedule=f.auto.schedule(f.x.a,dict(request_key='query_recurring_schedule',workflow={'workflow_id':w['workflow_id'],'workflow_version':1},authorization_id=policy['id'],cron='0 18 * * *',timezone='Asia/Kolkata',missed_run_policy='coalesce',overlap_policy='forbid',inputs={}))
    return jobs,schedule,policy,w


def test_recurring_query_fresh_plan_each_day_and_duplicate_trigger_no_delivery(automation,queries):
    from tests.test_durable_automation import drain
    f=automation;jobs,schedule,policy,w=recurring_query(f,queries)
    for day in range(2):
        f.now=f.auto.get(f.x.a,schedule['id'])['due']
        f.auto.tick(f.general.worker_authenticate);f.auto.tick(f.general.worker_authenticate)
        drain(f)
        assert jobs.tick()
        f.now+=2;f.auto.tick(f.general.worker_authenticate);drain(f)
        assert f.http.write_count==day+1 and len(f.http.sent)==day+1
    occurrences=f.auto.listing(f.x.a,'occurrence')['items']
    assert len(occurrences)==2
    assert len(jobs.list(f.x.a)['items'])==2
    assert len(queries.reader.calls)==2
    f.auto.tick(f.general.worker_authenticate);drain(f)
    assert len(f.http.sent)==2


def test_recurring_query_consent_requires_exact_data_scope(automation,queries):
    from workflow_api.service import ApiFailure
    f=automation;jobs,schedule,policy,w=recurring_query(f,queries)
    body=deepcopy(policy['request']);body['request_key']='unbounded_query_consent'
    body['operations']['workflow_data_query']={'type':'object'}
    with pytest.raises(ApiFailure) as error:f.auto.authorize(f.x.a,body)
    assert error.value.code=='AUTOMATION_QUERY_SCOPE_REQUIRED'


def test_population_request_corrects_case_reader_once_without_asking_for_id(automation,queries):
    f=automation;jobs,seen,inputs,body=setup_query(f,queries)
    proper=f.general.planner.provider.plan_actions
    calls=[]
    def mistaken_then_correct(goal,context):
        calls.append(deepcopy(context))
        return proposal(f.prepared) if len(calls)==1 else proper(goal,context)
    f.general.planner.provider=SimpleNamespace(plan_actions=mistaken_then_correct)
    doc=f.c.prepare_actions(f.x.a,body)
    assert len(calls)==2
    assert calls[1]['validation_feedback']['error_code']=='CASE_IDENTIFIER_REQUIRED'
    assert doc['planning']['model_calls']==2
    assert not doc['action_plan']['missing_inputs']
    assert all(not a['capability_id'].startswith('business.read.') for a in doc['action_plan']['actions'])
    assert doc['binding_context']['validated_context']['data_query_catalog']['context_hash']


def test_exact_prompt_internal_binding_correction_executes_read_only(automation,queries):
    from tests.test_intent_query_discovery import EXACT
    from tests.test_data_relationships import dataset
    from workflow_api.database_workflows import DatabaseWorkflows
    f=automation
    values=[i%151 for i in range(602)]+[None]
    with queries.store.transaction() as db:
        raw=db.execute("SELECT document FROM data_source_snapshots WHERE connection_id='pg' AND revision=1").fetchone()[0]
        snap=json.loads(raw)
        snap['datasets'].append(dataset('pg','complaints',[('operating_hours',['integer'])],'business'))
        snap['datasets'] += [dataset('pg','inventory'+str(i),[(f'attribute{j}',['integer']) for j in range(12)],'business') for i in range(95)]
        db.execute("UPDATE data_source_snapshots SET document=? WHERE connection_id='pg' AND revision=1",(json.dumps(snap),))
    queries.manager.relationships.request(f.x.a);assert queries.manager.relationships.tick()
    queries.reader.rows['pg_complaints']=[{'pg_complaints_operating_hours':v} for v in values]
    f.x.a['scopes']=sorted(set(f.x.a.get('scopes',[]))|{'workspace:read'})
    coordinator=DatabaseWorkflows(f.general,SimpleNamespace(manager=queries.manager,store=queries.store,policy=lambda:{'targets':[]}),queries,lambda w,o:f.x.a if (w,o)==('one','alice') else None)
    queries.retrieval=coordinator.retrieval
    typed=dict(base_dataset_id='pg_complaints',joins=[],fields=[],filters=[dict(field_id='pg_complaints_operating_hours',op='gte',value=0),dict(field_id='pg_complaints_operating_hours',op='lte',value=100)],group_by=[],metrics=[dict(label=op,op=op,expression='' if op=='count' else 'pg_complaints_operating_hours') for op in ('count','min','max','avg')],order_by=[],limit=1,explanation='Inclusive operating-hours range; exclude null measurements.',clarification='')
    from decimal import Decimal
    matched=[Decimal(v) for v in values if v is not None and 0<=v<=100]
    expected=[dict(count=len(matched),min=str(min(matched)),max=str(max(matched)),avg=str(sum(matched)/len(matched)))]
    jobs,seen,inputs,body=setup_query(f,queries,typed,expected)
    body['objective']=EXACT
    good=deepcopy(f.general.planner.provider.plan_actions(EXACT,{}))
    good['actions']=good['actions'][:3]
    good['completion_criteria']=['analysis']
    bad=dict(actions=[action('prepare_limited_report','content.prepare',[bind('context','data','validated_context',path=['validated_context'])])],completion_criteria=['prepare_limited_report'],missing_inputs=[])
    calls=[]
    def propose(goal,ctx):
        calls.append(deepcopy(ctx))
        return deepcopy(bad if len(calls)==1 else good)
    f.general.planner.provider.plan_actions=propose
    doc,w,rid=compile_run(f,body)
    assert len(calls)==2
    assert calls[1]['validation_feedback']['binding_issue']==dict(section='validated_context',key='validated_context',path=['validated_context'],target=['data'],rule='missing_binding_input',action_id='prepare_limited_report',capability_id='content.prepare')
    assert all(a['required_approvals']==[] for a in doc['action_plan']['actions'])
    f.runner.advance(rid,f.x.a);assert jobs.tick();f.now+=2
    assert complete(f,w,rid)['status']=='completed',stored(f,rid)
    assert not f.http.sent and f.http.write_count==0
    output=stored(f,rid)['action_instances']['read']['output']
    assert output['coverage']['complete_scan'] and output['result']['rows']==expected
    assert output['result']['matched_rows']==len([v for v in values if v is not None and 0<=v<=100])
    assert queries.reader.calls==['pg_complaints']
    catalog=doc['binding_context']['validated_context']['data_query_catalog']
    assert [d['name'] for d in catalog['datasets']]==['complaints']
    assert len(json.dumps(catalog).encode())<120000


@pytest.mark.parametrize('kind',['context','literal'])
def test_live_recipient_scalar_binding_generates_once_without_external_actions(automation,queries,kind):
    f=automation;_,seen,_,body=setup_query(f,queries)
    body['objective']='Find complaints with operating hours from 0 to 100, prepare a report and email me.'
    valid=deepcopy(f.general.planner.provider.plan_actions(body['objective'],{}))
    send=next(a for a in valid['actions'] if a['action_id']=='send')
    send['bindings'][0]=bind(kind,'to','recipient',path=['recipient'])
    calls=[]
    def generated(goal,ctx):calls.append(deepcopy(ctx));return deepcopy(valid)
    f.general.planner.provider.plan_actions=generated
    doc=f.c.prepare_actions(f.x.a,body)
    binding=next(b for a in doc['action_plan']['actions'] if a['action_id']=='send' for b in a['bindings'] if b['target']==['to'])
    assert binding==bind('literal','to','recipient')
    assert doc['binding_context']['user_values']['recipient']=='owner@example.com'
    assert doc['google_connection_id']==f.connection and len(calls)==1
    assert next(a for a in doc['action_plan']['actions'] if a['action_id']=='send')['required_approvals']==['exact_payload']
    assert not f.http.sent and f.http.write_count==0


def test_live_whole_query_envelope_is_normalized_before_runtime(automation,queries):
    """Exact hosted shape: planner output [] was bound to tool input [query]."""
    f=automation;jobs,seen,inputs,body=setup_query(f,queries)
    provider=f.general.planner.provider.plan_actions
    def whole_envelope(goal,context):
        result=deepcopy(provider(goal,context))
        read=next(a for a in result['actions'] if a['action_id']=='read')
        read['bindings'][0]['path']=[]
        return result
    f.general.planner.provider=SimpleNamespace(plan_actions=whole_envelope)
    doc,w,rid=compile_run(f,body)
    read=next(a for a in doc['action_plan']['actions'] if a['action_id']=='read')
    assert read['bindings'][0]['path']==['query']
    assert read['depends_on']==['query_plan']
    assert len(seen)==1 and doc['google_connection_id']==f.connection
    assert not f.http.sent and f.http.write_count==0
    f.runner.advance(rid,f.x.a)
    assert stored(f,rid)['action_instances']['read']['resolved_inputs']=={'query':plan()}
    assert stored(f,rid)['action_instances']['read']['state']=='waiting_for_query'
    assert jobs.tick()
    # Only controlled HTTP fixtures may deliver; real providers are never used.
    f.now+=2
    assert complete(f,w,rid)['status']=='completed'
    assert len(queries.reader.calls)==1 and len(f.http.sent)==1


def test_type_mismatch_feedback_names_exact_schemas_without_coercing(automation):
    f=automation;corrected=proposal(f.prepared);draft=deepcopy(corrected)
    draft['actions'][-1]['bindings'][1]['path']=[]
    contexts=[]
    def selector(goal,context):
        contexts.append(deepcopy(context))
        return deepcopy(draft if len(contexts)==1 else corrected)
    f.general.planner.provider=SimpleNamespace(plan_actions=selector)
    request=deepcopy(f.request);request.pop('action_plan');request['automatic_inputs']=True;request['google_connection_id']=f.connection
    doc=f.c.prepare_actions(f.x.a,request)
    assert len(contexts)==2
    issue=contexts[1]['validation_feedback']['binding_issue']
    assert issue['rule']=='incompatible_binding_types'
    assert issue['action_id']=='send' and issue['source_action_id']=='email'
    assert issue['source_path']==[] and issue['path']==['subject']
    assert issue['source_schema']['type']=='object' and issue['target_schema']['type']=='string'
    assert doc['action_plan']['actions'][-1]['bindings'][1]['path']==['subject']
    assert not f.http.sent and f.http.write_count==0
