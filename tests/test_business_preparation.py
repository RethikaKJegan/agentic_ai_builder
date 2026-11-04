"""Shared planning/evidence boundary: real services with deterministic transports."""
from copy import deepcopy
from unittest.mock import patch
import pytest
from tests.test_business_environments import release
from tests.test_business_investigations import investigation
from tests.test_business_retrieval import retrieval
from tests.test_business_knowledge import knowledge
from tests.test_business_reference import reference
from tests.test_business_generation import generation
from tests.test_business_ontology import foundation,auth
from tests.test_business_planning import GroundedProvider,planner_auth
from workflow_api.business_preparation import BusinessEvidenceAdapter,validate_preparation,verify_workflow_pin
from workflow_api.business_knowledge_model import digest
from workflow_api.service import WorkflowService,ApiFailure
from planner import PlannerService

OBJECTIVE='Compare complaint C123 with its linked inspection.'

@pytest.mark.parametrize('objective,tasks',[(OBJECTIVE,{'complaints','inspection'}),('Check warranty readiness for complaint C123.',{'complaints','warranty'}),('Review replacement evidence for complaint C123.',{'complaints','replacement'}),('Investigate ticket C123 and compare its JIR.',{'complaints','inspection'})])
def test_typed_task_specific_preparation(investigation,objective,tasks):
 x=investigation;p=x.service.coverage.preflight(x.a,dict(objective=objective))
 validate_preparation(p)
 assert set(p['tasks'])==tasks
 assert set(p['coverage'])==tasks
 assert p['pins']['ontology_version']==x.version
 assert p['source_retrieval_calls'] and p['company_writes']==0
 assert p['available_evidence']['complaints']['records'][0]['fields']['_id']=='C123'
 assert all(t['dependency_resolution']['complete'] for t in p['tasks'].values())
 assert x.service.coverage.preparation.get(x.a,p['preflight_id'])==p
 if tasks=={'complaints','inspection'}:assert not any(g.get('fact_id')=='applicable_policy' for g in p['gaps'])


def test_missing_identifier_and_unsupported_goal(investigation):
 s=investigation.service.coverage.preparation;a=investigation.a
 p=s.prepare(a,dict(objective='Compare complaint with its inspection.'))
 assert not p['source_retrieval_calls']
 assert all(v['state']=='needs_input' for v in p['coverage'].values())
 assert s.general_context(a,'Translate a paragraph into French')['state']=='unsupported'
 with pytest.raises(ApiFailure):s.prepare(a,dict(objective='Send warranty approval for complaint C123.'))

@pytest.mark.parametrize('variant,task,state',[('complete','replacement','ready'),('missing_exclusions','warranty','insufficient_evidence'),('conflicting_identity','replacement','conflicting_evidence'),('rejected_authorization','replacement','ready')])
def test_shared_scenario_coverage_and_adapter(investigation,variant,task,state):
 x=investigation;doc=release(x,(variant,));s=x.service.coverage.preparation
 p=s.prepare(x.a,dict(objective='Compare complaint C123, check warranty readiness and review replacement evidence.',evidence_context=dict(dataset_id=doc['dataset_id'],case_id=doc['cases'][0]['case_id'])))
 assert p['coverage'][task]['state'] in (state,'ready_with_limitations') if state=='ready' else p['coverage'][task]['state']==state
 result=BusinessEvidenceAdapter(s).invoke(x.a,dict(preparation_id=p['preflight_id'],task=task))
 assert result['scenario_context']['sha256']==doc['sha256']
 assert any(r['collection'].startswith('business_') for r in result['records'])
 assert result['coverage']['official_approval'] is False


def test_adapter_denies_query_injection_foreign_scope_and_revoked_source(investigation):
 x=investigation;s=x.service.coverage.preparation
 p=s.prepare(x.a,dict(objective=OBJECTIVE));adapter=BusinessEvidenceAdapter(s);body=dict(preparation_id=p['preflight_id'],task='inspection')
 with pytest.raises(ApiFailure):adapter.invoke(x.a,{**body,'query':'select *'})
 with pytest.raises(ApiFailure):adapter.invoke(auth(owner='other'),body)
 with pytest.raises(ApiFailure):adapter.invoke(x.a,{**body,'task':'replacement'})
 count=len(x.reader.calls);x.current['permissions']=[]
 with pytest.raises(ApiFailure):adapter.invoke(x.a,body)
 assert len(x.reader.calls)==count


