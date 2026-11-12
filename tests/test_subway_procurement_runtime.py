"""Existing Overview → Registry → GraphRunner/CrewAI → adaptive → report/map."""
from copy import deepcopy
import pytest
from tests.test_subway_intelligence import subway,engine,installed,selection
from tests.test_subway_autonomy import start,drain,decision
from tests.test_subway_procurement_knowledge import request,scenarios
from tests.test_subway_full_queries import Collection,Cursor
from tests.test_connected_action_plans import action,bind
from workflow_api.subway_assessments import definition


def test_existing_pipeline_executes_procurement_tool_and_records_map_evidence(subway,monkeypatch):
    f=subway
    def find(self,query,projection):
        return Cursor([r for r in self.rows if all(r.get(k) in v['$in'] for k,v in query.items())])
    monkeypatch.setattr(Collection,'find',find)
    f.rows['subway_finance'].update(deepcopy(scenarios.generate('missing_evidence')['evidence']))
    registry=f.adapter.service;policy=deepcopy(registry._policy);policy.remaining_quota['subway_assess']=100;policy.version+=1
    assert registry.update_policy(policy,f.auth)['status']==200
    assert registry.register_tool(definition(),f.auth)['status']==200
    f.selected_override=selection(f.q,['finance.purchaseorders','finance.grns','finance.invoicedatas','finance.approvals'])
    inputs=request(f.q,'purchase_order_reconciliation')
    f.query_plans={'query_plan':inputs['query']}
    def proposal(goal,ctx):
        f.planning_contexts.append(deepcopy(ctx))
        query=action('query_plan','subway.plan_query',[])
        query['budget'].update(max_llm_calls=1,max_tool_calls=0)
        read=action('assess','tool.subway_assess',[
            bind('context','assessment','business_knowledge',path=['procurement_knowledge','assessment_kinds','purchase_order_reconciliation']),
            bind('output','query',action='query_plan',path=['query'])],['query_plan'])
        read['budget']['timeout_seconds']=120
        report=action('report','content.prepare',[bind('output','data',action='assess')],['assess'],['assess'])
        return dict(actions=[query,read,report],completion_criteria=['report'],missing_inputs=[])
    f.service.planner.provider.plan_actions=proposal
    contexts=[]
    def evaluate(ctx,**_):contexts.append(deepcopy(ctx));return decision(ctx)
    rid,doc,w=start(f,evaluate,'Investigate purchase-order discrepancies, check approval evidence, analyze invoice and receipt differences, and prepare an evidence-backed report.')
    run=drain(f,rid)
    assert run['status']=='completed',run.get('error_code',run.get('adaptive'))
    output=run['action_instances']['assess']['output']
    assert output['report']['results'] and output['report']['reconciliations']
    assert run['action_instances']['assess']['verified_receipt']
    assert run['action_instances']['assess']['ontology_usage']
    assert any('subway-procurement-v1' in u['reason'] and 'subway_rule:' in u['reason'] for u in run['action_instances']['assess']['ontology_usage'])
    assert run['action_instances']['assess']['ontology_rule_usage']
    assert any(v['valid'] for v in contexts[-1]['evidence'].values())
    assert any(l['code']=='PROCUREMENT_SOURCE_FRESHNESS' for l in contexts[-1]['deterministic_limitations'])
    assert 'procurement_knowledge' in doc['binding_context']['validated_context']['business_knowledge']
    assert len(f.model_inputs)==2  # real query-planner and report actions via CrewAI
    assert any('subway_query_catalog' in i.get('context',{}) for i in f.model_inputs)


def test_existing_document_retrieval_can_cite_new_source_definitions(subway):
    from workflow_api.subway_documents import SubwayDocuments
    f=subway;package=f.app.state.client_packages.get(f.auth,'subway-business-v1',4)
    reader=SubwayDocuments(f.q,f.auth,dict(package_id=package['package_id'],revision=4,package_sha256=package['sha256']))
    result=reader.invoke(dict(tool_id='subway_documents'),dict(query='statusEnums CREATED_BY_VENDOR APPROVAL_IN_PROGRESS PARTIALLY_REJECTED'),None)
    assert result['records']
    assert any(r['source_id'].startswith('subway_procurement_') for r in result['records'])
    assert all(r['scope']==dict(workspace_id='client-subway',owner_id='subway-client') for r in result['records'])
