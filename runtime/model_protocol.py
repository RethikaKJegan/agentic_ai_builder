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
    'Use actual tool_results and delegated results as evidence; do not invent completed reads.'
)


def response_format(protocol, context):
    def obj(properties):
        return {'type':'object','properties':properties,'required':list(properties),'additionalProperties':False}
    string = {'type':'string'}
    def variant(action, fields=None):
        return obj({'action':{'type':'string','enum':[action]},'reason':string,**(fields or {})})
    variants = [variant('finish',{'output_json':{'type':'string','description':
        'Encode a JSON object matching this business schema: '+json.dumps(context.get('final_output_schema',{}))}})]
    if protocol == 'master':
        ids = [a['agent_id'] for a in context.get('available_agents', [])]
        task = obj({'agent_id':{'type':'string','enum':ids},'inputs_json':string,'reason':string})
        if ids:
            variants.append(variant('delegate',{'tasks':{'type':'array','items':task},
                      'continuation_json':{'type':['string','null']}}))
        variants += [variant('continue',{'continuation_json':string}),variant('wait')]
    elif protocol == 'tool':
        ids = [t['tool_id'] for t in context.get('available_tools', [])]
        if ids:
            variants.append(variant('tool',{'tool_id':{'type':'string','enum':ids},'inputs_json':string}))
    else:
        raise RuntimeFailure('MODEL_PROTOCOL_INVALID','Unknown application control protocol.')
    return {'type':'json_schema','name':'agent_control','strict':True,
            'schema':obj({'decision':{'anyOf':variants}})}


def decode_response(text):
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
            decision['tasks'] = [dict(agent_id=t['agent_id'],reason=t['reason'],inputs=json.loads(t['inputs_json']))
                                 for t in decision['tasks']]
            if any(not isinstance(t['inputs'],dict) for t in decision['tasks']):
                raise ValueError()
        return json.dumps(decision)
    except (ValueError,TypeError,KeyError):
        raise RuntimeFailure('MODEL_OUTPUT_SCHEMA_INVALID','The model control envelope contained an invalid encoded object.') from None
