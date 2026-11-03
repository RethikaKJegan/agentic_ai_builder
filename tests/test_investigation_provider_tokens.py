from copy import deepcopy
import json
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from runtime.model import BoundedLLM,OpenAIModelFactory
from runtime.service import RuntimeFailure
from workflow_api.investigation_agents import InvestigationAgents,definition
from workflow_api.investigation_graph import requirements,template
from workflow_api.investigation_planning import InvestigationPlanner


def context():
    return dict(records=[dict(record_id='native-1',values={'mapping:symptom':{'state':'known','value':'reported '*12000}})],citation_catalog=[dict(record_id='native-1',mapping_id='mapping:symptom')],task_requirements=[],missing=[])


def test_provider_managed_tokens_have_no_application_input_output_or_cost_ceiling():
    calls=[];d=definition('prepare_summary','fixture');d['limits'].update(max_tokens=1,max_estimated_cost_usd=0)
    def provider(messages,cap,timeout):
        calls.append(cap)
        return json.dumps(dict(summary='Complete.',findings=[],missing_information=[])),50000,80000
    model=BoundedLLM(d,provider,lambda _:70000,1,1,token_policy='provider')
    model.call([{'role':'user','content':'Evidence'}])
    assert calls==[None]
    assert model.actual_usage==dict(llm_calls=1,tokens=130000,estimated_cost_usd=130000)
    with pytest.raises(RuntimeFailure):model.call('Unauthorized second call')
    assert calls==[None]


@pytest.mark.parametrize('capability,incomplete', [('prepare_summary',False),('prepare_summary',True),('compare_inspection',True)])
def test_actual_crewai_provider_requests_omit_max_output_and_meter_large_or_incomplete_results(capability,incomplete):
    calls=[];original=context();before=deepcopy(original)
    class Client:
        def with_options(self,**kwargs):return self
        @property
        def responses(self):return self
        def create(self,**kwargs):
            calls.append(kwargs)
            return SimpleNamespace(status='incomplete' if incomplete else 'completed',output_text='partial untrusted provider text' if incomplete else json.dumps(dict(summary='Reported observations reviewed.',findings=[],missing_information=[])),usage=SimpleNamespace(input_tokens=50000,output_tokens=80000))
    with patch('tiktoken.encoding_for_model',return_value=SimpleNamespace(encode=lambda _:list(range(30000)))):
        # Even an injected bounded factory is explicitly opted in by the
        # investigation boundary. Unrelated agents retain the default policy.
        factory=OpenAIModelFactory({'fixture':dict(input_per_token=1,output_per_token=1)},Client())
        agents=InvestigationAgents(model_factory=factory,model_id='fixture')
        if incomplete and capability!='prepare_summary':
            with pytest.raises(RuntimeFailure) as caught:agents.run(capability,original)
            assert caught.value.code=='MODEL_OUTPUT_TRUNCATED'
            assert caught.value.usage['tokens']==130000
        else:
            result,usage=agents.run(capability,original)
            assert usage==dict(llm_calls=1,tokens=130000,estimated_cost_usd=130000)
            if incomplete:
                assert result['classification']=='backend_evidence_compilation'
                assert result['mode']=='evidence_only' and result['findings']==[]
                assert 'partial untrusted' not in json.dumps(result)
            else:assert result['mode']=='crewai'
    assert original==before and len(calls)==1
    assert 'max_output_tokens' not in calls[0]
    assert calls[0]['store'] is False and calls[0]['text']['format']['strict'] is True


def test_default_runtime_token_and_cost_limits_still_apply():
    d=definition('prepare_summary','fixture');d['limits']['max_tokens']=1;calls=[]
    model=BoundedLLM(d,lambda *a:calls.append(a),lambda _:1000,0,0)
    with pytest.raises(RuntimeFailure):model.call('Data')
    assert not calls


def test_content_filter_is_not_misreported_as_token_truncation():
    class Client:
        def with_options(self,**kwargs):return self
        @property
        def responses(self):return self
        def create(self,**kwargs):
            return SimpleNamespace(status='incomplete',incomplete_details=SimpleNamespace(reason='content_filter'),usage=SimpleNamespace(input_tokens=20,output_tokens=10))
    with patch('tiktoken.encoding_for_model',return_value=SimpleNamespace(encode=lambda _:[0]*10)):
        model=OpenAIModelFactory({'fixture':dict(input_per_token=0,output_per_token=0)},Client(),token_policy='provider')(definition('prepare_summary','fixture'))
        with pytest.raises(RuntimeFailure) as caught:model.call([{'role':'user','content':'Evidence'}])
    assert caught.value.code=='MODEL_OUTPUT_CONTENT_FILTER'
    assert caught.value.usage['llm_calls']==1 and caught.value.usage['tokens']==30


def test_planning_omits_max_output_tokens_and_keeps_strict_schema():
    calls=[];graph=template(requirements('Compare complaint C123 with inspection.'))
    class Client:
        def __init__(self,**kwargs):pass
        @property
        def responses(self):return self
        def create(self,**kwargs):calls.append(kwargs);return SimpleNamespace(output_text=json.dumps(graph))
    with patch('openai.OpenAI',Client):
        assert InvestigationPlanner({'OPENAI_API_KEY':'fixture','OPENAI_MODEL':'fixture'}).generate({})==graph
    assert 'max_output_tokens' not in calls[0]
    assert calls[0]['store'] is False and calls[0]['text']['format']['strict'] is True
