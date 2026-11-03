from copy import deepcopy
import pytest
from workflow_api.planning_requirements import separate_coverage_notes
NOTES=[
 'The database catalog provides no declared relationships between a, b, and c; matching must rely only on returned identifiers and explicit evidence.',
 'No specific complaint identifier was supplied in the setup objective; investigate the relevant available records and disclose scope, ambiguity, and coverage.',
 'The selected datasets are query-only and may contain sampled or limited metadata; missing records or fields cannot be treated as proof of absence.'
]
def draft():
 return {'inputs':[],'execution_policy':{'allow_external_writes':False},'tools':[{'tool_id':'database_read_query'}],
 'agents':[{'capabilities':['database.read_query','generate_report']}],
 'metadata':{'database_scope':{'sources':[{'dataset_id':'a'}]},'unresolved_requirements':deepcopy(NOTES),'report_limitations':[]}}
def test_coverage_is_preserved_with_audit_and_no_setup_blocker():
 w=draft();separate_coverage_notes(w)
 assert not w['metadata']['unresolved_requirements']
 assert w['metadata']['report_limitations']==NOTES
 assert len(w['metadata']['requirement_classifications'])==3
 before=deepcopy(w);separate_coverage_notes(w);assert before==w
@pytest.mark.parametrize('extra',['Provide a complaint identifier before running.','Configure the database connection credentials.',{'requirement':'condition_mapping','reason':'condition_mapping_required'}])
def test_real_setup_requirements_remain(extra):
 w=draft();w['metadata']['unresolved_requirements'].append(extra);separate_coverage_notes(w)
 assert w['metadata']['unresolved_requirements']==[extra]
@pytest.mark.parametrize('change',[lambda w:w.update(inputs=[{'name':'complaint_id','required':True}]),lambda w:w['execution_policy'].update(allow_external_writes=True),lambda w:w['tools'].append({'tool_id':'database_execute_operation'}),lambda w:w['metadata'].pop('database_scope')])
def test_required_input_write_or_absent_scope_does_not_remove_requirements(change):
 w=draft();change(w);before=deepcopy(w);separate_coverage_notes(w);assert w==before
def test_caveat_with_embedded_actionable_requirement_stays_blocked():
 w=draft();text=NOTES[0]+' Configure credentials before running.';w['metadata']['unresolved_requirements']=[text];separate_coverage_notes(w)
 assert w['metadata']['unresolved_requirements']==[text]
