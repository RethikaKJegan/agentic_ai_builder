"""Budget regression for delegated database queries; no external providers."""
from copy import deepcopy
import pytest
from workflow_api.database_budgets import normalize, validate, TOOL_UNITS
from workflow_api.database_workflows import DatabaseConnector, bounded_agent_reference
from workflow_api.service import ApiFailure


def draft():
    limits = dict(max_tool_calls=1, max_llm_calls=3, max_tokens=12000,
                  max_retries=0, timeout_seconds=300, max_estimated_cost_usd=.15)
    return dict(agents=[dict(agent_id='reader', hierarchy_role='sub_agent',
                capabilities=['database.read_query'], permissions=['data.read'], limits=limits)],
                nodes=[], tools=[dict(tool_id='database_read_query')],
                execution_policy=dict(allow_external_writes=False, limits=deepcopy(limits)), metadata={})


def test_failed_proposal_gets_finite_query_and_result_capacity():
    w = draft()
    with pytest.raises(ApiFailure, match='reservation'):
        validate(w)
    normalize(w)
    validate(w)
    assert w['agents'][0]['limits']['max_tool_calls'] == 4
    assert w['agents'][0]['limits']['max_tokens'] == 20000
    assert w['agents'][0]['permissions'] == ['data.read']
    assert w['execution_policy']['allow_external_writes'] is False
    assert w['agents'][0]['limits']['max_estimated_cost_usd'] == .15
    assert w['agents'][0]['limits']['timeout_seconds'] == 300
    prior = deepcopy(w)
    normalize(w)
    assert w == prior


def test_constants_match_actual_connector_reservations():
    for tool, units in TOOL_UNITS.items():
        assert DatabaseConnector(None, tool).reservation({})['tool_calls'] == units


def test_no_consumption_turn_and_undersized_workflow_rejected():
    w = draft(); normalize(w)
    w['agents'][0]['limits']['max_llm_calls'] = 1
    with pytest.raises(ApiFailure, match='consume'):
        validate(w)
    w['agents'][0]['limits']['max_llm_calls'] = 2
    w['execution_policy']['limits']['max_tool_calls'] = 3
    with pytest.raises(ApiFailure, match='Workflow tool allowance'):
        validate(w)


def test_coordinator_keeps_source_identity_without_duplicate_field_catalog():
    import json
    ref = dict(sources=[dict(dataset_id='db1', fields=[dict(field_id='f1', name='complaint_id')])])
    actual = json.loads(bounded_agent_reference(ref, dict(hierarchy_role='master',capabilities=['generate_report'])))
    assert actual['sources'] == [dict(dataset_id='db1', fields=[])]
    assert not actual['metadata_coverage']['complete']
    assert ref['sources'][0]['fields']


def test_executable_query_schema_rejects_operating_notes_in_clarification():
    from jsonschema import Draft202012Validator
    from workflow_api.database_workflows import schema
    plan = dict(base_dataset_id='d', joins=[], fields=['f'], filters=[], group_by=[],
                metrics=[], order_by=[], limit=5, explanation='Read only.', clarification='')
    checker = Draft202012Validator(schema('query_input'))
    assert not list(checker.iter_errors({'plan':plan}))
    plan['clarification'] = 'Read-only retrieval; no joins or modifications.'
    assert list(checker.iter_errors({'plan':plan}))


def test_queryable_paths_and_numeric_domain_remain_strict():
    from workflow_api.data_queries import queryable_field, query_types, mongo_scalar_path
    assert queryable_field(dict(name='complaint.symptom',types=['string']), 'mongodb')
    assert not queryable_field(dict(name='complaint.symptom',types=['string']), 'postgresql')
    for name in ('x.$where', 'x[].name', 'x..name', 'x.\x00name'):
        assert not queryable_field(dict(name=name,types=['string']), 'mongodb')
    assert query_types(dict(types=['integer','number'])) == {'number'}
    assert not queryable_field(dict(name='value',types=['integer','string']), 'mongodb')
    assert mongo_scalar_path({'inspection':{'checked':False}}, 'inspection.checked') is False
    assert mongo_scalar_path({}, 'inspection.checked') is None
    with pytest.raises(ApiFailure):
        mongo_scalar_path({'inspection':[{'checked':True}]}, 'inspection.checked')


def test_repacking_preserves_identity_candidates_and_task_text_without_promoting_links():
    import json
    fields=[dict(field_id='serial',name='engineSerialNumber',types=['string']),
            dict(field_id='description',name='complaintDescription',types=['string'])]
    fields += [dict(field_id='flag'+str(i), name='checkList.engineCondition.section'+str(i)+'.checked', types=['boolean']) for i in range(100)]
    ref=dict(sources=[dict(dataset_id='db1',fields=fields,identity_fields=[],writable_fields=[],operations=['query'])],relationships=[],business_relationships=[],business_mappings=[])
    agent=dict(hierarchy_role='sub_agent',capabilities=['database.read_query'],role='Engine evidence',goal='Retrieve serial identifiers and complaint description',instructions='Read serial number and complaint description.\nDatabase reference metadata: '+json.dumps(ref))
    packed=json.loads(bounded_agent_reference(ref,agent,maximum=2200))
    ids={f['field_id'] for f in packed['sources'][0]['fields']}
    assert {'serial','description'}<=ids
    assert not packed['sources'][0]['identity_fields']
    assert not packed['relationships']
    assert packed['metadata_coverage']['included_fields']<len(fields)


def test_read_only_synthesis_is_qualified_exact_and_does_not_change_originals():
    from runtime.delegation import read_only_synthesis_view
    w=draft();w['metadata']['database_scope']={'sources':[]}
    original=[{'result':{'records':[{'id':i,'flag':False,'missing':None} for i in range(10)],
                         'sources':[{'dataset_id':'d'+str(i),'total_rows':9000} for i in range(4)],
                         'limitations':['Only ten records were read.']}}]
    expected=deepcopy(original)
    view=read_only_synthesis_view(w,original)
    assert original==expected
    assert view[0]['result']['records']==original[0]['result']['records'][:3]
    assert view[0]['result']['sources']==original[0]['result']['sources']
    assert view[0]['result']['limitations']==original[0]['result']['limitations']
    assert view[0]['synthesis_view']['fields']['records']=={'original_items':10,'included_items':3}
    w['execution_policy']['allow_external_writes']=True
    assert read_only_synthesis_view(w,original)==original


def test_truncated_pure_model_turn_receives_only_one_concise_correction():
    from shared.llm_feedback import correct_once
    from runtime.service import RuntimeFailure
    calls=[];reserved=[]
    def model(feedback):
        calls.append(feedback)
        if not feedback:raise RuntimeFailure('MODEL_OUTPUT_TRUNCATED','Incomplete model output.')
        assert 'concise' in feedback['hint']
        return {'summary':'Complete concise summary.'}
    assert correct_once(model,lambda item:reserved.append(item))=={'summary':'Complete concise summary.'}
    assert len(calls)==2 and len(reserved)==1
    calls.clear()
    def always_incomplete(feedback):
        calls.append(feedback)
        raise RuntimeFailure('MODEL_OUTPUT_TRUNCATED','Incomplete model output.')
    with pytest.raises(RuntimeFailure):correct_once(always_incomplete,lambda item:True)
    assert len(calls)==2
