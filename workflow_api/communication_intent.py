"""Owned destination resolution and human communication choices, before planning."""
from copy import deepcopy
import re


def requested(text):
    return bool(re.search(r'\b(?:email|mail|calendar|meeting|appointment)\b|\b(?:schedule|arrange|set up|book)\b[^.!?]{0,100}\breview\b',text,re.I))


def question(field, text, options):
    return dict(field=field,question=text,options=[dict(value=value,label=label) for value,label in options])


def account(service, auth, body):
    """No provider call, connection mutation or cross-owner fallback."""
    google=getattr(service,'google_tools',None)
    if not google:return None,question('communication_connection_id','Connect a Google account to send email or schedule a review.',[])
    manager=google.manager
    identifier=body.get('google_connection_id') or body.get('user_values',{}).get('communication_connection_id')
    if identifier:
        with service.store.transaction(write=False) as db:row=manager.owned(db,auth,identifier)
        if row[6]!='connected' or not row[7]:
            return None,question('communication_connection_id','Reconnect the selected Google account before continuing.',[])
        return dict(connection_id=row[0],email=row[4]),None
    default=manager.workflow_default(auth)
    if default:return account(service,auth,{**body,'google_connection_id':default})
    choices=[item for item in manager.list(auth)['items'] if item['status']=='connected']
    if len(choices)==1:return account(service,auth,{**body,'google_connection_id':choices[0]['connection_id']})
    return None,question('communication_connection_id','Which connected Google account should I use?' if choices else 'Connect a Google account to send email or schedule a review.',[(item['connection_id'],item['account_email']) for item in choices])


def prepare(service,auth,body,route,schedule,resolved,timezone=None,reference_time=None):
    """All choices become reviewed source values; never model authority."""
    text=body['objective'];answers=body.get('user_values',{});route=deepcopy(route)
    selected,missing=account(service,auth,body)
    if missing:return route,None,[missing]
    info={**selected,'calendar_id':None,'recipient':None,'review':None}
    questions=[]
    # Generate a reviewable delivery workflow; normal approval still precedes sending.
    email=bool(re.search(r'\b(?:email|mail)\b',text,re.I))
    delivery=answers.get('email_delivery')
    explicit_draft=bool(re.search(r'\b(?:draft|do not send|don.t send)\b',text,re.I))
    if email:
        if delivery not in (None,'send','draft'):
            questions.append(question('email_delivery','Should I email the report or prepare a draft?',[('send','Email it to me'),('draft','Prepare a draft')]));delivery=None
        if not delivery:delivery='draft' if explicit_draft else 'send'
        if delivery is None:questions.append(question('email_delivery','Should I email the report to you, or prepare a draft for review?',[('send','Email it to me'),('draft','Prepare a draft')]))
        else:
            route['side_effects']=[s for s in route['side_effects'] if s not in ('email_send','email_draft')]+['email_send' if delivery=='send' else 'email_draft']
            addresses=re.findall(r'\b[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}\b',text)
            if route.get('recipient_mode')=='other' and not answers.get('recipient') and not addresses:
                questions.append(question('recipient','Who should receive the report?',[]))
            info['recipient']=answers.get('recipient') or (addresses[0] if len(set(addresses))==1 else selected['email'])
            route['recipient_mode']='explicit' if addresses or answers.get('recipient') else 'selected_account'
    if 'calendar_write' in route['side_effects']:
        # Primary is a Google-owned alias in the selected account; never invent an ID.
        info['calendar_id']=answers.get('calendar_id') or resolved['validated_context'].get('primary_calendar_id')
        if not info['calendar_id']:
            named=bool(re.search(r'\bcalendar\s+(?:called|named)\b|\b(?:team|shared|work|personal)\s+calendar\b',text,re.I))
            if named:
                choices=calendar_choices(service,auth,selected)
                questions.append(question('calendar_id','Which connected calendar should I use?' if choices else 'I can use your primary calendar. To choose another, connect calendar-list access in Integrations.',choices or [('primary','Use my primary calendar')]))
            else:
                connector=getattr(getattr(service,'runtime_runner',None),'connectors',{}).get('extension_calendar_create')
                allowed=sorted(getattr(connector,'calendars',[]))
                if not allowed or 'primary' in allowed:info['calendar_id']='primary'
                elif len(allowed)==1:info['calendar_id']=allowed[0]
                else:
                    choices=calendar_choices(service,auth,selected)
                    questions.append(question('calendar_id','Which available calendar should I use?',choices or [(v,v) for v in allowed]))
        duration=re.search(r'\b(\d{1,3})[- ]minutes?\b',text,re.I)
        minutes=answers.get('review_duration_minutes') or (int(duration[1]) if duration else 30)
        if isinstance(minutes,str) and minutes.isdigit():minutes=int(minutes)
        if type(minutes) is not int:minutes=None
        mode=answers.get('review_timing')
        if mode not in (None,'fixed','after_ready'):
            questions.append(question('review_timing','When should the reading session start?',[('after_ready','After the report is ready'),('fixed','At a fixed time')]));mode=None
        if not mode and re.search(r'\bafter\b[^.!?]{0,70}\b(?:ready|completed|finished|report|findings)\b',text,re.I):mode='after_ready'
        from .calendar_intent import explicit_timing
        explicit=explicit_timing(text,schedule is not None)
        if explicit and not resolved['validated_context'].get('calendar_event_start'):
            from .goal_inputs import calendar_context
            calendar_context(resolved,text,True,now=reference_time,timezone=answers.get('review_timezone') or timezone or route['recurrence'].get('timezone'))
        fixed=resolved['validated_context'].get('calendar_event_start')
        if explicit and not fixed:
            questions.append(question('review_time','Specify the meeting date, exact time and IANA timezone; the requested time could not be resolved safely.',[]))
            return route,info,questions
        if explicit and mode=='after_ready':
            questions.append(question('review_timing','The requested fixed meeting time conflicts with after-report timing. Confirm the intended schedule.',[]))
            return route,info,questions
        if fixed and mode is None:mode='fixed'
        if mode is None:
            mode='fixed' if answers.get('review_time') or re.search(r'\b(?:fixed time|specific time)\b',text,re.I) else 'after_ready'
        zone=(schedule or {}).get('timezone') or route['recurrence'].get('timezone') or timezone
        zone=answers.get('review_timezone') or zone
        if isinstance(zone,str) and zone.lower() in ('india','india time','indian standard time'):zone='Asia/Kolkata'
        try:
            from zoneinfo import ZoneInfo
            ZoneInfo(zone or '')
        except (ValueError,TypeError,KeyError):
            questions.append(question('review_timezone','Which timezone should the reading session use?',[]));zone=None
        if not mode:questions.append(question('review_timing','When would you like the reading session: at a fixed time or after the report is ready?',[('after_ready','After the report is ready'),('fixed','At a fixed time')]))
        if not minutes or not 1<=minutes<=999:questions.append(question('review_duration_minutes','How many minutes should the review last?',[]))
        if mode=='fixed' and not fixed and not re.fullmatch(r'(?:[01]\d|2[0-3]):[0-5]\d',str(answers.get('review_time',''))):
            questions.append(question('review_time','What time should the review start?',[]))
        if mode and minutes and zone:
            if mode=='after_ready':info['review']=dict(mode=mode,timezone=zone,duration_minutes=minutes,lead_minutes=5)
            elif fixed:
                from datetime import datetime
                start=datetime.fromisoformat(fixed['dateTime']);info['review']=dict(mode='fixed',timezone=fixed['timeZone'],duration_minutes=minutes,hour=start.hour,minute=start.minute)
                if schedule is None:info['review']['on_date']=start.date().isoformat()
            elif re.fullmatch(r'(?:[01]\d|2[0-3]):[0-5]\d',str(answers.get('review_time',''))):
                hour,minute=map(int,answers['review_time'].split(':'));info['review']=dict(mode='fixed',timezone=zone,duration_minutes=minutes,hour=hour,minute=minute)
    if info.get('recipient'):
        cid='extension_mail_draft' if delivery=='draft' else 'extension_mail_send'
        connector=getattr(getattr(service,'runtime_runner',None),'connectors',{}).get(cid)
        if connector and callable(getattr(connector,'recipient',None)):
            from runtime.service import RuntimeFailure
            try:connector.recipient(info['recipient'])
            except RuntimeFailure:
                allowed=sorted(getattr(connector,'recipients',[]))
                questions.append(question('recipient','This email setup restricts recipients. Which approved address should receive the report?',[(v,v) for v in allowed]))
    return route,info,questions


