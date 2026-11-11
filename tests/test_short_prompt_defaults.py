"""Short-prompt handoff through real scoped services; model transports controlled."""
from copy import deepcopy
import json
from types import SimpleNamespace
from unittest.mock import patch
import pytest
from tests.test_overview_automation_integration import (automation,google_setup,connected,composition,investigation,retrieval,knowledge,reference,generation,foundation,auth,release,queries,setup_query)
from tests.test_connected_action_plans import action,bind
from tests.test_overview_automation import intent
from tests.test_data_queries import plan
from workflow_api.overview_automation import OverviewAutomation
from workflow_api.data_queries import QueryPlanner
from workflow_api.planning_defaults import GUIDANCE


def router(f,interpret):
    return OverviewAutomation(f.general,dict(BUILDER_OVERVIEW_ROUTING_ENABLED='1',BUILDER_OVERVIEW_ROUTING_WORKSPACES='one',BUILDER_WORKSPACE_TIMEZONE='Asia/Kolkata'),interpreter=interpret)


@pytest.mark.parametrize('goal,recipient',[
    ('Email me today’s complaint summary.','owner@example.com'),
    ('Summarize accessible complaints today and email engineer@example.com.','engineer@example.com'),
    ('Summarize authorized complaints today.',None),
    ('Email today’s complaint summary to my manager.',None)])
def test_short_request_resolves_only_supplied_or_explicit_self_recipient_before_routing(automation,goal,recipient):
    f=automation;seen=[]
    route=intent('ambiguous');route['missing_requirements']=['Which date meaning?']
    r=router(f,lambda objective,context:seen.append(context) or deepcopy(route))
    r.prepare_intent(f.x.a,dict(objective=goal,request_key='short_recipient_context',google_connection_id=f.connection))
    ctx=seen[0]
    assert ctx['resolved_inputs']['user_values'].get('recipient')==recipient
    assert ctx['resolved_inputs']['validated_context']['selected_account_email']=='owner@example.com'
    assert ctx['workspace_timezone']=='Asia/Kolkata'
    assert ctx['planning_defaults']==GUIDANCE
    assert not f.http.sent and f.http.write_count==0


def test_revoked_selected_account_is_not_replaced_or_exposed_to_interpreter(automation):
    f=automation;seen=[];f.manager.disconnect(f.x.a,f.connection)
    r=router(f,lambda *_:seen.append(True))
    with pytest.raises(Exception) as error:
        r.prepare_intent(f.x.a,dict(objective='Email me today’s summary.',request_key='short_revoked_account',google_connection_id=f.connection))
    assert error.value.code=='GOOGLE_RECONNECT_REQUIRED' and not seen


def test_real_query_transport_receives_defaults_without_rewriting_explicit_business_filters():
    question='Summarize authorized complaints today; include only status APPROVED.'
    with patch('openai.OpenAI') as client:
        client.return_value.responses.create.return_value=SimpleNamespace(status='completed',output_text=json.dumps(plan()))
        model=QueryPlanner(dict(OPENAI_API_KEY='controlled',OPENAI_MODEL='controlled'))
        model.generate(question,dict(datasets=[]))
        request=client.return_value.responses.create.call_args.kwargs
        assert GUIDANCE in request['input'][0]['content']
        assert json.loads(request['input'][1]['content'])['question']==question


def test_short_self_mail_request_prepares_one_reviewable_workflow_without_technical_inputs(automation,queries):
    f=automation;jobs,_,_,body=setup_query(f,queries)
    seen=[];route=intent('one_time');route['temporal']['period']='none';route['side_effects']=['email_send']
    def interpret(objective,context):
        assert context['resolved_inputs']['user_values']['recipient']=='owner@example.com'
        assert 'report template' in context['planning_defaults']
        return deepcopy(route)
    def propose(goal,ctx):
        seen.append(ctx)
        assert ctx['binding_context']['user_values']['recipient']=='owner@example.com'
        read=action('query','data.plan_query',[])
        read['budget'].update(max_llm_calls=1,max_tool_calls=0)
        execute=action('read','tool.workflow_data_query',[bind('output','query',action='query',path=['query'])],['query'])
        content=action('summary','content.prepare',[bind('output','data',action='read')],['read'],['read'])
        send=action('send','tool.extension_mail_send',[bind('literal','to','recipient'),bind('generated','subject',action='summary',path=['subject']),bind('generated','body',action='summary',path=['body'])],['summary'])
        return dict(actions=[read,execute,content,send],completion_criteria=['send'],missing_inputs=[])
    f.general.planner.provider=SimpleNamespace(plan_actions=propose)
    body.pop('automatic_inputs');body['objective']='Summarize accessible complaints and email me.'
    result=router(f,interpret).handle(f.x.a,body)
    assert result['state']=='prepared' and result['schedule'] is None
    doc=f.c.get(f.x.a,result['composition_id'])
    assert not doc['action_plan']['missing_inputs']
    assert seen[0]['planning_defaults'].startswith(GUIDANCE)
    from runtime.aggregate_math import GUIDANCE as AGGREGATE_GUIDANCE
    assert AGGREGATE_GUIDANCE in seen[0]['planning_defaults']
    assert all(a['capability_id']!='tool.extension_sheets_create_report' for a in doc['action_plan']['actions'])
    assert not jobs.list(f.x.a)['items'] and not f.http.sent and f.http.write_count==0
