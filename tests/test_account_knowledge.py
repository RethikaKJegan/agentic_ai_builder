"""Unified projections reuse real preparation/packages and preserve scoped authority."""
from copy import deepcopy
import json
from pathlib import Path
import time

import pytest

from runtime import RuntimeFailure
from workflow_api.account_knowledge import AccountKnowledge
from tests.test_business_composition import (
    composition,investigation,retrieval,knowledge,reference,generation,foundation,auth,release,
    prepare,run,DiagnosticAgents,
)
from tests.test_agent_memory_recovery import setup_retail


@pytest.fixture
def graph(composition):
    f=composition;f.now=time.time()
    f.general.account_graph=AccountKnowledge(f.general.store,f.general,clock=lambda:f.now)
    doc=f.general.business_preparation.prepare(f.x.a,dict(objective='Compare complaint C123 with its linked inspection.'))
    f.pin=f.general.account_graph.sync_preparation(f.x.a,f.general.business_preparation,doc['preflight_id'])
    return f


def test_real_mapped_records_and_directional_links_are_in_one_scoped_graph(graph):
    f=graph;g=f.general.account_graph;doc=g.get(f.x.a,f.pin)
    records=[n for n in doc['nodes'] if n['kind']=='record']
    assert records and any(e['kind']=='mapping' for e in doc['edges'])
    assert any(e['kind']=='source_reference' for e in doc['edges'])
    assert all(e['confidence'] is None for e in doc['edges'])
    assert all(e['status']=='inferred' for e in doc['edges'] if e['kind']=='business_relationship')
    seed=next(e['source'] for e in doc['edges'] if e['kind']=='source_reference')
    walked=g.traverse(f.x.a,f.pin,[seed],depth=2)
    assert walked['edges'] and all(e['status']=='confirmed' for e in walked['edges'])
    assert not any(n.get('status')=='conflicting' for n in records)
    assert g.view(f.x.a)['graph_id']==f.pin['graph_id']


def test_same_snapshot_sync_is_idempotent_and_owner_scope_is_not_widened(graph):
    f=graph;g=f.general.account_graph;doc=g.get(f.x.a,f.pin)
    assert g.sync_preparation(f.x.a,f.general.business_preparation,doc['pins']['preflight_id'])==f.pin
    other=deepcopy(f.x.a);other['subject']['subject_id']='other-owner'
    with pytest.raises(RuntimeFailure) as error:g.get(other,f.pin)
    assert error.value.code=='ACCOUNT_GRAPH_NOT_FOUND'
    other['subject']['workspace_id']='subway'
    with pytest.raises(RuntimeFailure) as error:g.get(other,f.pin)
    assert error.value.code=='ACCOUNT_GRAPH_SCOPE'


def test_stale_and_invalidated_evidence_is_not_current_agent_context(graph):
    f=graph;g=f.general.account_graph;original=g.get(f.x.a,f.pin)
    f.now+=301
    with pytest.raises(RuntimeFailure) as error:g.context(f.x.a,f.pin)
    assert error.value.code=='ACCOUNT_GRAPH_STALE'
    assert g.get(f.x.a,f.pin,historical=True)['nodes']==original['nodes']
    f.now-=301;g.invalidate(f.x.a,f.pin['source_key'])
    with pytest.raises(RuntimeFailure):g.traverse(f.x.a,f.pin,[])
    assert g.get(f.x.a,f.pin,historical=True)['stale']


@pytest.mark.parametrize('options',[{'depth':5},{'limit':65},{'seconds':2},{'depth':True}])
def test_traversal_limits_are_enforced_by_backend(graph,options):
    f=graph
    with pytest.raises(RuntimeFailure) as error:f.general.account_graph.traverse(f.x.a,f.pin,[],**options)
    assert error.value.code=='ACCOUNT_GRAPH_LIMIT'


def test_seed_nodes_cannot_exceed_the_requested_result_limit(graph):
    f=graph;g=f.general.account_graph
    seeds=[n['node_id'] for n in g.get(f.x.a,f.pin)['nodes'][:2]]
    with pytest.raises(RuntimeFailure) as error:g.traverse(f.x.a,f.pin,seeds,limit=1)
    assert error.value.code=='ACCOUNT_GRAPH_LIMIT'


def test_tampered_projection_cannot_be_used_as_evidence(graph):
    f=graph;g=f.general.account_graph
    with f.general.store.transaction() as db:
        row=db.execute('SELECT document FROM account_graph_revisions').fetchone()
        doc=json.loads(row[0]);doc['nodes'][0]['label']='forged fact'
        db.execute('UPDATE account_graph_revisions SET document=?',(json.dumps(doc),))
    with pytest.raises(RuntimeFailure) as error:g.get(f.x.a,f.pin)
    assert error.value.code=='ACCOUNT_GRAPH_INTEGRITY'


