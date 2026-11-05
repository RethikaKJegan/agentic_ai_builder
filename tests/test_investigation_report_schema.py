from copy import deepcopy
import json
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from runtime.model import OpenAIModelFactory
from runtime.service import RuntimeFailure
from workflow_api.investigation_agents import InvestigationAgents, definition
from workflow_api.investigation_graph import requirements, template


@pytest.mark.parametrize('negative', [
    'Do not assess warranty.', "Don't assess warranty.", 'Without warranty assessment.',
    'Do not check coverage or eligibility.', 'Must not assess warranty.',
])
def test_explicit_excluded_warranty_does_not_select_warranty(negative):
    req=requirements('Compare complaint C123 with its inspection. '+negative)
    assert req['inspection'] and not req['warranty']
    assert not {'retrieve_warranty','warranty_readiness'}.intersection(n['capability'] for n in template(req)['nodes'])


def test_positive_clause_after_negative_is_preserved():
    req=requirements('Review complaint C123 without replacement but check warranty readiness.')
    assert req['warranty'] and not req['replacement']


@pytest.mark.parametrize('invalid', [False,True])
def test_actual_crewai_requests_exact_strict_analysis_schema_without_retry(invalid):
    calls=[];tokenized=[]
    class Client:
        def with_options(self,**kwargs):return self
        @property
        def responses(self):return self
        def create(self,**kwargs):
            calls.append(deepcopy(kwargs))
            output=dict(summary='Source-backed review.',findings=[dict(kind='observation',statement='Recorded symptom.',references=[dict(record_id='native-1',mapping_id='mapping:symptom')])],missing_information=[])
            if invalid:output['findings'][0]['references'][0]['record_id']='invented'
            return SimpleNamespace(output_text=json.dumps(output),usage=SimpleNamespace(input_tokens=10,output_tokens=20))
    context=dict(records=[dict(record_id='native-1',values={'mapping:symptom':'Observed'})],citation_catalog=[dict(record_id='native-1',mapping_id='mapping:symptom')],task_requirements=[],missing=[])
    def encode(value):tokenized.append(value);return [0]*10
    with patch('tiktoken.encoding_for_model',return_value=SimpleNamespace(encode=encode)):
        factory=OpenAIModelFactory({'gpt-5':{'input_per_token':0,'output_per_token':0}},Client())
        agents=InvestigationAgents(model_factory=factory,model_id='gpt-5')
        if invalid:
            with pytest.raises(RuntimeFailure) as caught:agents.run('prepare_summary',context)
            assert caught.value.code=='MODEL_OUTPUT_SCHEMA_INVALID'
            assert caught.value.validation_field
        else:
            output,usage=agents.run('prepare_summary',context)
            assert output['findings'][0]['references'][0]['record_id']=='native-1'
            assert usage['llm_calls']==1
    assert len(calls)==1 and calls[0]['store'] is False
    fmt=calls[0]['text']['format']
    assert fmt['type']=='json_schema' and fmt['strict'] is True
    reference=fmt['schema']['properties']['findings']['items']['anyOf'][0]['properties']['references']['items']['anyOf'][0]['properties']
    assert reference['record_id']['const']=='native-1'
    assert reference['mapping_id']['enum']==['mapping:symptom']
    assert any('investigation_analysis' in value and 'json_schema' in value for value in tokenized)


def test_plain_model_factory_keeps_existing_format():
    d=definition('prepare_summary','gpt-5')
    # Strict transport is opt-in; existing control protocols and unrelated agents
    # retain their current behavior.
    from runtime.model import BoundedLLM
    model=BoundedLLM(d,lambda *args:('',0,0),lambda _:1,0,0)
    assert model.structured_format is None and model.control_format is None