def review_lines(info):
    if not info:return []
    lines=['Connected account: '+info['email']]
    if info.get('recipient'):lines.append('Report recipient: '+info['recipient'])
    if info.get('calendar_id'):lines.append('Review calendar: '+('Primary calendar' if info['calendar_id']=='primary' else 'Selected calendar'))
    pin=info.get('review')
    if pin:
        when='5 minutes after the report is ready' if pin['mode']=='after_ready' else f"{pin.get('on_date','')} {pin['hour']:02d}:{pin['minute']:02d} ({pin['timezone']})".strip()
        lines.append(f"Reading session: {pin['duration_minutes']} minutes, starting {when}.")
    return lines


def calendar_choices(service,auth,selected):
    """Bounded existing Calendar metadata reader, using only the owned account.

    No model-supplied endpoint, writes, fallback token or scope escalation.
    Discovery is optional; without existing consent only Primary is proposed.
    """
    connector=getattr(getattr(service,'runtime_runner',None),'connectors',{}).get('extension_calendar_discover')
    if connector is None or 'calendar.read' not in auth.get('permissions',[]):return []
    visible={item['tool_id'] for item in service.business_composition.tools(auth)}
    if 'extension_calendar_discover' not in visible:return []
    from .google_tools import OwnedToken
    from connector_extension.google import GoogleAPI
    from copy import copy
    from time import monotonic
    from runtime.service import RuntimeFailure
    try:
        token=OwnedToken(service.google_tools.manager,auth,selected['connection_id'])
        # Scope validation precedes any provider request.
        row=token.record()
        import json
        if 'https://www.googleapis.com/auth/calendar.calendarlist.readonly' not in json.loads(row[5]):return []
        reader=copy(connector);reader.api=GoogleAPI(token,connector.api.transport)
        result=reader.execute(None,{'limit':100},'owned-calendar-metadata',monotonic()+10)
        return [(item['calendar_id'],item['name'] or ('Primary calendar' if item['primary'] else 'Unnamed calendar')) for item in result['calendars'] if item.get('access_role') in ('owner','writer')]
    except RuntimeFailure:return []
