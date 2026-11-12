"""Business blockers are explicit decisions, not patterns in explanatory prose."""
from copy import deepcopy
import json
import pytest
from jsonschema import Draft202012Validator
from workflow_api.subway_queries import SELECTION,business_question,selection_schema
from workflow_api.service import ApiFailure
from tests.test_subway_intelligence import engine,installed,subway,selection,overview,route


def value(**changes):
    return dict(dataset_ids=[],field_ids=[],relationship_ids=[],measure_basis='Keep distinct recorded measures separate.',clarification='',**changes) if not changes else {**value(),**changes}


@pytest.mark.parametrize('notes',[
    'Both source amounts remain distinct; disclose coverage and do not infer an approved basis.',
    'Confirm a different basis only if required.',
    'Question marks in a methodological note? They do not decide readiness.',
])
def test_ready_notes_are_not_questions(notes):
    v=value(business_resolution=dict(status='ready',question='',notes=notes))
    assert Draft202012Validator(SELECTION).is_valid(v)
    assert business_question(v)==''


def test_real_definition_question_and_legacy_behavior_remain_blocking():
    question='Which approved amount basis defines an overpayment?'
    blocked=value(business_resolution=dict(status='needs_definition',question=question,notes='No approved rule supplied.'))
    assert Draft202012Validator(SELECTION).is_valid(blocked) and business_question(blocked)==question
    assert business_question(value(clarification=question))==question
    assert business_question(value())==''
    with pytest.raises(ApiFailure):business_question(value(clarification=question,business_resolution=dict(status='ready',question='',notes='')))


@pytest.mark.parametrize('resolution',[
    dict(status='ready',question='Which amount?',notes=''),
    dict(status='needs_definition',question='',notes=''),
    dict(status='unknown',question='',notes=''),
])
def test_contradictory_resolution_shapes_are_rejected(resolution):
    assert not Draft202012Validator(SELECTION).is_valid(value(business_resolution=resolution))


def test_new_model_requires_explicit_resolution_and_empty_legacy_field():
    schema=selection_schema(dict(sources=[],relationships=[]))
    validator=Draft202012Validator(schema)
    assert not validator.is_valid(value())
    v=value(business_resolution=dict(status='ready',question='',notes='Source caveat.'))
    assert validator.is_valid(v)
    assert not validator.is_valid(dict(v,clarification='Source caveat.'))


@pytest.mark.parametrize('ready',[True,False])
def test_descriptive_notes_proceed_but_policy_questions_still_stop_in_question_free_mode(subway,ready):
    from workflow_api.overview_automation import OverviewAutomation
    f=subway;chosen=selection(f.q,['finance.invoicedatas','finance.purchaseorders'])
    notes='Compare distinct recorded amount fields separately. Do not choose an approved basis, infer equivalence or classify overpayments. Disclose missing links and snapshot limits.'
    chosen['business_resolution']=dict(status='ready' if ready else 'needs_definition',question='' if ready else 'Which approved rule defines overpayment?',notes=notes)
    f.service.overview_automation=OverviewAutomation(f.service,{**f.env,'BUILDER_QUESTION_FREE_WORKFLOWS':'1'},interpreter=lambda *_:route(chosen))
    result=f.service.overview_automation.handle(f.auth,dict(objective='Compare stored invoice records with linked purchase orders and report source limitations.',request_key='resolution_'+str(ready)))
    if ready:
        assert result['state']=='prepared' and result['composition_id']
        assert result['intent']['subway_selection']['business_resolution']['notes']==notes
        assert f.planning_contexts[-1]['binding_context']['validated_context']['subway_query_catalog']['interpretation']['business_resolution']['notes']==notes
        assert not result.get('questions')
    else:
        assert result['state']=='clarification' and result['business_clarification']
        assert result['questions']==['Which approved rule defines overpayment?']
        assert not f.planning_contexts
    assert not f.model_inputs  # Preparation never ran a query or delivery action.
