"""Phase 3 acceptance with real store/Registry/runtime, isolated transports only."""
from copy import deepcopy
import json
from threading import Lock
import pytest
from tests.test_business_composition import (composition, investigation, retrieval, knowledge, reference,
 generation, foundation, auth, release, prepare, approve, DiagnosticAgents, run)
from runtime import RuntimeService
from runtime.graph import GraphRunner
from runtime.service import RuntimeFailure
from runtime.memory import bounded_context, knowledge_pin
from runtime.recovery import classify, affected_tasks, CATEGORIES
from workflow_api.client_packages import (ClientPackages,PackageEvidenceConnector,package_tool_definition,PACKAGE_INPUT,PACKAGE_OUTPUT)
from workflow_api.capability_contracts import contract


def stored(rt, auth, rid):
 with rt.store.transaction(write=False) as db:return rt.load(db,rid,auth)


@pytest.mark.parametrize('code,category,write',[
 ('AGENT_OUTPUT_INVALID','invalid_model_output',False),('EVIDENCE_MISSING','missing_evidence',False),
 ('EVIDENCE_VALUE_INVALID','invalid_source_values',False),('SOURCE_METADATA_STALE','stale_metadata',False),
 ('MAPPING_INVALID','incorrect_source_mapping',False),('CONNECTOR_TIMEOUT','connector_timeout',False),
 ('CONNECTOR_AUTH_FAILED','connector_authentication',False),('OPERATION_NOT_AUTHORIZED','revoked_authorization',False),
 ('EVIDENCE_CONFLICT','conflicting_business_evidence',False),('CAPABILITY_UNSUPPORTED','unsupported_capability',False),
 ('OTHER','tool_execution_failure',False),('CONNECTOR_TIMEOUT','uncertain_external_write',True),
 ('CAPABILITY_DEPENDENCY','workflow_dependency',False)])
def test_failure_taxonomy(code,category,write):
 f=classify(code,task='task_1',source='source_1',external_write=write)
 assert f['category']==category and f['affected_task']=='task_1'
 assert f['recovery_strategy'] and (not write or not f['retry_eligible'])


def test_dependency_closure_preserves_independent_work():
 tasks=[dict(task_id='read_a',depends_on=[],dependency_refs=['mapping:a','record:a','rule:a']),dict(task_id='read_b',depends_on=[],dependency_refs=['mapping:b']),dict(task_id='analysis',depends_on=['read_a']),dict(task_id='report',depends_on=['analysis','read_b'])]
 assert affected_tasks(tasks,['mapping:a'])=={'read_a','analysis','report'}
 assert affected_tasks(tasks,['record:a'])=={'read_a','analysis','report'}
 assert affected_tasks(tasks,['rule:a'])=={'read_a','analysis','report'}
 assert affected_tasks(tasks,['unrelated'])==set()


def test_context_bound_and_task_isolation(composition):
 f=composition;d=prepare(f);agents=DiagnosticAgents();result,_,rt=run(f,d,agents)
 assert result['status']=='completed'
 child=[c for c in agents.contexts if 'context' in c]
 assert child
 for c in child:
  memory=c['context']['working_memory']
  assert memory['assigned_task']['task_id']==c['task_id']
  assert 'workflow_transcript' not in memory and 'task_graph' not in memory
  assert set(c['context']['dependency_results'])==set(memory['assigned_task']['depends_on'])
 assert stored(rt,f.x.a,result['run_id'])['outcome_evaluation']['achieved_outcome']=='completed'
 with pytest.raises(RuntimeFailure,match='context'):bounded_context({'required':'x'*200},max_bytes=100)


class InterruptRead:
 external_write=False;retry_safe=True;timeout=45
 def __init__(self,underlying,state=None):self.underlying=underlying;self.state=state or {'failed':False,'lock':Lock(),'calls':[]}
 def reservation(self,g):return self.underlying.reservation(g)
 def bind_context(self,w,r,a,n):return InterruptRead(self.underlying.bind_context(w,r,a,n),self.state)
 def invoke(self,g,i,key):
  with self.state['lock']:
   self.state['calls'].append(i['task'])
   if i['task']=='inspection' and not self.state['failed']:
    self.state['failed']=True;raise RuntimeFailure('CONNECTOR_TIMEOUT','Temporary fixture interruption')
  return self.underlying.invoke(g,i,key)


