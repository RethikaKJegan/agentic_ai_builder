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
    def test_control_transport_matches_runtime_limits(self):
        context={'available_agents':[{'agent_id':'specialist'}],'remaining_tasks':1,'remaining_rounds':2}
        wire={'decision':{'action':'delegate','reason':'Review.','tasks':[{'agent_id':'specialist','inputs_json':'{}','reason':'Check.'}],'continuation_json':None}}
        schema=response_format('master',context)['schema'];Draft202012Validator(schema).validate(wire)
        for mutate in ('empty','too_many','long_reason','array_input'):
            invalid=deepcopy(wire)
            if mutate=='empty':invalid['decision']['tasks']=[]
            if mutate=='too_many':invalid['decision']['tasks']*=2
            if mutate=='long_reason':invalid['decision']['reason']='x'*2001
            if mutate=='array_input':invalid['decision']['tasks'][0]['inputs_json']='[]'
            self.assertTrue(list(Draft202012Validator(schema).iter_errors(invalid)),mutate)
        context['remaining_tasks']=0
        self.assertTrue(list(Draft202012Validator(response_format('master',context)['schema']).iter_errors(wire)))
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

    def test_request_reference_preserves_multiline_input_and_structured_output(self):
        from workflow_api.procurement_fulfilment import OUTPUT
        context={'control_task_input_mode':'request', 'request':{'email_text':'Accepted.\n"Quoted" text \u2014 no reconstruction.', 'order':{'items':[]}},
                 'available_agents':[{'agent_id':'extract'}], 'remaining_tasks':2,'remaining_rounds':3,'final_output_schema':OUTPUT}
        wire={'decision':{'action':'delegate','reason':'Check update.', 'tasks':[{'agent_id':'extract','input_source':'request','reason':'Extract.'}]}}
        Draft202012Validator(response_format('master',context)['schema']).validate(wire)
        decision=json.loads(decode_response(json.dumps(wire),context))
        Draft202012Validator(DECISION_SCHEMA).validate(decision)
        self.assertEqual(decision['tasks'][0]['inputs'],context['request'])
        output={'event_kind':'ACCEPTED','items':[],'quantity_mode':'unknown','tracking_reference':None,'expected_delivery_date':None,
                'receipt_confirmed':False,'acceptance_confirmed':False,'resolution_confirmed':False,'note':'Accepted.', 'evidence':['Accepted.']}
        wire={'decision':{'action':'finish','reason':'Reviewed.', 'output':output}}
        Draft202012Validator(response_format('master',context)['schema']).validate(wire)
        self.assertEqual(json.loads(decode_response(json.dumps(wire),context))['output'],output)
        wire['decision']['output']['event_kind']='INVENTED'
        self.assertTrue(list(Draft202012Validator(response_format('master',context)['schema']).iter_errors(wire)))

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

    def test_research_decisions_use_exact_typed_inputs_and_outputs(self):
        from runtime.supplier_search import SEARCH,PAGE
        from workflow_api.inventory_ranking import RISK
        result_schema={'type':'object','properties':{'external_risks':{'type':'array','items':RISK}},
                       'required':['external_risks'],'additionalProperties':False}
        context={'available_tools':[SEARCH,PAGE],'final_output_schema':result_schema}
        schema=response_format('tool',context)['schema']
        wire={'decision':{'action':'tool','reason':'Search public evidence.','tool_id':SEARCH['tool_id'],
                          'inputs':{'query':'food wholesale supply risks','region':'wt-wt','max_results':3}}}
        Draft202012Validator(schema).validate(wire)
        decision=json.loads(decode_response(json.dumps(wire),context))
        Draft202012Validator(TOOL_DECISION_SCHEMA).validate(decision)
        for change in ('encoded','missing','wrong_type','wrong_tool'):
            bad=deepcopy(wire)
            if change=='encoded':bad['decision']['inputs_json']=json.dumps(bad['decision'].pop('inputs'))
            if change=='missing':bad['decision']['inputs'].pop('query')
            if change=='wrong_type':bad['decision']['inputs']['max_results']='three'
            if change=='wrong_tool':bad['decision']['tool_id']='unregistered'
            self.assertTrue(list(Draft202012Validator(schema).iter_errors(bad)),change)
        finish={'decision':{'action':'finish','reason':'Cite actual evidence.','output':{'external_risks':[
            {'finding':'Public fixture finding','source_url':'https://example.org/source'}]}}}
        Draft202012Validator(schema).validate(finish)
        Draft202012Validator(TOOL_DECISION_SCHEMA).validate(json.loads(decode_response(json.dumps(finish),context)))
        bad=deepcopy(finish);bad['decision']['output']['external_risks'][0]['source_url']='invented'
        self.assertTrue(list(Draft202012Validator(schema).iter_errors(bad)))

    def test_typed_public_research_crosses_real_crewai_and_factory_offline(self):
        from runtime.crew import CrewAdapter
        from runtime.supplier_search import SEARCH
        calls=[]
        wire={'decision':{'action':'tool','reason':'Read public evidence.','tool_id':SEARCH['tool_id'],
                          'inputs':{'query':'food wholesale supply risks','region':'wt-wt','max_results':3}}}
        class Client:
            def with_options(self,**kwargs):return self
            @property
            def responses(self):return self
            def create(self,**kwargs):
                calls.append(kwargs)
                Draft202012Validator(kwargs['text']['format']['schema']).validate(wire)
                return SimpleNamespace(output_text=json.dumps(wire),usage=SimpleNamespace(input_tokens=10,output_tokens=20))
        agent=json.loads((ROOT/'shared/contracts/examples/agents/valid-classifier.json').read_text())
        agent['input_schema']={'type':'object'};agent['output_schema']=TOOL_DECISION_SCHEMA;agent['allowed_tool_ids']=[]
        context={'available_tools':[SEARCH],'final_output_schema':{'type':'object','properties':{'summary':{'type':'string'}},
                                                                 'required':['summary'],'additionalProperties':False}}
        with patch('tiktoken.encoding_for_model',return_value=SimpleNamespace(encode=lambda value:[0]*10)):
            factory=OpenAIModelFactory({'gpt-5':{'input_per_token':0,'output_per_token':0}},Client())
            result=CrewAdapter(factory).execute(agent,context,protocol='tool')
        self.assertEqual(result,wire['decision']);self.assertEqual(len(calls),1)
        self.assertTrue(calls[0]['text']['format']['strict'])

    def test_optional_or_open_payloads_keep_encoded_fallback(self):
        from runtime.model_protocol import closed_payload
        for schema in ({'type':'object'}, {'type':'object','properties':{'optional':{'type':'string'}},
                                        'required':[],'additionalProperties':False}):
            self.assertFalse(closed_payload(schema))
            context={'available_tools':[{'tool_id':'generic','input_schema':schema}],'final_output_schema':schema}
            wire={'decision':{'action':'tool','reason':'Use exact authorized inputs.','tool_id':'generic','inputs_json':'{}'}}
            Draft202012Validator(response_format('tool',context)['schema']).validate(wire)
            Draft202012Validator(TOOL_DECISION_SCHEMA).validate(json.loads(decode_response(json.dumps(wire),context)))

    def test_complete_control_stream_consumes_only_first_decision(self):
        from runtime.supplier_search import SEARCH
        context={'available_tools':[SEARCH]}
        schema=response_format('tool',context)['schema']
        first={'decision':{'action':'tool','reason':'Read actual sources.','tool_id':SEARCH['tool_id'],
                           'inputs':{'query':'food wholesale supply risk','region':'wt-wt','max_results':3}}}
        second=deepcopy(first);second['decision']['inputs']['query']='speculative second query'
        finish={'decision':{'action':'finish','reason':'Speculative completion.','output_json':'{}'}}
        stream=''.join(json.dumps(w) for w in (first,second,finish))
        result=json.loads(decode_response(stream,context,schema))
        self.assertEqual(result,first['decision'])
        Draft202012Validator(TOOL_DECISION_SCHEMA).validate(result)
        # A malformed second frame must never be ignored just because the first is valid.
        for suffix in ('trailing prose','{','[]','{"decision":{"action":"invented"}}'):
            with self.subTest(suffix=suffix),self.assertRaises(RuntimeFailure):
                decode_response(json.dumps(first)+suffix,context,schema)
        with self.assertRaises(RuntimeFailure):decode_response(json.dumps(first)*17,context,schema)
        with self.assertRaises(RuntimeFailure):decode_response(stream,context)  # No schema means no stream mode.

    def test_factory_accounts_for_multiframe_response_but_returns_only_first_action(self):
        from runtime.supplier_search import SEARCH
        context={'available_tools':[SEARCH]}
        first={'decision':{'action':'tool','reason':'Search actual public evidence.','tool_id':SEARCH['tool_id'],
                           'inputs':{'query':'food wholesale supply risks','region':'wt-wt','max_results':3}}}
        finish={'decision':{'action':'finish','reason':'No results yet.','output_json':'{}'}}
        class Client:
            def with_options(self,**kwargs):return self
            @property
            def responses(self):return self
            def create(self,**kwargs):
                return SimpleNamespace(output_text=json.dumps(first)+json.dumps(finish),
                                       usage=SimpleNamespace(input_tokens=10,output_tokens=40))
        agent=json.loads((ROOT/'shared/contracts/examples/agents/valid-classifier.json').read_text())
        agent['output_schema']=TOOL_DECISION_SCHEMA
        with patch('tiktoken.encoding_for_model',return_value=SimpleNamespace(encode=lambda value:[0]*10)):
            model=OpenAIModelFactory({'gpt-5':{'input_per_token':0,'output_per_token':0}},Client())(agent)
            model.control_format=response_format('tool',context);model.control_context=context
            result=model.call([{'role':'user','content':'Check public evidence.'}])
        self.assertEqual(json.loads(result.removeprefix('Final Answer: ')),first['decision'])
        self.assertEqual(model.actual_usage['tokens'],50)
        self.assertEqual(model.actual_usage['llm_calls'],1)
