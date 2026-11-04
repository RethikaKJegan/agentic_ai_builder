"""Versioned Simpson process installation; all execution belongs to BusinessCases."""
import json
from pathlib import Path
from copy import deepcopy
from .lifecycle_driver import LifecycleDriver
from .business_cases import fail
from .business_knowledge_model import digest

PROCESS_PATH=Path(__file__).resolve().parents[1]/'ontology/business-processes/simpson-warranty-v1.json'


def definition():
    return json.loads(PROCESS_PATH.read_text())


def coordination_definition(composition,auth,tool_id):
    """Pin an optional registered mail/calendar action; no account or resource is invented."""
    selected=next((item for item in composition.tools(auth) if item['tool_id']==tool_id),None)
    if selected is None or selected['definition']['capability'] not in ('send_email','calendar_create'):
        fail('Choose an existing registered email-send or Calendar-create tool.','SIMPSON_COORDINATION_TOOL_INVALID')
    tool=selected['definition'];process=definition();mail=tool['capability']=='send_email'
    process['process_definition_id']+='_'+('mail_' if mail else 'calendar_')+digest([tool_id,selected['version'],tool])[:12]
    process['description']+=' Optional coordination uses an exact registered tool and actual caller-supplied resources under normal action approval.'
    scheduling=process['stages'][4]
    fields=tool['input_schema'].get('properties',{})
    def input_spec(name):
        return dict(schema=deepcopy(fields.get(name,{'type':'string','minLength':1})),binding=dict(source='user',path='coordination_inputs.'+name))
    required=tool['input_schema'].get('required',[])
    if not required:fail('Coordination tool requires an explicit input contract.','SIMPSON_COORDINATION_TOOL_INVALID')
    scheduling.update(required_capabilities=['tool.'+tool_id],required_inputs={k:input_spec(k) for k in required},
        optional_inputs={k:input_spec(k) for k in fields if k not in required},allowed_tools=[tool_id],side_effect_classification='write',
        external_event_requirements=[],retry_policy={'max_retries':0,'backoff_seconds':0})
    receipt='message_id' if mail else 'event_id'
    scheduling['output_schema']={'type':'object','additionalProperties':False,'required':[receipt,'complaint_id'],
        'properties':{receipt:{'type':'string','minLength':1},'complaint_id':{'type':'string','minLength':1}}}
    scheduling['output_bindings']={receipt:{'source':'receipt','path':'action_task_1.'+receipt},
        'complaint_id':{'source':'stage:oem_complaint','path':'complaint_id'}}
    scheduling['completion_criteria']=[{'source':'output','path':receipt,'operator':'exists'}]
    findings=process['stages'][5]['external_event_requirements'][0]
    findings['correlation_keys'][receipt]={'source':'stage:inspection_scheduling','path':receipt}
    findings['expected_source']='simpson.mail_reply' if mail else 'simpson.field_service'
    return process


class SimpsonLifecycle:
    def __init__(self,cases):self.cases=cases

    def create(self,auth,body):
        self.cases.body(body,('request_key','original_user_goal'),('inputs','business_request','resources','google_connection_id','coordination_tool_id'))
        payload=deepcopy(body);tool=payload.pop('coordination_tool_id',None)
        process=coordination_definition(self.cases.service.business_composition,auth,tool) if tool else definition()
        self.cases.publish(auth,process)
        return self.cases.create(auth,dict(payload,process_definition_id=process['process_definition_id'],process_definition_version=process['version']))

    def drive(self,auth,case_id,body):
        return LifecycleDriver(self.cases).drive(auth,case_id,body)
