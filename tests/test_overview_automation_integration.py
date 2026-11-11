"""Actual composition/Registry/runtime/scheduler with controlled source and HTTP."""
from copy import deepcopy
from types import SimpleNamespace
import json
import pytest
from tests.test_workflow_query_integration import (automation,google_setup,connected,composition,investigation,retrieval,knowledge,reference,generation,foundation,auth,release,queries,setup_query)
from tests.test_connected_action_plans import proposal,action,bind,approve,stored
from tests.test_durable_automation import drain
from workflow_api.overview_automation import OverviewAutomation
from workflow_api.temporal_queries import ANNOTATION,window
from workflow_api.service import ApiFailure
from tests.test_overview_automation import intent


def prepared(f, queries, kind='recurring', route_override=None):
    jobs,seen,inputs,body=setup_query(f,queries)
    base=proposal(f.prepared)
    base['actions'][0]=action('read','tool.workflow_data_query',[bind('context','query','reviewed_query')])
    f.general.planner.provider=SimpleNamespace(plan_actions=lambda goal,ctx:seen.append(deepcopy(ctx)) or deepcopy(base))
    route=deepcopy(route_override) if route_override is not None else intent(kind);route['side_effects']=['sheet_create','email_send'];route['temporal']['period']='none'
    router=OverviewAutomation(f.general,dict(BUILDER_OVERVIEW_ROUTING_ENABLED='1',BUILDER_OVERVIEW_ROUTING_WORKSPACES='one'),interpreter=lambda *_:deepcopy(route))
    body.pop('automatic_inputs',None);body['operation']='prepare';body['objective']='Daily source report at 6 PM India time. Create a spreadsheet and email engineer@example.com.'
    result=router.handle(f.x.a,body)
    return router,result,body,jobs,seen,inputs


def test_overview_prepares_scoped_query_and_consent_without_provider_effects(automation,queries):
    f=automation;router,result,body,jobs,seen,inputs=prepared(f,queries)
    assert result['state']=='prepared' and result['schedule']['cron']=='0 18 * * *'
    assert 'data.plan_query' not in seen[0]['capabilities']
    assert seen[0]['binding_context']['validated_context']['reviewed_query']==result['query']
    assert result['operations']['extension_mail_send']['properties']['to']=={'const':'engineer@example.com'}
    assert not f.http.sent and f.http.write_count==0 and not jobs.list(f.x.a)['items']
    assert router.handle(f.x.a,body)==result
    assert len(seen)==1
    changed=deepcopy(body);changed['objective']='Different scope'
    with pytest.raises(ApiFailure) as e:router.handle(f.x.a,changed)
    assert e.value.code=='OVERVIEW_CONFLICT'
    with pytest.raises(Exception):router.handle(auth(owner='other'),{'operation':'get','request_key':body['request_key']})


def test_overview_review_activation_two_occurrences_and_duplicate_retry(automation,queries):
    f=automation;router,result,body,jobs,seen,inputs=prepared(f,queries)
    with pytest.raises(Exception):router.handle(f.x.a,dict(operation='activate',request_key=body['request_key']))
    w=f.c.workflow(f.x.a,result['composition_id'])
    review=f.adapter.approve_pending(w,f.x.a);assert review['ready'],review
    w=approve(f,w)
    active=router.handle(f.x.a,dict(operation='activate',request_key=body['request_key']))
    assert router.handle(f.x.a,dict(operation='activate',request_key=body['request_key']))==active
    for day in range(2):
        f.now=f.auto.get(f.x.a,active['schedule_id'])['due']
        f.auto.tick(f.general.worker_authenticate);drain(f)
        assert jobs.tick()
        f.now+=2;f.auto.tick(f.general.worker_authenticate);drain(f)
        assert len(f.http.sent)==day+1
    assert len(jobs.list(f.x.a)['items'])==2 and len(queries.reader.calls)==2
    current=router.handle(f.x.a,dict(operation='get',request_key=body['request_key']))
    assert current['schedule_record']['state']=='active'
    f.auto.control(f.x.a,active['schedule_id'],dict(request_key='overview_pause_schedule',action='pause'))
    assert router.handle(f.x.a,dict(operation='get',request_key=body['request_key']))['schedule_record']['state']=='paused'