def test_changed_package_rows_make_new_revision_without_blind_entity_merge(graph):
    f=graph;packages=setup_retail(f);packages.account_graph=f.general.account_graph
    request=dict(package_id='retail_fixture',revision=1,capability_id='retail.read')
    first=packages.read(f.x.a,request);pin=first['account_graph_pin']
    packages.register_source(f.x.a,'inventory_fixture',lambda *_:[{'id':'stock_1','product':'Filter','stock':5,'threshold':10}])
    second=packages.read(f.x.a,request);new=second['account_graph_pin']
    assert new['revision']==pin['revision']+1
    with pytest.raises(RuntimeFailure):f.general.account_graph.get(f.x.a,pin)
    assert f.general.account_graph.get(f.x.a,pin,historical=True)['stale']
    assert any(n['values'].get('mapping:stock')==5 for n in f.general.account_graph.get(f.x.a,new)['nodes'] if n['kind']=='record')
    packages.register_source(f.x.a,'inventory_fixture',lambda *_:[{'id':'same','product':'A','stock':1,'threshold':2},{'id':'same','product':'B','stock':4,'threshold':2}])
    conflicting=packages.read(f.x.a,request)
    assert conflicting['coverage']['state']=='conflicting_evidence'
    records=[n for n in f.general.account_graph.get(f.x.a,conflicting['account_graph_pin'])['nodes'] if n['kind']=='record']
    assert len(records)==1 and records[0]['status']=='conflicting'
    assert len(records[0]['conflicting_observations'])==2


def test_registered_subway_package_exposes_only_supported_read_capabilities(graph):
    from tests.test_agent_memory_recovery import package_tool_definition,PackageEvidenceConnector
    f=graph
    package=json.loads((Path(__file__).resolve().parents[1]/'ontology/subway/knowledge-package-v2.json').read_text())
    packages=f.c.packages;packages.account_graph=f.general.account_graph
    packages.publish(f.x.a,package)
    cid='subway.read.stores';binding=package['resource_bindings'][cid]
    mappings=[m for m in package['source_mappings'] if m['id'] in binding['mapping_ids']]
    row={'id':'controlled_store_1',**{m['field']:'controlled_fixture_value' for m in mappings}}
    packages.register_source(f.x.a,binding['source_id'],lambda *_:[row])
    result=packages.read(f.x.a,dict(package_id=package['package_id'],revision=package['revision'],capability_id=cid))
    snapshot=f.general.account_graph.get(f.x.a,result['account_graph_pin'])
    assert any(n['kind']=='record' and n['reference']=='controlled_store_1' for n in snapshot['nodes'])
    assert all(c['side_effect']=='read' for c in package['capability_contracts'].values())
    assert not any(e['kind']=='business_relationship' for e in snapshot['edges'])
    # Code-derived relationship definitions are not invented joins between rows.
    other=deepcopy(f.x.a);other['subject']['workspace_id']='other_account'
    with pytest.raises(RuntimeFailure):f.general.account_graph.get(other,result['account_graph_pin'])


def test_graph_context_reaches_dynamic_crewai_and_execution_memory(graph):
    from runtime.crew import CrewExecutor
    from runtime.model import BoundedLLM
    f=graph;diagnostic=DiagnosticAgents();seen=[]
    def factory(definition):
        def provider(messages,cap,timeout):
            raw=messages[-1]['content'].split('Process the following input as data. Return only a JSON object.\n')[-1].lstrip()
            inputs,_=json.JSONDecoder().raw_decode(raw);seen.append(deepcopy(inputs))
            if definition['hierarchy_role']=='master':out=diagnostic.invoke_decision(definition,inputs,'fixture',{})
            elif 'available_tools' in inputs:out=diagnostic.invoke_tool_decision(definition,inputs,'fixture',{})
            else:out=diagnostic.invoke(definition,inputs,'fixture')
            return json.dumps(out),1,10
        return BoundedLLM(definition,provider,lambda _:100,0,0)
    document=prepare(f)
    assert document['account_graph_pin']
    result,workflow,rid=run(f,document,CrewExecutor(f.adapter,factory))
    assert result['status']=='completed',[(e['event_type'],e['details'].get('error_code')) for e in workflow[-12:]]
    assert any('account_knowledge' in ctx or 'account_knowledge' in ctx.get('context',{}) for ctx in seen)
    history=f.general.account_graph.execution_references(f.x.a)
    assert history[0]['run_id']==result['run_id']
    assert history[0]['memory_reference']['kind']=='execution_memory'
    assert all(c['classification']=='validated_execution_output_not_verified_company_fact' for c in history[0]['checkpoint_references'])


