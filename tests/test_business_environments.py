from copy import deepcopy
import pytest
from tests.test_business_investigations import investigation
from tests.test_business_retrieval import retrieval
from tests.test_business_knowledge import knowledge
from tests.test_business_reference import reference
from tests.test_business_generation import generation
from tests.test_business_ontology import foundation,auth
from tests.test_business_coverage import evidence
from workflow_api.business_environments import build_case,build_release,VARIANTS
from workflow_api.service import ApiFailure


def release(x,variants=('complete',)):
 x.a['permissions']+=['workflow.edit','workflow.plan'];x.current['permissions']+=['workflow.edit','workflow.plan']
 version=x.f.version(x.a,x.result['version_id']) if hasattr(x,'result') else x.service.ontology.version(x.a,x.service.retrieval.latest(x.a))
 x.reader.rows['jointinspectionreports'][0]['dateOfInspection']='2025-09-24'
 captured=[]
 for task,question in [('inspection','Show inspection findings for complaint C123.'),('warranty','Check warranty evidence for complaint C123.'),('replacement','Review replacement for complaint C123.')]:
  preview=x.service.retrieval.preview(x.a,dict(question=question,request_key='environment_capture_'+task))
  captured.append(x.service.retrieval.execute(x.a,preview['request_id'],{}))
 doc=build_release([build_case(captured,variant) for variant in variants],version)
 x.service.coverage.environments.install(x.a,doc)
 return doc


def test_release_manifest_reproducible_and_scoped(investigation):
 x=investigation;doc=release(x,VARIANTS)
 assert len(doc['manifest']['validation_results'])==36
 assert x.service.coverage.environments.get(x.a,doc['dataset_id'])==doc
 with pytest.raises(ApiFailure):x.service.coverage.environments.get(auth(owner='bob'),doc['dataset_id'])
 tampered=deepcopy(doc);tampered['cases'][0]['business_records'].pop()
 with pytest.raises((ApiFailure,ValueError)):x.service.coverage.environments.install(x.a,tampered)
 assert x.service.coverage.environments.list(x.a)['items'][0]['dataset_id']==doc['dataset_id']


def test_preflight_then_real_executor_complete_and_rejected(investigation):
 x=investigation;doc=release(x,('complete','rejected_authorization','missing_exclusions'))
 for index,case in enumerate(doc['cases']):
  body=dict(objective='Compare complaint C123 with inspection, review replacement and warranty evidence.',request_key='new_coverage_plan_'+str(index),planning_mode='offline',analysis_mode='offline',evidence_context=dict(dataset_id=doc['dataset_id'],case_id=case['case_id']))
  p=x.service.coverage.prepare_plan(x.a,body)
  assert x.service.coverage.prepare_plan(x.a,body)['workflow_id']==p['workflow_id']
  assert p['preflight']['coverage']['inspection']['conclusion_ready']
  r=x.service.create_run(x.a,p['workflow_id'],dict(request_key='new_coverage_run_'+str(index)))
  r=x.service.execute(x.a,r['run_id'],{})
  assert r['status']=='completed',r['node_errors']
  report=r['outputs']['end']
  assert report['scenario_context']['sha256']==doc['sha256']
  assert report['decision_readiness']['replacement']['state'] in ('ready','ready_with_limitations')
  if case['variant']=='rejected_authorization':assert report['decision_readiness']['replacement']['business_outcomes']['authorization_outcome']=='rejected'
  if case['variant']=='missing_exclusions':assert report['decision_readiness']['warranty']['state']=='insufficient_evidence'
  else:assert not [g for g in report['missing_information'] if g['impact']!='optional_supporting_evidence']
  assert report['warranty_approval']=='not_performed'


def test_revocation_detected_after_preflight_before_run(investigation):
 x=investigation;doc=release(x);case=doc['cases'][0]
 p=x.service.coverage.prepare_plan(x.a,dict(objective='Review replacement evidence for complaint C123.',request_key='revocation_plan_001',planning_mode='offline',analysis_mode='offline',evidence_context=dict(dataset_id=doc['dataset_id'],case_id=case['case_id'])))
 rid=next(r['record_id'] for r in case['business_records'] if r['kind']=='authorization')
 x.service.coverage.environments.revoke(x.a,doc['dataset_id'],rid,'Authorization evidence withdrawn')
 r=x.service.create_run(x.a,p['workflow_id'],dict(request_key='revoked_run_001'));r=x.service.execute(x.a,r['run_id'],{})
 assert r['outputs']['end']['decision_readiness']['replacement']['state']=='insufficient_evidence'
 assert any(g['fact_id']=='commercial_authorization' for g in r['outputs']['end']['missing_information'])
 assert any(record['record_id']==rid and record['source_reference']['withdrawn'] for record in r['outputs']['end']['source_records'])


def test_case_identifier_mismatch_and_arbitrary_record_override_denied(investigation):
 x=investigation;doc=release(x);case=doc['cases'][0]
 with pytest.raises(ApiFailure):x.service.coverage.prepare_plan(x.a,dict(objective='Review replacement for complaint C999.',request_key='wrong_case_001',evidence_context=dict(dataset_id=doc['dataset_id'],case_id=case['case_id'])))


def test_real_preflight_retrieves_then_runtime_refreshes_changed_values(investigation):
 x=investigation
 p=x.service.coverage.prepare_plan(x.a,dict(objective='Compare complaint C123 with inspection and check warranty readiness.',request_key='real_coverage_plan',planning_mode='offline',analysis_mode='offline'))
 assert x.reader.calls and p['preflight']['coverage']['warranty']['state']=='needs_input'
 x.reader.rows['jointinspectionreports'][0]['defectDescription']='A changed reported observation'
 r=x.service.create_run(x.a,p['workflow_id'],dict(request_key='real_coverage_run'));r=x.service.execute(x.a,r['run_id'],{})
 assert r['status']=='completed',r['node_errors']
 report=r['outputs']['end']
 assert any(record['fields'].get('defectDescription')=='A changed reported observation' for record in report['source_records'])
 assert report['decision_readiness']['warranty']['state']=='needs_input'
 assert r['outputs']['warranty_review']['classification']=='backend_coverage_check'


def test_cached_environment_still_rejects_mutation(investigation):
 import json
 x=investigation;doc=release(x)
 x.service.coverage.environments.selected(x.a,dict(dataset_id=doc['dataset_id'],case_id=doc['cases'][0]['case_id']))
 with x.f.store.transaction() as db:
  changed=deepcopy(doc);changed['manifest']['coverage_status']='tampered'
  db.execute('UPDATE business_evidence_environments SET document=?',(json.dumps(changed),))
 with pytest.raises(ApiFailure):x.service.coverage.environments.get(x.a,doc['dataset_id'])


def test_environment_installation_rejects_secrets_before_storage(investigation):
 from registry.contracts import RegistryError
 x=investigation;doc=release(x)
 altered=deepcopy(doc);next(r for r in altered['cases'][0]['business_records'] if r['kind']=='technical_decision')['data']['reason']='api_key=must-not-be-stored'
 with pytest.raises(RegistryError):x.service.coverage.environments.install(x.a,altered)


def test_exported_business_record_schema_matches_provider_contract():
 import json
 from pathlib import Path
 from workflow_api.business_coverage import RECORD_SCHEMA
 assert json.loads((Path(__file__).resolve().parents[1]/'workflow_api/schemas/business-evidence-record-v1.json').read_text())==RECORD_SCHEMA
