"""Canonical composition category preserves operations and existing safeguards."""
from copy import deepcopy
from types import SimpleNamespace
import pytest
from tests.test_overview_automation import intent
from tests.test_short_prompt_defaults import (automation,google_setup,connected,composition,investigation,retrieval,knowledge,reference,generation,foundation,auth,release,queries,setup_query)
from tests.test_connected_action_plans import action,bind
from workflow_api.overview_automation import OverviewAutomation
from workflow_api.service import ApiFailure

GOAL='Count tickets by status, show their average hmr, and email me the summary.'


@pytest.mark.parametrize('kind',['population','investigation'])
@pytest.mark.parametrize('recurrence,expected',[('none','one_time'),('once','one_time'),('daily','recurring'),('monthly','recurring')])
def test_composed_category_preserves_all_validated_analysis_and_delivery_fields(kind,recurrence,expected):
    source=intent(kind);source['side_effects']=['email_send','sheet_create','calendar_write'];source['recurrence']['kind']=recurrence
    original=deepcopy(source)
    router=OverviewAutomation(None,interpreter=lambda *_:source)
    actual=router.interpret(GOAL,{})
    assert actual['intent_type']==expected
    actual['intent_type']=kind
    assert actual==original and source==original


@pytest.mark.parametrize('objective',['Count tickets. No external writes.','Count tickets; do not send emails.'])
def test_category_correction_does_not_bypass_explicit_negative_instructions(objective):
    source=intent('population');source['side_effects']=['email_send']
    with pytest.raises(ApiFailure,match='explicit restriction'):
        OverviewAutomation(None,interpreter=lambda *_:source).interpret(objective,{})


def test_read_only_analysis_stays_read_only():
    source=intent('population');source['recurrence']['kind']='none'
    assert OverviewAutomation(None,interpreter=lambda *_:source).interpret('Count tickets by status.',{})==source


def test_exact_reported_prompt_prepares_email_workflow_with_existing_review_gates(automation,queries):
    f=automation;jobs,_,_,body=setup_query(f,queries)
    source=intent('population');source['recurrence']['kind']='none';source['temporal']['period']='none';source['side_effects']=['email_send']
    def propose(goal,ctx):
        assert goal==GOAL and ctx['overview_intent']['route']['intent_type']=='one_time'
        assert ctx['binding_context']['user_values']['recipient']=='owner@example.com'
        read=action('query','data.plan_query',[]);read['budget'].update(max_llm_calls=1,max_tool_calls=0)
        execute=action('read','tool.workflow_data_query',[bind('output','query',action='query',path=['query'])],['query'])
        content=action('summary','content.prepare',[bind('output','data',action='read')],['read'],['read'])
        send=action('send','tool.extension_mail_send',[bind('literal','to','recipient'),bind('generated','subject',action='summary',path=['subject']),bind('generated','body',action='summary',path=['body'])],['summary'])
        return dict(actions=[read,execute,content,send],completion_criteria=['send'],missing_inputs=[])
    f.general.planner.provider=SimpleNamespace(plan_actions=propose)
    router=OverviewAutomation(f.general,dict(BUILDER_OVERVIEW_ROUTING_ENABLED='1',BUILDER_OVERVIEW_ROUTING_WORKSPACES='one'),interpreter=lambda *_:source)
    body.pop('automatic_inputs');body['objective']=GOAL
    result=router.handle(f.x.a,body)
    assert result['state']=='prepared' and result['intent']['intent_type']=='one_time'
    assert result['schedule'] is None
    doc=f.c.get(f.x.a,result['composition_id'])
    assert not doc['action_plan']['missing_inputs']
    send=next(a for a in doc['action_plan']['actions'] if a['action_id']=='send')
    assert send['required_approvals']==['exact_payload']
    workflow=f.c.workflow(f.x.a,result['composition_id'])
    assert workflow['status']=='draft' and workflow['execution_policy']['requires_review_before_execution']
    assert not f.http.sent and f.http.write_count==0 and not jobs.list(f.x.a)['items']
