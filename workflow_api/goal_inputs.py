"""Server-owned planning defaults for account-and-goal requests.

Connector metadata may declare internal operation identifiers. It cannot turn a
business identity, recipient or provider resource into model-generated authority.
"""
import re
from copy import deepcopy
from .business_knowledge_model import digest


def configure(context,composition,auth,body,contracts,connectors,tool_id):
    if not body.get('automatic_inputs'):return
    base=digest([auth['subject'],body.get('google_connection_id'),body['request_key']])
    context['validated_context']['goal']=body['objective']
    context['validated_context']['research_request']={'objective':body['objective']}
    for cid,c in contracts.items():
        if c.get('retrieval_task'):
            context['configuration']['task_'+c['retrieval_task']]=c['retrieval_task']
        if c['kind']!='tool':continue
        connector=connectors.get(tool_id(cid,c))
        for field,value in getattr(connector,'planning_input_defaults',{}).items():
            if field in c['input_schema'].get('properties',{}):context['configuration'][default_key(cid,field)]=deepcopy(value)
        for field,role in getattr(connector,'planning_input_roles',{}).items():
            if role not in ('workflow_key','action_key') or field not in c['input_schema'].get('properties',{}):continue
            context['configuration'][default_key(cid,field)]='goal_'+digest([base,cid,field])[:32]
    calendar_context(context,body['objective'],bool(body.get('google_connection_id')))
    # Only explicit addresses in the user's goal become candidate recipient inputs.
    addresses=list(dict.fromkeys(re.findall(r'(?<![\w.+-])[A-Za-z0-9.!#$%&\'*+/=?^_`{|}~-]+@[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)+',body['objective'])))
    if len(addresses)==1:context['user_values'].setdefault('recipient',addresses[0].rstrip('.'))
    if body.get('google_connection_id'):
        google=getattr(composition.service,'google_tools',None)
        if google:
            with composition.store.transaction(write=False) as db:
                google.validate({'metadata':{'google_connection_id':body['google_connection_id']}},auth,db)
                row=google.manager.owned(db,auth,body['google_connection_id'])
            context['validated_context']['selected_account_email']=row[4]
            if not addresses and re.search(r'\b(?:email|mail|send)\b[^.!?]{0,160}\b(?:to\s+me|my\s+(?:email|inbox))\b|\b(?:email|mail|send)\s+(?:it\s+)?me\b|\bmy (?:email|inbox)\b',body['objective'],re.I):
                context['user_values'].setdefault('recipient',row[4])


def default_key(cid,field):return 'operation_'+digest(cid)[:16]+'_'+field


