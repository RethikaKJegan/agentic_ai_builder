from copy import deepcopy
import pytest
from workflow_api.business_coverage import coverage,validate_record,TASKS
from workflow_api.business_environments import build_case,case_coverage,build_release,VARIANTS


def evidence():
 def record(rid,collection,fields,values):return dict(record_id=rid,collection=collection,fields=fields,values={k:dict(state='value',value=v) for k,v in values.items()},source_reference={'native_value':fields['_id']},read_at='2025-09-25T10:00:00+00:00',states=[])
 return dict(version_id='v1',knowledge_sha256='k1',request_id='fixture-source-read',records=[record('ticket:one','tickets',{'_id':'C123','engineNo':'E123'},{'mapping:ticket_serial':'E123','mapping:complaint_hours':'1000','mapping:complaint_symptom':'Reported cooling symptom'}),record('report:one','jointinspectionreports',{'_id':'J1','ticketId':'C123'},{'mapping:inspection_date':'2025-09-24','mapping:inspection_defect_text':'Reported component condition'})],reference_edges=[dict(binding_id='identity:inspection_ticket',classification='direct_reference',record_id='report:one',parent_record_id='ticket:one')],record_reads_complete=True,completeness='bounded',missing=[],findings=[],conversion_issues=[],ambiguous_associations=[],executed_steps=[],rule_results=[],intent={'task':'inspection'})

@pytest.mark.parametrize('variant',VARIANTS)
def test_independent_coverage_matrix(variant):
 case=build_case([evidence()],variant)
 expected={
 'missing_inspection':{'inspection':'insufficient_evidence','warranty':'insufficient_evidence','replacement':'insufficient_evidence'},
 'conflicting_identity':{'warranty':'conflicting_evidence','replacement':'conflicting_evidence'},
 'missing_exclusions':{'warranty':'insufficient_evidence'},
 'invalid_dates':{'warranty':'insufficient_evidence','replacement':'insufficient_evidence'},
 'ambiguous_policy':{'warranty':'conflicting_evidence'},
 'missing_authorization':{'replacement':'insufficient_evidence'},
 'conflicting_evidence':{'replacement':'conflicting_evidence'},
 }.get(variant,{})
 for task in TASKS:
  result=case_coverage(case,task)
  if task in expected:assert result['state']==expected[task],result
  else:assert result['conclusion_ready'],result
  assert result['official_approval'] is False
 if variant=='rejected_authorization':assert case_coverage(case,'replacement')['business_outcomes']['authorization_outcome']=='rejected'
 if variant=='expired_policy':assert case_coverage(case,'warranty')['business_outcomes']['policy_period']=='expired_or_not_effective'
 if variant=='confirmed_exclusion':assert case_coverage(case,'warranty')['business_outcomes']['warranty']=='outside_configured_conditions'


def test_case_construction_preserves_originals_and_qualified_record_schemas():
 source=evidence();before=deepcopy(source);case=build_case([source])
 assert source==before and case==build_case([source])
 for r in case['business_records']:validate_record(r)
 assert all(r['provenance']['source_references'] for r in case['business_records'])
 assert not coverage('replacement',source)['conclusion_ready']


def test_conflicting_authority_and_revocation_do_not_approve():
 case=build_case([evidence()]);auth=next(r for r in case['business_records'] if r['kind']=='authorization')
 result=case_coverage(case,'replacement',revoked=[auth['record_id']])
 assert not result['conclusion_ready']
 auth['data']['authority_role']='unauthorized-role'
 assert not case_coverage(case,'replacement')['conclusion_ready']
 auth['data']['authority_role']=auth['data']['required_role'];auth['data']['revoked']=True
 result=case_coverage(case,'replacement')
 assert result['conclusion_ready'] and result['business_outcomes']['authorization_outcome']=='revoked'


def test_different_case_records_and_impossible_dates_fail():
 case=build_case([evidence()]);case['business_records'][0]['case_id']='foreign'
 assert not case_coverage(case,'warranty')['conclusion_ready']
 case=build_case([evidence()]);case['inputs'].pop('assessment_date')
 assert case_coverage(case,'warranty')['state']=='needs_input'


def test_optional_bounded_history_does_not_block_comparison():
 e=evidence();e['executed_steps']=[dict(collection='tickettimelines',truncated=True)]
 assert coverage('inspection',e)['state']=='ready_with_limitations'
 e['executed_steps']=[dict(collection='jointinspectionreports',truncated=True)]
 assert coverage('inspection',e)['state']=='insufficient_evidence'


def test_cross_record_invoice_profile_is_not_mislabeled_as_one_source_record():
 source=evidence();source['records'][0]['values']['mapping:sale_date']=dict(state='value',value='2025-08-01')
 source['records'].append(dict(record_id='invoice:one',collection='enginedetails',fields={'_id':'I1'},values={'mapping:invoice_serial':dict(state='value',value='E123'),'mapping:invoice_date':dict(state='value',value='2025-07-01')},source_reference={'native_value':'I1'},read_at='2025-09-25T10:00:00+00:00',states=[]))
 case=build_case([source]);invoice=next(r for r in case['business_records'] if r['kind']=='invoice')
 assert invoice['data']['invoice_date']=='2025-07-01' and invoice['data']['sale_date']=='2025-08-01'
 assert invoice['provenance']['kind']=='generated'
 assert case['evidence']['records']==source['records']


@pytest.mark.parametrize('hours',['-1','NaN','not-a-number'])
def test_invalid_operating_hours_do_not_become_eligibility(hours):
 case=build_case([evidence()]);case['evidence']['records'][0]['values']['mapping:complaint_hours']['value']=hours
 result=case_coverage(case,'warranty')
 assert not result['conclusion_ready']
 assert any(g['fact_id']=='operating_hours' and g['state']=='invalid_value' for g in result['gaps'])