def interrupted(f):
 d=prepare(f,recovery_max_retries=1)
 connector=InterruptRead(f.connectors['business_retrieve_evidence']);f.connectors['business_retrieve_evidence']=connector
 result,events,rt=run(f,d)
 assert result['status']=='failed'
 with rt.store.transaction() as db:
  r=rt.load(db,result['run_id'],f.x.a);r['lease_until']=0;rt.save(db,r)
 return d,connector,result,rt


def test_resume_preserves_checkpoints_usage_and_pins(composition):
 f=composition;d,connector,result,rt=interrupted(f);rid=result['run_id'];before=stored(rt,f.x.a,rid)
 assert 'task_1' in before['task_checkpoints']
 rt2=RuntimeService(f.general) # Restart service using the same store.
 assert rt2.recovery.resume(rid,f.x.a)['status']=='queued'
 after=GraphRunner(rt2,agents=DiagnosticAgents(),connectors=f.connectors).advance(rid,f.x.a)
 assert after['status']=='completed',stored(rt2,f.x.a,rid)
 saved=stored(rt2,f.x.a,rid)
 assert connector.state['calls'].count('complaints')==1
 assert connector.state['calls'].count('inspection')==2
 assert saved['workflow_digest']==before['workflow_digest'] and saved['inputs']==before['inputs']
 assert saved['created_at']==before['created_at']
 assert saved['usage']['workflow']['llm_calls']>before['usage']['workflow']['llm_calls']
 assert saved['outcome_evaluation']['recovery_success']
 assert saved['task_checkpoints']['task_1']==before['task_checkpoints']['task_1']


def test_targeted_recovery_invalidates_changed_mapping(composition):
 f=composition;_,connector,result,rt=interrupted(f);rid=result['run_id']
 rt.recovery.resume(rid,f.x.a,changed_dependencies=['mapping:ticket_id'])
 saved=stored(rt,f.x.a,rid)
 assert 'task_1' not in saved['task_checkpoints']
 assert 'task_1' in saved['recovery_history'][0]['invalidated_results']
 assert GraphRunner(rt,agents=DiagnosticAgents(),connectors=f.connectors).advance(rid,f.x.a)['status']=='completed',stored(rt,f.x.a,rid)


@pytest.mark.parametrize('error',['SOURCE_METADATA_STALE','OPERATION_NOT_AUTHORIZED','EVIDENCE_MISSING','EVIDENCE_CONFLICT','UNKNOWN_INVOCATION_RESULT'])
def test_nonretryable_cause_requires_review(composition,error):
 f=composition;_,_,result,rt=interrupted(f)
 with rt.store.transaction() as db:
  r=rt.load(db,result['run_id'],f.x.a);r['error_code']=error
  if error=='UNKNOWN_INVOCATION_RESULT':
   # An ordinary tool graph cannot assert that an unknown effect was a safe read.
   # Do not alter approved workflow controls: use a known uncertain-write code instead.
   r['error_code']='SMTP_DELIVERY_UNCERTAIN'
  rt.save(db,r)
 with pytest.raises(RuntimeFailure) as exc:rt.recovery.resume(result['run_id'],f.x.a)
 assert exc.value.code=='RECOVERY_REVIEW_REQUIRED'


def test_experience_validation_freshness_and_tenant_isolation(composition):
 f=composition;_,_,result,rt=interrupted(f);rid=result['run_id']
 rt.recovery.resume(rid,f.x.a)
 assert GraphRunner(rt,agents=DiagnosticAgents(),connectors=f.connectors).advance(rid,f.x.a)['status']=='completed',stored(rt,f.x.a,rid)
 w=f.c.workflow(f.x.a,prepare(f)['composition_id']);pins=knowledge_pin(w)
 kwargs=dict(domain='configured_business_ontology',capability='business.read.inspection',category='connector_timeout',strategy='retry_read',evidence_references=[{'run_id':rid}],pins=pins,expires_at=rt.clock()+3600)
 entry=rt.experience_memory.candidate(f.x.a,**kwargs)
 query=dict(domain='configured_business_ontology',capability='business.read.inspection',category='connector_timeout',pins=pins)
 assert rt.experience_memory.relevant(f.x.a,**query)==[]
 rt.experience_memory.validate(f.x.a,entry['experience_id'],run_id=rid)
 assert len(rt.experience_memory.relevant(f.x.a,**query))==1
 other=deepcopy(f.x.a);other['subject']['workspace_id']='another-tenant'
 assert rt.experience_memory.relevant(other,**query)==[]
 other=deepcopy(f.x.a);other['subject']['subject_id']='another-owner'
 assert rt.experience_memory.relevant(other,**query)==[]
 assert rt.experience_memory.relevant(f.x.a,**{**query,'pins':{**pins,'mapping_sha256':'changed'}})==[]
 assert rt.experience_memory.relevant(f.x.a,**query)==[]


