"""New fixed-time plans use original facts through actual compilation and approval."""
from copy import deepcopy
from types import SimpleNamespace
from datetime import datetime
import pytest
from tests.test_calendar_action_routing import automation,google_setup,connected,composition,investigation,retrieval,knowledge,reference,generation,foundation,auth,release,source_free_route,propose,router,NOW
from tests.test_google_tools import add_scopes
from tests.test_connected_action_plans import bind,approve,complete,stored
from workflow_api.calendar_intent import original_request

@pytest.mark.parametrize('goal',[
 'Schedule an engine quality review tomorrow at 11 AM for 30 minutes. Add a short agenda about complaints and inspections.',
 'Set up a 30-minute purchase-order review tomorrow at 11 AM and add an agenda about invoice discrepancies.'
])
def test_original_time_corrects_generated_binding_and_survives_review(automation,goal):
 f=automation;f.now=NOW;add_scopes(f.manager,f.connection,['calendar.events'])
 def wrong_time(goal,ctx):
  p=propose(goal,ctx)
  p['actions'][-1]['bindings'].append(bind('generated','event.start',action='content',path=['summary']))
  return p
 f.general.planner.provider=SimpleNamespace(plan_actions=wrong_time)
 r=router(f,source_free_route());r.env['BUILDER_NATURAL_COMMUNICATION_ENABLED']='1'
 with original_request(NOW):result=r.handle(f.x.a,dict(objective=goal,request_key='explicit_calendar_accuracy',google_connection_id=f.connection))
 assert result['state']=='prepared',result
 doc=f.c.get(f.x.a,result['composition_id']);w=f.c.workflow(f.x.a,doc['composition_id'])
 pin=w['metadata']['overview_intent']['communication']['review']
 assert pin['mode']=='fixed' and pin['hour']==11 and pin['minute']==0 and pin['on_date']=='2026-11-13'
 assert any(x['field']=='event.event.start' for x in w['metadata']['validation_repairs'])
 assert not f.http.events and not f.http.sent
 assert f.adapter.approve_pending(w,f.x.a)['ready'];w=approve(f,w)
 f.now+=3600 # Delayed execution must not reinterpret tomorrow.
 created=f.runtime.create_run(dict(request_id='calendar_accuracy',idempotency_key='calendar_accuracy',payload=dict(workflow_id=w['workflow_id'],workflow_version=1,inputs={})),f.x.a)
 assert complete(f,w,created['run_id'])['status']=='completed'
 assert len(f.http.events)==1 and not f.http.sent
 actual=f.http.events[0]
 assert actual['start']==dict(dateTime='2026-11-13T11:00:00+05:30',timeZone='Asia/Kolkata')
 assert actual['end']==dict(dateTime='2026-11-13T11:30:00+05:30',timeZone='Asia/Kolkata')
 assert 'attendees' not in actual
 assert stored(f,created['run_id'])['action_instances']['event']['verified_receipt']
