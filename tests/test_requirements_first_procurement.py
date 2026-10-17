from copy import deepcopy
from types import SimpleNamespace
from unittest.mock import Mock
import pytest
from planner.errors import PlannerFailure
from workflow_api.procurement import ProcurementPlanner
from workflow_api.sheet_discovery import planning_spreadsheet_references

RESTAURANT_PROMPT='''I am planning to open a new 60-seat restaurant. Help me plan and procure all the equipment, furniture, kitchen appliances, utensils, and other essential items required to set it up.

Start by generating a detailed Bill of Quantities (BOQ) with item names, specifications, quantities, and estimated prices. Identify suitable suppliers for each item, compare their prices, availability, quality, and delivery timelines, and prepare Requests for Quotations (RFQs). Simulate supplier quotations if live supplier connections are unavailable, compare the quotations, and recommend the best supplier for each item while considering my budget of ₹25 lakh.

Generate a procurement report showing the total estimated cost, supplier-wise comparison, budget utilisation, and expected delivery schedule. Finally, prepare purchase orders for the selected suppliers, but require my approval before issuing any RFQs or purchase orders.

Automatically create a visual multi-agent workflow showing each stage, the agents responsible, their inputs and outputs, and the connections between them. Allow me to execute the workflow and inspect the results of every stage.'''

def test_exact_restaurant_prompt_reaches_requirements_first_planner_without_a_source():
 expected={'draft':'from-general-planner'};fallback=SimpleNamespace(generate=Mock(return_value=expected));discover=Mock(side_effect=AssertionError('No source should be required by procurement adapter'))
 planner=ProcurementPlanner(fallback,Mock(),'offline',discover)
 context={'execution_input_mode':'automatic','generation_mode':'hierarchy','workspace_knowledge':[{'source_id':'policy','content':'Approved internal procurement policy'}]};before=deepcopy(context)
 assert planner.generate(RESTAURANT_PROMPT,context) is expected
 fallback.generate.assert_called_once_with(RESTAURANT_PROMPT,{**context,'procurement_planning_mode':'requirements_first'})
 assert context==before;discover.assert_not_called()

@pytest.mark.parametrize('prompt',['Generate a new BOQ for procurement of restaurant furniture.','Create a detailed bill of quantities and draft RFQs.','Prepare a comprehensive BOQ for procurement planning.'])
def test_new_boq_variants_do_not_require_an_existing_boq(prompt):
 fallback=SimpleNamespace(generate=Mock(return_value={}));planner=ProcurementPlanner(fallback,Mock(),'offline',Mock())
 planner.generate(prompt,{})
 assert fallback.generate.call_args.args[1]['procurement_planning_mode']=='requirements_first'

def test_existing_boq_source_flow_is_preserved_and_workspace_sources_are_inspected():
 class StopBeforeModel(Exception):pass
 discover=Mock(return_value={'spreadsheet_id':'saved_book','tables':[]});client=SimpleNamespace(responses=SimpleNamespace(create=Mock(side_effect=StopBeforeModel)))
 fallback=SimpleNamespace(generate=Mock());planner=ProcurementPlanner(fallback,client,'offline',discover)
 with pytest.raises(StopBeforeModel):planner.generate('Prepare RFQs from the existing BOQ and vendor table.',{'workspace_sources':[{'spreadsheet_id':'saved_book'}]})
 discover.assert_called_once_with('saved_book');fallback.generate.assert_not_called()

def test_missing_source_is_still_a_specific_setup_error_for_existing_boq_ingestion():
 planner=ProcurementPlanner(SimpleNamespace(generate=Mock()),Mock(),'offline',Mock())
 with pytest.raises(PlannerFailure) as error:planner.generate('Prepare RFQs from the existing BOQ.',{})
 assert error.value.code=='PROCUREMENT_SOURCE_REQUIRED' and 'generate' in str(error.value)

def test_explicit_source_failure_is_safe_and_optional_stale_sources_do_not_mask_valid_ones():
 def discover(ref):
  if ref=='good_book':return {'spreadsheet_id':ref,'tables':[]}
  raise RuntimeError('private transport detail')
 planner=ProcurementPlanner(SimpleNamespace(generate=Mock()),Mock(),'offline',discover)
 with pytest.raises(PlannerFailure) as error:planner.generate('Prepare RFQs from https://docs.google.com/spreadsheets/d/bad_book/edit',{})
 assert error.value.code=='SHEETS_DISCOVERY_FAILED' and 'private transport detail' not in str(error.value)
 client=SimpleNamespace(responses=SimpleNamespace(create=Mock(side_effect=RuntimeError('Reached model'))));planner.client=client
 with pytest.raises(RuntimeError,match='Reached model'):planner.generate('Prepare RFQs from existing BOQ.',{'workspace_sources':[{'spreadsheet_id':'bad_book'},{'spreadsheet_id':'good_book'}]})

def test_general_customer_request_keeps_original_planner():
 fallback=SimpleNamespace(generate=Mock(return_value={}));planner=ProcurementPlanner(fallback,Mock(),'offline',Mock())
 prompt='Classify a duplicated customer charge and draft a reply.';context={'execution_input_mode':'automatic'}
 planner.generate(prompt,context);fallback.generate.assert_called_once_with(prompt,context)

