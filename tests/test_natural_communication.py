from copy import deepcopy
from types import SimpleNamespace
from datetime import datetime
import pytest
from tests.test_overview_automation_integration import automation,google_setup,connected,composition,investigation,retrieval,knowledge,reference,generation,foundation,auth,release,queries,setup_query,action,bind,approve,stored,drain,intent
from tests.test_google_tools import add_scopes
from workflow_api.overview_automation import OverviewAutomation
from workflow_api.communication_timing import runtime_values,validate
from runtime.service import RuntimeFailure

GOAL='Every day at 10:20 PM India time, investigate procurement exceptions and prepare an email report and a calendar event for 30 minutes to read and understand about it better'


def test_after_ready_times_are_future_stable_and_require_completed_report():
 pin=dict(mode='after_ready',timezone='Asia/Kolkata',duration_minutes=30,lead_minutes=5,after_actions=['report'])
 run={'action_instances':{'report':{'state':'completed'}}};now=1794499200
 first=runtime_values(pin,run,'calendar',now)
 assert datetime.fromisoformat(first['calendar_event_start']['dateTime']).timestamp()==now+300
 assert runtime_values(pin,run,'calendar',now+120)==first
 with pytest.raises(RuntimeFailure) as caught:runtime_values(pin,run,'calendar',now+301)
 assert caught.value.code=='CALENDAR_REVIEW_TIME_PASSED'
 with pytest.raises(RuntimeFailure):runtime_values(pin,{'action_instances':{}},'calendar',now)
 forged=deepcopy(run);forged['communication_calendar_times']['calendar']['values']['calendar_event_end']['dateTime']='2040-01-01T00:00:00+05:30'
 with pytest.raises(RuntimeFailure):runtime_values(pin,forged,'calendar',now+120)


@pytest.mark.parametrize('expire_review',[False,True])
def test_direct_generation_then_two_reviewed_email_calendar_occurrences(automation,queries,expire_review):
 f=automation;f.connectors['extension_mail_send'].recipients=frozenset(['owner@example.com','engineer@example.com']);add_scopes(f.manager,f.connection,['gmail.send','calendar.events'])
 jobs,seen,inputs,body=setup_query(f,queries)
 body.pop('automatic_inputs',None);body.pop('google_connection_id',None);body['objective']=GOAL;body['user_values']={};body['request_key']='natural_initial'
 route=intent('recurring');route.update(side_effects=['calendar_write']);route['temporal']['period']='none';route['recurrence'].update(hour=22,minute=20)
 calls=[]
 def propose(goal,context):
  calls.append(deepcopy(context))
  read=action('read','tool.workflow_data_query',[bind('context','query','reviewed_query')])
  report=action('report','content.prepare',[bind('output','data',action='read')],['read'],['read'])
  mail=action('mail','tool.extension_mail_send',[bind('generated','subject',action='report',path=['title']),bind('generated','body',action='report',path=['summary'])],['report'])
  calendar=action('review','tool.extension_calendar_create',[bind('generated','event.summary',action='report',path=['title']),bind('generated','event.description',action='report',path=['summary'])],['report','mail'])
  return dict(actions=[read,report,mail,calendar],completion_criteria=['mail','review'],missing_inputs=[])
 f.general.planner.provider=SimpleNamespace(plan_actions=propose)
 r=OverviewAutomation(f.general,dict(BUILDER_OVERVIEW_ROUTING_ENABLED='1',BUILDER_OVERVIEW_ROUTING_WORKSPACES='one',BUILDER_NATURAL_COMMUNICATION_ENABLED='1',BUILDER_WORKSPACE_TIMEZONE='Asia/Kolkata'),interpreter=lambda *_:deepcopy(route))
 result=r.handle(f.x.a,body);assert result['state']=='prepared',result
 assert len(calls)==1 and not result.get('clarifications') and not result.get('communication_review')
 assert result['schedule']['cron']=='20 22 * * *'
 doc=f.c.get(f.x.a,result['composition_id']);pin=doc['overview_intent']['communication']['review']
 assert pin['after_actions']==['report']
 assert result['operations']['extension_mail_send']['properties']['to']=={'const':'owner@example.com'}
 assert result['operations']['extension_calendar_create']['properties']['calendar_id']=={'const':'primary'}
 w=f.c.workflow(f.x.a,result['composition_id']);assert f.adapter.approve_pending(w,f.x.a)['ready'];w=approve(f,w)
 active=r.handle(f.x.a,dict(operation='activate',request_key=body['request_key']))
 if expire_review:
  original_approve=f.auto._approve;delayed=[]
  def late(auth,run):
   if not delayed and run['approvals'][-1].get('resolved_payload',{}).get('event'):
    f.now+=301;delayed.append(True)
   return original_approve(auth,run)
  f.auto._approve=late
 for day in range(1 if expire_review else 2):
  f.now=f.auto.get(f.x.a,active['schedule_id'])['due']
  f.auto.tick(f.general.worker_authenticate);drain(f);assert jobs.tick()
  f.now+=2;f.auto.tick(f.general.worker_authenticate);drain(f)
  history=f.auto.history(f.x.a,active['schedule_id']);assert len(history)==day+1
  if expire_review:
   f.now+=1;f.auto.tick(f.general.worker_authenticate);drain(f);history=f.auto.history(f.x.a,active['schedule_id'])
   assert history[0]['state'] in ('failed','dead_letter') and len(f.http.sent)==1 and not f.http.events
   old=stored(f,history[0]['run_id']);assert old['error_code']=='CALENDAR_REVIEW_TIME_PASSED' and not old.get('node_invocations',{}).get('review')
   mail=deepcopy(old['action_instances']['mail']);sent=[message.as_bytes() for message in f.http.sent]
   recovery_body=dict(operation='recover_calendar',request_key='calendar_recovery_test',composition_id=result['composition_id'],run_id=old['run_id'])
   recovery=r.handle(f.x.a,recovery_body);assert recovery==r.handle(f.x.a,recovery_body)
   new=f.c.get(f.x.a,recovery['composition_id']);assert {a['capability_id'] for a in new['action_plan']['actions']}=={'tool.extension_calendar_create'}
   nw=f.c.workflow(f.x.a,new['composition_id']);assert f.adapter.approve_pending(nw,f.x.a)['ready'];nw=approve(f,nw)
   created=f.runtime.create_run(dict(request_id='calendar_only_recovery',idempotency_key='calendar_only_recovery',payload=dict(workflow_id=nw['workflow_id'],workflow_version=nw['version'],inputs={})),f.x.a)
   from tests.test_connected_action_plans import complete
   assert complete(f,nw,created['run_id'])['status']=='completed'
   assert len(f.http.events)==1 and [message.as_bytes() for message in f.http.sent]==sent and stored(f,old['run_id'])['action_instances']['mail']==mail
   with f.general.store.transaction() as db:
    changed=f.runtime.load(db,old['run_id'],f.x.a);changed['node_invocations']['review']='possibly_dispatched';f.runtime.save(db,changed)
   with pytest.raises(Exception):r.handle(f.x.a,{**recovery_body,'request_key':'unknown_write_rejected'})
   return
  assert all(o['state']=='completed' for o in history),[(o.get('last_error_code'),stored(f,o['run_id']).get('node_states')) for o in history]
  assert len(f.http.sent)==len(f.http.events)==day+1
  run=stored(f,history[-1]['run_id']);assert run['action_instances']['mail']['verified_receipt']
  start=datetime.fromisoformat(f.http.events[-1]['start']['dateTime']).timestamp();assert start>f.now
  assert datetime.fromisoformat(f.http.events[-1]['end']['dateTime']).timestamp()-start==1800