def test_unverified_experience_cannot_be_promoted(composition):
 f=composition;d=prepare(f);result,_,rt=run(f,d)
 entry=rt.experience_memory.candidate(f.x.a,domain='configured_business_ontology',capability='business.compare',category='connector_timeout',strategy='retry_read',evidence_references=[{'run_id':result['run_id']}],pins={},expires_at=rt.clock()+100)
 with pytest.raises(RuntimeFailure):rt.experience_memory.validate(f.x.a,entry['experience_id'],run_id=result['run_id'])
 with pytest.raises(RuntimeFailure):rt.experience_memory.candidate(f.x.a,domain='configured_business_ontology',capability='business.compare',category='approval',strategy='approve_claim',evidence_references=[{}],pins={},expires_at=rt.clock()+100)


def retail_package():
 read=contract('retail.read','retrieve_mapped_evidence','Read mapped inventory',kind='tool',tool_operation='business.retrieve_package_evidence',effect='read',inputs=PACKAGE_INPUT,outputs=PACKAGE_OUTPUT,verify='mapped_evidence_and_coverage',domain='retail')
 read['required_ontology']=['Inventory','Product'];read['required_evidence']=['mapping:stock','mapping:threshold']
 review=contract('retail.review','interpret_supported_evidence','Summarize products below configured threshold',domain='retail');review['preconditions']=['retail.read'];review['required_ontology']=['Inventory','Product']
 return dict(package_id='retail_fixture',revision=1,client_id='isolated-retailer',domain='retail',ontology_version='retail_v1',
 concepts=[{'id':'Asset'},{'id':'Store'},{'id':'Product','parent':'Asset'},{'id':'Inventory'},{'id':'Supplier'},{'id':'ReplenishmentRequest'}],
 relationships=[{'source':'Inventory','predicate':'holds','target':'Product'},{'source':'Store','predicate':'has','target':'Inventory'}],
 source_mappings=[{'id':'mapping:stock','concept':'Inventory','field':'stock','source':'inventory_fixture'},{'id':'mapping:threshold','concept':'Inventory','field':'threshold','source':'inventory_fixture'},{'id':'mapping:product','concept':'Product','field':'product','source':'inventory_fixture'}],
 evidence_requirements=[{'capability_id':'retail.read','mapping_id':'mapping:stock'},{'capability_id':'retail.read','mapping_id':'mapping:threshold'}],
 capability_contracts={'retail.read':read,'retail.review':review},rules=[{'id':'rule:below_threshold','operator':'lt','left_mapping':'mapping:stock','right_mapping':'mapping:threshold'}],
 resource_bindings={'retail.read':{'source_id':'inventory_fixture','mapping_ids':['mapping:stock','mapping:threshold','mapping:product']}},validation_requirements=['acyclic_dependencies','mapped_evidence','current_source_authority'])


def setup_retail(f):
 f.registry._policy.remaining_quota['client_package_read']=100
 assert f.registry.register_tool(package_tool_definition(),f.x.a)['status']==200
 packages=f.c.packages
 packages.register_source(f.x.a,'inventory_fixture',lambda auth,binding:[{'id':'stock_1','product':'Filter','stock':3,'threshold':10},{'id':'stock_2','product':'Belt','stock':20,'threshold':5}])
 packages.publish(f.x.a,retail_package())
 f.connectors['client_package_read']=PackageEvidenceConnector(packages)
 return packages


