from copy import deepcopy
import json
from types import SimpleNamespace
from unittest.mock import patch
import httpx
import pytest
from openai import APITimeoutError,APIConnectionError,APIStatusError
from runtime.model import OpenAIModelFactory
from runtime.report_evidence import compact,expand
from runtime.recovery import classify
from runtime.service import RuntimeFailure
from workflow_api.investigation_agents import definition
from workflow_api.composition_presentation import CompositionPresentation


def test_compaction_roundtrip_retains_every_rule_and_conflicting_value():
    provenance={'source_id':'source-a','quote':'Company source record. '*100}
    data={'report':{'results':[{'rule_id':f'rule-{n}','outcome':'FAIL' if n%2 else 'PASS','provenance':deepcopy(provenance),'amount':'9007199254740993.123'} for n in range(150)],'missing':['approval date'],'coverage':{'has_more':True}},'foreign':{'$provenance_ref':'untrusted'}}
    before=deepcopy(data);packet=compact(data)
    assert expand(packet)==data==before
    assert len(json.dumps(packet))<len(json.dumps(data))*.25
    assert len(expand(packet)['report']['results'])==150
    assert compact({'ordinary':'no evidence'})=={'ordinary':'no evidence'}


@pytest.mark.parametrize('failure,code',[
 ('timeout','MODEL_PROVIDER_TIMEOUT'),('connection','MODEL_PROVIDER_CONNECTION'),
 (401,'MODEL_PROVIDER_AUTH'),(403,'MODEL_PROVIDER_AUTH'),(429,'MODEL_PROVIDER_RATE_LIMIT'),
 (500,'MODEL_PROVIDER_UNAVAILABLE'),(400,'MODEL_REQUEST_REJECTED'),('unknown','MODEL_INVOCATION_FAILED')])
def test_model_failures_are_typed_private_and_never_repeat_delivery(failure,code):
    request=httpx.Request('POST','https://provider.invalid/responses')
    exc=(APITimeoutError(request=request) if failure=='timeout' else
         APIConnectionError(request=request,message='private provider message') if failure=='connection' else
         APIStatusError('private provider message',response=httpx.Response(failure,request=request),body={'private':'payload'}) if isinstance(failure,int) else
         AttributeError('private provider message'))
    calls=[]
    class Client:
        def with_options(self,**kw):return self
        @property
        def responses(self):return self
        def create(self,**kw):calls.append(kw);raise exc
    with patch('tiktoken.encoding_for_model',return_value=SimpleNamespace(encode=lambda _: [0])):
        llm=OpenAIModelFactory({'fixture':dict(input_per_token=0,output_per_token=0)},Client(),token_policy='provider')(definition('prepare_summary','fixture'))
        with pytest.raises(RuntimeFailure) as caught:llm.call([{'role':'user','content':'Evidence'}])
    assert caught.value.code==code and len(calls)==1
    assert 'private' not in json.dumps(caught.value.model_diagnostic)
    assert caught.value.model_diagnostic['exception_type']==type(exc).__name__
    classified=classify(code,external_write=True)
    assert classified['category']=='model_service_failure' and not classified['retry_eligible']
    view=CompositionPresentation.recovery_view(dict(status='blocked',error_code=code,node_states={}),dict(nodes=[]),0)
    assert 'model service' in view['reason'] and 'authorization issue' not in view['reason'] and not view['eligible']
