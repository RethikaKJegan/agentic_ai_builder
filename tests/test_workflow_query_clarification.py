"""Clarifications block safely before reads and remain visible across restart/history."""
from copy import deepcopy
import json
import pytest
from tests.test_workflow_query_integration import (automation,google_setup,connected,composition,investigation,retrieval,knowledge,reference,generation,foundation,auth,release,queries,setup_query,compile_run,stored)
from tests.test_data_queries import plan
from workflow_api.composition_presentation import CompositionPresentation
from runtime import RuntimeService
from runtime.graph import GraphRunner
from runtime.recovery import node_external_write

QUESTION='Which recorded hours field and unit define operating hours for complaints?'


@pytest.mark.parametrize('historical',[False,True])
def test_query_clarification_is_visible_without_reads_writes_or_replay(automation,queries,historical):
    f=automation;p=plan();p['clarification']=QUESTION
    jobs,_,_,body=setup_query(f,queries,p)
    doc,w,rid=compile_run(f,body)
    result=f.runner.advance(rid,f.x.a)
    assert result['status']=='blocked'
    saved=stored(f,rid)
    assert saved['action_instances']['read']['state']=='needs_input'
    assert saved['action_instances']['read']['clarification']==QUESTION
    assert saved['action_instances']['read']['external_effect_status']=='not_performed'
    assert not queries.reader.calls and not jobs.list(f.x.a)['items']
    assert not f.http.sent and f.http.write_count==0
    assert saved['action_instances']['sheet']['state']=='pending'
    if historical:
        with f.runtime.store.transaction() as db:
            old=f.runtime.load(db,rid,f.x.a);old['status']='failed';old['node_states']['read']='failed'
            old['action_instances']['read'].update(state='failed',external_effect_status='failed')
            old['action_instances']['read'].pop('clarification',None);f.runtime.save(db,old)
    before=stored(f,rid)
    restarted=RuntimeService(f.general,clock=lambda:f.now)
    f.general.runtime_runner=GraphRunner(restarted,agents=f.runner.agents,connectors=f.connectors)
    ui=CompositionPresentation(f.c)
    view=ui.view(f.x.a,doc['composition_id'],rid)
    query=next(t for t in view['tasks'] if t['id']=='read')
    assert query['state']=='needs_input'
    assert query['result']['missing_information']==[QUESTION]
    assert query['result']['classification']=='query_clarification'
    assert not query['result']['records'] and not query['result']['tool_receipts']
    assert QUESTION in view['recovery']['reason'] and 'Reconcile' not in view['recovery']['reason']
    assert view['recovery']['can_clarify'] and not view['recovery']['eligible']
    assert stored(f,rid)==before # Historical projection never rewrites a run.
    inspection=restarted.recovery.inspect(rid,f.x.a)
    assert not inspection['uncertain_invocations']
    assert f.general.runtime_runner.advance(rid,f.x.a)['status']==before['status']
    assert stored(f,rid)['usage']==before['usage']
    with f.runtime.store.transaction() as db:
        modified=f.runtime.load(db,rid,f.x.a);modified['node_states']['send']='executing';f.runtime.save(db,modified)
    blocked=ui.view(f.x.a,doc['composition_id'],rid)
    assert not blocked['recovery']['can_clarify']
    assert 'Reconcile' in blocked['recovery']['reason']


def test_unknown_legacy_write_tools_remain_fail_closed():
    node=dict(node_id='read',kind='tool',tool_id='unknown')
    legacy=dict(nodes=[node],execution_policy={'allow_external_writes':True})
    assert node_external_write(legacy,node)
    pinned=deepcopy(legacy);pinned['metadata']=dict(connected_action_plan={'actions':[{'action_id':'read','capability_id':'tool.read'}]},connected_contracts={'tool.read':{'side_effect':'read'}})
    assert not node_external_write(pinned,node)
    pinned['metadata']['connected_contracts']['tool.read']['side_effect']='write'
    assert node_external_write(pinned,node)


@pytest.mark.parametrize('value',[None,[],{'actions':None},{'actions':['invalid']}])
def test_untyped_legacy_metadata_cannot_downgrade_write_safety(value):
    node=dict(node_id='read',kind='tool',tool_id='unknown')
    workflow=dict(execution_policy={'allow_external_writes':True},metadata={'connected_action_plan':value,'connected_contracts':None})
    assert node_external_write(workflow,node)