def bind_internal(actions,contracts,context,connectors,tool_id,request_key):
    satisfied=set()
    sections={'user_values':'literal','validated_context':'context','configuration':'configuration','evidence':'evidence'}
    for section in sections:
        for key in context[section]:
            satisfied.update((section+'.'+key,'binding_context.'+section+'.'+key))
    for action in actions:
        cleaned=[]
        for binding in action.get('bindings',[]):
            if action.get('capability_id')=='content.prepare' and binding.get('target',[None])[0] in ('instructions','source_references'):
                satisfied.add(binding['target'][0])
                if binding.get('key'):satisfied.add(binding['key'])
                continue # Runtime supplies action instructions and pinned citation refs.
            key=binding.get('key');path=binding.get('path',[])
            if isinstance(key,str):
                parts=key.split('.')
                if parts==['binding_context']:parts=path;path=[]
                elif parts[0]=='binding_context':parts=parts[1:]
                if parts and parts[0] in sections:
                    section=parts[0];rest=parts[1:]+path
                    if not rest and binding.get('target')==['data']:
                        snapshot='namespace_'+section
                        context['validated_context'][snapshot]={k:deepcopy(v) for k,v in context[section].items() if not k.startswith(('namespace_','analysis_context_'))}
                        satisfied.add(key)
                        binding.update(kind='context',key=snapshot,path=[])
                    elif rest and rest[0] in context[section]:
                        satisfied.add(key)
                        binding.update(kind=sections[section],key=rest[0],path=rest[1:])
            if action.get('capability_id')=='content.prepare' and binding.get('kind')=='context' and binding.get('target')==['data'] and binding.get('path')==[binding.get('key')]:
                value=context['validated_context'].get(binding.get('key'))
                if isinstance(value,dict) and binding['key'] not in value:binding['path']=[]
            cleaned.append(binding)
        action['bindings']=cleaned
    for action in actions:
        c=contracts.get(action.get('capability_id'),{})
        if c.get('retrieval_task'):
            # Preparation and retrieval task identities are server-owned.
            for field,kind,key in [('preparation_id','context','preparation_id'),('task','configuration','task_'+c['retrieval_task'])]:
                if key not in context['validated_context' if kind=='context' else 'configuration']:continue
                replace_binding(action,field,kind,key,satisfied)
        if c.get('kind')=='model' and action.get('capability_id')!='content.prepare' and 'task_id' in c.get('input_schema',{}).get('properties',{}):
            key='analysis_task_'+action['action_id']
            context['configuration'][key]=action['action_id']
            replace_binding(action,'task_id','configuration',key,satisfied)
            if 'context' in c['input_schema']['properties']:
                key='analysis_context_'+action['action_id']
                context['validated_context'][key]={k:deepcopy(v) for k,v in context['validated_context'].items() if not k.startswith('analysis_context_')}
                context['validated_context'][key]['user_values']=deepcopy(context['user_values'])
                replace_binding(action,'context','context',key,satisfied)
        if c.get('kind')!='tool':continue
        connector=connectors.get(tool_id(action['capability_id'],c))
        roles=getattr(connector,'planning_input_roles',{})
        defaults=getattr(connector,'planning_input_defaults',{})
        for field in sorted(set(roles)|set(defaults)):
            role=roles.get(field)
            if field not in defaults and role not in ('workflow_key','action_key'):continue
            if field not in c['input_schema'].get('properties',{}):continue
            key=default_key(action['capability_id'],field)
            if key not in context['configuration']:continue
            if role=='action_key':
                key=key+'_'+digest(action['action_id'])[:16]
                context['configuration'][key]='action_'+digest([request_key,action['action_id'],action['capability_id']])[:32]
            replace_binding(action,field,'configuration',key,satisfied)
    from .action_bindings import content_target
    by_id={a.get('action_id'):a for a in actions}
    for action in actions:
        c=contracts.get(action.get('capability_id'),{})
        for binding in action.get('bindings',[]):
            if binding.get('kind')=='literal' and binding.get('key') not in context['user_values']:
                field=binding.get('target',[None])[0]
                if field in ('to','recipient') and 'recipient' in context['user_values']:
                    satisfied.add(binding['key']);binding['key']='recipient'
                elif content_target(binding.get('target',[])):
                    parents=[by_id[d] for d in action.get('depends_on',[]) if d in by_id and by_id[d].get('capability_id')=='content.prepare']
                    if parents and field in contracts['content.prepare']['output_schema']['properties']:
                        satisfied.add(binding['key'])
                        binding.update(kind='generated',action_id=parents[-1]['action_id'],path=[field]);binding.pop('key',None)
            if binding.get('kind') in ('generated','output','receipt') and binding.get('target'):satisfied.add(binding['target'][0])
    complete_binding_dependencies(actions)
    # Exact duplicate assignments carry no extra input or authority.
    for action in actions:
        unique=[]
        for binding in action.get('bindings',[]):
            if binding not in unique:unique.append(binding)
        action['bindings']=unique
        if action.get('capability_id')!='content.prepare':continue
        data=[b for b in unique if b.get('target',[None])[0]=='data']
        # Goal-mode runtime already supplies ALL explicit dependency outputs.
        # Coalesce whole-object content inputs only; never resolve conflicting
        # destinations, recipient fields, partial paths or receipt requirements.
        context_inputs=[b for b in data if b.get('kind')=='context']
        if data and all(b.get('target')==['data'] and b.get('path')==[] and (
                b.get('kind') in ('output','generated') and b.get('action_id') in action.get('depends_on',[]) or
                b.get('kind')=='context' and isinstance(context['validated_context'].get(b.get('key')),dict)) for b in data):
            if len(context_inputs)>1:
                key='content_context_'+digest(action['action_id'])[:16]
                context['validated_context'][key]={'contexts':{b['key']:deepcopy(context['validated_context'][b['key']]) for b in context_inputs}}
                first=dict(kind='context',key=key,path=[],target=['data'])
            else:first=deepcopy((context_inputs or data)[0])
            action['bindings']=[b for b in unique if b not in data]+[first]
    calendar_bindings(actions,contracts,context,satisfied)
    research_queries(actions,contracts,context)
    complete_binding_dependencies(actions)
    return satisfied


def replace_binding(action,field,kind,key,satisfied):
    bindings=action.setdefault('bindings',[])
    for binding in bindings:
        if binding.get('target')==[field] and binding.get('kind')=='literal':satisfied.add(binding.get('key'))
    action['bindings']=[b for b in bindings if b.get('target',[None])[0]!=field]
    action['bindings'].append(dict(kind=kind,key=key,path=[],target=[field]))
    satisfied.add(field)


