"""Shared regression coverage for actual operation semantics and original meeting intent."""
from copy import deepcopy
from datetime import datetime
from types import SimpleNamespace
import pytest
from tests.test_workflow_readiness import context
from workflow_api.readiness import assess
from workflow_api.capability_contracts import fulfills,catalogue
from workflow_api.goal_inputs import calendar_context
from workflow_api.communication_intent import prepare
from workflow_api.communication_timing import runtime_values
from workflow_api.calendar_intent import issues,check_runtime,original_request,request_timestamp
from runtime.service import RuntimeFailure
from connector_extension.catalog import CATALOG

ANCHOR=datetime.fromisoformat('2026-11-14T23:50:00+05:30').timestamp()
GOALS=['Schedule an engine quality review tomorrow at 11 AM for 30 minutes. Add a short agenda about complaints and inspections.','Set up a 30-minute purchase-order review tomorrow at 11 AM and add an agenda about invoice discrepancies.','Can you arrange a review meeting tomorrow at 11 AM to discuss our engine failures and send me an email with the main issues we need to discuss?']

@pytest.mark.parametrize('tool,accept',[('extension_sheets_create',True),('extension_sheets_create_report',True),('google_sheets_read_rows',False),('extension_sheets_add_tabs',False)])
def test_registered_sheet_operations_are_not_interchangeable(context,tool,accept):
 s,w,a=context;cid='tool.'+tool
 w['metadata'].update(overview_intent={'route':{'side_effects':['sheet_create']}},connected_action_plan={'actions':[{'action_id':'sheet','capability_id':cid,'depends_on':[],'bindings':[]}]})
 with s.store.transaction(write=False) as db:r=assess(s,w,a,db)
 assert (not any(i['resource']=='sheet_create' for i in r['issues']))==accept

@pytest.mark.parametrize('denied,missing',[(True,False),(False,True)])
def test_fulfillment_does_not_bypass_auth_or_required_inputs(context,denied,missing):
 s,w,a=context;cid='tool.extension_sheets_create_report';definition=CATALOG['extension_sheets_create_report'];contract=catalogue(None,[{'definition':definition}])[cid]
 w['metadata'].update(connected_contracts={cid:contract},overview_intent={'route':{'side_effects':['sheet_create']}},connected_action_plan={'actions':[{'action_id':'sheet','capability_id':cid,'depends_on':[],'bindings':[]}]})
 if denied:s.registry_adapter.review=lambda *_:{'items':[{'authorization_state':'denied','reason_codes':['FORBIDDEN']}]}
 with s.store.transaction(write=False) as db:r=assess(s,w,a,db)
 assert not r['ready']
 assert not any(i['resource']=='sheet_create' for i in r['issues'])
 if missing:assert any(i['problem']=='A required action input has no binding.' for i in r['issues'])
 if denied:assert any('FORBIDDEN' in i['problem'] for i in r['issues'])

@pytest.mark.parametrize('goal',GOALS)
@pytest.mark.parametrize('zone',['Asia/Kolkata','America/New_York'])
def test_tomorrow_is_anchored_and_default_duration_is_visible(goal,zone):
 c={'validated_context':{}};calendar_context(c,goal,True,now=ANCHOR,timezone=zone)
 v=c['validated_context'];start=datetime.fromisoformat(v['calendar_event_start']['dateTime']);end=datetime.fromisoformat(v['calendar_event_end']['dateTime'])
 from zoneinfo import ZoneInfo
 assert start.date().toordinal()==datetime.fromtimestamp(ANCHOR,ZoneInfo(zone)).date().toordinal()+1
 assert (start.hour,start.minute)==(11,0) and (end-start).total_seconds()==1800

@pytest.mark.parametrize('goal',['Schedule tomorrow at 25:00 Asia/Kolkata','Schedule tomorrow at 11','Schedule tomorrow at noon','Schedule 2026-03-08 at 02:30 America/New_York','Schedule 2026-11-01 at 01:30 America/New_York'])
def test_unresolved_or_dst_ambiguous_times_never_get_a_default(goal):
 c={'validated_context':{}};calendar_context(c,goal,True,now=ANCHOR,timezone='Asia/Kolkata')
 assert 'calendar_event_start' not in c['validated_context']


