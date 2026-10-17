"""Routing regressions; no model/network calls or procurement execution."""
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock
import pytest
from planner.errors import PlannerFailure
from workflow_api.procurement import ProcurementPlanner
from tests.test_requirements_first_procurement import RESTAURANT_PROMPT

WORKSHOP_PROMPT=(Path(__file__).parent/'fixtures/workshop_procurement_prompt.txt').read_text().strip()

class ReachedSetupModel(Exception):pass

def planner(discover=None):
 fallback=SimpleNamespace(generate=Mock(return_value={'draft':'general'}))
 client=SimpleNamespace(responses=SimpleNamespace(create=Mock(side_effect=ReachedSetupModel)))
 discover=discover or Mock(side_effect=lambda ref:{'spreadsheet_id':ref,'tables':[]})
 return ProcurementPlanner(fallback,client,'offline',discover),fallback,client,discover

def test_exact_workshop_prompt_discovers_source_and_reaches_native_setup_model():
 p,fallback,client,discover=planner()
 with pytest.raises(ReachedSetupModel):p.generate(WORKSHOP_PROMPT,{'generation_mode':'hierarchy','execution_input_mode':'automatic'})
 discover.assert_called_once_with('1sioBVNHo3TsHgGJ6YUEp3OxAltA0rvhTlPIqTDLrjwM')
 client.responses.create.assert_called_once();fallback.generate.assert_not_called()

@pytest.mark.parametrize('instructions',[
 'Read the requirements and prepare the BOQ.',
 'Discover the actual Requirements and Vendors tabs and prepare a detailed BOQ.',
 'Load the saved BOQ and generate a new BOQ.',
 'Import requirements and generate a comprehensive Bill of Quantities.',
 'Prepare a BOQ from the supplied requirements.',
 'Generate a BOQ from the connected spreadsheet.',
])
def test_existing_source_intent_uses_saved_sources_even_with_boq_creation(instructions):
 p,fallback,_,discover=planner()
 with pytest.raises(ReachedSetupModel):p.generate(instructions,{'workspace_sources':[{'spreadsheet_id':'saved_requirements'}]})
 discover.assert_called_once_with('saved_requirements');fallback.generate.assert_not_called()

@pytest.mark.parametrize('suffix',['','\nConsult this equipment reference for additional knowledge: https://docs.google.com/spreadsheets/d/reference_book/edit'])
def test_restaurant_new_boq_still_uses_general_planning_with_supplementary_knowledge(suffix):
 p,fallback,_,discover=planner();prompt=RESTAURANT_PROMPT+suffix
 assert p.generate(prompt,{})=={'draft':'general'}
 fallback.generate.assert_called_once_with(prompt,{'procurement_planning_mode':'requirements_first'});discover.assert_not_called()

def test_existing_requirements_without_accessible_sources_keeps_specific_blocker():
 p,fallback,_,_=planner()
 with pytest.raises(PlannerFailure) as error:p.generate('Read the requirements and prepare the BOQ.',{})
 assert error.value.code=='PROCUREMENT_SOURCE_REQUIRED';fallback.generate.assert_not_called()

def test_inaccessible_workshop_source_does_not_fall_back_or_hide_access_failure():
 discover=Mock(side_effect=RuntimeError('private provider response'));p,fallback,client,_=planner(discover)
 with pytest.raises(PlannerFailure) as error:p.generate(WORKSHOP_PROMPT,{})
 assert error.value.code=='SHEETS_DISCOVERY_FAILED' and 'private provider' not in str(error.value)
 fallback.generate.assert_not_called();client.responses.create.assert_not_called()

def test_workshop_prompt_native_setup_produces_canonical_draft_without_procurement_execution():
 from tests.test_integrated_procurement import IntegratedTests
 fixture=IntegratedTests('test_native_prompt_to_approved_sends_and_tracking');fixture.setUp()
 try:
  # Source discovery is stubbed; the extraction fixture references these catalogs.
  fixture.service.planner.provider.discoverer=lambda ref:next(c for c in fixture.catalogs if c['spreadsheet_id']==('requirements_book' if ref=='1sioBVNHo3TsHgGJ6YUEp3OxAltA0rvhTlPIqTDLrjwM' else ref))
  workflow=fixture.service.planner.provider.generate(WORKSHOP_PROMPT,{'execution_input_mode':'automatic','workspace_sources':[{'spreadsheet_id':'vendors_book'}]})
  fixture.service.validate_document(workflow)
  assert workflow['status']=='draft' and workflow['metadata']['procurement_plan']
  assert workflow['metadata'].get('unresolved_requirements',[])==[]
  assert fixture.http.sent==[] and fixture.http.drafts==[]
  assert fixture.client.get('/workflows').json()['data']['total']==0
 finally:fixture.tearDown();fixture.doCleanups()