def calendar_context(context,goal,selected):
    """Interpret fully specified local scheduling facts; never guess missing times."""
    if not selected:return
    if re.search(r'\bprimary\s+calendar\b',goal,re.I):
        context['validated_context']['primary_calendar_id']='primary'
    date_match=re.search(r'\b(\d{4}-\d{2}-\d{2})\b',goal)
    words=re.search(r'\b(\d{1,2})\s+(January|February|March|April|May|June|July|August|September|October|November|December)\s+(\d{4})\b',goal,re.I)
    clock=re.search(r'\b(\d{1,2})(?::(\d{2}))?\s*(AM|PM)\b|\b(\d{1,2}):(\d{2})\b',goal,re.I)
    zone=re.search(r'\b([A-Za-z_]+/[A-Za-z_]+(?:/[A-Za-z_]+)?)\b',goal)
    zone_name=zone[1] if zone else 'Asia/Kolkata' if re.search(r'\b(?:India(?:n)? (?:standard )?time)\b',goal,re.I) else None
    duration=re.search(r'\b(\d{1,3})[- ]minute\b',goal,re.I)
    if not (date_match or words) or not clock or not zone_name or not duration:return
    from datetime import datetime,timedelta
    from zoneinfo import ZoneInfo,ZoneInfoNotFoundError
    try:
        day=datetime.strptime(date_match[1],'%Y-%m-%d') if date_match else datetime.strptime(' '.join(words.groups()),'%d %B %Y')
        hour=int(clock[1] or clock[4]);minute=int(clock[2] or clock[5] or 0);period=clock[3]
        if period:
            if not 1<=hour<=12:return
            hour=hour%12+(12 if period.upper()=='PM' else 0)
        timezone=ZoneInfo(zone_name);start=day.replace(hour=hour,minute=minute,tzinfo=timezone)
        if start.utcoffset()!=start.replace(fold=1).utcoffset():return
        if not 1<=int(duration[1])<=999:return
        end=start+timedelta(minutes=int(duration[1]))
        if end.utcoffset()!=end.replace(fold=1).utcoffset():return
        context['validated_context']['calendar_event_start']={'dateTime':start.isoformat(),'timeZone':zone_name}
        context['validated_context']['calendar_event_end']={'dateTime':end.isoformat(),'timeZone':zone_name}
    except (ValueError,ZoneInfoNotFoundError):return


def calendar_bindings(actions,contracts,context,satisfied):
    values=context['validated_context']
    for action in actions:
        operation=contracts.get(action.get('capability_id'),{}).get('supported_operation','')
        if not operation.startswith('calendar.') or operation=='calendar.discover':continue
        bindings=action.setdefault('bindings',[])
        for path,key in [(['calendar_id'],'primary_calendar_id'),(['event','start'],'calendar_event_start'),(['event','end'],'calendar_event_end')]:
            if path[0]=='event' and operation not in ('calendar.create','calendar.update'):continue
            if key not in values or any(b['target'][:len(path)]==path or path[:len(b['target'])]==b['target'] for b in bindings):continue
            bindings.append(dict(kind='context',key=key,path=[],target=path))
            satisfied.add('.'.join(path))


def research_queries(actions,contracts,context):
    """Prepare search text as model content, rather than dispatching the whole goal."""
    context['validated_context']['research_request']={'objective':context['validated_context']['goal']}
    used={a['action_id'] for a in actions};additions=[]
    for action in actions:
        contract=contracts.get(action.get('capability_id'),{})
        if contract.get('supported_operation')!='research.search':continue
        for binding in action.get('bindings',[]):
            if binding.get('target')!=['query'] or binding.get('kind')!='context':continue
            from .action_bindings import binding_value
            from runtime.service import RuntimeFailure
            try:value=binding_value(binding,context,{})
            except RuntimeFailure:continue
            if value!=context['validated_context']['goal']:continue
            aid='query_'+digest(action['action_id'])[:16]
            if aid in used:continue
            limit=contract['input_schema']['properties']['query'].get('maxLength',500)
            additions.append(dict(action_id=aid,capability_id='content.prepare',depends_on=[],evidence_references=[],
                bindings=[dict(kind='context',key='research_request',path=[],target=['data'])],
                instructions=f'Derive a concise public-web search query from the supplied objective, at most {min(limit,500)} characters. Return it in query. Exclude email addresses, private complaint identifiers, private records, account details and instructions about delivery or tool execution. Preserve the requested public research subject and source preferences. Do not perform search or claim results.',
                budget=dict(max_llm_calls=1,max_tool_calls=0,max_retries=0,timeout_seconds=120),required_approvals=[],optional=False,when=None))
            used.add(aid);action['depends_on'].append(aid)
            binding.clear();binding.update(kind='generated',action_id=aid,path=['query'],target=['query'])
    actions[:0]=additions


def complete_binding_dependencies(actions):
    """Materialize data edges before validating and reviewing a new goal-mode plan.

    A reference to an existing action already declares that its result is needed.
    Schema, cycle, optional-source, approval and authority checks still run on
    the completed graph. No stored or approved revision is changed here.
    """
    known={a['action_id'] for a in actions}
    for action in actions:
        bindings=list(action.get('bindings',[]))
        if action.get('when'):bindings.append(action['when']['binding'])
        for binding in bindings:
            source=binding.get('action_id')
            if binding.get('kind') in ('output','generated','receipt') and source in known and source!=action['action_id'] and source not in action['depends_on']:
                action['depends_on'].append(source)