def test_relative_query_changes_only_approved_dates_at_delayed_occurrence(automation,queries):
    from workflow_api.data_query_jobs import DataQueryJobs
    from workflow_api.workflow_queries import install
    f=automation
    with queries.store.transaction() as db:
        row=db.execute("SELECT document FROM data_source_snapshots WHERE connection_id='pg'").fetchone()
        snap=json.loads(row[0]);dataset=snap['datasets'][0]
        dataset['fields'].append(dict(field_id='pg_lines_created',name='created',types=['timestamp with time zone'],nullable=True))
        db.execute("UPDATE data_source_snapshots SET document=? WHERE connection_id='pg'",(json.dumps(snap),))
    queries.manager.relationships.request(f.x.a);queries.manager.relationships.tick()
    # Reuse full runtime transport but generate a controlled date-scoped plan.
    jobs,_,inputs,body=setup_query(f,queries)
    for row in queries.reader.rows['pg_lines']:row['pg_lines_created']='2026-11-10T08:00:00+00:00'
    f.now=1794297600.0  # 10 November 2026 UTC
    route=intent();route['side_effects']=['sheet_create','email_send'];route['temporal']['field_id']='pg_lines_created'
    old_generate=queries.planner.generate
    def generate(question,catalog):
        p=old_generate(question,catalog)
        low,high=window('today','Asia/Kolkata',f.now)
        p['filters']=[dict(field_id='pg_lines_created',op='gte',value=low),dict(field_id='pg_lines_created',op='lt',value=high)]
        return p
    queries.planner.generate=generate
    base=proposal(f.prepared);base['actions'][0]=action('read','tool.workflow_data_query',[bind('context','query','reviewed_query')])
    f.general.planner.provider=SimpleNamespace(plan_actions=lambda *_:deepcopy(base))
    router=OverviewAutomation(f.general,dict(BUILDER_OVERVIEW_ROUTING_ENABLED='1',BUILDER_OVERVIEW_ROUTING_WORKSPACES='one'),interpreter=lambda *_:deepcopy(route))
    body.pop('automatic_inputs',None)
    result=router.handle(f.x.a,body)
    assert ANNOTATION in result['operations']['workflow_data_query']
    w=f.c.workflow(f.x.a,result['composition_id']);assert f.adapter.approve_pending(w,f.x.a)['ready'];w=approve(f,w)
    active=router.handle(f.x.a,dict(operation='activate',request_key=body['request_key']))
    scheduled=f.auto.get(f.x.a,active['schedule_id'])['due']
    f.now=scheduled+12*3600  # next calendar day, before the next scheduled run
    f.auto.tick(f.general.worker_authenticate);drain(f)
    assert jobs.tick()
    f.now+=2;f.auto.tick(f.general.worker_authenticate);drain(f)
    occurrences=f.auto.listing(f.x.a,'occurrence')['items'];assert len(occurrences)==1
    run=stored(f,occurrences[0]['run_id'])
    assert run['automation_reference']['scheduled_due']==scheduled
    actual=run['action_instances']['read']['resolved_inputs']['query']
    assert [v['value'] for v in actual['filters']]==list(window('today','Asia/Kolkata',scheduled))
    assert run['status']=='completed',run.get('error_code')
    next_due=f.auto.get(f.x.a,active['schedule_id'])['due']
    low,high=window('today','Asia/Kolkata',next_due)
    for row in queries.reader.rows['pg_lines']:row['pg_lines_created']=low
    f.now=next_due;f.auto.tick(f.general.worker_authenticate);drain(f);assert jobs.tick()
    f.now+=2;f.auto.tick(f.general.worker_authenticate);drain(f)
    occurrences=f.auto.listing(f.x.a,'occurrence')['items'];assert len(occurrences)==2
    second=next(stored(f,o['run_id']) for o in occurrences if o['due']==next_due)
    assert second['status']=='completed',second.get('error_code')
    assert [v['value'] for v in second['action_instances']['read']['resolved_inputs']['query']['filters']]==[low,high]
    assert len(f.http.sent)==2


