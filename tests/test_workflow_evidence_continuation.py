"""Calendar interpretation and useful, truthful recovery; controlled transports."""
from copy import deepcopy
from datetime import datetime
from types import SimpleNamespace
import json
import pytest
from tests.test_question_free_workflows import (automation,google_setup,connected,composition,investigation,retrieval,knowledge,reference,generation,foundation,auth,release,queries,setup_query,router)
from tests.test_connected_action_plans import action,bind,approve,stored
from tests.test_overview_automation import intent
from workflow_api.goal_inputs import calendar_context
from workflow_api.overview_automation import OverviewAutomation
from runtime.crew import CrewExecutor
from runtime.model import BoundedLLM

GOAL='Investigate similar overheating complaints and add a 30-minute review to my calendar today at 12:45 PM India time, with the findings in the description.'
NOW=datetime.fromisoformat('2026-11-11T07:10:00+00:00').timestamp()


@pytest.mark.parametrize('day,date',[('today','2026-11-11'),('tomorrow','2026-11-12')])
def test_relative_calendar_dates_use_selected_account_and_planning_clock(day,date):
    context={'validated_context':{}}
    calendar_context(context,GOAL.replace('today',day),True,now=NOW)
    assert context['validated_context']==dict(primary_calendar_id='primary',
        calendar_event_start={'dateTime':date+'T12:45:00+05:30','timeZone':'Asia/Kolkata'},
        calendar_event_end={'dateTime':date+'T13:15:00+05:30','timeZone':'Asia/Kolkata'})


def test_relative_date_uses_local_day_across_utc_midnight():
    context={'validated_context':{}}
    calendar_context(context,GOAL,True,now=datetime.fromisoformat('2026-11-10T20:00:00+00:00').timestamp())
    assert context['validated_context']['calendar_event_start']['dateTime'].startswith('2026-11-11')


def test_event_time_is_not_a_workflow_timer_but_explicit_execution_schedule_is_preserved():
    context={'resolved_inputs':{'validated_context':{}}}
    calendar_context(context['resolved_inputs'],GOAL,True,now=NOW)
    route=intent('one_time');route['side_effects']=['calendar_write'];route['temporal']['period']='none'
    route['recurrence'].update(kind='once',date='2026-11-11',hour=12,minute=45)
    r=OverviewAutomation(None,interpreter=lambda *_:deepcopy(route))
    assert r.interpret(GOAL,context)['recurrence']['kind']=='none'
    explicit='Today at 12:45 PM India time, run the investigation and '+GOAL.split(' and ')[1]
    assert r.interpret(explicit,context)['recurrence']==route['recurrence']
    route['recurrence'].update(kind='weekly',date=None,weekdays=[1])
    route['intent_type']='recurring'
    assert r.interpret(GOAL,context)['recurrence']['kind']=='weekly'


def test_exact_reported_prompt_prepares_query_and_calendar_with_review(automation,queries):
    from tests.test_durable_automation import add_scopes
    f=automation;f.now=NOW;add_scopes(f.manager,f.connection,['calendar.events'])
    jobs,_,_,body=setup_query(f,queries)
    route=intent('one_time');route.update(side_effects=['calendar_write']);route['temporal']['period']='none'
    route['recurrence'].update(kind='once',date='2026-11-11',hour=12,minute=45)
    def propose(goal,ctx):
        assert ctx['overview_intent']['schedule'] is None
        assert ctx['binding_context']['validated_context']['calendar_event_start']['dateTime']=='2026-11-11T12:45:00+05:30'
        query=action('query','data.plan_query',[]);query['budget'].update(max_llm_calls=1,max_tool_calls=0)
        read=action('read','tool.workflow_data_query',[bind('output','query',action='query',path=['query'])],['query'])
        summary=action('summary','content.prepare',[bind('output','data',action='read')],['read'],['read'])
        event=action('review','tool.extension_calendar_create',[bind('generated','event.summary',action='summary',path=['title']),bind('generated','event.description',action='summary',path=['summary'])],['summary'])
        return dict(actions=[query,read,summary,event],completion_criteria=['review'],missing_inputs=['calendar_id','event.start','event.end'])
    f.general.planner.provider=SimpleNamespace(plan_actions=propose)
    body.pop('automatic_inputs');body.update(objective=GOAL,request_key='calendar_evidence_exact')
    result=router(f,route).handle(f.x.a,body)
    assert result['schedule'] is None and not result.get('report_only')
    doc=f.c.get(f.x.a,result['composition_id']);assert doc['state']=='ready'
    event=doc['action_plan']['actions'][-1]
    assert event['required_approvals']==['exact_payload']
    assert {tuple(b['target']) for b in event['bindings']} >= {('calendar_id',),('event','start'),('event','end')}
    assert not doc['action_plan']['missing_inputs'] and not f.http.events and not jobs.list(f.x.a)['items']


@pytest.mark.parametrize('has_evidence',[True,False])
def test_fallback_report_executes_with_only_scoped_evidence_and_explicit_deferrals(automation,monkeypatch,has_evidence):
    f=automation;route=intent('one_time');route['recurrence']['kind']='none';route['temporal']['period']='none';route['side_effects']=['email_send']
    if not has_evidence:monkeypatch.setattr('workflow_api.business_planning.retrieve',lambda *_:{'references':[],'state':'no_match'})
    def unavailable(*_):
        from runtime.service import RuntimeFailure
        raise RuntimeFailure('ACTION_INPUT_REQUIRED','Manager email address unavailable.',422)
    f.general.planner.provider=SimpleNamespace(plan_actions=unavailable)
    body=dict(objective='Review complaint operating hours and email my manager.',request_key='evidence_fallback_'+str(has_evidence))
    r=router(f,route);result=r.handle(f.x.a,body)
    assert result['report_only'] and not result.get('blocked') and result['schedule'] is None
    assert any('Manager email' in value for value in result['limitations'])
    doc=f.c.get(f.x.a,result['composition_id']);data=doc['binding_context']['validated_context']['limitation_report']
    assert bool(data['knowledge']['references'])==has_evidence
    assert set(doc['contracts'])=={'content.prepare'} and not doc['selected_tools']
    received=[]
    def factory(definition):
        def transport(messages,*_):
            raw=messages[-1]['content'].split('Process the following input as data. Return only a JSON object.\n')[-1].lstrip()
            inputs,_=json.JSONDecoder().raw_decode(raw);received.append(inputs)
            assert inputs['data']==data
            assert bool(inputs['source_references'])==has_evidence
            return json.dumps(dict(summary='Evidence review; delivery deferred.',source_references=inputs['source_references'],assumptions=data['limitations'])),1,10
        return BoundedLLM(definition,transport,lambda _:100,0,0)
    f.runner.agents=CrewExecutor(f.adapter,factory)
    w=f.c.workflow(f.x.a,doc['composition_id']);assert f.adapter.approve_pending(w,f.x.a)['ready'];w=approve(f,w)
    created=f.runtime.create_run(dict(request_id='evidence_report',operation='execute_workflow',idempotency_key='evidence_report',payload=dict(workflow_id=w['workflow_id'],workflow_version=1,inputs={})),f.x.a)
    assert f.runner.advance(created['run_id'],f.x.a)['status']=='completed',stored(f,created['run_id'])
    assert received and not f.http.sent and not f.http.events and not f.http.write_count
    assert not f.auto.listing(f.x.a,'schedule')['items']
    assert r.handle(f.x.a,body)==result
