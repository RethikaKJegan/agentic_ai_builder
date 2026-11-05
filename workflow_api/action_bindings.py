"""Typed action bindings. No expressions, eval, implicit identity or model authority."""
from copy import deepcopy
import json
from pathlib import Path
from jsonschema import Draft202012Validator,FormatChecker
from runtime.service import RuntimeFailure

SCHEMA_V2=json.loads((Path(__file__).resolve().parents[1]/'shared/contracts/orchestration-plan-v2.json').read_text())
SCHEMA=json.loads((Path(__file__).resolve().parents[1]/'shared/contracts/orchestration-plan-v1.json').read_text())
CONTENT_FIELDS={'subject','body','summary','description','title','tabs','rows','questions','findings','source_references','assumptions','query'}
REFERENCES={'output','generated','receipt'}


def deny(message,code='ACTION_BINDING_INVALID'):
    raise RuntimeFailure(code,message,422)


def traverse(value,path):
    for part in path:
        if type(part) is int:
            if not isinstance(value,list) or not 0<=part<len(value):deny('Array binding index is outside the returned data.')
            value=value[part];continue
        if not isinstance(value,dict) or part not in value or part.startswith('_'):
            deny('Binding path does not reference a declared value.')
        value=value[part]
    return deepcopy(value)


def field_schema(schema,path):
    for part in path:
        if type(part) is int:
            if schema.get('type')!='array' or not isinstance(schema.get('items'),dict):deny('Array binding must reference declared items.')
            schema=schema['items'];continue
        if part.startswith('_') or schema.get('type')!='object' or part not in schema.get('properties',{}):
            deny('Binding path must name declared object properties.')
        schema=schema['properties'][part]
    return schema


def checked_field(schema,path,action_id,side):
    try:return field_schema(schema,path)
    except RuntimeFailure as exc:
        exc.binding_issue=dict(action_id=action_id,side=side,path=deepcopy(path))
        raise


def declared_paths(schema):
    """Only paths accepted by field_schema; opaque objects are whole values."""
    result=[[]]
    if schema.get('type')=='object':
        for name,child in schema.get('properties',{}).items():
            if not name.startswith('_'):
                result.extend([[name,*p] for p in declared_paths(child) if len(p)<8])
    elif schema.get('type')=='array' and isinstance(schema.get('items'),dict):
        result.extend([[0,*p] for p in declared_paths(schema['items']) if len(p)<8])
    return result


def value_schema(value):
    if isinstance(value,dict):return {'type':'object','properties':{k:value_schema(v) for k,v in value.items()},'required':list(value),'additionalProperties':False}
    if isinstance(value,list):return {'type':'array','items':value_schema(value[0]) if value else {}}
    return {'type':'null' if value is None else 'boolean' if type(value) is bool else 'integer' if type(value) is int else 'number' if type(value) is float else 'string'}


def compatible(source,target):
    def types(s):
        t=s.get('type');return set(t if isinstance(t,list) else [t]) if t else set()
    for union in ('oneOf','anyOf'):
        if union in target:return any(compatible(source,t) for t in target[union])
    a,b=types(source),types(target)
    if a==b=={'array'} and isinstance(source.get('items'),dict) and isinstance(target.get('items'),dict):
        return compatible(source['items'],target['items'])
    if a==b=={'object'} and target.get('additionalProperties') is False:
        if set(source.get('required',[]))-set(target.get('properties',{})):return False
    return bool(a and b and (a<=b or a=={'integer'} and 'number' in b)) or source==target


def content_target(path):
    # Event descriptions are content; event times, attendees and IDs are authority.
    return path[0] in CONTENT_FIELDS or path[:2] in (['event','summary'],['event','description'])


def put(result,path,value):
    cursor=result
    for part in path[:-1]:
        cursor=cursor.setdefault(part,{})
        if not isinstance(cursor,dict):deny('Overlapping input binding targets.')
    if path[-1] in cursor:deny('Duplicate input binding target.')
    cursor[path[-1]]=value