def test_second_domain_same_compiler_factory_registry_and_runtime(composition):
 f=composition;packages=setup_retail(f)
 d=prepare(f,'Identify products below their configured stock threshold and prepare a replenishment summary.',client_package_id='retail_fixture',client_package_revision=1,operations=[{'capability_id':'retail.review','inputs':{}}])
 assert d['state']=='ready',d['gaps']
 assert {t['capability_id'] for t in d['tasks']}=={'retail.read','retail.review','business.report'}
 assert len(d['configurations'])==3
 result,_,rt=run(f,d)
 assert result['status']=='completed',stored(rt,f.x.a,result['run_id'])
 saved=stored(rt,f.x.a,result['run_id'])
 read=next(c['result'] for c in saved['task_checkpoints'].values() if c['result'].get('coverage'))
 outcomes=read['source_evidence'][0]['rule_results']
 assert [(o['record_id'],o['matched']) for o in outcomes]==[('stock_1',True),('stock_2',False)]
 assert saved['outcome_evaluation']['evidence_validity'] is True
 w=f.c.workflow(f.x.a,d['composition_id'])
 assert w['metadata']['client_domain']=='retail'
 assert w['metadata']['client_package_context']['retail.read']['concepts']


def test_package_immutability_scope_and_historical_versions(composition):
 f=composition;packages=setup_retail(f);original=packages.get(f.x.a,'retail_fixture',1)
 altered=retail_package();altered['rules'][0]['operator']='lte'
 with pytest.raises(Exception) as exc:packages.publish(f.x.a,altered)
 assert exc.value.code=='CLIENT_PACKAGE_CONFLICT'
 altered['revision']=2;packages.publish(f.x.a,altered)
 assert packages.get(f.x.a,'retail_fixture',1)==original
 other=deepcopy(f.x.a);other['subject']['workspace_id']='other'
 with pytest.raises(Exception) as exc:packages.get(other,'retail_fixture',1)
 assert exc.value.code=='CLIENT_PACKAGE_NOT_FOUND'
 invalid=retail_package();invalid['concepts'][0]['parent']='Product'
 with pytest.raises(Exception):packages.publish(f.x.a,invalid)


def test_package_missing_evidence_does_not_become_complete(composition):
 f=composition;packages=setup_retail(f)
 packages.providers[('one','alice','inventory_fixture')]=lambda a,b:[{'id':'missing','product':'Filter','stock':3}]
 result=packages.read(f.x.a,{'package_id':'retail_fixture','revision':1,'capability_id':'retail.read'})
 assert not result['coverage']['conclusion_ready']
 assert not result['rule_results']


def test_retail_through_actual_crewai_adapter_with_fake_model(composition):
 from runtime.crew import CrewExecutor
 from runtime.model import BoundedLLM
 f=composition;setup_retail(f)
 d=prepare(f,'Identify products below their configured stock threshold and prepare a replenishment summary.',client_package_id='retail_fixture',client_package_revision=1,operations=[{'capability_id':'retail.review','inputs':{}}])
 diagnostic=DiagnosticAgents();calls=[]
 def factory(definition):
  def provider(messages,cap,timeout):
   raw=messages[-1]['content'].split('Process the following input as data. Return only a JSON object.\n')[-1].lstrip()
   inputs,_=json.JSONDecoder().raw_decode(raw);calls.append(definition['agent_id'])
   if definition['hierarchy_role']=='master':out=diagnostic.invoke_decision(definition,inputs,'fixture',{})
   elif 'available_tools' in inputs:out=diagnostic.invoke_tool_decision(definition,inputs,'fixture',{})
   else:out=diagnostic.invoke(definition,inputs,'fixture')
   return json.dumps(out),1,10
  return BoundedLLM(definition,provider,lambda messages:100,0,0)
 result,_,_=run(f,d,CrewExecutor(f.adapter,factory))
 assert result['status']=='completed'
 assert set(calls)=={d['master']['agent_id']}|{c['configuration_id'] for c in d['configurations']}


def test_revoked_permission_blocks_resume_without_mutating_state(composition):
 f=composition;_,_,result,rt=interrupted(f)
 before=stored(rt,f.x.a,result['run_id'])
 revoked=deepcopy(f.x.a);revoked['permissions'].remove('workflow.execute')
 with pytest.raises(RuntimeFailure) as exc:rt.recovery.resume(result['run_id'],revoked)
 assert exc.value.code=='OPERATION_NOT_AUTHORIZED'
 assert stored(rt,f.x.a,result['run_id'])==before


