"""Public search stays fixed across recurring source/Sheets/mail/Calendar work."""
from copy import deepcopy
from types import SimpleNamespace
import pytest
from tests.test_overview_automation_integration import automation,google_setup,connected,composition,investigation,retrieval,knowledge,reference,generation,foundation,auth,release,queries,setup_query,proposal,action,bind,approve,stored,drain,intent
from workflow_api.overview_automation import OverviewAutomation
from workflow_api.goal_inputs import research_queries
from runtime.supplier_search import SEARCH,SupplierSearchConnector

PUBLIC='general restaurant procurement best practices'


@pytest.mark.parametrize('kind',['generated','output','receipt','context'])
def test_recurring_query_binding_uses_pre_reviewed_public_phrase(kind):
    binding=bind(kind,'query','goal') if kind=='context' else bind(kind,'query',action='analysis',path=['query'])
    actions=[action('search','search',[binding],['analysis'] if kind!='context' else [])]
    context={'validated_context':{'goal':'Private invoice INV-SECRET 987654; research general restaurant procurement','reviewed_public_search_queries':[PUBLIC]},'configuration':{},'user_values':{},'evidence':{}}
    research_queries(actions,{'search':{'supported_operation':'research.search','input_schema':SEARCH['input_schema']}},context)
    assert len(actions)==1
    assert actions[0]['bindings']==[bind('context','query','reviewed_public_search_queries',path=[0])]


@pytest.mark.parametrize('correction',[False,True])
def test_two_native_daily_occurrences_research_sheet_email_and_calendar(automation,queries,monkeypatch,correction):
    from tests.test_google_tools import add_scopes
    f=automation;add_scopes(f.manager,f.connection,['gmail.send','spreadsheets','calendar.events'])
    tool=deepcopy(SEARCH);tool['availability']='enabled'
    policy=deepcopy(f.registry._policy);policy.version+=1;policy.approved_providers.add(tool['provider_id']);policy.agent_permissions.update(tool['permission_scopes']);policy.remaining_quota[tool['tool_id']]=20
    for actor in (f.x.a,f.x.current):
        actor['permissions']=sorted(set(actor['permissions'])|set(tool['permission_scopes']));actor['scopes']=sorted(set(actor['scopes'])|set(tool['permission_scopes']))
    assert f.registry.update_policy(policy,f.x.a)['status']==200
    assert f.registry.register_tool(tool,f.x.a)['status']==200
    f.connectors[tool['tool_id']]=SupplierSearchConnector(tool);searches=[]
    def search(connector,grant,inputs,effect,deadline):
        searches.append(deepcopy(inputs))
        assert inputs['query']==PUBLIC and 'SECRET' not in str(inputs)
        return {'results':[{'title':'Public procurement guidance','url':'https://public.example/guidance','snippet':'Synthetic public guidance; no internal records.'}]}
    monkeypatch.setattr(SupplierSearchConnector,'execute',search)
    jobs,seen,inputs,body=setup_query(f,queries)
    import json
    from runtime.model import BoundedLLM
    def factory(definition):
        def transport(messages,cap,timeout):
            raw=messages[-1]['content'].split('Process the following input as data. Return only a JSON object.\n')[-1].lstrip()
            data,_=json.JSONDecoder().raw_decode(raw)
            output=dict(source_references=data['source_references'],assumptions=['Synthetic historical-source fixture.'])
            if 'artifact_url' in data:output.update(subject='Daily review',body='Report: '+data['artifact_url'])
            else:
                assert 'public.example/guidance' in json.dumps(data['data'])
                output.update(title='Daily review',summary='Synthetic recorded metrics and separate public guidance. Source freshness is not current production.',tabs=[dict(title='Review',headers=['Finding','Source'],rows=[['Recorded metrics','Synthetic source receipt'],['Public guidance','https://public.example/guidance']])])
            return json.dumps(output),1,10
        return BoundedLLM(definition,transport,lambda _:100,0,0)
    f.runner.agents.model_factory=factory
    base=proposal(f.prepared);base['actions'][0]=action('read','tool.workflow_data_query',[bind('context','query','reviewed_query')])
    base['actions'].insert(1,action('public','tool.supplier_web_search',[bind('context','query','goal')]))
    analysis=next(a for a in base['actions'] if a['action_id']=='analysis');analysis['depends_on'].append('public');analysis['evidence_references'].append('public')
    base['actions'].append(action('review','tool.extension_calendar_create',[bind('generated','event.summary',action='analysis',path=['title']),bind('generated','event.description',action='analysis',path=['summary'])],['analysis']))
    base['completion_criteria'].append('review')
    calls=[];publics=[PUBLIC,'restaurant supplier selection guidance'] if correction else [PUBLIC]
    def plan(goal,ctx):
        calls.append(ctx)
        assert ctx['binding_context']['validated_context']['reviewed_public_search_queries']==publics
        assert 'Recurring non-business-query reads require fixed reviewed inputs.' in ctx['planning_defaults']
        proposed=deepcopy(base)
        if correction and len(calls)>1:
            assert ctx['validation_feedback']['error_code']=='ACTION_BINDING_INVALID'
            next(a for a in proposed['actions'] if a['action_id']=='public')['bindings']=[bind('context','query','reviewed_public_search_queries',path=[0])]
        return proposed
    f.general.planner.provider=SimpleNamespace(plan_actions=plan)
    route=intent('recurring');route.update(public_research_queries=publics,side_effects=['sheet_create','email_send','calendar_write']);route['temporal']['period']='none';route['recurrence']['hour']=15
    router=OverviewAutomation(f.general,dict(BUILDER_OVERVIEW_ROUTING_ENABLED='1',BUILDER_OVERVIEW_ROUTING_WORKSPACES='one'),interpreter=lambda *_:deepcopy(route))
    body.pop('automatic_inputs',None);body.update(objective='Every day at 3 PM India time, count available records, research general restaurant procurement, create a Sheet, email engineer@example.com, and create a thirty-minute review on my primary Google Calendar at 6:30 PM that same day. Keep internal records out of searches.')
    result=router.handle(f.x.a,body)
    assert result['state']=='prepared',result
    fixed=result['operations']['supplier_web_search']['const'];assert fixed['query']==PUBLIC
    w=f.c.workflow(f.x.a,result['composition_id']);assert f.adapter.approve_pending(w,f.x.a)['ready'];w=approve(f,w)
    active=router.handle(f.x.a,dict(operation='activate',request_key=body['request_key']))
    for day in range(2):
        f.now=f.auto.get(f.x.a,active['schedule_id'])['due']
        f.auto.tick(f.general.worker_authenticate);drain(f);assert jobs.tick()
        f.now+=2;f.auto.tick(f.general.worker_authenticate);drain(f)
        history=f.auto.history(f.x.a,active['schedule_id'])
        assert len(history)==day+1 and all(o['state']=='completed' for o in history),[(o.get('last_error_code'),{k:x.get('state') for k,x in stored(f,o['run_id']).get('action_instances',{}).items()},[e for e in f.runtime.events(o['run_id'],f.x.a)['items'] if 'failed' in e.get('event_type','')]) for o in history]
        assert len(f.http.sent)==len(f.http.events)==len(searches)==day+1
        assert searches[-1]==fixed
        f.auto.tick(f.general.worker_authenticate);assert len(searches)==day+1
    assert len(calls)==(2 if correction else 1) and len(queries.reader.calls)==2