def test_account_selection_is_scoped_and_asks_only_for_ambiguity(automation):
 from workflow_api.communication_intent import account
 f=automation;body={'objective':GOAL,'user_values':{}}
 selected,missing=account(f.general,f.x.a,body);assert selected['connection_id']==f.connection and not missing
 with f.general.store.transaction() as db:
  original=list(db.execute('SELECT * FROM google_connections WHERE connection_id=?',(f.connection,)).fetchone())
  own=original.copy();own[0]='gc_'+'b'*32;own[3]='second-account';own[4]='second@example.com';db.execute('INSERT INTO google_connections VALUES ('+','.join('?' for _ in own)+')',own)
  foreign=original.copy();foreign[0]='gc_'+'c'*32;foreign[1]='foreign';foreign[2]='foreign-owner';foreign[3]='foreign-account';foreign[4]='foreign@example.com';db.execute('INSERT INTO google_connections VALUES ('+','.join('?' for _ in foreign)+')',foreign)
 selected,missing=account(f.general,f.x.a,body);assert not selected
 assert {o['label'] for o in missing['options']}=={'owner@example.com','second@example.com'}
 with pytest.raises(Exception):account(f.general,f.x.a,{**body,'google_connection_id':foreign[0]})
 f.manager.set_workflow_default(f.x.a,f.connection)
 selected,missing=account(f.general,f.x.a,body);assert selected['connection_id']==f.connection and not missing
 f.manager.disconnect(f.x.a,f.connection)
 with pytest.raises(Exception):account(f.general,f.x.a,body)


def test_fixed_review_preserves_timezone_and_refuses_past_time():
 pin=dict(mode='fixed',timezone='Asia/Kolkata',duration_minutes=30,hour=22,minute=50)
 now=datetime.fromisoformat('2026-11-12T22:20:00+05:30').timestamp()
 run={'action_instances':{}}
 value=runtime_values(pin,run,'event',now,now)
 assert value['calendar_event_start']['dateTime']=='2026-11-12T22:50:00+05:30'
 with pytest.raises(RuntimeFailure) as caught:runtime_values(pin,run,'event',now+1801,now)
 assert caught.value.code=='CALENDAR_REVIEW_TIME_PASSED'


def test_owned_calendar_discovery_does_not_make_network_call_without_existing_list_scope(automation):
 from workflow_api.communication_intent import calendar_choices
 f=automation;assert calendar_choices(f.general,f.x.a,dict(connection_id=f.connection,email='owner@example.com'))==[]
 assert not f.http.events and not f.http.sent


def test_explicit_draft_fixed_time_and_duration_defaults(automation):
 from workflow_api.communication_intent import prepare
 f=automation
 route=intent('recurring');route['side_effects']=['calendar_write'];schedule={'timezone':'Asia/Kolkata'}
 resolved={'validated_context':{}}
 body={'objective':'Prepare a draft email report and a calendar reading session','user_values':{}}
 changed,info,questions=prepare(f.general,f.x.a,body,route,schedule,resolved)
 assert not questions and 'email_draft' in changed['side_effects'] and 'email_send' not in changed['side_effects']
 assert info['review']==dict(mode='after_ready',timezone='Asia/Kolkata',duration_minutes=30,lead_minutes=5)
 body['user_values']={'review_timing':'fixed','review_time':'23:10','review_duration_minutes':45}
 changed,info,questions=prepare(f.general,f.x.a,body,route,schedule,resolved)
 assert not questions and info['review']==dict(mode='fixed',timezone='Asia/Kolkata',duration_minutes=45,hour=23,minute=10)
 body['user_values']={'review_timing':'fixed'}
 _,_,questions=prepare(f.general,f.x.a,body,route,schedule,resolved)
 assert [q['field'] for q in questions]==['review_time']