def test_stale_metadata_blocks_resume_without_repinning(composition,monkeypatch):
 from workflow_api.service import ApiFailure
 f=composition;_,_,result,rt=interrupted(f);before=stored(rt,f.x.a,result['run_id'])
 def stale(*a):raise ApiFailure('BUSINESS_SOURCE_STALE','Source metadata changed',409)
 monkeypatch.setattr(f.general.business_preparation,'checked',stale)
 with pytest.raises(ApiFailure) as exc:rt.recovery.resume(result['run_id'],f.x.a)
 assert exc.value.code=='BUSINESS_SOURCE_STALE'
 assert stored(rt,f.x.a,result['run_id'])==before


def test_approved_retry_budget_is_required(composition):
 f=composition;d=prepare(f)
 class Bad(DiagnosticAgents):
  def invoke(self,*args):raise RuntimeFailure('CONNECTOR_TIMEOUT','Fixture interruption')
 result,_,rt=run(f,d,Bad())
 with rt.store.transaction() as db:
  r=rt.load(db,result['run_id'],f.x.a);r['lease_until']=0;rt.save(db,r)
 with pytest.raises(RuntimeFailure) as exc:rt.recovery.resume(result['run_id'],f.x.a)
 assert exc.value.code=='RETRY_EXHAUSTED'


def test_unknown_dependency_does_not_invalidate_anything(composition):
 f=composition;_,_,result,rt=interrupted(f);before=stored(rt,f.x.a,result['run_id'])
 with pytest.raises(RuntimeFailure) as exc:rt.recovery.resume(result['run_id'],f.x.a,changed_dependencies=['invented:mapping'])
 assert exc.value.code=='RECOVERY_INPUT_INVALID'
 assert stored(rt,f.x.a,result['run_id'])==before


def test_expired_and_explicitly_invalidated_memory_is_not_reused(composition):
 f=composition;_,_,result,rt=interrupted(f);rid=result['run_id'];rt.recovery.resume(rid,f.x.a)
 assert GraphRunner(rt,agents=DiagnosticAgents(),connectors=f.connectors).advance(rid,f.x.a)['status']=='completed'
 w=f.c.workflow(f.x.a,prepare(f)['composition_id']);pins=knowledge_pin(w)
 data=dict(domain='configured_business_ontology',capability='business.read.inspection',category='connector_timeout',strategy='retry_read',evidence_references=[{'run_id':rid}],pins=pins,expires_at=rt.clock()+100)
 entry=rt.experience_memory.candidate(f.x.a,**data);rt.experience_memory.validate(f.x.a,entry['experience_id'],run_id=rid)
 query={k:data[k] for k in ('domain','capability','category','pins')}
 assert rt.experience_memory.relevant(f.x.a,**query)
 rt.experience_memory.invalidate(f.x.a,entry['experience_id'],'operator_correction')
 assert not rt.experience_memory.relevant(f.x.a,**query)
 entry=rt.experience_memory.candidate(f.x.a,**data);rt.experience_memory.validate(f.x.a,entry['experience_id'],run_id=rid)
 original=rt.clock;rt.clock=lambda:original()+101
 assert not rt.experience_memory.relevant(f.x.a,**query)


def test_invalid_model_output_recovers_through_existing_correction(composition):
 f=composition;d=prepare(f)
 class Corrected(DiagnosticAgents):
  def __init__(self):super().__init__();self.malformed=False
  def invoke_decision(self,agent,inputs,invocation_id,schema):
   if not self.malformed:self.malformed=True;return {'malformed':'output'}
   return super().invoke_decision(agent,inputs,invocation_id,schema)
 result,events,_=run(f,d,Corrected())
 assert result['status']=='completed'
 assert any(e['event_type']=='agent.correction' for e in events)


