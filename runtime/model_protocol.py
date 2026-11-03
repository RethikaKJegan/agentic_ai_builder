"""Strict transport envelopes for generic dynamic agent control decisions."""
from copy import deepcopy
import json
from jsonschema import Draft202012Validator, ValidationError

from .service import RuntimeFailure

INSTRUCTIONS = (
    'The application requires its control transport envelope: return {"decision": {...}}. '
    'Emit exactly one decision and stop. Do not simulate tool execution, later turns or completion before actual results arrive. '
    'Select a valid action from the supplied strict response schema. inputs_json, output_json and '
    'continuation_json contain JSON-encoded OBJECT strings, not prose. For a tool action encode '
    'the exact tool inputs in inputs_json. For delegation encode each specialist input object in '
    'the task inputs_json. For finish encode the business result matching final_output_schema in '
    'output_json. Business instructions describe that result, not the outer control envelope. '
    'When the schema offers input_source=request, delegate the original request by reference. '
    'When it offers output, return the business object directly instead of output_json. '
    'When it offers inputs, return the exact typed input object directly instead of inputs_json. '
    'When it offers output_fields, return key/value entries for the final business object; nested objects use {entries:[{key,value}]}. Scalars and arrays remain typed values, never JSON-encoded strings. '
    'Use actual tool_results and delegated results as evidence; do not invent completed reads.'
)


def closed_payload(schema):
    """Whether the existing schema already meets strict object requirements.

    Do not invent properties, promote optional inputs or loosen constraints.
    Generic/open finish schemas use the strict recursive field transport.
    """
    if not isinstance(schema, dict) or '$ref' in schema:
        return False
    if 'anyOf' in schema:
        return all(closed_payload(item) for item in schema['anyOf'])
    kind = schema.get('type')
    if kind == 'object':
        properties = schema.get('properties')
        return (isinstance(properties, dict) and schema.get('additionalProperties') is False and
                set(schema.get('required', [])) == set(properties) and
                all(closed_payload(value) for value in properties.values()))
    if kind == 'array':
        return closed_payload(schema.get('items'))
    return kind in ('string', 'integer', 'number', 'boolean', 'null')


def structured_value_definitions():
    """Strict recursive JSON values; open maps are explicit entry arrays."""
    entry = {'type':'object','properties':{'key':{'type':'string'},
              'value':{'$ref':'#/$defs/control_value'}},'required':['key','value'],'additionalProperties':False}
    entries = {'type':'array','items':{'$ref':'#/$defs/control_entry'}}
    value = {'anyOf':[{'type':kind} for kind in ('string','number','boolean','null')] + [
        {'type':'array','items':{'$ref':'#/$defs/control_value'}},
        {'type':'object','properties':{'entries':deepcopy(entries)},'required':['entries'],'additionalProperties':False}]}
    return {'control_entry':entry,'control_value':value}


def encode_object_fields(value):
    """Deterministic test/adapter encoder; the provider generates the same tree."""
    def encode(item):
        if isinstance(item,dict):return {'entries':encode_object_fields(item)}
        if isinstance(item,list):return [encode(v) for v in item]
        return item
    return [{'key':key,'value':encode(item)} for key,item in value.items()]


def decode_object_fields(entries):
    import math
    remaining = [20000]
    def value(item,depth):
        remaining[0]-=1
        if remaining[0]<0 or depth>32:raise ValueError()
        if isinstance(item,dict):
            if set(item)!={'entries'}:raise ValueError()
            return obj(item['entries'],depth+1)
        if isinstance(item,list):return [value(v,depth+1) for v in item]
        if item is None or type(item) in (str,bool,int):return item
        if type(item) is float and math.isfinite(item):return item
        raise ValueError()
    def obj(items,depth):
        if not isinstance(items,list) or depth>32:raise ValueError()
        result={}
        for entry in items:
            if not isinstance(entry,dict) or set(entry)!={'key','value'}:raise ValueError()
            key=entry['key']
            if not isinstance(key,str) or key in result:raise ValueError()
            result[key]=value(entry['value'],depth+1)
        return result
    return obj(entries,0)


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
    final_schema = context.get('final_output_schema', {})
    structured_finish = not (final_schema.get('type') == 'object' and closed_payload(final_schema))
    finish = ({'output_fields': {'type':'array','items':{'$ref':'#/$defs/control_entry'},
                  'description':'Represent the business result as key/value entries. Values are ordinary JSON scalars or arrays; nested objects use {entries:[{key,value}]}. Do not JSON-encode values as strings. The decoded object must match: '+json.dumps(final_schema)}}
              if structured_finish else {'output':deepcopy(final_schema)})
    variants = [variant('finish', finish)]
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
        encoded_ids = []
        for tool in context.get('available_tools', []):
            input_schema = tool.get('input_schema', {})
            if input_schema.get('type') == 'object' and closed_payload(input_schema):
                variants.append(variant('tool', {'tool_id': {'type': 'string', 'enum': [tool['tool_id']]},
                                                  'inputs': deepcopy(input_schema)}))
            else:
                encoded_ids.append(tool['tool_id'])
        if encoded_ids:
            variants.append(variant('tool', {'tool_id': {'type': 'string', 'enum': encoded_ids},
                                              'inputs_json': encoded_object}))
    else:
        raise RuntimeFailure('MODEL_PROTOCOL_INVALID','Unknown application control protocol.')
    wire_schema=obj({'decision':{'anyOf':variants}})
    if structured_finish:
        wire_schema['$defs']=structured_value_definitions()
    return {'type':'json_schema','name':'agent_control','strict':True,'schema':wire_schema}


def decode_response(text, context=None, wire_schema=None):
    transport_field = 'decision/encoded_object'
    try:
        if wire_schema is None:
            wire = json.loads(text)
        else:
            # SDK output_text can join several complete assistant decisions.
            # Validate the entire stream; consume one turn, never speculative
            # later tool calls or completion claims. No partial/prose salvage.
            decoder = json.JSONDecoder()
            validator = Draft202012Validator(wire_schema)
            offset, frames = 0, []
            while offset < len(text):
                while offset < len(text) and text[offset].isspace():
                    offset += 1
                if offset == len(text):
                    break
                if len(frames) >= 16:
                    raise ValueError()
                frame, offset = decoder.raw_decode(text, offset)
                validator.validate(frame)
                frames.append(frame)
            if not frames:
                raise ValueError()
            wire = frames[0]
        if set(wire) != {'decision'} or not isinstance(wire['decision'],dict):
            raise ValueError()
        decision = dict(wire['decision'])
        if 'output_fields' in decision:
            transport_field = 'decision/output_fields'
            decision['output'] = decode_object_fields(decision.pop('output_fields'))
            if context and context.get('final_output_schema'):
                Draft202012Validator(context['final_output_schema']).validate(decision['output'])
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
    except (ValueError,TypeError,KeyError,ValidationError) as exc:
        failure = RuntimeFailure('MODEL_OUTPUT_SCHEMA_INVALID','The model control envelope failed its structured object schema.')
        failure.validation_field = ('/'.join(str(p) for p in exc.absolute_schema_path)
                                    if isinstance(exc, ValidationError) else transport_field)
        raise failure from None