def binding_value(binding,context,actions,run=None):
    kind=binding['kind']
    if kind in REFERENCES:
        aid=binding['action_id']
        if run is None:return None
        entry=run.get('action_instances',{}).get(aid,{})
        if entry.get('state')!='completed':deny('Required upstream action is not completed.','ACTION_DEPENDENCY_PENDING')
        if kind=='receipt' and not entry.get('verified_receipt'):deny('A verified connector receipt is required.','ACTION_RECEIPT_REQUIRED')
        if kind=='generated' and entry.get('provenance_type')!='INFERRED':deny('Generated binding must reference a content result.')
        return traverse(entry['output'],binding['path'])
    section={'literal':'user_values','context':'validated_context','evidence':'evidence','configuration':'configuration'}[kind]
    if binding['key'] not in context.get(section,{}):deny('Required binding input is missing.','ACTION_INPUT_REQUIRED')
    entry=context[section][binding['key']]
    return traverse(entry,binding['path'])


def resolve_inputs(action,context,actions,run):
    if any(run.get('action_instances',{}).get(a,{}).get('state')!='completed' for a in action['depends_on']):
        deny('Required action dependencies are not completed.','ACTION_DEPENDENCY_PENDING')
    result={}
    for binding in action['bindings']:
        put(result,binding['target'],binding_value(binding,context,actions,run))
    return result


