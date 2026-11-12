"""Strict provider structure, lossless evidence values and safe rejection."""
from copy import deepcopy
import json
from types import SimpleNamespace
import pytest
from jsonschema import Draft202012Validator
from planner.evaluator_protocol import transport_schema, bind_context, encode, decode
from planner.errors import PlannerFailure
from planner.provider import OpenAIStructuredOutputProvider
from workflow_api.workflow_adaptive import CONTRACT, evidence_preview
from tests.test_subway_autonomy import decision


def assessment():
    return decision(dict(completed_actions=[],plan=dict(actions=[dict(action_id='read',depends_on=[])]),
                         evidence={},original_objective='Review available records.'))


@pytest.mark.parametrize('value',[None,False,17,1.25,'100','a "quoted" value',[],{},[{'x':None,'y':1}]])
def test_strict_transport_preserves_exact_evidence_types(value):
    result=assessment()
    result['assessment']['findings']=[dict(evidence_id='evidence:test',path=['rows',0,'value'],value=value,classification='observation')]
    wire_schema=transport_schema(CONTRACT)
    wire=encode(result,CONTRACT)
    assert not list(Draft202012Validator(wire_schema).iter_errors(wire))
    assert decode(SimpleNamespace(status='completed',output_text=json.dumps(wire)),CONTRACT,wire_schema)==result


def test_every_transport_object_is_closed_and_all_properties_required():
    def check(value):
        if isinstance(value,dict):
            if value.get('type')=='object':
                assert value['additionalProperties'] is False
                assert set(value['properties'])==set(value['required'])
            for child in value.values():check(child)
        elif isinstance(value,list):
            for child in value:check(child)
    check(transport_schema(CONTRACT))


def test_transport_constrains_exact_goal_and_frozen_requirement_identities():
    result = assessment()
    frozen = [{k: v for k, v in result['assessment']['requirements'][0].items() if k in ('id','description')}]
    wire_schema = bind_context(transport_schema(CONTRACT), dict(
        original_objective=result['assessment']['objective'], frozen_requirements=frozen))
    wire = encode(result, CONTRACT)
    validator = Draft202012Validator(wire_schema)
    assert not list(validator.iter_errors(wire))
    wrong = deepcopy(wire)
    wrong['assessment']['objective'] = 'Paraphrased goal'
    assert list(validator.iter_errors(wrong))
    wrong = deepcopy(wire)
    wrong['assessment']['requirements'][0]['description'] = 'Changed requirement'
    assert list(validator.iter_errors(wrong))
    wrong = deepcopy(wire)
    wrong['assessment']['requirements'].append(deepcopy(wrong['assessment']['requirements'][0]))
    assert list(validator.iter_errors(wrong))


@pytest.mark.parametrize('stage',['response','incomplete','transport','encoded_value','canonical'])
def test_invalid_decisions_fail_without_raw_content_or_extra_calls(stage):
    wire=encode(assessment(),CONTRACT)
    status='completed'
    if stage=='transport':wire['decision']='private-invalid-value'
    if stage=='encoded_value':wire['proposal']='private-not-json'
    if stage=='canonical':wire['proposal']='17'
    if stage=='incomplete':status='incomplete'
    response=SimpleNamespace(status=status,output_text='private-not-json' if stage=='response' else json.dumps(wire))
    with pytest.raises(PlannerFailure) as caught:decode(response,CONTRACT,transport_schema(CONTRACT))
    assert caught.value.code=='ADAPTIVE_DECISION_INVALID'
    assert caught.value.details==dict(validation_stage=stage)
    assert 'private' not in str(caught.value.envelope('test'))


def test_provider_requests_schema_enforcement_without_hidden_retry():
    calls=[];result=assessment()
    def create(**kwargs):
        calls.append(kwargs)
        assert kwargs['text']['format']['type']=='json_schema'
        assert kwargs['text']['format']['strict'] is True
        return SimpleNamespace(status='completed',output_text=json.dumps(encode(result,CONTRACT)))
    provider=OpenAIStructuredOutputProvider(SimpleNamespace(responses=SimpleNamespace(create=create)))
    assert provider.evaluate_actions(dict(evaluation_kind='workflow-investigation'),max_output_tokens=6000)==result
    assert len(calls)==1 and calls[0]['max_output_tokens']==6000


def test_query_metadata_survives_sorted_keys_and_nested_freshness():
    output={f'a{i}':i for i in range(12)}
    output.update(query_id='synthetic',coverage=dict(complete_scan=True,aggregate_complete=True,matched_records=100),
        scope=dict(owner_id='synthetic'),sources=[dict(freshness=dict(status='historical_snapshot',detail=dict(synced_at=None)))],
        rows=[dict(count=i) for i in range(7)])
    preview=evidence_preview(json.loads(json.dumps(output,sort_keys=True)))
    assert preview['sources']==output['sources'] and preview['coverage']==output['coverage'] and preview['scope']==output['scope']
    assert set(preview)==set(output) and 'row_preview' not in preview
    assert len(preview['rows'])==4 and len(output['rows'])==7