def test_future_customer_default_package_does_not_assume_a_customer_name(automation):
    from tests.test_simpson_lifecycle import configure
    from tests.test_generic_lifecycle_phase6 import retail
    f=automation;cases,_,_=configure(f,True);retail(f,cases)
    f.general.default_client_package=dict(package_id='retail_complaint_fixture',revision=1)
    req=dict(objective='Read mapped retail complaint evidence.',request_key='future_customer_overview',user_values={'capability':'retail.complaint.read'},
        action_plan=dict(actions=[action('read','retail.complaint.read',[bind('context','package_id','package_id'),bind('context','revision','package_revision'),bind('literal','capability_id','capability')])],completion_criteria=['read'],missing_inputs=[]))
    doc=f.c.prepare_actions(f.x.a,req)
    assert doc['action_plan']['scope']['client_id']==doc['client_package_context']['package']['client_id']
    changed=deepcopy(req);changed['request_key']='foreign_customer_overview';changed['client_id']='another_customer'
    with pytest.raises(Exception) as caught:f.c.prepare_actions(f.x.a,changed)
    assert caught.value.code=='ACTION_SCOPE_DENIED'


def test_new_automation_metadata_is_part_of_immutable_workflow_control(automation,queries):
    from workflow_api.business_composition import verify_composition
    f=automation;router,result,*_=prepared(f,queries)
    w=f.c.workflow(f.x.a,result['composition_id'])
    w['metadata']['overview_intent']['query']['filters'].append(dict(field_id='invented',op='gte',value=0))
    with f.general.store.transaction(write=False) as db:
        with pytest.raises(Exception) as caught:verify_composition(db,f.x.a,w)
    assert caught.value.code=='CAPABILITY_CHANGED'


def test_recurring_identified_case_reuses_existing_case_reader_without_population_query(automation):
    f=automation;route=intent();route['entity_scope']='identified_case';route['temporal']['period']='none';route['side_effects']=['sheet_create','email_send']
    f.general.planner.provider=SimpleNamespace(plan_actions=lambda *_:proposal(f.prepared))
    router=OverviewAutomation(f.general,dict(BUILDER_OVERVIEW_ROUTING_ENABLED='1',BUILDER_OVERVIEW_ROUTING_WORKSPACES='one'),interpreter=lambda *_:deepcopy(route))
    result=router.handle(f.x.a,dict(objective='Every day at 6 PM India time, review complaint C123, create a spreadsheet and email engineer@example.com.',request_key='recurring_identified_case',business_request={},google_connection_id=f.connection))
    assert result['state']=='prepared' and result['query'] is None
    assert result['operations']['business_retrieve_evidence']['const']['task']=='complaints'
    assert 'workflow_data_query' not in result['operations']
    assert not f.http.sent and f.http.write_count==0


def test_restart_after_composition_commit_resumes_persisted_interpretation(automation,queries):
    f=automation;router,result,body,jobs,seen,inputs=prepared(f,queries)
    # Model a crash after composition commit but before the final response-ledger
    # commit. Only this test-owned final response is removed; the durable stages
    # and immutable composition must be reused by the restarted adapter.
    with f.general.store.transaction() as db:
        db.execute('DELETE FROM mutations WHERE workspace=? AND subject=? AND key=?',router._key(f.x.a,body['request_key']))
    def forbidden(*_):raise AssertionError('A committed planning stage must not be repeated')
    restarted=OverviewAutomation(f.general,router.env,interpreter=forbidden)
    f.general.planner.provider=SimpleNamespace(plan_actions=forbidden)
    f.now+=3600
    assert restarted.handle(f.x.a,body)==result
    assert len(seen)==1 and not f.http.sent and not jobs.list(f.x.a)['items']


