from copy import deepcopy
import pytest
from jsonschema import Draft202012Validator
from runtime.crew import scoped_query_schema
from runtime.action_plans import validate_content
from workflow_api.workflow_queries import INPUT
from tests.test_data_queries import plan


def catalog():
 return dict(datasets=[dict(dataset_id='one',fields=[dict(field_id='one_note',types=['string'])]),dict(dataset_id='two',fields=[dict(field_id='two_note',types=['string'])])],relationships=[])


def definition():return dict(output_schema=deepcopy(INPUT))


def test_cross_source_projection_is_prevented_without_choosing_a_source():
 schema=scoped_query_schema(definition(),{'context':{'data_query_catalog':catalog()}})
 q=plan();q.update(base_dataset_id='one',fields=['one_note'],metrics=[])
 assert not list(Draft202012Validator(schema).iter_errors({'query':q}))
 q['fields']=['two_note'];assert list(Draft202012Validator(schema).iter_errors({'query':q}))
 q.update(base_dataset_id='two');assert not list(Draft202012Validator(schema).iter_errors({'query':q}))
 assert definition()['output_schema']==INPUT


def test_clarification_and_count_remain_supported():
 schema=scoped_query_schema(definition(),{'context':{'data_query_catalog':catalog()}});v=Draft202012Validator(schema)
 q=plan();q.update(base_dataset_id='',fields=[],metrics=[],clarification='An exact unsupported query cannot execute.')
 assert not list(v.iter_errors({'query':q}))
 q.update(base_dataset_id='one',clarification='',metrics=[dict(label='count',op='count',expression='')])
 assert not list(v.iter_errors({'query':q}))


@pytest.mark.parametrize('kind',['relationships','large','empty','other_catalog'])
def test_unsupported_schema_specialization_retains_existing_contract(kind):
 c=catalog()
 if kind=='relationships':c['relationships']=[{'relationship_id':'reviewed'}]
 elif kind=='large':c['datasets'][0]['fields']=[{'field_id':str(i)} for i in range(701)]
 elif kind=='empty':c['datasets']=[]
 inputs={'context':{'data_query_catalog':c}} if kind!='other_catalog' else {'context':{'subway_query_catalog':c}}
 assert scoped_query_schema(definition(),inputs)==INPUT


def test_correction_feedback_preserves_precise_rule_without_model_prose():
 q=plan();q.update(base_dataset_id='one',fields=['two_note'],metrics=[],explanation='UNTRUSTED SECRET PROSE')
 workflow={'metadata':{'connected_action_plan':{'actions':[{'action_id':'query','capability_id':'data.plan_query'}]}}}
 with pytest.raises(Exception) as err:validate_content(workflow,{'node_id':'query'},{'query':q},{'context':{'data_query_catalog':catalog()}})
 assert err.value.code=='AGENT_OUTPUT_INVALID'
 assert 'Plan references an unavailable field.' in err.value.validation_hint
 assert 'UNTRUSTED' not in err.value.validation_hint and len(err.value.validation_hint)<=400
