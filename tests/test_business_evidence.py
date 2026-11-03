"""Independent evidence outcomes. No company/model access or service startup."""
from copy import deepcopy
import pytest
from workflow_api.business_evidence import evaluate,normalize_gaps,resolution_views,definitions,REGISTRY,RECOVERY
from workflow_api.business_knowledge_model import convert
from workflow_api.investigation_agents import validate_analysis


def record(rid,collection,fields=None,values=None):
    return dict(record_id=rid,collection=collection,fields=fields or {},values=values or {},connection_id='isolated-service',source_reference={'native_value':rid},read_at='2026-01-03T00:00:00Z')


def comparison():
    return dict(records=[record('ticket','tickets',{'complaintRecord.natureOfCustomerComplaint':'code-id','serviceEngineer':'user-id'}),
        record('report','jointinspectionreports',{}, {'mapping:inspection_defect_text':{'state':'value','value':'Additional reported inspection observation'},'mapping:inspection_failure_date':{'state':'value','value':'2026-01-02'}}),
        record('code','simpsoncodes',{}, {'mapping:code_value':{'state':'value','value':'C07'},'mapping:code_description':{'state':'value','value':'Recorded symptom'},'mapping:code_type':{'state':'value','value':'COMPLAINT'}}),
        record('person','users',{}, {'mapping:engineer_active':{'state':'value','value':False}})],
        reference_edges=[dict(record_id=child,parent_record_id='ticket',binding_id=binding,classification='direct_reference') for child,binding in [('report','identity:inspection_ticket'),('code','identity:complaint_code'),('person','identity:ticket_engineer')]])


@pytest.mark.parametrize('value,converter,state,result',[
 ('21-03-2026','source_dmy_date','value','2026-03-21'),
 ('03-04-2026','source_dmy_date','value','2026-04-03'),
 ('2026-03-21','source_dmy_date','value','2026-03-21'),
 ('29-02-2024','source_dmy_date','value','2024-02-29'),
 ('29-02-2025','source_dmy_date','conversion_issue',None),
 ('31-04-2026','source_dmy_date','conversion_issue',None),
 ('03/04/2026','source_dmy_date','ambiguous_value',None),
 ('2026-03-21 11:57:00','iso_calendar_component','value','2026-03-21'),
 ('2026-03-21T00:30:00+05:30','iso_calendar_component','value','2026-03-21'),
 ('21-03-2026','iso_date','conversion_issue',None),
 ('21-03-2026','iso_calendar_component','conversion_issue',None),
 (None,'source_dmy_date','unknown',None),
 ('','source_dmy_date','conversion_issue',None),
 (False,'source_dmy_date','conversion_issue',None),
])
def test_field_specific_dates(value,converter,state,result):
    assert convert(value,converter,'date')==dict(state=state,value=result)


def test_resolutions_preserve_original_and_provenance_without_promoting_active():
    e=comparison();original=deepcopy(e);views=resolution_views(e)
    assert e==original
    code=next(v for v in views if v['kind']=='controlled_code')
    assert code['original_value']=='code-id' and code['resolved_values']['mapping:code_description']=='Recorded symptom'
    assert {r['record_id'] for r in code['source_references']}=={'ticket','code'}
    engineer=next(v for v in views if v['kind']=='engineer')
    assert engineer['status']=='resolved' and engineer['resolved_values']['mapping:engineer_active'] is False


@pytest.mark.parametrize('mutation,status',[
 (lambda e:e['reference_edges'].pop(1),'not_found'),
 (lambda e:e['records'][2]['values']['mapping:code_type'].update(value='ACTION'),'not_established'),
 (lambda e:e['records'][2]['values']['mapping:code_description'].update(value=''),'not_established'),
])
def test_unresolved_codes_never_invent_description(mutation,status):
    e=comparison();mutation(e);v=next(v for v in resolution_views(e) if v['kind']=='controlled_code');assert v['status']==status


def test_comparison_finishes_without_warranty_or_incorporation():
    result=evaluate('inspection',comparison())
    assert result['task_executable'] and result['conclusion_ready']
    assert {g['fact_id'] for g in result['gaps']}=={'inspection_activity_completion_evidence'}
    assert result['gaps'][0]['impact']=='later_stage'
    assert not {'applicable_policy','actual_incorporation','commercial_authorization'} & {r['fact_id'] for r in result['requirements']}


def test_publication_does_not_satisfy_activity_completion():
    e=comparison();e['records'][1]['values']['mapping:inspection_status']={'state':'value','value':'PUBLISHED'}
    completion=next(r for r in evaluate('inspection',e)['requirements'] if r['fact_id']=='inspection_activity_completion_evidence')
    assert completion['state']=='not_established'


def test_native_link_required_for_comparison():
    e=comparison();e['reference_edges'][0]['classification']='candidate'
    result=evaluate('inspection',e)
    assert not result['task_executable']
    assert any(g['fact_id']=='linked_inspection' and g['state']=='not_established' for g in result['gaps'])


