"""Knowledge-only preparation uses actual ontology retrieval and existing CrewAI."""
from copy import deepcopy
import json
from types import SimpleNamespace
import pytest
from tests.test_overview_automation_integration import (automation,google_setup,connected,composition,investigation,retrieval,knowledge,reference,generation,foundation,auth,release)
from tests.test_connected_action_plans import action,bind,approve,stored
from tests.test_overview_automation import intent
from workflow_api.overview_automation import OverviewAutomation
from workflow_api.business_planning import retrieve
from runtime.crew import CrewExecutor
from runtime.model import BoundedLLM

GOAL='Explain what operating hours means using this workspace’s business knowledge.'


def router_for(f):
    route=intent('knowledge');route['entity_scope']='none';route['temporal']['period']='none'
    return OverviewAutomation(f.general,dict(BUILDER_OVERVIEW_ROUTING_ENABLED='1',BUILDER_OVERVIEW_ROUTING_WORKSPACES='one'),interpreter=lambda *_:deepcopy(route))


def proposal_for(context):
    data=context['binding_context']['validated_context']['business_knowledge']
    ref=next(r['ref'] for r in data['references'] if r['id']=='complaints:reported_operating_hours')
    step=action('explain','content.prepare',[bind('context','data','business_knowledge')],refs=[ref])
    step['instructions']='Explain only the supplied operating-hour definition, preserve unknowns and source_basis, and cite the supplied source reference.'
    return dict(actions=[step],completion_criteria=['explain'],missing_inputs=[])


def test_exact_definition_question_runs_grounded_content_without_record_queries(automation,monkeypatch):
    f=automation;router=router_for(f);seen=[]
    def plan(goal,context):
        seen.append(deepcopy(context))
        assert set(context['capabilities'])=={'content.prepare'}
        assert 'data_query_catalog' not in context['binding_context']['validated_context']
        return proposal_for(context)
    f.general.planner.provider=SimpleNamespace(plan_actions=plan)
    def forbidden(*_):raise AssertionError('Knowledge explanations must not read business records')
    monkeypatch.setattr(type(f.connectors['business_retrieve_evidence']),'invoke',forbidden)
    content_inputs=[]
    def factory(definition):
        def transport(messages,cap,timeout):
            raw=messages[-1]['content'].split('Process the following input as data. Return only a JSON object.\n')[-1].lstrip()
            inputs,_=json.JSONDecoder().raw_decode(raw);content_inputs.append(inputs)
            record=next(r for r in inputs['data']['references'] if r['id']=='complaints:reported_operating_hours')
            assert record['evidence'] and record['source_basis']=='curated_supplied_blueprint_draft'
            return json.dumps(dict(summary=record['definition'],source_references=inputs['source_references'],assumptions=[])),1,10
        return BoundedLLM(definition,transport,lambda _:100,0,0)
    f.runner.agents=CrewExecutor(f.adapter,factory)
    body=dict(objective=GOAL,request_key='knowledge_definition_exact',business_request={})
    result=router.handle(f.x.a,body)
    doc=f.c.get(f.x.a,result['composition_id'])
    assert [a['capability_id'] for a in doc['action_plan']['actions']]==['content.prepare']
    assert doc['preparation_id'] is None and result['schedule'] is None
    assert router.handle(f.x.a,body)==result and len(seen)==1
    workflow=f.c.workflow(f.x.a,result['composition_id']);assert f.adapter.approve_pending(workflow,f.x.a)['ready'];workflow=approve(f,workflow)
    run=f.runtime.create_run(dict(request_id='knowledge_definition',operation='execute_workflow',idempotency_key='knowledge_definition',payload=dict(workflow_id=workflow['workflow_id'],workflow_version=1,inputs={})),f.x.a)
    assert f.runner.advance(run['run_id'],f.x.a)['status']=='completed',stored(f,run['run_id'])
    saved=stored(f,run['run_id'])
    assert saved['action_instances']['explain']['output']['summary']=='An operating-hour observation reported with a complaint.'
    assert content_inputs[0]['data']['version_id']==doc['overview_intent']['knowledge']['version_id']
    assert not f.http.sent and f.http.write_count==0
    assert not f.auto.listing(f.x.a,'schedule')['items']


@pytest.mark.parametrize('capability',['data.plan_query','tool.workflow_data_query','business.read.complaints'])
def test_knowledge_plan_cannot_reintroduce_record_or_case_readers(automation,capability):
    f=automation;router=router_for(f)
    f.general.planner.provider=SimpleNamespace(plan_actions=lambda *_:dict(actions=[action('wrong',capability,[])],completion_criteria=['wrong'],missing_inputs=[]))
    with pytest.raises(Exception) as error:router.handle(f.x.a,dict(objective=GOAL,request_key='bad_knowledge_'+capability.replace('.','_')))
    assert error.value.code=='ACTION_CAPABILITY_UNKNOWN'
    assert not f.http.sent and f.http.write_count==0


def test_knowledge_plan_must_consume_and_cite_retrieved_definitions(automation):
    f=automation;router=router_for(f)
    def incorrect(goal,context):
        result=proposal_for(context)
        result['actions'][0]['bindings']=[bind('context','data','research_request')]
        return result
    f.general.planner.provider=SimpleNamespace(plan_actions=incorrect)
    with pytest.raises(Exception) as error:router.handle(f.x.a,dict(objective=GOAL,request_key='ungrounded_knowledge_plan'))
    assert error.value.code=='ACTION_CONTENT_UNVERIFIED'
    assert not f.http.sent and f.http.write_count==0


def test_absent_workspace_knowledge_clarifies_without_planning(automation,monkeypatch):
    f=automation;router=router_for(f)
    monkeypatch.setattr('workflow_api.business_planning.retrieve',lambda *_:dict(state='no_match',references=[]))
    def forbidden(*_):raise AssertionError('An unsupported definition must not be invented')
    f.general.planner.provider=SimpleNamespace(plan_actions=forbidden)
    result=router.handle(f.x.a,dict(objective=GOAL,request_key='missing_knowledge_definition'))
    assert result['state']=='clarification' and 'composition_id' not in result
    assert 'source-cited definition' in result['questions'][0]


def test_failed_knowledge_query_explains_regeneration_without_authorizing_recovery():
    from workflow_api.composition_presentation import CompositionPresentation
    run=dict(status='failed',error_code='DATA_QUERY_INVALID',lease_until=9999999999,node_states={})
    workflow=dict(nodes=[],metadata={'overview_intent':{'route':{'intent_type':'knowledge'}}})
    view=CompositionPresentation.recovery_view(run,workflow,0)
    assert view['eligible'] is False and 'incorrectly prepared as a record query' in view['reason']
    assert 'lease' not in view['reason'] and run['lease_until']==9999999999