def workflow():
 c={'validated_context':{}};calendar_context(c,GOALS[0],True,now=ANCHOR,timezone='Asia/Kolkata')
 return {'description':GOALS[0],'metadata':{'original_objective':GOALS[0],'overview_intent':{'prepared_at':ANCHOR,'schedule':None,'route':{},'communication':{'review':{'mode':'fixed','timezone':'Asia/Kolkata','duration_minutes':30,'hour':11,'minute':0,'on_date':'2026-11-15'}}},'action_binding_context':c,'connected_action_plan':{'actions':[{'action_id':'event','capability_id':'tool.extension_calendar_create','bindings':[{'kind':'context','key':'calendar_event_'+f,'path':[],'target':['event',f]} for f in ('start','end')]}]}}}


def test_11am_vs_6pm_is_blocked_in_validation_and_runtime():
 w=workflow();assert not issues(w)
 event={f:deepcopy(w['metadata']['action_binding_context']['validated_context']['calendar_event_'+f]) for f in ('start','end')}
 action=w['metadata']['connected_action_plan']['actions'][0];check_runtime(w,action,{'event':event})
 event['start']['dateTime']='2026-11-15T18:00:00+05:30'
 with pytest.raises(RuntimeFailure) as caught:check_runtime(w,action,{'event':event})
 assert caught.value.code=='CALENDAR_INTENT_MISMATCH'
 w['metadata']['action_binding_context']['validated_context']['calendar_event_start']=event['start']
 assert '11:00 AM' in issues(w)[0][1] and '18:00' in issues(w)[0][1]


def test_delayed_execution_preserves_original_date_and_fails_if_expired():
 w=workflow();pin=w['metadata']['overview_intent']['communication']['review'];run={}
 first=runtime_values(pin,run,'event',ANCHOR+3600)
 assert first['calendar_event_start']['dateTime']=='2026-11-15T11:00:00+05:30'
 assert runtime_values(pin,run,'event',ANCHOR+7200)==first
 with pytest.raises(RuntimeFailure) as caught:runtime_values(pin,run,'event',ANCHOR+86400)
 assert caught.value.code=='CALENDAR_REVIEW_TIME_PASSED'


def test_queue_arrival_timestamp_context_is_stable_and_scoped():
 with original_request(ANCHOR):assert request_timestamp(ANCHOR+86400)==ANCHOR
 assert request_timestamp(ANCHOR+86400)==ANCHOR+86400


def test_existing_resolved_dates_are_not_reinterpreted_at_compilation():
 w=workflow();c=w['metadata']['action_binding_context'];old=deepcopy(c)
 calendar_context(c,GOALS[0],True,now=ANCHOR+86400,timezone='Asia/Kolkata')
 assert c==old

@pytest.mark.parametrize('phrase,zone,minutes',[('tomorrow at 11 AM UTC for 1 hour','UTC',60),('tomorrow from 11 AM to 12 PM Asia/Kolkata','Asia/Kolkata',60)])
def test_explicit_utc_and_duration_intervals(phrase,zone,minutes):
 c={'validated_context':{}};calendar_context(c,'Schedule a meeting '+phrase,True,now=ANCHOR,timezone='Asia/Kolkata')
 v=c['validated_context'];assert v['calendar_event_start']['timeZone']==zone
 assert (datetime.fromisoformat(v['calendar_event_end']['dateTime'])-datetime.fromisoformat(v['calendar_event_start']['dateTime'])).total_seconds()==minutes*60


def test_ambiguous_timezone_is_not_replaced_by_workspace_zone():
 c={'validated_context':{}};calendar_context(c,'Schedule a meeting tomorrow at 11 AM CST',True,now=ANCHOR,timezone='Asia/Kolkata')
 assert 'calendar_event_start' not in c['validated_context']