def test_read_only_intent_rejects_a_proposal_that_adds_delivery(automation,queries):
    f=automation;setup_query(f,queries)
    f.general.planner.provider=SimpleNamespace(plan_actions=lambda *_:proposal(f.prepared))
    route=intent('population');route['temporal']['period']='none'
    router=OverviewAutomation(f.general,dict(BUILDER_OVERVIEW_ROUTING_ENABLED='1',BUILDER_OVERVIEW_ROUTING_WORKSPACES='one'),interpreter=lambda *_:route)
    with pytest.raises(Exception):router.handle(f.x.a,dict(objective='Count complaints. No external writes.',request_key='readonly_no_delivery',business_request={}))
    assert not f.http.sent and f.http.write_count==0


def test_multiple_identified_case_reads_keep_finite_whole_payload_consent(automation):
    from jsonschema import Draft202012Validator
    f=automation;route=intent();route.update(entity_scope='identified_case',side_effects=['sheet_create','email_send']);route['temporal']['period']='none'
    base=proposal(f.prepared)
    base['actions'].insert(1,action('warranty','business.read.warranty',[bind('context','preparation_id','preparation_id'),bind('literal','task','task')]))
    f.general.planner.provider=SimpleNamespace(plan_actions=lambda *_:deepcopy(base))
    router=OverviewAutomation(f.general,dict(BUILDER_OVERVIEW_ROUTING_ENABLED='1',BUILDER_OVERVIEW_ROUTING_WORKSPACES='one'),interpreter=lambda *_:route)
    result=router.handle(f.x.a,dict(objective='Every day at 6 PM India time review complaint C123 and its warranty evidence, create a spreadsheet and email engineer@example.com.',request_key='recurring_two_case_reads',business_request={},google_connection_id=f.connection))
    schema=result['operations']['business_retrieve_evidence'];assert len(schema['anyOf'])==2
    assert {v['const']['task'] for v in schema['anyOf']}=={'complaints','warranty'}
    for v in schema['anyOf']:Draft202012Validator(schema).validate(v['const'])
    forged=deepcopy(schema['anyOf'][0]['const']);forged['task']='inspection'
    assert list(Draft202012Validator(schema).iter_errors(forged))


def test_one_time_overview_executes_existing_crewai_query_report_and_approved_delivery(automation,queries):
    from tests.test_connected_action_plans import complete
    f=automation;jobs,seen,inputs,body=setup_query(f,queries)
    route=intent('one_time');route['temporal']['period']='none';route['side_effects']=['sheet_create','email_send']
    router=OverviewAutomation(f.general,dict(BUILDER_OVERVIEW_ROUTING_ENABLED='1',BUILDER_OVERVIEW_ROUTING_WORKSPACES='one'),interpreter=lambda *_:deepcopy(route))
    body.pop('automatic_inputs',None)
    result=router.handle(f.x.a,body);assert result['schedule'] is None
    w=f.c.workflow(f.x.a,result['composition_id']);assert f.adapter.approve_pending(w,f.x.a)['ready'];w=approve(f,w)
    run=f.runtime.create_run(dict(request_id='overview_once_run',operation='execute_workflow',idempotency_key='overview_once_run',payload=dict(workflow_id=w['workflow_id'],workflow_version=1,inputs={})),f.x.a)
    f.runner.advance(run['run_id'],f.x.a);assert jobs.tick();f.now+=2
    assert complete(f,w,run['run_id'])['status']=='completed'
    assert len(f.http.sent)==1 and f.http.write_count==1
    assert not f.auto.listing(f.x.a,'schedule')['items']