def test_current_source_values_refresh_but_pinned_observations_stay(investigation):
 x=investigation;s=x.service.coverage.preparation;p=s.prepare(x.a,dict(objective=OBJECTIVE))
 original=deepcopy(p['available_evidence']);x.reader.rows['jointinspectionreports'][0]['defectDescription']='Changed observation'
 result=BusinessEvidenceAdapter(s).invoke(x.a,dict(preparation_id=p['preflight_id'],task='inspection'))
 assert any(r['fields'].get('defectDescription')=='Changed observation' for r in result['records'])
 assert s.get(x.a,p['preflight_id'])['available_evidence']==original


def test_both_planners_use_shared_preparation_and_pin_persistence(investigation):
 x=investigation;x.a=planner_auth(x.a);x.current.update(deepcopy(x.a))
 provider=GroundedProvider();general=WorkflowService(x.f.store,PlannerService(provider));general.business_preparation=x.service.coverage.preparation
 req=dict(operation='plan_workflow',request_id='shared_req',idempotency_key='shared_general_001',payload=dict(objective=OBJECTIVE,context=dict(generation_mode='hierarchy',business_preparation={'forged':True})))
 with patch.object(general.business_preparation,'prepare',wraps=general.business_preparation.prepare) as shared:
  response=general.handle(req,x.a)
  assert response['status']==200,response
  plan=x.service.coverage.prepare_plan(x.a,dict(objective=OBJECTIVE,request_key='shared_investigation_001',planning_mode='offline',analysis_mode='offline'))
  assert shared.call_count==2
 workflow=response['data']['workflow'];pin=workflow['metadata']['business_preparation']
 assert workflow['metadata']['dynamic_delegation']
 assert provider.contexts[0]['business_preparation']['pins']==plan['ontology_context']['business_preparation']['pins']
 assert pin['pins']['ontology_version']==x.version
 with x.f.store.transaction(write=False) as db:verify_workflow_pin(db,x.a,workflow)
 changed=deepcopy(workflow);changed['metadata'].pop('business_preparation')
 with x.f.store.transaction(write=False) as db:
  with pytest.raises(ApiFailure):verify_workflow_pin(db,x.a,changed)
 before=len(x.reader.calls);retry=general.handle(req,x.a)
 assert retry['data']['workflow']==workflow and len(x.reader.calls)==before


def test_version_scope_and_integrity(investigation):
 x=investigation;s=x.service.coverage.preparation
 with pytest.raises(ApiFailure):s.prepare(x.a,dict(objective=OBJECTIVE,workspace_id='foreign'))
 p=s.prepare(x.a,dict(objective=OBJECTIVE,version_id=x.version,client_id='simpson',domain_id='manufacturing'))
 assert p['domain_context']==dict(client_id='simpson',domain_id='manufacturing')
 with x.f.store.transaction() as db:
  changed=deepcopy(p);changed['pins']['knowledge_sha256']='forged'
  from workflow_api.business_knowledge_model import canonical
  db.execute('UPDATE business_evidence_preflights SET document=? WHERE preflight_id=?',(canonical(changed),p['preflight_id']))
 with pytest.raises(ApiFailure):s.get(x.a,p['preflight_id'])


def test_runtime_connector_contract_and_exact_workflow_binding(investigation):
 from workflow_api.business_preparation import BusinessEvidenceConnector,retrieval_tool_definition,bind_workflow
 from registry.contracts import validate
 from runtime.service import RuntimeFailure
 x=investigation;s=x.service.coverage.preparation;p=s.prepare(x.a,dict(objective=OBJECTIVE));definition=retrieval_tool_definition();validate(definition,'tool')
 workflow={'metadata':{}};bind_workflow(workflow,{'business_preparation':s.context(p)})
 connector=BusinessEvidenceConnector(s).bind_context(workflow,{},x.a,{})
 result=connector.invoke({'tool_id':definition['tool_id']},dict(preparation_id=p['preflight_id'],task='inspection'),'test_read')
 assert result['version_id']==p['version_id'] and result['coverage']
 with pytest.raises(RuntimeFailure):connector.invoke({'tool_id':definition['tool_id']},dict(preparation_id='foreign',task='inspection'),'test_denied')