def test_source_candidates_are_bounded_deduplicated_and_explicit_first():
 sources=[{'spreadsheet_id':f'saved_{i}'} for i in range(20)]
 refs=planning_spreadsheet_references('Use https://docs.google.com/spreadsheets/d/explicit_book/edit',{'workspace_sources':sources,'workspace_knowledge':[{'spreadsheet_id':'saved_0'}]})
 assert len(refs)==8 and len(set(refs))==8 and refs[0]=='explicit_book'

def test_model_guidance_covers_simulated_evidence_approval_and_sequential_stage_budgets():
 import json
 from planner.provider import OpenAIStructuredOutputProvider
 create=Mock(return_value=SimpleNamespace(output_text=json.dumps({'metadata':{'dynamic_delegation':{'master':{'max_rounds':8,'max_tasks':12}}}})))
 provider=OpenAIStructuredOutputProvider(client=SimpleNamespace(responses=SimpleNamespace(create=create)),model='offline')
 provider.generate(RESTAURANT_PROMPT,{'generation_mode':'hierarchy','procurement_planning_mode':'requirements_first'})
 system=create.call_args.kwargs['input'][0]['content']
 for instruction in ['generates a new BOQ','SIMULATED/UNVERIFIED','authorized tools',"user's required approval gate",'max_rounds=8','max_tasks=12']:
  assert instruction in system
 assert create.call_args.kwargs['store'] is False

def test_queued_restaurant_request_uses_requirements_first_and_creates_no_run():
 from planner import PlannerService
 from planner.provider import RuleBasedStructuredOutputProvider
 from tests.test_workflow_api import WorkflowApiTests
 fixture=WorkflowApiTests('test_same_prompt_after_deletion_gets_stable_fresh_identity_and_agents');fixture.setUp()
 try:
  canonical=RuleBasedStructuredOutputProvider().generate('Classify a support request',{'generation_mode':'hierarchy','execution_input_mode':'automatic'})
  fallback=SimpleNamespace(generate=Mock(return_value=canonical))
  fixture.service.planner=PlannerService(ProcurementPlanner(fallback,Mock(),'offline',Mock(side_effect=AssertionError('No procurement source prerequisite'))))
  jobs=fixture.client.app.state.planning_jobs;auth=fixture.client.app.state.workflow_auth
  request={'request_id':'req_queued_restaurant','operation':'plan_workflow','idempotency_key':'queued_restaurant_requirement','payload':{'objective':RESTAURANT_PROMPT,'context':{'generation_mode':'hierarchy','execution_input_mode':'automatic'}}}
  job=jobs.submit(request,auth);assert jobs.tick() is True
  result=jobs.get(job['job_id'],auth);assert result['state']=='succeeded',result
  assert result['result']['data']['workflow']['inputs']==[]
  assert fallback.generate.call_args.args[1]['procurement_planning_mode']=='requirements_first'
  assert fixture.client.get('/workflows').json()['data']['total']==0
 finally:fixture.tearDown();fixture.doCleanups()

def test_missing_trigger_draft_gets_actionable_correction_and_only_valid_graph_is_returned():
 from planner.provider import RuleBasedStructuredOutputProvider
 from workflow_api.live_providers import LivePlannerProvider
 provider=LivePlannerProvider('offline',['owner@example.com'],Mock())
 canonical=RuleBasedStructuredOutputProvider().generate('Classify a support request',{**provider.context,'generation_mode':'hierarchy','execution_input_mode':'automatic'})
 for agent in canonical['agents']:agent['model']=deepcopy(provider.context['runtime_model'])
 invalid=deepcopy(canonical)
 triggers={node['node_id'] for node in invalid['nodes'] if node['kind']=='trigger'}
 invalid['nodes']=[node for node in invalid['nodes'] if node['node_id'] not in triggers]
 invalid['edges']=[edge for edge in invalid['edges'] if edge['source'] not in triggers and edge['target'] not in triggers]
 seen=[]
 def generate(objective,context):
  seen.append(deepcopy(context))
  return deepcopy(invalid if len(seen)==1 else canonical)
 provider.provider=SimpleNamespace(generate=generate)
 result=provider.generate(RESTAURANT_PROMPT,{'generation_mode':'hierarchy','execution_input_mode':'automatic','procurement_planning_mode':'requirements_first'})
 assert len(seen)==2 and any(node['kind']=='trigger' for node in result['nodes'])
 feedback=seen[1]['validation_feedback']
 assert feedback[0]['code']=='WORKFLOW_VALIDATION_FAILED' and 'kind=trigger' in feedback[0]['hint']

def test_automatic_procurement_planning_does_not_request_customer_email_automation():
 from workflow_api.live_providers import LivePlannerProvider
 class CapturedContext(Exception):pass
 provider=LivePlannerProvider('offline',['owner@example.com'],Mock(),direct_send=True)
 captured={}
 def generate(objective,context):
  captured.update(context)
  raise CapturedContext
 provider.provider=SimpleNamespace(generate=generate)
 with pytest.raises(CapturedContext):provider.generate(RESTAURANT_PROMPT,{'procurement_planning_mode':'requirements_first'})
 assert captured['customer_automation_requested'] is False
 assert 'customer_automation_defaults' not in captured