def test_uncertain_external_write_requires_reconciliation(composition):
 from tests.test_business_composition import install_external
 f=composition;_,fake=install_external(f,'extension_mail_draft')
 def uncertain(*args):raise RuntimeFailure('UNKNOWN_INVOCATION_RESULT','Provider response lost')
 fake.invoke=uncertain
 d=prepare(f,'Prepare an inspection draft.',operations=[dict(capability_id='tool.extension_mail_draft',inputs=dict(to='fixture@example.test',subject='Review',body='Fixture only'))],resources={'destination':'extension_recipients'},recovery_max_retries=1)
 w=f.c.workflow(f.x.a,d['composition_id']);f.adapter.auto_resolve_planner=True
 assert f.adapter.approve_pending(w,f.x.a)['ready'];approve(f,w)
 rt=RuntimeService(f.general);runner=GraphRunner(rt,agents=DiagnosticAgents(),connectors=f.connectors)
 created=rt.create_run(dict(request_id='uncertain',idempotency_key='uncertain_write_001',payload=dict(workflow_id=w['workflow_id'],workflow_version=1,inputs={})),f.x.a)
 rid=created['run_id'];assert runner.advance(rid,f.x.a)['status']=='paused_for_approval'
 r=stored(rt,f.x.a,rid)
 runner.decide(dict(request_id='approve_fixture',operation='decide_approval',idempotency_key='approve_uncertain_001',payload=dict(approval_id=r['approvals'][-1]['approval_id'],workflow_id=w['workflow_id'],workflow_version=1,decision='approved')),f.x.a)
 assert runner.advance(rid,f.x.a)['status']=='blocked'
 with rt.store.transaction() as db:
  r=rt.load(db,rid,f.x.a);r['lease_until']=0;rt.save(db,r)
 with pytest.raises(RuntimeFailure) as exc:rt.recovery.resume(rid,f.x.a)
 assert exc.value.code=='RECOVERY_RECONCILIATION_REQUIRED'
 assert stored(rt,f.x.a,rid)['classified_failures'][-1]['category']=='uncertain_external_write'


def test_expired_worker_lease_blocks_then_resumes_without_duplicate_reads(composition):
 f=composition;_,connector,result,rt=interrupted(f);rid=result['run_id']
 # Model a worker dying while the coordinator was executing, after a durable child checkpoint.
 with rt.store.transaction() as db:
  r=rt.load(db,rid,f.x.a);r['status']='running';r['node_states']['master_orchestrator']='executing';r['lease_until']=0;rt.save(db,r)
 restarted=RuntimeService(f.general);runner=GraphRunner(restarted,agents=DiagnosticAgents(),connectors=f.connectors)
 assert runner.advance(rid,f.x.a)['status']=='blocked'
 with rt.store.transaction() as db:
  r=rt.load(db,rid,f.x.a);r['lease_until']=0;rt.save(db,r)
 restarted.recovery.resume(rid,f.x.a)
 assert runner.advance(rid,f.x.a)['status']=='completed'
 assert connector.state['calls'].count('complaints')==1


def test_changed_source_observation_invalidates_its_descendants(composition,monkeypatch):
 f=composition;_,connector,result,rt=interrupted(f);rid=result['run_id']
 original=f.general.business_preparation.coverage.refresh
 def changed(*args,**kwargs):
  evidence=deepcopy(original(*args,**kwargs))
  if args[-1]=='complaints':evidence['records'][0]['values']['mapping:ticket_hours']=999
  return evidence
 monkeypatch.setattr(f.general.business_preparation.coverage,'refresh',changed)
 rt.recovery.resume(rid,f.x.a)
 state=stored(rt,f.x.a,rid)
 assert 'task_1' not in state['task_checkpoints']
 assert any(not r['unchanged'] for r in state['recovery_history'][0]['source_revalidations'])
 assert GraphRunner(rt,agents=DiagnosticAgents(),connectors=f.connectors).advance(rid,f.x.a)['status']=='completed'


def test_retail_conflicting_inventory_stays_a_conflict(composition):
 f=composition;packages=setup_retail(f)
 packages.providers[('one','alice','inventory_fixture')]=lambda a,b:[{'id':'same','stock':1,'threshold':5},{'id':'same','stock':10,'threshold':5}]
 evidence=packages.read(f.x.a,{'package_id':'retail_fixture','revision':1,'capability_id':'retail.read'})
 assert evidence['coverage']['state']=='conflicting_evidence'
 assert not evidence['coverage']['conclusion_ready']