def test_pins_survive_new_ontology_head_and_detect_metadata_changes(investigation):
 import json
 x=investigation;s=x.service.coverage.preparation;p=s.prepare(x.a,dict(objective=OBJECTIVE,version_id=x.version))
 version=deepcopy(x.snapshot);version['version_id']='later_version';version['revision']+=1
 with x.f.store.transaction() as db:db.execute('INSERT INTO business_ontology_versions VALUES (?,?,?,?)',('one','alice',version['version_id'],json.dumps(version)))
 assert s.checked(x.a,p['preflight_id'])['version_id']==x.version
 original=x.s.binding
 def changed(*args):return {**original(*args),'stamp':'changed'}
 with patch.object(x.s,'binding',side_effect=changed):
  with pytest.raises(ApiFailure) as error:BusinessEvidenceAdapter(s).invoke(x.a,dict(preparation_id=p['preflight_id'],task='inspection'))
  assert error.value.code=='BUSINESS_SOURCE_STALE'


def test_request_schema_and_scenario_version_are_enforced(investigation):
 x=investigation;s=x.service.coverage.preparation
 with pytest.raises(ApiFailure):s.prepare(x.a,dict(objective=OBJECTIVE,query='select *'))
 release_doc=release(x)
 with pytest.raises(ApiFailure):s.prepare(x.a,dict(objective=OBJECTIVE,version_id='wrong',evidence_context=dict(dataset_id=release_doc['dataset_id'],case_id=release_doc['cases'][0]['case_id'])))


def test_prepared_sources_only_in_child_model_view(investigation):
 x=investigation;s=x.service.coverage.preparation;p=s.prepare(x.a,dict(objective=OBJECTIVE));view=s.context(p)
 for task,t in view['tasks'].items():
  assert all(mid in view['definitions']['mappings'] for mid in t['mappings'])
  assert set(t['dependency_resolution']['concept_ids'])<=set(view['definitions']['concepts'])
 assert all('fields' not in r for rs in view['available_evidence'].values() for r in rs)


def test_registry_candidates_are_discovery_not_assignments(investigation):
 from registry import RegistryService,WorkspacePolicy
 from workflow_api.business_preparation import retrieval_tool_definition
 x=investigation;s=x.service.coverage.preparation
 admin=deepcopy(x.a);admin['roles']=['admin'];admin['permissions']+=['tools.manage']
 registry=RegistryService(WorkspacePolicy('one',approved_providers={'builder_business'},remaining_quota={'business_retrieve_evidence':10}))
 assert registry.register_tool(retrieval_tool_definition(),admin)['status']==200
 s.registry=registry;p=s.prepare(x.a,dict(objective=OBJECTIVE))
 assert p['tool_candidates']==[]
 x.a['scopes'].append('tools.read');x.current['scopes'].append('tools.read')
 x.a['roles']=['builder'];x.current['roles']=['builder']
 p=s.prepare(x.a,dict(objective=OBJECTIVE))
 assert p['tool_candidates'][0]['tool_id']=='business_retrieve_evidence'
 assert p['tool_candidates'][0]['authorization_state']=='requires_assignment'
 assert 'credential_reference' not in p['tool_candidates'][0]


def test_approved_runtime_rejects_modified_preparation(investigation):
 import json
 from pathlib import Path
 from runtime import RuntimeService,RuntimeFailure
 from workflow_api.business_preparation import bind_workflow,record_workflow_pin
 x=investigation;s=x.service.coverage.preparation;p=s.prepare(x.a,dict(objective=OBJECTIVE))
 workflow=json.loads((Path(__file__).resolve().parents[1]/'shared/contracts/examples/workflows/support-triage.json').read_text())
 bind_workflow(workflow,{'business_preparation':s.context(p)});record_workflow_pin(x.f.store,x.a,workflow)
 workflow['status']='approved';workflow['metadata'].update(workspace_id='one',approved_by='reviewer',validation_state='validated')
 workflow['metadata']['business_preparation']['sha256']='changed'
 general=WorkflowService(x.f.store);runtime=RuntimeService(general)
 with x.f.store.transaction() as db:x.f.store.put(db,'one',workflow)
 current=deepcopy(x.a);current['roles']=['admin']
 with x.f.store.transaction(write=False) as db:
  with pytest.raises(RuntimeFailure) as error:runtime.revision(db,workflow['workflow_id'],workflow['version'],current)
  assert error.value.code=='BUSINESS_PREPARATION_PIN_INVALID'

 # Removing the pin must also fail, rather than becoming a legacy workflow.
 workflow['metadata'].pop('business_preparation')
 with x.f.store.transaction() as db:x.f.store.put(db,'one',workflow)
 with x.f.store.transaction(write=False) as db:
  with pytest.raises(RuntimeFailure) as error:runtime.revision(db,workflow['workflow_id'],workflow['version'],current)
  assert error.value.code=='BUSINESS_PREPARATION_PIN_INVALID'
