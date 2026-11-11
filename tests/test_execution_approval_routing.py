"""Approval-only notices permit planning, never provider execution or access grants."""
from copy import deepcopy
from types import SimpleNamespace
import pytest
from workflow_api.overview_automation import OverviewAutomation,execution_approval_notice
from tests.test_overview_automation import intent
from tests.test_question_free_workflows import (automation,google_setup,connected,composition,investigation,retrieval,knowledge,reference,generation,foundation,auth,release,queries,setup_query,empty_once,GOAL,router)

@pytest.mark.parametrize('notice',[
 'Approval is required before sending the email to aravind@bellcorpstudio.com.',
 'Approval is required before creating the Google spreadsheet.',
 'User approval is needed before updating the spreadsheet.',
 'Human approval is required before creating the Calendar event.',
 'Approval is required for web search.',
 'Explicit approval is required before executing the workflow with email, Sheets, Calendar and web search.',
 'Approval to send the email is required.',
 'Approval is required.',
])
def test_clear_execution_notices_do_not_block_supported_planning(notice):
 route=intent('one_time');route['missing_requirements']=[notice]
 r=OverviewAutomation(None,{'BUILDER_QUESTION_FREE_WORKFLOWS':'1'},interpreter=lambda *_:route)
 actual=r.interpret('Prepare the requested workflow.',{})
 assert actual['missing_requirements']==[] and execution_approval_notice(notice)
 assert route['missing_requirements']==[notice] # input and original interpreter record preserved
 assert actual['side_effects']==route['side_effects']

@pytest.mark.parametrize('requirement',[
 'Approval is required but the recipient is unknown.',
 'Approval is required before sending email; provide the recipient.',
 'Approval is required before sending the email and the recipient is unspecified.',
 'Approval is required before access to the calendar is available.',
 'Approval is required for missing Google OAuth scopes.',
 'Approval is required for warranty eligibility.',
 'Which manager should approve this?',
 'Approval is required before sending the email. Confirm the spreadsheet destination.',
 'Missing permission to search the web.',
])
def test_real_gaps_mixed_requirements_and_business_approvals_stay_unresolved(requirement):
 assert not execution_approval_notice(requirement)
 route=intent('one_time');route['missing_requirements']=[requirement]
 actual=OverviewAutomation(None,{'BUILDER_QUESTION_FREE_WORKFLOWS':'1'},interpreter=lambda *_:route).interpret('Prepare.',{})
 assert actual['missing_requirements']==[requirement]

def test_disabled_mode_preserves_legacy_requirement_handling():
 route=intent('one_time');route['missing_requirements']=['Approval is required.']
 assert OverviewAutomation(None,interpreter=lambda *_:route).interpret('Prepare.',{})==route

def test_mixed_approval_and_actual_missing_input_still_creates_blocked_draft(automation):
 route=empty_once();route['missing_requirements']=['Approval is required before sending email.','The manager email is unknown.']
 def unresolved(*_):
  from runtime.service import RuntimeFailure
  raise RuntimeFailure('ACTION_INPUT_REQUIRED','The manager email remains unknown.',422)
 automation.general.planner.provider=SimpleNamespace(plan_actions=unresolved)
 result=router(automation,route).handle(automation.x.a,dict(objective='Email my manager.',request_key='approval_mixed_actual_gap'))
 assert result['blocked'] and result['questions']==[] and result['schedule'] is None
 assert not automation.http.sent

def test_actual_faulty_route_reaches_action_planning_and_keeps_email_gate(automation,queries):
 from tests.test_question_free_workflows import test_supported_qualitative_workflow_receives_policy_at_planning_and_runtime_without_blocker
 # Exercise the exact saved approval-only shape through real composition compilation.
 from unittest.mock import patch
 route=empty_once();route['missing_requirements']=['Approval is required before sending the email to aravind@bellcorpstudio.com.']
 with patch('tests.test_question_free_workflows.empty_once',return_value=route):
  test_supported_qualitative_workflow_receives_policy_at_planning_and_runtime_without_blocker(automation,queries)
 docs=automation.general.store
 with docs.transaction(write=False) as db:
  import json
  row=db.execute('SELECT document FROM business_compositions ORDER BY rowid DESC LIMIT 1').fetchone();doc=json.loads(row[0])
 wf=automation.c.workflow(automation.x.a,doc['composition_id'])
 assert wf['approval_gates']
 assert wf['execution_policy']['requires_review_before_execution']
 assert not automation.http.sent and automation.http.write_count==0
