"""No follow-up questions: supported work or scoped evidence reports."""
from copy import deepcopy
from types import SimpleNamespace
import pytest
from tests.test_immediate_workflow_default import (automation,google_setup,connected,composition,investigation,retrieval,knowledge,reference,generation,foundation,auth,release,queries,setup_query,empty_once,GOAL)
from tests.test_overview_automation import intent
from tests.test_connected_action_plans import action,bind
from workflow_api.overview_automation import OverviewAutomation
from workflow_api.business_composition import verify_composition
from workflow_api.planning_defaults import QUESTION_FREE_GUIDANCE

def router(f,route):
    return OverviewAutomation(f.general,dict(BUILDER_OVERVIEW_ROUTING_ENABLED='1',BUILDER_OVERVIEW_ROUTING_WORKSPACES='one',BUILDER_QUESTION_FREE_WORKFLOWS='1',BUILDER_WORKSPACE_TIMEZONE='Asia/Kolkata'),interpreter=lambda *_:deepcopy(route))

@pytest.mark.parametrize('reason',['missing_definition','unknown_manager','unsupported_event','missing_schedule','no_knowledge'])
def test_unresolved_request_creates_report_without_answers_or_external_actions(automation,reason):
    f=automation;route=intent('one_time');route['recurrence']['kind']='none';route['temporal']['period']='none'
    if reason in ('missing_definition','unknown_manager'):route['missing_requirements']=['Which definition or recipient should be used?']
    elif reason=='unsupported_event':route['intent_type']='event';route['recurrence']['kind']='none'
    elif reason=='missing_schedule':route['intent_type']='recurring';route['recurrence'].update(kind='daily',hour=None)
    else:route['intent_type']='knowledge';route['entity_scope']='none'
    if reason in ('missing_definition','unknown_manager'):
        def unavailable(*_):
            from runtime.service import RuntimeFailure
            raise RuntimeFailure('ACTION_INPUT_REQUIRED','A required execution input remains unavailable.',422)
        f.general.planner.provider=SimpleNamespace(plan_actions=unavailable)
    r=router(f,route)
    if reason=='no_knowledge':
        from unittest.mock import patch
        with patch('workflow_api.business_planning.retrieve',return_value={'references':[]}):
            result=r.handle(f.x.a,dict(objective=GOAL,request_key='question_free_'+reason,business_request={}))
    else:result=r.handle(f.x.a,dict(objective=GOAL,request_key='question_free_'+reason,business_request={}))
    assert result['state']=='prepared' and result['questions']==[] and result['report_only']
    assert result['schedule'] is None
    doc=f.c.get(f.x.a,result['composition_id']);assert doc['state']=='ready' and not doc['gaps']
    assert not doc['selected_tools'] and not doc['action_plan']['missing_inputs']
    assert all(a['capability_id']=='content.prepare' for a in doc['action_plan']['actions'])
    workflow=f.c.workflow(f.x.a,result['composition_id'])
    assert not workflow['metadata']['unresolved_requirements'] and not workflow['execution_policy']['allow_external_writes']
    with f.general.store.transaction(write=False) as db:
        verify_composition(db,f.x.a,workflow)
        modified=deepcopy(workflow);modified['metadata']['overview_intent']['limitations']=[]
        with pytest.raises(Exception) as error:verify_composition(db,f.x.a,modified)
        assert error.value.code=='CAPABILITY_CHANGED'
    review=f.adapter.approve_pending(workflow,f.x.a)
    assert review['ready'],review
    assert doc['configurations'][0]['definition']['output_schema']['properties']['questions']['maxItems']==0
    assert not f.http.sent and f.http.write_count==0

def test_action_missing_input_falls_back_without_inventing_a_recipient_and_is_idempotent(automation):
    f=automation;route=intent('one_time');route['recurrence']['kind']='none';route['temporal']['period']='none';route['side_effects']=['email_send']
    def propose(goal,ctx):
        assert QUESTION_FREE_GUIDANCE in ctx['planning_defaults']
        from runtime.service import RuntimeFailure
        raise RuntimeFailure('ACTION_INPUT_REQUIRED','Unknown manager email',422)
    f.general.planner.provider=SimpleNamespace(plan_actions=propose)
    r=router(f,route);body=dict(objective='Investigate and email my manager.',request_key='question_free_action_missing')
    result=r.handle(f.x.a,body)
    assert result['report_only'] and not result['questions']
    doc=f.c.get(f.x.a,result['composition_id'])
    assert 'recipient' not in doc['binding_context']['user_values']
    assert r.handle(f.x.a,body)==result

def test_authorization_failure_is_not_replaced_with_an_unauthorized_draft(automation):
    f=automation;route=intent('one_time');route['recurrence']['kind']='none';route['temporal']['period']='none'
    def denied(*_):
        from runtime.service import RuntimeFailure
        raise RuntimeFailure('ACTION_SCOPE_DENIED','Forbidden scope',403)
    f.general.planner.provider=SimpleNamespace(plan_actions=denied)
    with pytest.raises(Exception) as error:router(f,route).handle(f.x.a,dict(objective=GOAL,request_key='question_free_denied'))
    assert error.value.code=='ACTION_SCOPE_DENIED'

def test_supported_qualitative_workflow_receives_policy_at_planning_and_runtime_without_blocker(automation,queries):
    f=automation;jobs,_,_,body=setup_query(f,queries);route=empty_once()
    def propose(goal,ctx):
        assert QUESTION_FREE_GUIDANCE in ctx['planning_defaults']
        query=action('query','data.plan_query',[]);query['budget'].update(max_llm_calls=1,max_tool_calls=0)
        read=action('read','tool.workflow_data_query',[bind('output','query',action='query',path=['query'])],['query'])
        content=action('summary','content.prepare',[bind('output','data',action='read')],['read'],['read'])
        send=action('send','tool.extension_mail_send',[bind('literal','to','recipient'),bind('generated','subject',action='summary',path=['subject']),bind('generated','body',action='summary',path=['body'])],['summary'])
        return dict(actions=[query,read,content,send],completion_criteria=['send'],missing_inputs=[])
    f.general.planner.provider=SimpleNamespace(plan_actions=propose)
    body.pop('automatic_inputs');body.update(objective=GOAL,request_key='question_free_supported')
    result=router(f,route).handle(f.x.a,body);assert result['state']=='prepared' and not result['questions'] and result['schedule'] is None
    doc=f.c.get(f.x.a,result['composition_id']);assert doc['state']=='ready'
    assert all(QUESTION_FREE_GUIDANCE in c['definition']['instructions'] for c in doc['configurations'] if c['assigned_task'] in {'query','summary'})
    assert not f.c.workflow(f.x.a,result['composition_id'])['metadata']['unresolved_requirements']
    assert not jobs.list(f.x.a)['items'] and not f.http.sent

def test_question_free_query_transport_keeps_unresolved_exact_requirements_blocked():
    import json
    from unittest.mock import patch
    from workflow_api.data_queries import QueryPlanner
    from tests.test_data_queries import plan
    query=plan();query['clarification']='Exact complete semantic matching is unsupported.'
    with patch('openai.OpenAI') as client:
        client.return_value.responses.create.return_value=SimpleNamespace(status='completed',output_text=json.dumps(query))
        planner=QueryPlanner(dict(OPENAI_API_KEY='controlled',OPENAI_MODEL='controlled',BUILDER_QUESTION_FREE_WORKFLOWS='1'))
        assert planner.generate('Count every overheating case exactly.',{})==query
        assert QUESTION_FREE_GUIDANCE in client.return_value.responses.create.call_args.kwargs['input'][0]['content']
