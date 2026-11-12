"""Workflow subscriptions over DurableAutomation records and lifecycle jobs.

Adapters are installed by the server. Request bodies and event payloads cannot
create adapters, credentials, tenant identity or executable authority.
"""
from copy import deepcopy
import json
from datetime import datetime
from zoneinfo import ZoneInfo
from jsonschema import Draft202012Validator
from registry.safety import reject_secrets
from registry.contracts import RegistryError
from .service import ApiFailure
from .lifecycle import LifecycleFailure
from runtime.service import RuntimeService
from .business_cases import fail
from .business_knowledge_model import canonical,digest


def sources(auto,auth):
    result=[]
    for provider,adapter in auto.providers.items():
        if not all(callable(getattr(adapter,m,None)) for m in ('workflow_sources','authenticate','poll_workflow')):continue
        for source in adapter.workflow_sources(auth):
            if not isinstance(source,dict) or not {'source_id','event_type','payload_schema'}<=set(source) or set(source)-{'source_id','event_type','payload_schema','query_bindings'}:continue
            reject_secrets(source)
            if len(canonical(source))>12000:continue
            Draft202012Validator.check_schema(source['payload_schema'])
            # No remote schema references or dynamically fetched authority.
            def local(v):
                if isinstance(v,dict):return not ({'$ref','$dynamicRef'}&set(v)) and all(local(x) for x in v.values())
                return all(local(x) for x in v) if isinstance(v,list) else True
            if local(source):result.append(dict(provider=provider,**deepcopy(source)))
    if len(result)>32:fail('Configured event source catalogue exceeds its bound.')
    return result


def validate_source(auto,auth,pin):
    if not isinstance(pin,dict) or set(pin)!={'provider','source_id','event_type','timezone'}:fail('Pin an authorized source and event type.')
    try:ZoneInfo(pin['timezone'])
    except (ValueError,KeyError,TypeError):fail('Use an IANA event reporting timezone.')
    source=next((s for s in sources(auto,auth) if all(s[k]==pin[k] for k in ('provider','source_id','event_type'))),None)
    if source is None:fail('No configured authenticated business-event source matches this request.','AUTOMATION_EVENT_SOURCE_UNAVAILABLE',403)
    return source


def matches(value,condition):
    target=condition['value'];op=condition['op']
    numeric=type(value) in (int,float) and type(target) in (int,float)
    equal=(numeric or type(value) is type(target)) and value==target
    if op=='eq':return equal
    if op=='ne':return not equal
    if not numeric:return False
    return {'gt':lambda:value>target,'gte':lambda:value>=target,'lt':lambda:value<target,'lte':lambda:value<=target}[op]()


def subscribe(auto,auth,body):
    doc=auto._document(auth,'subscription',body)
    RuntimeService.authorize(auth,'events.ingest',{'admin','builder'})
    old=auto._existing(doc)
    if old:return old
    workflow=auto._workflow(auth,body['workflow']);policy=auto.get(auth,body['authorization_id'])
    if policy['kind']!='authorization' or policy['state']!='active' or not auto.clock()<body['expires_at']<=policy['request']['expires_at']:fail('An active bounded event authorization is required.','AUTOMATION_AUTH_EXPIRED',403)
    pin=policy['request']['schedule']
    if any(body[k]!=pin.get(k) for k in ('provider','source_id','event_type')):fail('Event source differs from reviewed authorization.','AUTOMATION_SCOPE_DENIED',403)
    source=validate_source(auto,auth,pin)
    reviewed=workflow.get('metadata',{}).get('overview_intent',{}).get('event_subscription')
    if reviewed and body['conditions']!=reviewed.get('conditions',[]):fail('Event conditions differ from the reviewed workflow.','AUTOMATION_SCOPE_DENIED',403)
    if workflow.get('metadata',{}).get('google_connection_id')!=policy['request']['connection_id']:fail('Event workflow account differs from authorization.')
    bindings=source.get('query_bindings',[])
    catalog=workflow.get('metadata',{}).get('action_binding_context',{}).get('validated_context',{}).get('subway_query_catalog',{})
    fields={f['field_id'] for d in catalog.get('sources',[]) for f in d['fields']}
    if not isinstance(bindings,list) or len(bindings)>8 or any(not isinstance(b,dict) or set(b)!={'field_id','path'} or b['field_id'] not in fields or not isinstance(b['path'],str) or not 1<=len(b['path'])<=512 for b in bindings):fail('Event entity bindings require fields in the reviewed query catalogue.','AUTOMATION_SCOPE_DENIED',403)
    try:
        for binding in bindings:auto.service.lifecycle.event_path(binding['path'])
        for condition in body['conditions']:auto.service.lifecycle.event_path(condition['path'])
    except LifecycleFailure:fail('Event mappings require literal field paths.','AUTOMATION_EVENT_INVALID',422)
    doc['query_bindings']=deepcopy(bindings)
    doc.update(name=policy['request']['purpose'],workflow_sha256=digest(workflow),payload_schema=source['payload_schema'],due=auto.clock(),occurrences=0,cursor=None,processed_count=0)
    return auto._put(doc)


