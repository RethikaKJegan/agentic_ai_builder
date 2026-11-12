"""Calendar-only and recurring Calendar actions with real runtime/fake providers."""
from copy import deepcopy
from datetime import datetime
from types import SimpleNamespace
import pytest
from tests.test_goal_planning import automation,google_setup,connected,composition,investigation,retrieval,knowledge,reference,generation,foundation,auth,release
from tests.test_durable_automation import add_scopes
from tests.test_connected_action_plans import action,bind,approve,complete,stored
from tests.test_overview_automation import intent
from workflow_api.goal_inputs import calendar_context
from workflow_api.calendar_occurrences import prepare_pin,values
from workflow_api.overview_automation import OverviewAutomation
from workflow_api.action_plans import prepare
from runtime.action_plans import params

NOW=datetime.fromisoformat('2026-11-12T08:00:00+00:00').timestamp()
GOAL='Create one event on my primary Google Calendar titled Calendar connection test tomorrow from 4:00 PM to 4:30 PM India time. Description: Testing calendar event creation. No attendees.'


@pytest.mark.parametrize('goal', [GOAL,GOAL.replace('from 4:00 PM to 4:30 PM','at 4 PM for thirty minutes').replace('thirty minutes','thirty-minute review'),GOAL.replace('India time','Asia/Kolkata')])
def test_explicit_calendar_intervals_and_word_duration(goal):
    context={'validated_context':{}};calendar_context(context,goal,True,now=NOW)
    assert context['validated_context']['primary_calendar_id']=='primary'
    assert context['validated_context']['calendar_event_start']['dateTime']=='2026-11-13T16:00:00+05:30'
    assert context['validated_context']['calendar_event_end']['dateTime']=='2026-11-13T16:30:00+05:30'


def source_free_route():
    result=intent('one_time');result.update(entity_scope='none',business_goal='',side_effects=['calendar_write'])
    result['temporal'].update(period='none',field_id=None)
    return result


def propose(goal,ctx):
    assert 'data.plan_query' not in ctx['capabilities'] and 'subway.plan_query' not in ctx['capabilities']
    content=action('content','content.prepare',[bind('context','data','connected_request')]);content['budget'].update(max_llm_calls=2,max_tool_calls=0)
    event=action('event','tool.extension_calendar_create',[bind('generated','event.summary',action='content',path=['title']),bind('generated','event.description',action='content',path=['summary'])],['content'])
    return dict(actions=[content,event],completion_criteria=['event'],missing_inputs=[])


def router(f,route):
    return OverviewAutomation(f.general,dict(BUILDER_OVERVIEW_ROUTING_ENABLED='1',BUILDER_OVERVIEW_ROUTING_WORKSPACES=f.x.a['subject']['workspace_id'],BUILDER_WORKSPACE_TIMEZONE='Asia/Kolkata'),interpreter=lambda *_:deepcopy(route))


def test_calendar_only_prepares_and_executes_with_exact_approval_and_no_business_source(automation):
    f=automation;f.now=NOW;add_scopes(f.manager,f.connection,['calendar.events']);f.general.planner.provider=SimpleNamespace(plan_actions=propose)
    result=router(f,source_free_route()).handle(f.x.a,dict(objective=GOAL,request_key='calendar_only',google_connection_id=f.connection))
    assert result['state']=='prepared' and result['schedule'] is None
    doc=f.c.get(f.x.a,result['composition_id']);assert set(doc['contracts'])=={'content.prepare','tool.extension_calendar_create'}
    w=f.c.workflow(f.x.a,doc['composition_id']);assert f.adapter.approve_pending(w,f.x.a)['ready'];w=approve(f,w)
    run=f.runtime.create_run(dict(request_id='calendar_test',idempotency_key='calendar_test',payload=dict(workflow_id=w['workflow_id'],workflow_version=1,inputs={})),f.x.a)
    out=complete(f,w,run['run_id']);assert out['status']=='completed',stored(f,run['run_id'])
    saved=stored(f,run['run_id']);assert saved['action_instances']['event']['verified_receipt']
    assert len(f.http.events)==1
    f.runner.advance(run['run_id'],f.x.a);assert len(f.http.events)==1


def test_missing_calendar_action_gets_bounded_correction_never_successful_report(automation):
    f=automation;f.now=NOW;add_scopes(f.manager,f.connection,['calendar.events']);calls=[]
    def omitted(goal,ctx):
        calls.append(ctx)
        p=propose(goal,ctx);p['actions']=p['actions'][:1];p['completion_criteria']=['content'];return p
    f.general.planner.provider=SimpleNamespace(plan_actions=omitted)
    with pytest.raises(Exception) as caught:router(f,source_free_route()).handle(f.x.a,dict(objective=GOAL,request_key='omitted_calendar',google_connection_id=f.connection))
    assert caught.value.code=='ACTION_REQUIRED_OPERATION_MISSING' and len(calls)==2
    assert not f.http.events


