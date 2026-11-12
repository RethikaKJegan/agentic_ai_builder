"""Reviewed Calendar timing, resolved once before exact action approval."""
from datetime import datetime,timedelta
from zoneinfo import ZoneInfo
from copy import deepcopy
from runtime.service import RuntimeFailure

ANNOTATION='x-praxi-calendar-review-v1'


def validate(pin):
    base={'mode','timezone','duration_minutes'}
    expected=base|({'lead_minutes','after_actions'} if pin.get('mode')=='after_ready' else {'hour','minute'} if pin.get('mode')=='fixed' else set())
    if 'on_date' in pin and pin.get('mode')=='fixed':expected.add('on_date')
    if set(pin)!=expected or pin.get('mode') not in ('fixed','after_ready'):raise RuntimeFailure('CALENDAR_REVIEW_INVALID','Choose when the reading session should start.',422)
    ZoneInfo(pin['timezone'])
    if type(pin['duration_minutes']) is not int or not 1<=pin['duration_minutes']<=999:raise RuntimeFailure('CALENDAR_REVIEW_INVALID','Choose a valid reading duration.',422)
    if pin['mode']=='fixed':
        if type(pin['hour']) is not int or type(pin['minute']) is not int or not 0<=pin['hour']<24 or not 0<=pin['minute']<60:raise RuntimeFailure('CALENDAR_REVIEW_INVALID','Choose a valid reading time.',422)
    elif pin['lead_minutes']!=5 or not isinstance(pin['after_actions'],list) or not pin['after_actions'] or len(pin['after_actions'])>16 or any(not isinstance(a,str) for a in pin['after_actions']):
        raise RuntimeFailure('CALENDAR_REVIEW_INVALID','The review must follow its completed report.',422)


def preview_values(pin,anchor):
    start=datetime.fromtimestamp(anchor,ZoneInfo(pin['timezone']))
    if pin['mode']=='after_ready':start+=timedelta(minutes=pin['lead_minutes'])
    else:
        if pin.get('on_date'):
            day=datetime.fromisoformat(pin['on_date']);start=start.replace(year=day.year,month=day.month,day=day.day)
        start=start.replace(hour=pin['hour'],minute=pin['minute'],second=0,microsecond=0)
    end=start+timedelta(minutes=pin['duration_minutes'])
    for instant in (start,end):
        if instant.utcoffset()!=instant.replace(fold=1).utcoffset() or datetime.fromtimestamp(instant.timestamp(),ZoneInfo(pin['timezone']))!=instant:
            raise RuntimeFailure('CALENDAR_REVIEW_INVALID','That review time is unavailable or ambiguous in this timezone.',422)
    return dict(calendar_event_start=dict(dateTime=start.isoformat(),timeZone=pin['timezone']),calendar_event_end=dict(dateTime=end.isoformat(),timeZone=pin['timezone']))


def bind_reports(actions,contracts,pin):
    calendar=[a for a in actions if contracts[a['capability_id']].get('supported_operation')=='calendar.create']
    by_id={a['action_id']:a for a in actions}
    reports=set()
    for event in calendar:
        for b in event['bindings']:
            if b.get('kind') in ('generated','output') and b.get('target') in (['event','summary'],['event','description']):
                parent=by_id.get(b.get('action_id'))
                if parent and parent['capability_id']=='content.prepare':reports.add(parent['action_id'])
    if pin['mode']=='after_ready':
        if not calendar or not reports:raise RuntimeFailure('ACTION_BINDING_INVALID','The review event needs the completed report summary.',422)
        pin['after_actions']=sorted(reports)
    validate(pin)


def runtime_values(pin,run,node_id,now,due=None):
    validate(pin)
    saved=run.setdefault('communication_calendar_times',{})
    if node_id not in saved:
        if pin['mode']=='after_ready' and any(run.get('action_instances',{}).get(a,{}).get('state')!='completed' for a in pin['after_actions']):
            raise RuntimeFailure('ACTION_DEPENDENCY_PENDING','The report must finish before scheduling the reading session.',409)
        anchor=now if pin['mode']=='after_ready' else due if due is not None else now
        saved[node_id]=dict(anchor=anchor,values=preview_values(pin,anchor))
    record=saved[node_id]
    if record['values']!=preview_values(pin,record['anchor']):raise RuntimeFailure('AUTOMATION_SCOPE_DENIED','The reviewed reading time changed.',403)
    if datetime.fromisoformat(record['values']['calendar_event_start']['dateTime']).timestamp()<=now:
        raise RuntimeFailure('CALENDAR_REVIEW_TIME_PASSED','The reading-session time has passed. Choose a new time; no Calendar action was sent.',409)
    return deepcopy(record['values'])
