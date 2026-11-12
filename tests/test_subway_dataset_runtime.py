"""Shared runtime/scheduler with persistent SQLite demo reads and controlled models.

Configured-provider acceptance is recorded separately in the OpenSpec verification.
"""
from copy import deepcopy
import pytest
from tests.test_subway_intelligence import subway,engine,installed,selection,route
from tests.test_subway_autonomy import start,drain,decision
from tests.test_connected_action_plans import action,bind
from workflow_api.subway_demonstration import install,DemoQueries
from workflow_api.subway_assessments import definition
from workflow_api.subway_demo_data import LABEL
from workflow_api.automation import DurableAutomation

@pytest.mark.parametrize('recurring',[False,True])
def test_automatic_overview_replan_restart_and_frozen_scheduled_source(subway,monkeypatch,recurring):
    f=subway;install(f.service.store,f.auth,f.q.version,automatic_default=True);f.q=DemoQueries(f.q,f.auth)
    f.selected_override=selection(f.q,['finance.purchaseorders','finance.invoicedatas','finance.approvals','finance.budgets'])
    c=f.q.catalog(f.auth);d=next(d for d in c['datasets'].values() if d['label']=='finance.purchaseorders');fid=next(v['field_id'] for v in d['fields'] if v['name']=='_id')
    f.query_plans={'query_plan':dict(base_dataset_id=d['dataset_id'],fields=[fid],metrics=[],joins=[],filters=[],group_by=[],order_by=[],offset=0,limit=20)}
    registry=f.adapter.service;policy=deepcopy(registry._policy);policy.remaining_quota['subway_assess']=100;policy.version+=1
    assert registry.update_policy(policy,f.auth)['status']==200
    assert registry.register_tool(definition(),f.auth)['status']==200
    def proposal(goal,ctx):
        query=action('query_plan','subway.plan_query',[]);query['budget'].update(max_llm_calls=1,max_tool_calls=0)
        read=action('assess','tool.subway_assess',[bind('context','assessment','business_knowledge',path=['procurement_knowledge','assessment_kinds','purchase_order_reconciliation']),bind('output','query',action='query_plan',path=['query'])],['query_plan']);read['budget']['timeout_seconds']=120
        report=action('report','content.prepare',[bind('output','data',action='assess')],['assess'],['assess'])
        return dict(actions=[query,read,report],completion_criteria=['report'],missing_inputs=[])
    f.service.planner.provider.plan_actions=proposal
    if recurring:
        import tests.test_subway_autonomy as helpers
        def recurring_route(selected,**kw):return route(selected,**{**kw,'intent_type':'recurring','recurrence':dict(kind='daily',hour=9,minute=0,weekdays=[],timezone='Asia/Kolkata',date=None,month_day=None)})
        monkeypatch.setattr(helpers,'route',recurring_route)
    contexts=[]
    waited=False;replanned=False
    def evaluator(ctx,**kw):
        nonlocal waited,replanned
        contexts.append(deepcopy(ctx))
        if 'assess' in ctx['completed_actions'] and 'report' not in ctx['completed_actions']:
            if not waited:
                waited=True;return decision(ctx,choice='request_input',wait=True)
            if not replanned:
                replanned=True;actions=deepcopy(ctx['plan']['actions']);actions[-1]['instructions']+=' Preserve the original pinned source version.'
                return decision(ctx,choice='replan',proposal=dict(actions=actions,completion_criteria=ctx['plan']['completion_criteria'],missing_inputs=[]))
        return decision(ctx)
    rid,doc,w=start(f,evaluator,'Investigate procurement exceptions and prepare an evidence-backed report.'+(' Every day at 9 AM India time.' if recurring else ''))
    if recurring:
        f.now=f.service.lifecycle.clock();f.service.lifecycle.clock=lambda:f.now
        f.service.worker_authenticate=lambda ws,owner:deepcopy(f.auth) if (ws,owner)==('client-subway','subway-client') else None
        auto=DurableAutomation(f.service,clock=lambda:f.now)
        f.service.automation=auto
        active=f.service.overview_automation.handle(f.auth,dict(operation='activate',request_key='phase2_acceptance'))
    run=drain(f,rid);assert run['adaptive']['status']=='waiting_for_input'
    original=deepcopy(run['action_instances']['assess'])
    from workflow_api.subway_dataset_lifecycle import SubwayDatasetLifecycle
    from tests.test_subway_dataset_lifecycle import newer
    manager=SubwayDatasetLifecycle(f.service.store);manager.register(f.auth,newer(f.q.real))
    assert f.q.real.for_objective(f.auth,'Investigate orders.').demo_context['revision']==2
    from workflow_api.workflow_adaptive import supply
    from runtime.graph import GraphRunner
    from runtime import RuntimeService
    previous=f.service.runtime_runner
    f.adapter.agents.clear();f.adapter._grants.clear();f.adapter.service._agents.clear();f.adapter.service._assignments.clear()
    f.service.runtime_runner=GraphRunner(RuntimeService(f.service),agents=previous.agents,connectors=previous.connectors)
    supply(f.service.runtime_runner.runtime,f.auth,rid,dict(wait_id=run['adaptive']['pending_wait']['wait_id'],values=dict(threshold=42)))
    run=drain(f,rid);assert run['status']=='completed',run.get('error_code',run.get('adaptive'))
    assert run['action_instances']['assess']==original
    assert run['adaptive']['revision']==2
    assert w['metadata']['action_binding_context']['validated_context']['source_resolution']['selection']=='automatic'
    out=run['action_instances']['assess']['output'];assert out['coverage']['matched_records']==8
    assert out['report']['provenance']['mode']=='modeled_demonstration' and len(out['report']['invoice_reconciliation'])==8
    assert all(r['invoice_item_comparison']!='INSUFFICIENT_EVIDENCE' for r in out['report']['reconciliations'])
    assert LABEL in run['action_instances']['report']['output']['summary']
    assert run['action_instances']['assess']['ontology_rule_usage']
    assert all('subway-demonstration-v1 revision 1' in u['reason'] for u in run['action_instances']['assess']['ontology_usage'])
    assert all(v['valid'] for v in contexts[-1]['evidence'].values())
    if recurring:
        f.now=active['due']
        for _ in range(10):
            auto.tick(f.service.worker_authenticate)
            for job in f.service.lifecycle.lease('client-subway'):f.service.lifecycle.execute_job(job['job_id'],f.service.runtime_runner)
            occurrences=auto.listing(f.auth,'occurrence')['items']
            if occurrences and occurrences[0]['state'] in ('completed','failed','dead_letter'):break
        assert len(occurrences)==1 and occurrences[0]['state']=='completed',occurrences
        from tests.test_subway_autonomy import load
        scheduled=load(f,occurrences[0]['run_id'])
        assert scheduled['action_instances']['assess']['output']['report']['demo_context']['revision']==1
        assert f.q.real.for_objective(f.auth,'Investigate orders.').demo_context['revision']==2
