"""Reviewed same-day Calendar timestamps anchored to logical occurrences."""
from datetime import datetime
from zoneinfo import ZoneInfo
import re

from .goal_inputs import calendar_context
from .service import ApiFailure


def prepare_pin(objective, selected, due):
    if not re.search(r'\b(?:that(?: same)?|the same) day\b',objective,re.I):return None
    context={'validated_context':{}}
    calendar_context(context,re.sub(r'\b(?:that(?: same)?|the same) day\b','today',objective,flags=re.I),bool(selected),now=due)
    values=context['validated_context']
    if 'calendar_event_start' not in values or 'calendar_event_end' not in values:return None
    start=datetime.fromisoformat(values['calendar_event_start']['dateTime']);end=datetime.fromisoformat(values['calendar_event_end']['dateTime'])
    return dict(timezone=values['calendar_event_start']['timeZone'],hour=start.hour,minute=start.minute,duration_minutes=int((end-start).total_seconds()/60))


def values(pin,due):
    from datetime import timedelta
    if due is None:raise ApiFailure('AUTOMATION_SCOPE_DENIED','Logical Calendar occurrence time is missing.',403)
    zone=ZoneInfo(pin['timezone']);start=datetime.fromtimestamp(due,zone).replace(hour=pin['hour'],minute=pin['minute'],second=0,microsecond=0)
    end=start+timedelta(minutes=pin['duration_minutes'])
    for instant in (start,end):
        if instant.utcoffset()!=instant.replace(fold=1).utcoffset() or datetime.fromtimestamp(instant.timestamp(),zone)!=instant:
            raise ApiFailure('CALENDAR_TIME_INVALID','The reviewed event time is ambiguous or unavailable on this occurrence date.',422)
    return dict(calendar_event_start=dict(dateTime=start.isoformat(),timeZone=pin['timezone']),calendar_event_end=dict(dateTime=end.isoformat(),timeZone=pin['timezone']))