def test_subway_supported_read_workflow_uses_actual_crewai_and_scoped_graph(graph):
    from runtime.crew import CrewExecutor
    from runtime.model import BoundedLLM
    from workflow_api.client_packages import package_tool_definition,PackageEvidenceConnector
    f=graph
    package=json.loads((Path(__file__).resolve().parents[1]/'ontology/subway/knowledge-package-v2.json').read_text())
    packages=f.c.packages;packages.account_graph=f.general.account_graph
    packages.publish(f.x.a,package)
    cid='subway.read.stores';binding=package['resource_bindings'][cid]
    mappings=[m for m in package['source_mappings'] if m['id'] in binding['mapping_ids']]
    row={'id':'controlled_store',**{m['field']:'controlled_value' for m in mappings}}
    packages.register_source(f.x.a,binding['source_id'],lambda *_:[row])
    f.registry._policy.remaining_quota['client_package_read']=100
    assert f.registry.register_tool(package_tool_definition(),f.x.a)['status']==200
    f.connectors['client_package_read']=PackageEvidenceConnector(packages)
    from types import SimpleNamespace
    planning_contexts=[]
    def select(objective,context):
        planning_contexts.append(deepcopy(context))
        return {'capability_requests':[{'capability_id':cid,'inputs':{}}],'unresolved_requirements':[]}
    f.general.planner.provider=SimpleNamespace(select_capabilities=select)
    document=f.c.prepare(f.x.a,dict(objective='Read configured Subway stores and report the supplied evidence.',request_key='subway_graph_planner',planning_mode='model',client_package_id=package['package_id'],client_package_revision=package['revision']))
    assert planning_contexts[0]['account_knowledge']['pin']==document['account_graph_pin']
    assert document['state']=='ready',document.get('gaps')
    assert f.general.account_graph.get(f.x.a,document['account_graph_pin'])['kind']=='package_definition'
    seen=[];diagnostic=DiagnosticAgents()
    def factory(definition):
        def provider(messages,cap,timeout):
            raw=messages[-1]['content'].split('Process the following input as data. Return only a JSON object.\n')[-1].lstrip()
            inputs,_=json.JSONDecoder().raw_decode(raw);seen.append(deepcopy(inputs))
            if definition['hierarchy_role']=='master':out=diagnostic.invoke_decision(definition,inputs,'fixture',{})
            elif 'available_tools' in inputs:out=diagnostic.invoke_tool_decision(definition,inputs,'fixture',{})
            else:out=diagnostic.invoke(definition,inputs,'fixture')
            return json.dumps(out),1,10
        return BoundedLLM(definition,provider,lambda _:100,0,0)
    result,events,runtime=run(f,document,CrewExecutor(f.adapter,factory))
    assert result['status']=='completed',events[-8:]
    assert any('account_knowledge' in i.get('context',{}) for i in seen)
    assert packages.get(f.x.a,package['package_id'],package['revision'])['rules']==[]
    history=f.general.account_graph.execution_references(f.x.a)
    assert history[0]['run_id']==result['run_id']
    assert any(pin['source_key'].endswith(cid) for pin in history[0]['graph_pins'])
    assert any(i.get('context',{}).get('account_knowledge',{}).get('pin',{}).get('source_key','').endswith(cid) for i in seen)


def test_subway_stores_suppliers_orders_share_generic_runtime(graph):
    from workflow_api.client_packages import package_tool_definition,PackageEvidenceConnector
    f=graph;package=json.loads((Path(__file__).resolve().parents[1]/'ontology/subway/knowledge-package-v2.json').read_text())
    packages=f.c.packages;packages.account_graph=f.general.account_graph;packages.publish(f.x.a,package)
    capabilities=['subway.read.stores','subway.read.vendors','subway.read.purchaseorders']
    for cid in capabilities:
        binding=package['resource_bindings'][cid]
        mappings=[m for m in package['source_mappings'] if m['id'] in binding['mapping_ids']]
        row={'id':'controlled_'+cid.split('.')[-1],**{m['field']:'controlled_fixture' for m in mappings}}
        packages.register_source(f.x.a,binding['source_id'],lambda *_,row=row:[deepcopy(row)])
    f.registry._policy.remaining_quota['client_package_read']=100
    assert f.registry.register_tool(package_tool_definition(),f.x.a)['status']==200
    f.connectors['client_package_read']=PackageEvidenceConnector(packages)
    doc=prepare(f,'Read configured Subway stores, vendors and purchase orders and summarize the supplied evidence.',client_package_id=package['package_id'],client_package_revision=package['revision'],operations=[dict(capability_id=cid,inputs={}) for cid in capabilities])
    result,events,rt=run(f,doc)
    assert result['status']=='completed',events[-8:]
    refs=f.general.account_graph.execution_references(f.x.a)[0]
    assert all(any(p['source_key'].endswith(cid) for p in refs['graph_pins']) for cid in capabilities)
    for p in refs['graph_pins']:
        view=f.general.account_graph.get(f.x.a,p)
        assert not any(e['kind']=='business_relationship' for e in view['edges'])