def test_same_day_recurrence_binds_fresh_event_dates_to_logical_occurrence():
    goal='Every day at 3 PM India time, summarize purchase orders. Create a thirty-minute review event on my primary Google Calendar for 4 PM India time that same day.'
    pin=prepare_pin(goal,True,NOW);assert pin==dict(timezone='Asia/Kolkata',hour=16,minute=0,duration_minutes=30)
    first=values(pin,NOW);next_day=values(pin,NOW+86400)
    assert first['calendar_event_start']['dateTime']=='2026-11-12T16:00:00+05:30'
    assert next_day['calendar_event_end']['dateTime']=='2026-11-13T16:30:00+05:30'
    a=dict(action_id='event',capability_id='tool.extension_calendar_create',depends_on=[],bindings=[bind('context','event.start','calendar_event_start'),bind('context','event.end','calendar_event_end')])
    workflow=dict(agents=[dict(agent_id='calendar')],metadata=dict(connected_contracts={'tool.extension_calendar_create':dict(input_schema=dict(type='object'))},connected_action_plan=dict(actions=[a],constraints={}),action_binding_context=dict(validated_context=first),overview_intent=dict(calendar_occurrence=pin)))
    actual=params(workflow,dict(node_id='event',kind='tool',agent_id='calendar'),dict(automation_reference=dict(scheduled_due=NOW+86400)))
    assert actual==dict(event=dict(start=next_day['calendar_event_start'],end=next_day['calendar_event_end']))
    assert workflow['metadata']['action_binding_context']['validated_context']==first


def test_calendar_only_recurring_dispatch_creates_event_each_day_with_fresh_dates(automation):
    f=automation;f.now=NOW;add_scopes(f.manager,f.connection,['calendar.events']);f.general.planner.provider=SimpleNamespace(plan_actions=propose)
    goal='Every day at 3 PM India time, create a thirty-minute review event on my primary Google Calendar for 4 PM India time that same day. Description: Calendar connection test. No attendees.'
    route=source_free_route();route['intent_type']='recurring';route['recurrence'].update(kind='daily',hour=15,minute=0,timezone='Asia/Kolkata')
    r=router(f,route);result=r.handle(f.x.a,dict(objective=goal,request_key='recurring_calendar',google_connection_id=f.connection))
    assert result['operations']['extension_calendar_create']['x-praxi-calendar-occurrence-v1']['hour']==16
    doc=f.c.get(f.x.a,result['composition_id']);w=f.c.workflow(f.x.a,doc['composition_id']);assert f.adapter.approve_pending(w,f.x.a)['ready'];w=approve(f,w)
    active=r.handle(f.x.a,dict(operation='activate',request_key='recurring_calendar'))
    for day in range(2):
        schedule=f.auto.get(f.x.a,active['schedule_id']);f.now=schedule['due']
        lookup=lambda workspace,owner:deepcopy(f.x.a) if f.x.a['subject']==dict(workspace_id=workspace,subject_id=owner) else None
        for _ in range(8):
            f.auto.tick(lookup)
            for job in f.general.lifecycle.lease(f.x.a['subject']['workspace_id']):f.general.lifecycle.execute_job(job['job_id'],f.runner)
            records=f.auto.history(f.x.a,active['schedule_id'])
            if len(records)==day+1 and all(o['state'] in ('completed','failed','dead_letter') for o in records):break
        assert len(records)==day+1 and all(o['state']=='completed' for o in records),records
        assert len(f.http.events)==day+1
        recent=max(records,key=lambda x:x['due']);run=stored(f,recent['run_id'])
        event=run['action_instances']['event']['resolved_inputs']['event']
        expected=values(doc['overview_intent']['calendar_occurrence'],recent['due'])
        assert event['start']==expected['calendar_event_start'] and event['end']==expected['calendar_event_end']
        f.auto.tick(lookup);assert len(f.http.events)==day+1


# Real Subway source catalogue; no business dataset should be required for a
# connector-only request even when the tenant has a fully configured ontology.
from tests.test_subway_intelligence import subway,engine,installed,route as subway_route


def test_subway_calendar_only_does_not_require_dataset_selection(subway):
    f=subway
    selected=dict(dataset_ids=[],field_ids=[],relationship_ids=[],measure_basis='',clarification='')
    routed=subway_route(selected,intent_type='one_time',entity_scope='none',business_goal='',side_effects=['calendar_write'])
    r=OverviewAutomation(f.service,f.env,interpreter=lambda *_:deepcopy(routed))
    prepared=r.prepare_intent(f.auth,dict(objective=GOAL,request_key='calendar_subway_routing'))
    assert prepared['intent'] and prepared['intent']['source_free'] and prepared['result']['state']=='prepared'
    assert not prepared['result'].get('questions')


def test_calendar_creation_is_not_an_incoming_business_event_subscription():
    route=source_free_route();route['intent_type']='event'
    context={'resolved_inputs':{'validated_context':{}}}
    calendar_context(context['resolved_inputs'],GOAL,True,now=NOW)
    r=OverviewAutomation(None,interpreter=lambda *_:deepcopy(route))
    assert r.interpret(GOAL,context)['intent_type']=='one_time'


def test_calendar_question_free_mode_preserves_missing_inputs_without_successful_fallback(automation,monkeypatch):
    from runtime.service import RuntimeFailure
    f=automation;f.now=NOW
    r=router(f,source_free_route());r.env['BUILDER_QUESTION_FREE_WORKFLOWS']='1'
    def missing(*args,**kwargs):raise RuntimeFailure('ACTION_INPUT_REQUIRED','Select the calendar event interval.',422)
    monkeypatch.setattr('workflow_api.action_plans.prepare',missing)
    result=r.handle(f.x.a,dict(objective=GOAL,request_key='calendar_missing'))
    assert result['state']=='clarification' and not result.get('composition_id') and not result.get('report_only')
