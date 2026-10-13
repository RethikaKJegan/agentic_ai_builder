"""Strict transport envelopes for generic dynamic agent control decisions."""
import json

from .service import RuntimeFailure

INSTRUCTIONS = (
    'The application requires its control transport envelope: return {"decision": {...}}. '
    'Select a valid action from the supplied strict response schema. inputs_json, output_json and '
    'continuation_json contain JSON-encoded OBJECT strings, not prose. For a tool action encode '
    'the exact tool inputs in inputs_json. For delegation encode each specialist input object in '
    'the task inputs_json. For finish encode the business result matching final_output_schema in '
    'output_json. Business instructions describe that result, not the outer control envelope. '
    'When the schema offers input_source=request, delegate the original request by reference. '
    'When it offers output, return the business object directly instead of output_json. '
    'Use actual tool_results and delegated results as evidence; do not invent completed reads.'
)


def response_format(protocol, context):
    def obj(properties):
        return {'type':'object','properties':properties,'required':list(properties),'additionalProperties':False}
    string = {'type':'string'}
    encoded_object = {'type':'string','pattern':r'^\s*\{[\s\S]*\}\s*$'}
    def variant(action, fields=None):
        return obj({'action':{'type':'string','enum':[action]},'reason':{'type':'string','minLength':1,'maxLength':2000},**(fields or {})})
    if protocol == 'master' and context.get('control_task_input_mode') == 'request':
        task = obj({'agent_id': {'type': 'string', 'enum': [a['agent_id'] for a in context['available_agents']]},
                    'input_source': {'type': 'string', 'enum': ['request']},
                    'reason': {'type': 'string', 'minLength': 1, 'maxLength': 2000}})
        variants = [variant('finish', {'output': context['final_output_schema']})]
        if context.get('remaining_tasks', 0) > 0 and context.get('remaining_rounds', 0) > 0:
            variants.append(variant('delegate', {'tasks': {'type': 'array', 'minItems': 1,
                'maxItems': min(50, context['remaining_tasks']), 'items': task}}))
        return {'type': 'json_schema', 'name': 'agent_control', 'strict': True,
                'schema': obj({'decision': {'anyOf': variants}})}
    variants = [variant('finish',{'output_json':{**encoded_object,'description':
        'Encode a JSON object matching this business schema: '+json.dumps(context.get('final_output_schema',{}))}})]
    if protocol == 'master':
        ids = [a['agent_id'] for a in context.get('available_agents', [])]
        task = obj({'agent_id':{'type':'string','enum':ids},'inputs_json':encoded_object,
                    'reason':{'type':'string','minLength':1,'maxLength':2000}})
        capacity=context.get('remaining_tasks',50)
        if ids and capacity>0 and context.get('remaining_rounds',1)>0:
            variants.append(variant('delegate',{'tasks':{'type':'array','minItems':1,'maxItems':min(50,capacity),'items':task},
                      'continuation_json':{'type':['string','null'],'pattern':encoded_object['pattern']}}))
        variants += [variant('continue',{'continuation_json':encoded_object}),variant('wait')]
    elif protocol == 'tool':
        ids = [t['tool_id'] for t in context.get('available_tools', [])]
        if ids:
            variants.append(variant('tool',{'tool_id':{'type':'string','enum':ids},'inputs_json':encoded_object}))
    else:
        raise RuntimeFailure('MODEL_PROTOCOL_INVALID','Unknown application control protocol.')
    return {'type':'json_schema','name':'agent_control','strict':True,
            'schema':obj({'decision':{'anyOf':variants}})}


def decode_response(text, context=None):
    try:
        wire = json.loads(text)
        if set(wire) != {'decision'} or not isinstance(wire['decision'],dict):
            raise ValueError()
        decision = dict(wire['decision'])
        for field in ('inputs','output','continuation'):
            encoded = decision.pop(field+'_json',None)
            if encoded is not None:
                value = json.loads(encoded)
                if not isinstance(value,dict):
                    raise ValueError()
                decision[field] = value
        if 'tasks' in decision:
            decision['tasks'] = [dict(agent_id=t['agent_id'],reason=t['reason'],inputs=(
                context['request'] if context and context.get('control_task_input_mode') == 'request' and t.get('input_source') == 'request'
                else json.loads(t['inputs_json'])))
                                 for t in decision['tasks']]
            if any(not isinstance(t['inputs'],dict) for t in decision['tasks']):
                raise ValueError()
        return json.dumps(decision)
    except (ValueError,TypeError,KeyError):
        raise RuntimeFailure('MODEL_OUTPUT_SCHEMA_INVALID','The model control envelope contained an invalid encoded object.') from None
