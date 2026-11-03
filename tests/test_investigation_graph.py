from copy import deepcopy
import pytest
from workflow_api.investigation_graph import requirements,template,validate_graph,predicate,CATALOGUE,GRAPH_SCHEMA
from workflow_api.service import ApiFailure
from runtime.graph import ready_frontier

OBJECTIVE='Investigate complaint C123, compare its linked inspection, check warranty readiness and prepare a report.'

@pytest.mark.parametrize('objective',[
 OBJECTIVE,'Find service issues for motor E123.','Review replacement evidence for complaint C123.',
 'Check warranty evidence for engine E123.','Investigate complaint history for engine E123.',
 'Compare the complaint with its inspection.',
])
def test_generated_structure_has_required_capabilities(objective):
    r=requirements(objective);g=template(r);v=validate_graph(g,r)
    assert v['valid'],v
    caps={n['capability'] for n in g['nodes']}
    assert 'prepare_summary' in caps and 'retrieve_complaint' in caps
    assert ('retrieve_replacement' in caps)==r['replacement']
    assert ('compare_inspection' in caps)==r['inspection']
    assert all(CATALOGUE[c]['read_only'] for c in caps if c)

@pytest.mark.parametrize('mutate,code',[
 (lambda g:g['edges'].append(dict(id='cycle',source='end',target='complaint',outcome=None)),'CYCLE'),
 (lambda g:g['edges'][0].update(target='absent'),'MISSING_NODE_REFERENCE'),
 (lambda g:g['nodes'][2]['inputs'][0].update(type='analysis'),'INPUT_TYPE'),
 (lambda g:g['nodes'][2]['inputs'].clear(),'REQUIRED_INPUTS'),
 (lambda g:g['nodes'][2].update(capability='approve_warranty'),'SCHEMA_INVALID'),
 (lambda g:g['edges'].pop(4),'BRANCH_COVERAGE'),
 (lambda g:g['nodes'][-1]['inputs'][0].update(source='end'),'INPUT_NOT_UPSTREAM'),
 (lambda g:g['nodes'][1].update(output_type='analysis'),'CONTROL_OUTPUT_TYPE'),
])
def test_invalid_graphs_rejected(mutate,code):
    g=template(requirements(OBJECTIVE));mutate(g);r=validate_graph(g,requirements(OBJECTIVE))
    assert not r['valid'] and code in {e['code'] for e in r['errors']},r


def test_unreachable_and_required_capabilities():
    r=requirements(OBJECTIVE);g=template(r)
    g['edges']=[e for e in g['edges'] if e['target']!='warranty']
    assert 'UNREACHABLE_NODE' in {e['code'] for e in validate_graph(g,r)['errors']}
    g=template(requirements('Show complaints for engine E123.'))
    assert 'MISSING_REQUIRED_CAPABILITY' in {e['code'] for e in validate_graph(g,r)['errors']}

@pytest.mark.parametrize('q',['Approve warranty for engine E123.','Delete complaint C123.','Count complaints for engine E123.','Send an email about complaint C123.','Cook a meal'])
def test_unsupported(q):
    with pytest.raises(ApiFailure):requirements(q)


def test_three_valued_conditions_no_activity_inference():
    e=dict(records=[],missing=[],executed_steps=[],physical_engine_identity='unresolved')
    assert predicate('complaint_found',e)=='false'
    assert predicate('identity_supported',e)=='unknown'
    assert predicate('authorization_present',e)=='unknown'
    e['records']=[dict(collection='jointinspectionreports',fields={'status':'PUBLISHED'})]
    assert predicate('inspection_available',e)=='true'
    e['missing']=[{'fact':'inspection_activity_completion_evidence'}]
    assert predicate('assessment_inputs_complete',e)=='unknown'
    e['records']=[];e['executed_steps']=[dict(truncated=True)]
    assert predicate('complaint_found',e)=='unknown'
    assert predicate('evidence_truncated',e)=='true'


def test_frontier_all_incoming_resolved_skips_and_parallel():
    nodes=[dict(node_id=n) for n in ('start','a','b','join')]
    edges=[dict(edge_id='sa',source='start',target='a'),dict(edge_id='sb',source='start',target='b'),dict(edge_id='aj',source='a',target='join'),dict(edge_id='bj',source='b',target='join')]
    ready,skipped=ready_frontier(nodes,edges,{'start':'succeeded'},{'sa':'selected','sb':'selected'})
    assert {n['node_id'] for n in ready}=={'a','b'} and not skipped
    assert not ready_frontier(nodes,edges,{'start':'succeeded','a':'succeeded','b':'running'},{'sa':'selected','sb':'selected','aj':'selected'})[0]
    ready,_=ready_frontier(nodes,edges,{'start':'succeeded','a':'succeeded','b':'skipped'},{'sa':'selected','sb':'skipped','aj':'selected','bj':'skipped'})
    assert [n['node_id'] for n in ready]==['join']


def test_capability_retry_policy_cannot_be_overridden_by_model():
    r=requirements(OBJECTIVE);g=template(r)
    next(n for n in g['nodes'] if n['capability']=='compare_inspection')['constraints']['max_attempts']=2
    assert 'CAPABILITY_RETRY_LIMIT' in {e['code'] for e in validate_graph(g,r)['errors']}


def test_exported_schema_matches_execution_schema():
    import json
    from pathlib import Path
    assert json.loads((Path(__file__).resolve().parents[1]/'workflow_api/schemas/simpson-investigation-v1.json').read_text())==GRAPH_SCHEMA