def accept(auto,auth,sub,event):
    scope=auto.scope(auth,True)
    RuntimeService.authorize(auth,'events.ingest',{'admin','builder'})
    body=sub['request'];policy=auto.get(auth,body['authorization_id'])
    source=validate_source(auto,auth,policy['request']['schedule'])
    if source['payload_schema']!=sub['payload_schema'] or source.get('query_bindings',[])!=sub.get('query_bindings',[]):fail('Event source mapping changed; review the subscription again.','AUTOMATION_SCOPE_DENIED',403)
    adapter=auto.providers[body['provider']]
    # Verification precedes persistence and deduplication. Every replay authenticates.
    if adapter.authenticate(sub,event,auth) is not True:fail('Business-event authentication failed.','AUTOMATION_EVENT_AUTH_FAILED',403)
    reject_secrets(event)
    if not isinstance(event,dict) or not {'event_id','payload','occurred_at'}<=set(event) or set(event)-{'event_id','payload','occurred_at','sequence'} or not isinstance(event['event_id'],str) or not 1<=len(event['event_id'])<=200 or len(canonical(event))>50000:fail('Use a bounded authenticated event envelope.','AUTOMATION_EVENT_INVALID',422)
    try:
        stamp=datetime.fromisoformat(event['occurred_at'].replace('Z','+00:00'))
        if stamp.tzinfo is None:raise ValueError()
        due=stamp.timestamp()
    except (ValueError,TypeError,AttributeError):fail('Event time must include a timezone.','AUTOMATION_EVENT_INVALID',422)
    if 'sequence' in event and (type(event['sequence']) is not int or event['sequence']<0):fail('Event sequence must be a nonnegative integer.')
    invalid=bool(list(Draft202012Validator(sub['payload_schema']).iter_errors(event['payload'])))
    with auto.store.transaction() as db:
        current=auto._get(db,scope,sub['id'],'subscription');policy=auto._get(db,scope,body['authorization_id'],'authorization')
        row=db.execute('SELECT document FROM automation_deliveries WHERE workspace=? AND owner=? AND subscription=? AND event_id=?',(*scope,sub['id'],event['event_id'])).fetchone()
        if row:
            saved=json.loads(row[0])
            if saved['fingerprint']!=digest(event):fail('Event identity was reused with different content.','AUTOMATION_CONFLICT',409)
            current['duplicate_count']=current.get('duplicate_count',0)+1;auto._save(db,current)
            return dict(accepted=False,duplicate=True,occurrence_id=saved.get('occurrence_id'))
        if current['state']!='active' or policy['state']!='active' or min(body['expires_at'],policy['request']['expires_at'])<=auto.clock():return dict(accepted=False,reason='inactive')
        reason='invalid_payload' if invalid else 'out_of_order' if event.get('sequence',current.get('sequence',-1)+1)<=current.get('sequence',-1) else 'future_event' if due>auto.clock()+300 else None
        entity_filters=[]
        if not reason:
            try:
                for binding in sub.get('query_bindings',[]):
                    value=auto.service.lifecycle._lookup(event['payload'],binding['path'])
                    if type(value) not in (str,int,float,bool) or isinstance(value,str) and len(value)>500:raise ValueError()
                    entity_filters.append(dict(field_id=binding['field_id'],op='eq',value=value))
            except (KeyError,IndexError,TypeError,ValueError,LifecycleFailure):reason='invalid_entity_binding'
        if not reason:
            for condition in body['conditions']:
                try:value=auto.service.lifecycle._lookup(event['payload'],condition['path'])
                except (KeyError,IndexError,TypeError,ValueError,LifecycleFailure):reason='conditions_not_matched';break
                if not matches(value,condition):reason='conditions_not_matched';break
        if not reason and policy['used_occurrences']>=policy['request']['limits']['max_occurrences']:reason='occurrence_limit'
        if not reason and body['overlap_policy']=='forbid':
            active=db.execute("SELECT 1 FROM automation_records WHERE workspace=? AND owner=? AND kind='occurrence' AND json_extract(document,'$.schedule_id')=? AND state IN ('queued','running','waiting','requires_reconciliation')",(*scope,sub['id'])).fetchone()
            if active:return dict(accepted=False,reason='overlap_deferred') # Cursor stays uncommitted; provider must replay.
        receipt=dict(fingerprint=digest(event),status=reason or 'accepted',received_at=auto.clock())
        if reason:
            current['rejected_count']=current.get('rejected_count',0)+1
            current['last_error_code']='AUTOMATION_EVENT_'+reason.upper()
        else:
            identifier='occ_'+digest([scope,sub['id'],event['event_id']])[:32]
            occurrence=dict(id=identifier,kind='occurrence',workspace_id=scope[0],owner_id=scope[1],schedule_id=sub['id'],state='queued',due=due,created_at=auto.clock(),errors=[],attempts=0,run_id=None,
                trigger=dict(kind='event',automation_id=sub['id'],event_id=event['event_id'],provider=body['provider'],source_id=body['source_id'],event_type=body['event_type'],query_filters=entity_filters,payload=deepcopy(event['payload']),qualification='Authenticated adapter event; not a business conclusion.'))
            occurrence['job_id']=auto._enqueue(db,scope,identifier,identifier,'occurrence',serialization_key='subscription:'+sub['id'] if body['overlap_policy']=='forbid' else None)
            auto._save(db,occurrence);receipt['occurrence_id']=identifier
            current['occurrences']+=1;current['processed_count']+=1;policy['used_occurrences']+=1
        if 'sequence' in event:current['sequence']=max(current.get('sequence',-1),event['sequence'])
        db.execute('INSERT INTO automation_deliveries VALUES (?,?,?,?,?)',(*scope,sub['id'],event['event_id'],canonical(receipt)))
        auto._save(db,current);auto._save(db,policy)
    return dict(accepted=reason is None,duplicate=False,reason=reason,occurrence_id=receipt.get('occurrence_id'))