def test_existing_queue_reattaches_prepared_overview_without_model_or_provider_replay(automation,queries):
    from workflow_api.planning_jobs import PlanningJobs
    f=automation;router,result,body,jobs,seen,inputs=prepared(f,queries)
    f.general.overview_automation=router
    queue=PlanningJobs(f.general,f.general.worker_authenticate)
    request=dict(request_id='overview_existing_queue',operation='plan_workflow',idempotency_key=body['request_key'],payload=dict(objective=body['objective'],context={'praxi_overview_request_v1':body}))
    job=queue.submit(request,f.x.a);assert job['state']=='queued'
    assert queue.tick()
    saved=queue.get(job['job_id'],f.x.a);assert saved['state']=='succeeded'
    assert saved['result']['data']['composition_id']==result['composition_id']
    assert queue.submit(request,f.x.a)['job_id']==job['job_id']
    assert len(seen)==1 and not jobs.list(f.x.a)['items'] and not f.http.sent



def test_one_time_overview_runs_existing_query_graph_only_after_exact_approvals(automation,queries):
    from tests.test_connected_action_plans import complete,decide
    f=automation;jobs,seen,inputs,body=setup_query(f,queries)
    route=intent('one_time');route.update(side_effects=['sheet_create','email_send']);route['temporal']['period']='none'
    router=OverviewAutomation(f.general,dict(BUILDER_OVERVIEW_ROUTING_ENABLED='1',BUILDER_OVERVIEW_ROUTING_WORKSPACES='one'),interpreter=lambda *_:deepcopy(route))
    body.pop('automatic_inputs');body['objective']='Analyze mapped records once, create a report and email engineer@example.com.'
    result=router.handle(f.x.a,body)
    assert result['schedule'] is None and result['operations']=={}
    assert not f.http.sent and f.http.write_count==0
    workflow=f.c.workflow(f.x.a,result['composition_id'])
    assert f.adapter.approve_pending(workflow,f.x.a)['ready'];workflow=approve(f,workflow)
    run=f.runtime.create_run(dict(request_id='one_time_overview',operation='execute_workflow',idempotency_key='one_time_overview',payload=dict(workflow_id=workflow['workflow_id'],workflow_version=1,inputs={})),f.x.a)
    rid=run['run_id'];assert f.runner.advance(rid,f.x.a)['status']=='running';assert jobs.tick()
    f.now+=2
    waiting=f.runner.advance(rid,f.x.a)
    assert waiting['status']=='paused_for_approval'
    assert not f.http.sent and f.http.write_count==0
    decide(f,workflow,waiting)
    assert complete(f,workflow,rid)['status']=='completed'
    final=stored(f,rid)
    assert final['action_instances']['send']['verified_receipt']
    assert final['action_instances']['sheet']['verified_receipt']
    assert len(f.http.sent)==1 and f.http.write_count==1
    assert not f.auto.listing(f.x.a,'schedule')['items']
    assert f.runner.advance(rid,f.x.a)['status']=='completed' and len(f.http.sent)==1


def test_expired_one_time_proposal_cannot_roll_forward_to_next_year(automation,queries):
    from datetime import datetime,timedelta
    from zoneinfo import ZoneInfo
    f=automation;route=intent('one_time')
    day=(datetime.fromtimestamp(f.now,ZoneInfo('Asia/Kolkata'))+timedelta(days=1)).date().isoformat()
    route['recurrence'].update(kind='once',date=day,hour=10)
    router,result,body,*_=prepared(f,queries,route_override=route)
    workflow=f.c.workflow(f.x.a,result['composition_id'])
    assert f.adapter.approve_pending(workflow,f.x.a)['ready'];approve(f,workflow)
    f.now=result['schedule']['next_due']+1
    with pytest.raises(ApiFailure) as caught:router.handle(f.x.a,dict(operation='activate',request_key=body['request_key']))
    assert caught.value.code=='OVERVIEW_CLARIFICATION'
    assert not f.auto.listing(f.x.a,'schedule')['items']
    assert not f.auto.listing(f.x.a,'authorization')['items']
    assert not f.http.sent and f.http.write_count==0