def test_per_record_dates_and_gap_dedup_preserve_references():
    e=comparison();e['records'][1]['values']['mapping:inspection_failure_date']={'state':'conversion_issue','value':None}
    e['records'].append(record('report2','jointinspectionreports',{}, {'mapping:inspection_failure_date':{'state':'conversion_issue','value':None}}))
    gaps=[g for g in evaluate('inspection',e)['gaps'] if g['fact_id']=='inspection_failure_date']
    assert len(gaps)==2 and {g['context_id'] for g in gaps}=={'report','report2'}
    another=deepcopy(gaps[0]);another['source_references'][0]['read_at']='2026-01-04T00:00:00Z'
    merged=normalize_gaps([*gaps,another]);assert len(merged)==2 and len(merged[0]['source_references'])==2


def test_warranty_unknowns_and_zero_hours_are_not_false():
    e=dict(records=[record('ticket','tickets',{}, {'mapping:complaint_hours':{'state':'value','value':'0'}})])
    result=evaluate('warranty',e)
    assert result['task_executable'] and not result['conclusion_ready']
    assert next(r for r in result['requirements'] if r['fact_id']=='operating_hours')['state']=='satisfied'
    assert next(r for r in result['requirements'] if r['fact_id']=='policy_applicable')['state']=='not_established'
    assert next(g for g in result['gaps'] if g['fact_id']=='assessment_date')['recovery_action']['id']=='assessment_date'


def test_policy_selection_is_not_applicability_and_date_scope_is_conditional():
    policy=dict(policy_id='p1',revision=1,sha256='hash',clauses={'coverage_mode':{'value':'sale_and_hours'}})
    e=dict(records=[record('ticket','tickets')])
    result=evaluate('warranty',e,{'policy_id':'p1','assessment_date':'2026-01-03'},[policy])
    states={r['fact_id']:r for r in result['requirements']}
    assert states['applicable_policy']['state']=='satisfied' and states['policy_applicable']['state']=='not_established'
    assert states['sale_date']['requirement_level']=='required_for_conclusion' and 'invoice_date' not in states


def test_replacement_recommendation_is_not_authorization():
    e=dict(records=[record('ticket','tickets'),record('replacement','enginereplacements',{'mode':'WARRANTY','recommendation':'replace'})])
    assert next(r for r in evaluate('replacement',e)['requirements'] if r['fact_id']=='commercial_authorization')['state']=='not_established'


def test_effectiveness_never_comes_from_counts_or_untrusted_verified_flags():
    e=dict(records=[record('qa','failedengineanalyses',{'status':'APPROVED'})],actual_incorporation=True,physical_engine_identity='verified',failure_count=0)
    result=evaluate('recurrence',e)
    assert not result['conclusion_ready']
    assert {'actual_incorporation','operating_exposure','comparable_confirmed_failure'} <= {g['fact_id'] for g in result['gaps']}


def test_additional_observation_is_not_automatically_a_discrepancy():
    output=dict(summary='Comparison',findings=[dict(kind='discrepancy',statement='Inspection adds a fault not mentioned in the complaint.',references=[dict(record_id='r',mapping_id='m')])],missing_information=[])
    result=validate_analysis(output,dict(records=[dict(record_id='r',values={'m':{'state':'value','value':'fault'}})]))
    assert result['findings'][0]['kind']=='unverified' and result['findings'][0]['comparison_classification']=='additional_observation'


def test_every_requirement_has_a_registered_nonwriting_recovery():
    for task in REGISTRY:
        for r in definitions(task):
            assert r['recovery_action']['id'] in RECOVERY
            assert r['recovery_action']['executable'] is False and r['missing_behavior']=='preserve_unknown'


def test_optional_model_context_is_bounded_without_mutating_source_or_required_facts():
    from workflow_api.investigation_agents import packet
    e=comparison();e.update(request_id='e1',missing=[])
    for i in range(8):e['records'].append(record('timeline'+str(i),'tickettimelines',{}, {'mapping:timeline_description':{'state':'value','value':'Recorded event '+str(i)}}))
    before=deepcopy(e);result=packet([e])
    assert e==before
    assert len([r for r in result['records'] if r['collection']=='tickettimelines'])==3
    assert result['optional_context_coverage'][0]['omitted_records']==5
    assert any(r['collection']=='jointinspectionreports' for r in result['records'])
    e['evidence_requirements']=[dict(task='history',fact_id='required_timeline',requirement_level='required_to_execute',business_meaning='Required history',state='satisfied',mapping_ids=['mapping:timeline_description'])]
    protected=packet([e]);assert len([r for r in protected['records'] if r['collection']=='tickettimelines'])==8


def test_compatible_agent_views_merge_with_all_observation_provenance():
    from workflow_api.investigation_agents import packet
    r=record('r','tickets',{}, {'m':{'state':'value','value':'one'}})
    other=deepcopy(r);other['read_at']='2026-01-04T00:00:00Z';other['values']['n']={'state':'value','value':'two'}
    a=dict(request_id='e1',records=[r]);b=dict(request_id='e2',records=[other]);before=deepcopy([a,b]);result=packet([a,b])
    assert [a,b]==before and len(result['records'])==1
    assert {ref['evidence_id'] for ref in result['records'][0]['evidence_references']}=={'e1','e2'}
    other['values']['m']['value']='conflicting observation'
    assert len(packet([a,b])['records'])==2