def poll(auto,auth,sub):
    if sub['request']['expires_at']<=auto.clock():
        with auto.store.transaction() as db:
            current=auto._get(db,auto.scope(auth),sub['id']);current['state']='expired';auto._save(db,current)
        return
    events,cursor=auto.providers[sub['request']['provider']].poll_workflow(sub,auth)
    if not isinstance(events,list) or len(events)>100:fail('Event adapter exceeded its bounded batch.')
    for event in events:
        try:
            if accept(auto,auth,sub,event).get('reason')=='overlap_deferred':return
        except (ApiFailure,RegistryError) as error:
            if error.code not in {'AUTOMATION_EVENT_INVALID','AUTOMATION_CONFLICT','SENSITIVE_DATA_DETECTED','INVALID_REQUEST'}:raise
            # An authenticated poison envelope cannot indefinitely block its batch.
            if auto.providers[sub['request']['provider']].authenticate(sub,event,auth) is not True:raise
            fingerprint=digest(event);identity='poison:'+fingerprint
            with auto.store.transaction() as db:
                scope=auto.scope(auth,True);current=auto._get(db,scope,sub['id'])
                old=db.execute('SELECT 1 FROM automation_deliveries WHERE workspace=? AND owner=? AND subscription=? AND event_id=?',(*scope,sub['id'],identity)).fetchone()
                if not old:
                    db.execute('INSERT INTO automation_deliveries VALUES (?,?,?,?,?)',(*scope,sub['id'],identity,canonical(dict(status='dead_letter',fingerprint=fingerprint,error_code=error.code,received_at=auto.clock()))))
                    current['rejected_count']=current.get('rejected_count',0)+1;current['last_error_code']='AUTOMATION_EVENT_POISON';auto._save(db,current)

    with auto.store.transaction() as db:
        current=auto._get(db,auto.scope(auth),sub['id']);current.update(cursor=cursor,poll_after=auto.clock()+15,last_polled_at=auto.clock());auto._save(db,current)
