"""Generated drafts normalize; explicit plans and all execution limits stay strict."""
from copy import deepcopy
from types import SimpleNamespace
import pytest
from workflow_api.action_budgets import normalize_generated,validate_allowance
from runtime.service import RuntimeFailure
from tests.test_goal_planning import automation,google_setup,connected,composition,investigation,retrieval,knowledge,reference,generation,foundation,auth,release,request,proposal,compile_run,complete,stored
from tests.test_overview_automation_integration import queries


@pytest.mark.parametrize('kind,effect,llm,tools,expected',[
 ('model','none',0,1,(1,0)),('model','none',3,2,(3,0)),
 ('tool','read',1,0,(0,1)),('tool','read',0,3,(0,3)),
 ('tool','write',1,0,(0,1)),('tool','write',2,3,(0,1)),('tool','draft',0,0,(0,1))])
def test_normalizes_any_registered_capability_without_changing_other_fields(kind,effect,llm,tools,expected):
 a=dict(action_id='custom',capability_id='arbitrary.registered.operation',bindings=[{'identity':'unchanged'}],budget=dict(max_llm_calls=llm,max_tool_calls=tools,max_retries=0,timeout_seconds=45))
 before=deepcopy(a);c=dict(kind=kind,side_effect=effect)
 normalize_generated(a,c,minimum_timeout_seconds=60)
 assert (a['budget']['max_llm_calls'],a['budget']['max_tool_calls'])==expected
 assert a['bindings']==before['bindings'] and a['budget']['max_retries']==0
 assert a['budget']['timeout_seconds']==(60 if kind=='tool' else 45)
 validate_allowance(a,c)
 again=deepcopy(a);normalize_generated(a,c,minimum_timeout_seconds=60);assert a==again


@pytest.mark.parametrize('value',[None,True,-1,'1'])
def test_malformed_budgets_are_left_for_strict_schema_validation(value):
 a={'budget':dict(max_llm_calls=value,max_tool_calls=0,max_retries=0,timeout_seconds=45)};before=deepcopy(a)
 normalize_generated(a,dict(kind='model',side_effect='none'));assert a==before


@pytest.mark.parametrize('kind,llm,tools',[('model',0,1),('model',1,1),('tool',0,0)])
def test_explicit_invalid_allowance_has_exact_feedback(kind,llm,tools):
 a=dict(action_id='prepare_report',capability_id='registered.op',budget=dict(max_llm_calls=llm,max_tool_calls=tools));before=deepcopy(a)
 with pytest.raises(RuntimeFailure) as caught:validate_allowance(a,dict(kind=kind))
 assert a==before and caught.value.code=='ACTION_BINDING_INVALID'
 issue=caught.value.binding_issue
 assert issue['action_id']=='prepare_report' and issue['rule']=='capability_budget_mismatch'
 assert issue['observed']==before['budget'] and 'prepare_report' in str(caught.value)


def test_generated_wrong_allocations_compile_and_execute_with_existing_approvals(automation):
 f=automation;body,seen=request(f)
 original=proposal(f.prepared);before=deepcopy(original)
 for a in original['actions']:
  a['budget'].update(max_llm_calls=0,max_tool_calls=1 if a['capability_id']=='content.prepare' else 0)
 f.general.planner.provider=SimpleNamespace(plan_actions=lambda *_:deepcopy(original))
 raw=deepcopy(original);doc,w,rid=compile_run(f,body)
 assert original==raw
 for a in doc['action_plan']['actions']:
  assert a['budget']['max_tool_calls']==(0 if a['capability_id']=='content.prepare' else 1)
  assert a['budget']['max_llm_calls']>=1 if a['capability_id']=='content.prepare' else a['budget']['max_llm_calls']==0
 assert complete(f,w,rid)['status']=='completed'
 assert f.http.write_count==1 and len(f.http.sent)==1
 assert stored(f,rid)['action_instances']['send']['approval_references']


def test_explicit_wrong_allocation_stays_rejected(automation):
 f=automation;body,_=request(f);body['action_plan']=proposal(f.prepared)
 a=next(a for a in body['action_plan']['actions'] if a['capability_id']=='content.prepare');a['budget'].update(max_llm_calls=0,max_tool_calls=1)
 before=deepcopy(body)
 with pytest.raises(RuntimeFailure) as caught:f.c.prepare_actions(f.x.a,body)
 assert caught.value.binding_issue['action_id']==a['action_id'] and body==before
 assert not f.http.sent and f.http.write_count==0


def test_generated_allowances_do_not_raise_plan_caps_or_drop_actions(automation):
 f=automation;body,_=request(f);body['constraints']=dict(max_actions=16,max_seconds=300,max_llm_calls=0,max_tool_calls=16)
 with pytest.raises(RuntimeFailure) as caught:f.c.prepare_actions(f.x.a,body)
 assert 'exceed plan limits' in str(caught.value)
 assert body['constraints']['max_llm_calls']==0 and not f.http.sent and f.http.write_count==0


def test_recurring_email_calendar_two_occurrences_with_bad_generated_budgets(automation,queries,monkeypatch):
 import tests.test_reviewed_recurring_research as journey
 original=journey.action
 def malformed(*args,**kw):
  a=original(*args,**kw);a['budget'].update(max_llm_calls=0,max_tool_calls=1 if a['capability_id']=='content.prepare' else 0);return a
 monkeypatch.setattr(journey,'action',malformed)
 journey.test_two_native_daily_occurrences_research_sheet_email_and_calendar(automation,queries,monkeypatch,False)


def test_generated_write_retry_is_not_silently_authorized(automation):
 f=automation;body,_=request(f);p=proposal(f.prepared)
 next(a for a in p['actions'] if a['action_id']=='send')['budget']['max_retries']=1
 f.general.planner.provider=SimpleNamespace(plan_actions=lambda *_:deepcopy(p))
 with pytest.raises(RuntimeFailure) as caught:f.c.prepare_actions(f.x.a,body)
 assert 'Retry allowance' in str(caught.value) and not f.http.sent and f.http.write_count==0


from tests.test_subway_intelligence import subway,engine,installed

def test_subway_overview_and_daily_assessment_with_incompatible_generated_calls(subway,monkeypatch):
 import tests.test_subway_persistent_demo_runtime as journey
 original=journey.action
 def malformed(*args,**kw):
  a=original(*args,**kw);a['budget'].update(max_llm_calls=0,max_tool_calls=1 if a['capability_id']=='content.prepare' else 0);return a
 monkeypatch.setattr(journey,'action',malformed)
 journey.test_persistent_demo_overview_assessment_report_and_reviewed_occurrence(subway,monkeypatch,True,True)
