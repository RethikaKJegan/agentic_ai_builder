"""Canonical query handoff fixes one known envelope, without value coercion."""
from copy import deepcopy
import pytest
from workflow_api.goal_inputs import normalize_query_envelopes
from workflow_api.workflow_queries import INPUT


def fixture():
    contracts={
        'data.plan_query':{'output_schema':deepcopy(INPUT)},
        'tool.workflow_data_query':{'input_schema':deepcopy(INPUT)}}
    parent={'action_id':'plan','capability_id':'data.plan_query'}
    binding={'kind':'output','action_id':'plan','path':[],'target':['query']}
    read={'action_id':'read','capability_id':'tool.workflow_data_query','depends_on':['plan'],'bindings':[binding]}
    return [parent,read],contracts,binding


def test_known_envelope_is_normalized_idempotently_without_other_changes():
    actions,contracts,binding=fixture();before=deepcopy(actions)
    for _ in range(2):normalize_query_envelopes(actions,contracts,{a['action_id']:a for a in actions})
    before[1]['bindings'][0]['path']=['query']
    assert actions==before


@pytest.mark.parametrize('variant',['producer','consumer','kind','path','target','dependency','schema','optional_query'])
def test_other_bindings_are_never_reinterpreted(variant):
    actions,contracts,binding=fixture()
    if variant=='producer':actions[0]['capability_id']='content.prepare'
    elif variant=='consumer':actions[1]['capability_id']='tool.other'
    elif variant=='kind':binding['kind']='receipt'
    elif variant=='path':binding['path']=['other']
    elif variant=='target':binding['target']=['to']
    elif variant=='dependency':actions[1]['depends_on']=[]
    elif variant=='schema':contracts['data.plan_query']['output_schema']['properties']['query']={'type':'string'}
    elif variant=='optional_query':contracts['data.plan_query']['output_schema']['required']=[]
    before=deepcopy(actions)
    normalize_query_envelopes(actions,contracts,{a['action_id']:a for a in actions})
    assert actions==before
