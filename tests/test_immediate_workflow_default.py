"""An empty once schedule must not block an ordinary immediate request."""
from copy import deepcopy
from types import SimpleNamespace
import pytest
from tests.test_composed_intent_routing import (automation,google_setup,connected,composition,investigation,retrieval,knowledge,reference,generation,foundation,auth,release,queries,setup_query)
from tests.test_connected_action_plans import action,bind
from tests.test_overview_automation import intent
from workflow_api.overview_automation import OverviewAutomation
from workflow_api.service import ApiFailure

GOAL='My Simpsons engine is overheating and losing power. Investigate the likely causes and email me the findings'

def empty_once():
    route=intent('one_time');route['side_effects']=['email_send'];route['temporal']['period']='none'
    route['recurrence'].update(kind='once',hour=None,date=None,timezone=None)
    return route

@pytest.mark.parametrize('goal',[GOAL,'Investigate what may cause overheating and email me.',
    'Email me today’s complaint summary.','Summarize the previous month’s complaints and email me.',
    'Run this once and email me the findings.','Investigate now and email me.',
    'Email me November’s complaint summary.'])
def test_empty_once_without_execution_timing_becomes_immediate_without_mutating_proposal(goal):
    route=empty_once();original=deepcopy(route)
    router=OverviewAutomation(None,interpreter=lambda *_:route)
    actual=router.interpret(goal,{})
    assert actual['recurrence']['kind']=='none'
    assert router.schedule(actual,0) is None
    actual['recurrence']['kind']='once'
    assert actual==original and route==original

@pytest.mark.parametrize('goal',['Run tomorrow morning.','Email the report later.','Run at 6 PM.',
    'Send the report in two hours.','Run on 15 November.','Run every day.','Run next week.'])
def test_explicit_execution_timing_is_not_silently_changed_to_now(goal):
    router=OverviewAutomation(None,dict(BUILDER_WORKSPACE_TIMEZONE='Asia/Kolkata'),interpreter=lambda *_:empty_once())
    actual=router.interpret(goal,{})
    assert actual['recurrence']['kind']=='once'
    with pytest.raises(ApiFailure,match='At what time'):router.schedule(actual,0)

def test_explicit_recurring_time_and_reporting_window_are_preserved():
    route=intent();original=deepcopy(route)
    actual=OverviewAutomation(None,interpreter=lambda *_:route).interpret('Every day at 6 PM India time email today’s complaint summary.',{})
    assert actual==original and actual['temporal']['period']=='today'

def test_reported_request_prepares_without_schedule_and_retains_email_review(automation,queries):
    f=automation;jobs,_,_,body=setup_query(f,queries)
    def propose(goal,ctx):
        assert goal==GOAL and ctx['overview_intent']['schedule'] is None
        assert ctx['overview_intent']['route']['recurrence']['kind']=='none'
        read=action('query','data.plan_query',[]);read['budget'].update(max_llm_calls=1,max_tool_calls=0)
        execute=action('read','tool.workflow_data_query',[bind('output','query',action='query',path=['query'])],['query'])
        content=action('summary','content.prepare',[bind('output','data',action='read')],['read'],['read'])
        send=action('send','tool.extension_mail_send',[bind('literal','to','recipient'),bind('generated','subject',action='summary',path=['subject']),bind('generated','body',action='summary',path=['body'])],['summary'])
        return dict(actions=[read,execute,content,send],completion_criteria=['send'],missing_inputs=[])
    f.general.planner.provider=SimpleNamespace(plan_actions=propose)
    router=OverviewAutomation(f.general,dict(BUILDER_OVERVIEW_ROUTING_ENABLED='1',BUILDER_OVERVIEW_ROUTING_WORKSPACES='one'),interpreter=lambda *_:empty_once())
    body.pop('automatic_inputs');body['objective']=GOAL
    result=router.handle(f.x.a,body)
    assert result['state']=='prepared' and result['schedule'] is None
    doc=f.c.get(f.x.a,result['composition_id'])
    assert not doc['action_plan']['missing_inputs']
    assert next(a for a in doc['action_plan']['actions'] if a['action_id']=='send')['required_approvals']==['exact_payload']
    assert not f.http.sent and f.http.write_count==0 and not jobs.list(f.x.a)['items']