def test_historical_composition_keeps_original_compilation(composition):
 from workflow_api.business_composition import compile_workflow,verify_composition
 from workflow_api.business_knowledge_model import digest
 f=composition;doc=prepare(f);doc.pop('runtime_features_version');doc.pop('sha256');doc['sha256']=digest(doc)
 with f.x.f.store.transaction() as db:
  db.execute('UPDATE business_compositions SET document=? WHERE composition_id=?',(json.dumps(doc),doc['composition_id']))
 old=compile_workflow(doc)
 assert all('dependency_refs' not in t and 'mapped_evidence' not in t for t in old['metadata']['composition_tasks'].values())
 with f.x.f.store.transaction(write=False) as db:verify_composition(db,f.x.a,old)
 assert f.c.get(f.x.a,doc['composition_id'])==doc


def test_memory_and_package_http_boundaries(tmp_path):
 from fastapi.testclient import TestClient
 from workflow_api.main import create_app
 app=create_app(database=tmp_path/'phase3-api.sqlite',dev_auth=True,roles=['admin'],runtime_enabled=True,start_workers=False)
 client=TestClient(app)
 assert client.get('/business-ontology/v1/run-memory/missing').status_code==401
 client.get('/session');client.cookies.set('builder_dev_session',client.cookies.get('builder_dev_session'),path='/')
 assert client.post('/business-ontology/v1/client-packages',json=retail_package(),headers={'origin':'https://untrusted.example'}).status_code==403
 response=client.post('/business-ontology/v1/client-packages',json=retail_package())
 assert response.status_code==200,response.text
 assert client.get('/business-ontology/v1/client-packages/retail_fixture/1').status_code==200
 assert client.post('/business-ontology/v1/experiences/candidate',json={}).status_code==422
 assert client.post('/business-ontology/v1/experiences/unknown',json={}).status_code==422
 assert client.get('/business-ontology/v1/run-memory/missing').status_code==404
 assert client.get('/business-ontology/v1/run-outcomes/missing').status_code==404
 assert client.post('/business-ontology/v1/recovery/missing/resume',json={}).status_code==404
 assert client.post('/business-ontology/v1/recovery/missing/resume',json={'inputs':{'forged':True}}).status_code==422


def test_source_adapter_registration_is_tenant_and_owner_scoped(composition):
 f=composition;packages=setup_retail(f)
 other=deepcopy(f.x.a);other['subject']['subject_id']='another-owner'
 packages.publish(other,retail_package())
 with pytest.raises(Exception) as exc:packages.read(other,{'package_id':'retail_fixture','revision':1,'capability_id':'retail.read'})
 assert exc.value.code=='CLIENT_SOURCE_UNAVAILABLE'


def test_validated_strategy_hint_enters_only_relevant_future_task(composition):
 f=composition;_,_,result,rt=interrupted(f);rid=result['run_id'];rt.recovery.resume(rid,f.x.a)
 assert GraphRunner(rt,agents=DiagnosticAgents(),connectors=f.connectors).advance(rid,f.x.a)['status']=='completed'
 d=prepare(f);w=f.c.workflow(f.x.a,d['composition_id'])
 entry=rt.experience_memory.candidate(f.x.a,domain='configured_business_ontology',capability='business.read.inspection',category='connector_timeout',strategy='retry_read',evidence_references=[{'run_id':rid}],pins=knowledge_pin(w),expires_at=rt.clock()+1000)
 rt.experience_memory.validate(f.x.a,entry['experience_id'],run_id=rid)
 class Capture(DiagnosticAgents):
  def __init__(self):super().__init__();self.read_contexts=[]
  def invoke_tool_decision(self,agent,inputs,invocation_id,schema):
   self.read_contexts.append(deepcopy(inputs['request']['context']))
   return super().invoke_tool_decision(agent,inputs,invocation_id,schema)
 agents=Capture();approve(f,w)
 created=rt.create_run(dict(request_id='future_hint',idempotency_key='experience_future_001',payload=dict(workflow_id=w['workflow_id'],workflow_version=1,inputs={})),f.x.a)
 result=GraphRunner(rt,agents=agents,connectors=f.connectors).advance(created['run_id'],f.x.a)
 assert result['status']=='completed'
 views={c['task']['capability_id']:c['validated_strategy_hints'] for c in agents.read_contexts}
 assert views['business.read.inspection'][0]['experience_id']==entry['experience_id']
 assert not views['business.read.complaints']
 assert set(views['business.read.inspection'][0])=={'experience_id','strategy','evidence_references','verified_outcome'}
