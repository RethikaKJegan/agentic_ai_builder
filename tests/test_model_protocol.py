from copy import deepcopy
import json
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from jsonschema import Draft202012Validator
from runtime.delegation import DECISION_SCHEMA, TOOL_DECISION_SCHEMA
from runtime.model import OpenAIModelFactory
from runtime.model_protocol import response_format,decode_response
from runtime.service import RuntimeFailure

ROOT=Path(__file__).resolve().parents[1]


class ControlProtocolTests(unittest.TestCase):
    def test_strict_master_envelope_and_tool_envelope_decode_to_existing_protocol(self):
        context={'available_agents':[{'agent_id':'specialist'}]}
        wire={'decision':{'action':'delegate','reason':'Check facts.','tasks':[{
            'agent_id':'specialist','inputs_json':json.dumps({'reference':'X1'}),'reason':'Check record.'}], 'continuation_json':None}}
        Draft202012Validator(response_format('master',context)['schema']).validate(wire)
        result=json.loads(decode_response(json.dumps(wire)))
        Draft202012Validator(DECISION_SCHEMA).validate(result)
        self.assertEqual(result['tasks'][0]['inputs'],{'reference':'X1'})
        invalid=deepcopy(wire);invalid['decision']['tasks'][0]['agent_id']='unregistered'
        self.assertTrue(list(Draft202012Validator(response_format('master',context)['schema']).iter_errors(invalid)))
        report={'records':[{'arbitrary_column':'actual fact'}]}
        wire={'decision':{'action':'finish','reason':'Report evidence.','output_json':json.dumps(report)}}
        Draft202012Validator(response_format('tool',{'available_tools':[]})['schema']).validate(wire)
        result=json.loads(decode_response(json.dumps(wire)))
        Draft202012Validator(TOOL_DECISION_SCHEMA).validate(result)
        self.assertEqual(result['output'],report)

    def test_invalid_encoded_object_fails_closed(self):
        for value in ('not json','[]','null'):
            with self.subTest(value=value),self.assertRaises(RuntimeFailure):
                decode_response(json.dumps({'decision':{'action':'finish','reason':'Result.','output_json':value}}))

    def test_openai_factory_uses_strict_format_and_returns_decoded_control(self):
        calls=[]
        class Client:
            def with_options(self,**kwargs):return self
            @property
            def responses(self):return self
            def create(self,**kwargs):
                calls.append(kwargs)
                wire={'decision':{'action':'tool','reason':'Read authorized source.','tool_id':'read_records',
                                  'inputs_json':json.dumps({'reference':'X1'})}}
                return SimpleNamespace(output_text=json.dumps(wire),usage=SimpleNamespace(input_tokens=10,output_tokens=20))
        agent=json.loads((ROOT/'shared/contracts/examples/agents/valid-classifier.json').read_text())
        agent['output_schema']=TOOL_DECISION_SCHEMA
        with patch('tiktoken.encoding_for_model',return_value=SimpleNamespace(encode=lambda value:[0]*10)):
            model=OpenAIModelFactory({'gpt-5':{'input_per_token':0,'output_per_token':0}},Client())(agent)
            model.control_format=response_format('tool',{'available_tools':[{'tool_id':'read_records'}]})
            result=model.call([{'role':'user','content':'Check the record.'}])
        self.assertEqual(calls[0]['text']['format']['type'],'json_schema')
        self.assertTrue(calls[0]['text']['format']['strict'])
        self.assertIn('"inputs": {"reference": "X1"}',result)
        self.assertEqual(model.actual_usage['tokens'],30)