def validate_plan(plan,contracts,context,scope):
    if list(Draft202012Validator(SCHEMA_V2 if plan.get('schema_version')=='orchestration-plan-v2' else SCHEMA,format_checker=FormatChecker()).iter_errors(plan)):deny('Plan violates orchestration-plan-v1.','ACTION_PLAN_INVALID')
    if plan['scope']!=scope:deny('Plan belongs to another workspace, owner or client.','ACTION_SCOPE_DENIED')
    if plan['constraints'].get('time_zone'):
        from zoneinfo import ZoneInfo,ZoneInfoNotFoundError
        try:ZoneInfo(plan['constraints']['time_zone'])
        except (ZoneInfoNotFoundError,ValueError):deny('Use a valid IANA timing timezone.')
    actions={a['action_id']:a for a in plan['actions']}
    if len(actions)!=len(plan['actions']):deny('Action instance IDs must be unique.')
    if len(actions)>plan['constraints']['max_actions']:deny('Action count exceeds plan budget.')
    if set(plan['completion_criteria'])-set(actions):deny('Completion criteria reference an unknown action.')
    if any(actions[a]['optional'] for a in plan['completion_criteria']):deny('Completion criteria must name required actions.')
    pending=set(actions);done=set()
    while pending:
        ready={i for i in pending if set(actions[i]['depends_on'])<=done}
        if not ready:deny('Unknown dependency or cyclic action graph.','ACTION_DEPENDENCY_INVALID')
        done|=ready;pending-=ready
    for action in actions.values():
        cid=action['capability_id']
        if cid not in contracts:deny('Plan references an unregistered capability.','ACTION_CAPABILITY_UNKNOWN')
        c=contracts[cid]
        if action['action_id'] in {'objective_received','workflow_output'} or action['action_id'].startswith(('approve_','condition_','skip_')):deny('Action ID is reserved by the compiler.')
        if action['expected_output_schema']!=c['output_schema']:deny('Output schema differs from the registered capability.')
        if action['optional']!=(action['when'] is not None):deny('Conditional actions require explicit optional status.')
        if action['when'] and not action['optional']:deny('A required action cannot be skipped.')
        if action['action_id'] in action['depends_on']:deny('An action cannot depend on itself.')
        if any(actions[d]['optional'] for d in action['depends_on']):deny('A dependency cannot require a conditionally skipped action.')
        write=c['side_effect'] in ('draft','write')
        if action['required_approvals']!=(['exact_payload'] if write else []):deny('Approval assumptions differ from registered side effects.','ACTION_APPROVAL_REQUIRED')
        if action['budget']['max_tool_calls']<(1 if c['kind']=='tool' else 0) or c['kind']=='model' and action['budget']['max_tool_calls']!=0 or action['budget']['max_llm_calls']<(1 if c['kind']=='model' else 0):deny('Action execution budget is insufficient.')
        if action['budget']['max_retries']>plan['constraints'].get('max_retries',0) or write and (action['budget']['max_retries'] or action['budget']['max_tool_calls']!=1):deny('Retry allowance exceeds the reviewed plan or write boundary.')
        targets=[]
        bindings=action['bindings']+([action['when']['binding']] if action['when'] else [])
        for b in bindings:
            conditional=bool(action['when'] and b is action['when']['binding'])
            target={'type':'boolean'} if conditional else checked_field(c['input_schema'],b['target'],action['action_id'],'target')
            if not conditional:
                t=b['target']
                overlap=next((x for x in targets if t[:len(x)]==x or x[:len(t)]==t),None)
                if overlap is not None:
                    exc=RuntimeFailure('ACTION_BINDING_INVALID','Duplicate or overlapping binding targets.',422)
                    exc.binding_issue=dict(action_id=action['action_id'],side='target',path=deepcopy(t),overlaps=deepcopy(overlap))
                    raise exc
                targets.append(t)
            if b['kind'] in REFERENCES:
                if b['action_id'] not in action['depends_on']:
                    error=RuntimeFailure('ACTION_BINDING_INVALID','Output binding must name an explicit dependency.',422)
                    error.binding_issue=dict(action_id=action['action_id'],side='source',source_action_id=b['action_id'],path=deepcopy(b['path']),required_dependency=b['action_id'])
                    raise error
                parent=actions[b['action_id']];pc=contracts[parent['capability_id']]
                if parent['optional']:deny('Required data cannot depend on a conditionally skipped action.')
                source=checked_field(pc['output_schema'],b['path'],action['action_id'],'source')
                if b['kind']=='receipt' and pc['kind']!='tool':deny('Only connector results can supply receipts.')
                if b['kind']=='generated' and parent['capability_id']!='content.prepare':deny('Generated binding requires content preparation.')
                if not conditional and c['kind']=='tool' and not content_target(b['target']):
                    if not (b['kind']=='receipt' and c['supported_operation']=='research.fetch' and pc['supported_operation']=='research.search' and b['path']==['results',0,'url']) and (b['kind']!='receipt' or b['path'] not in (['spreadsheet_id'],['spreadsheet_url'],['event_id'],['message_id'],['draft_id'],['thread_id'],['artifact_id'])):
                        error=RuntimeFailure('ACTION_AUTHORITY_DENIED','Generated or interpreted values cannot supply execution authority.',422)
                        error.binding_issue=dict(action_id=action['action_id'],side='target',path=deepcopy(b['target']),source_action_id=b['action_id'],source_path=deepcopy(b['path']),rule='explicit_authority_required')
                        raise error
            else:
                value=binding_value(b,context,actions)
                source=value_schema(value)
                violations=list(Draft202012Validator(target).iter_errors(value))
                if violations:
                    error=RuntimeFailure('ACTION_BINDING_INVALID','Literal/context value violates its destination schema.',422)
                    error.binding_issue=dict(action_id=action['action_id'],side='target',path=deepcopy(b['target']),rule=violations[0].validator)
                    raise error
                if b['kind']=='evidence' and c['kind']=='tool' and not content_target(b['target']) and b['path'] not in context.get('authority_evidence_paths',{}).get(b['key'],[]):
                    deny('Mapped evidence is not approved as identity authority.','ACTION_AUTHORITY_DENIED')
            if not compatible(source,target):
                # Provider receipts may omit an identifier. Admit explicit non-null
                # narrowing only for receipts; runtime input validation still blocks
                # the dependent action when the actual receipt contains null.
                narrowed=deepcopy(source)
                if b['kind']=='receipt' and isinstance(source.get('type'),list) and 'null' in source['type']:
                    narrowed['type']=[t for t in source['type'] if t!='null']
                if narrowed==source or not compatible(narrowed,target):deny('Binding input/output types are incompatible.')
        # Required top-level fields must be fully supplied; nested required fields are checked on resolution.
        if c['supported_operation'].startswith('calendar.') and c['supported_operation']!='calendar.discover' and ['calendar_id'] not in targets:deny('Calendar identity must be explicit.','ACTION_INPUT_REQUIRED')
        if set(c['input_schema'].get('required',[]))-{p[0] for p in targets}:deny('A required action input has no binding.','ACTION_INPUT_REQUIRED')
    for name,field in [('max_llm_calls','max_llm_calls'),('max_tool_calls','max_tool_calls')]:
        if sum(a['budget'][field] for a in actions.values())>plan['constraints'][name]:deny('Action budgets exceed plan limits.')
    return actions
