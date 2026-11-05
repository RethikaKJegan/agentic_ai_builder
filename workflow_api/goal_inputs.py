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
            if not addresses and re.search(r'\b(?:email|mail|send)\s+(?:it\s+)?(?:to\s+)?me\b|\bmy (?:email|inbox)\b',body['objective'],re.I):
                context['user_values'].setdefault('recipient',row[4])


def default_key(cid,field):return 'operation_'+digest(cid)[:16]+'_'+field


def bind_internal(actions,contracts,context,connectors,tool_id,request_key):
    satisfied=set()
    for action in actions:
        c=contracts.get(action.get('capability_id'),{})
        if c.get('retrieval_task'):
            # Preparation and retrieval task identities are server-owned.
            for field,kind,key in [('preparation_id','context','preparation_id'),('task','configuration','task_'+c['retrieval_task'])]:
                if key not in context['validated_context' if kind=='context' else 'configuration']:continue
                replace_binding(action,field,kind,key,satisfied)
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
    return satisfied


def replace_binding(action,field,kind,key,satisfied):
    bindings=action.setdefault('bindings',[])
    for binding in bindings:
        if binding.get('target')==[field] and binding.get('kind')=='literal':satisfied.add(binding.get('key'))
    action['bindings']=[b for b in bindings if b.get('target',[None])[0]!=field]
    action['bindings'].append(dict(kind=kind,key=key,path=[],target=[field]))
    satisfied.add(field)
