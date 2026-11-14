"""Original-request Calendar facts; never replace explicit time with readiness defaults."""
from contextvars import ContextVar
from contextlib import contextmanager
from datetime import datetime
import re

_REQUEST_TIME=ContextVar('calendar_original_request_time',default=None)

@contextmanager
def original_request(timestamp):
    token=_REQUEST_TIME.set(timestamp)
    try:yield
    finally:_REQUEST_TIME.reset(token)

def request_timestamp(fallback):
    value=_REQUEST_TIME.get()
    return fallback if value is None else value

def explicit_timing(text,recurring=False):
    if recurring:
        # The workflow trigger is distinct from the Calendar session time.
        clause=re.search(r'\b(?:add|create|book|schedule|set up|arrange)\b[^.!?\n]*?\b(?:review|meeting|event|appointment)\b',text,re.I)
        if not clause:return False
        text=text[clause.start():]
        if not re.search(r'\b(?:today|tomorrow|\d{4}-\d{2}-\d{2})\b',text,re.I):return False
    return bool(re.search(r'\b(?:today|tomorrow|tonight|noon|midnight|\d{4}-\d{2}-\d{2})\b|\b\d{1,2}(?::\d{2})?\s*(?:AM|PM)\b|\b\d{1,2}:\d{2}\b|\bat\s+\d{1,2}\b',text,re.I))

def expected(workflow):
    meta=workflow.get('metadata',{});overview=meta.get('overview_intent',{})
    route=overview.get('route',{});text=meta.get('original_objective') or workflow.get('description','')
    if not explicit_timing(text,overview.get('schedule') is not None):return None
    anchor=overview.get('prepared_at')
    if not isinstance(anchor,(int,float)):return {}
    info=overview.get('communication',{});zone=(info.get('review') or {}).get('timezone')
    from .goal_inputs import calendar_context
    context={'validated_context':{}}
    calendar_context(context,text,True,now=anchor,timezone=zone)
    return context['validated_context'] if 'calendar_event_start' in context['validated_context'] else {}

def issues(workflow):
    meta=workflow.get('metadata',{});actions=meta.get('connected_action_plan',{}).get('actions',[])
    calendar=[a for a in actions if a.get('capability_id')=='tool.extension_calendar_create']
    if not calendar:return []
    target=expected(workflow)
    if target is None:return []
    if not target:return [('','The requested meeting date/time cannot be resolved from its original request context. Specify the date, exact time and IANA timezone.')]
    from .action_bindings import binding_value,put
    context=meta.get('action_binding_context',{});pin=meta.get('overview_intent',{}).get('communication',{}).get('review',{})
    found=[]
    for action in calendar:
        event={}
        for binding in action.get('bindings',[]):
            if binding.get('target',[None])[0]!='event':continue
            if binding.get('kind') not in ('literal','context','configuration'):continue
            try:put(event,binding['target'][1:],binding_value(binding,context,{}))
            except Exception:continue
        # Whole-event bindings are handled separately (put requires a path).
        for b in action.get('bindings',[]):
            if b.get('target')==['event'] and b.get('kind') in ('literal','context','configuration'):
                try:event=binding_value(b,context,{})
                except Exception:pass
        for field in ('start','end'):
            want=target['calendar_event_'+field];actual=event.get(field) if isinstance(event,dict) else None
            if actual!=want:
                label=datetime.fromisoformat(want['dateTime']).strftime('%Y-%m-%d %I:%M %p')
                shown=actual.get('dateTime','unresolved') if isinstance(actual,dict) else 'unresolved'
                found.append((action['action_id'],f'Requested meeting {field} is {label} ({want["timeZone"]}), but the generated event uses {shown}.'))
        if pin and pin.get('mode')!='fixed':found.append((action['action_id'],'An explicit meeting time cannot use after-report scheduling. Preserve the original fixed date/time.'))
    return found

def check_workflow(workflow,issue):
    for task,problem in issues(workflow):
        issue('Needs input',problem,task=task,resource='calendar_event_time',correction='Correct the editable draft from original request facts, or create a reviewed revision; changed event details require fresh exact-payload approval.')

def check_runtime(workflow,action,result):
    if action.get('capability_id')!='tool.extension_calendar_create':return
    target=expected(workflow)
    if target is None:return
    from runtime.service import RuntimeFailure
    if not target or any(result.get('event',{}).get(field)!=target['calendar_event_'+field] for field in ('start','end')):
        raise RuntimeFailure('CALENDAR_INTENT_MISMATCH','The Calendar payload differs from the original requested date/time. Review a corrected revision; no event was sent.',409)
