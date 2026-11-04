"""Actual durable jobs/canonical lifecycle/UI projections, no live transports."""
from copy import deepcopy
import pytest
from tests.test_business_composition import (composition,investigation,retrieval,knowledge,reference,generation,foundation,auth,release,prepare,approve,run,DiagnosticAgents)
from workflow_api.composition_presentation import CompositionPresentation
from workflow_api.investigation_jobs import InvestigationJobs
from workflow_api.service import ApiFailure
from planner.provider import RuleBasedStructuredOutputProvider
from runtime import RuntimeService
from runtime.graph import GraphRunner


def setup(f):
 f.x.a['permissions']=sorted(set(f.x.a['permissions'])|{'workflow.validate','workflow.delete'})
 f.x.current.update(deepcopy(f.x.a))
 rt=RuntimeService(f.general);f.general.runtime_runner=GraphRunner(rt,agents=DiagnosticAgents(),connectors=f.connectors)
 class Provider:
  def generate(self,objective,context):
   w=RuleBasedStructuredOutputProvider().generate('Write a report',{})
   w['metadata']['unresolved_requirements']=[]
   w['metadata']['capability_requests']=[{'capability_id':'business.compare','inputs':{}}]
   return w
 f.general.planner.provider=Provider()
 jobs=InvestigationJobs(f.x.service,lambda w,o:f.x.a if (w,o)==('one','alice') else None,composition=f.c)
 return jobs,CompositionPresentation(f.c),rt


def submit(jobs,f,objective='Compare complaint C123 with its linked inspection.'):
 body=dict(request_key='compose_ui_key_001',kind='compose',payload=dict(objective=objective,request_key='compose_ui_plan_001',planning_mode='model',recovery_max_retries=1))
 return jobs.submit(f.x.a,body)


def test_job_prepares_and_saves_draft_without_execution(composition):
 f=composition;jobs,ui,rt=setup(f);created=submit(jobs,f)
 assert created['state']=='queued';assert jobs.tick()
 finished=jobs.get(f.x.a,created['job_id']);assert finished['state']=='succeeded',finished
 view=ui.view(f.x.a,finished['composition_id'])
 assert view['workflow_status']=='draft' and view['run'] is None
 assert len(view['tasks'])==4 and len(ui.listing(f.x.a))==1
 assert next(t for t in view['tasks'] if t['capability_id']=='business.compare')['depends_on']
 with rt.store.transaction(write=False) as db:assert db.execute('SELECT COUNT(*) FROM runtime_runs').fetchone()[0]==0
 assert jobs.get(f.x.a,submit(jobs,f)['job_id'])['job_id']==created['job_id']


def test_canonical_validation_approval_execution_and_projection(composition):
 f=composition;jobs,ui,rt=setup(f);job=submit(jobs,f);jobs.tick();cid=jobs.get(f.x.a,job['job_id'])['composition_id'];view=ui.view(f.x.a,cid);wid=view['workflow_id']
 f.adapter.auto_resolve_planner=True
 for op,payload in [('validate_workflow',{}),('approve_workflow',{'action':'approve'})]:
  response=f.general.handle(dict(request_id='ui_'+op,operation=op,idempotency_key='ui_'+op+'_001',payload=dict(workflow_id=wid,workflow_version=1,**payload)),f.x.a)
  assert response['status']==200,response
 created=rt.create_run(dict(request_id='ui_run',idempotency_key='ui_run_key_001',payload=dict(workflow_id=wid,workflow_version=1,inputs={})),f.x.a)
 result=f.general.runtime_runner.advance(created['run_id'],f.x.a);assert result['status']=='completed'
 snapshot=ui.view(f.x.a,cid,created['run_id'])
 assert snapshot['run']['status']=='completed' and snapshot['memory']
 assert all(t['state']=='completed' for t in snapshot['tasks'])
 assert any(t['result']['records'] for t in snapshot['tasks'])
 assert all('source_evidence' not in t['result'] and 'tool_results' not in t['result'] for t in snapshot['tasks'])
 assert snapshot['run']['outcome']['achieved_outcome']=='completed'


def test_missing_anchor_is_a_visible_preparation_gap_not_a_failed_job(composition):
 f=composition;jobs,ui,_=setup(f);job=submit(jobs,f,'Compare a complaint with its linked inspection.');jobs.tick()
 saved=jobs.get(f.x.a,job['job_id']);assert saved['state']=='succeeded',saved
 snapshot=ui.view(f.x.a,saved['composition_id']);assert snapshot['state']=='needs_input' and snapshot['gaps']
 assert snapshot['workflow_status'] is None and snapshot['run'] is None


def test_projection_enforces_owner_run_and_metadata_integrity(composition):
 f=composition;_,ui,_=setup(f);doc=prepare(f);result,_,rt=run(f,doc);f.general.runtime_runner=GraphRunner(rt,agents=DiagnosticAgents(),connectors=f.connectors)
 other=deepcopy(f.x.a);other['subject']['subject_id']='other'
 with pytest.raises(Exception):ui.view(other,doc['composition_id'])
 another=prepare(f,'Show history for engine E123.')
 with pytest.raises(ApiFailure) as exc:ui.view(f.x.a,another['composition_id'],result['run_id'])
 assert exc.value.code=='RUN_NOT_FOUND'


def test_display_name_and_deletion_preserve_composition_and_history(composition):
 f=composition;_,ui,rt=setup(f);doc=prepare(f)
 original=f.c.get(f.x.a,doc['composition_id'])
 assert ui.rename(f.x.a,doc['composition_id'],{'display_name':'Service review'})['display_name']=='Service review'
 assert ui.view(f.x.a,doc['composition_id'])['display_name']=='Service review'
 assert ui.delete(f.x.a,doc['composition_id'],{'confirmed':True})['deleted']
 assert not ui.listing(f.x.a)
 assert f.c.get(f.x.a,doc['composition_id'])==original
 with pytest.raises(ApiFailure) as exc:f.c.workflow(f.x.a,doc['composition_id'])
 assert exc.value.code=='WORKFLOW_DELETED'


def test_historical_view_still_available_when_current_metadata_is_stale(composition,monkeypatch):
 f=composition;_,ui,_=setup(f);doc=prepare(f)
 def stale(*args):raise ApiFailure('BUSINESS_SOURCE_STALE','Metadata changed',409)
 monkeypatch.setattr(f.c.preparation,'checked',stale)
 assert ui.view(f.x.a,doc['composition_id'])['knowledge']
 with pytest.raises(ApiFailure):f.c.workflow(f.x.a,doc['composition_id'])


def test_cancel_is_bound_to_owner_and_composition(composition):
 f=composition;_,ui,rt=setup(f);doc=prepare(f);workflow=approve(f,f.c.workflow(f.x.a,doc['composition_id']))
 created=rt.create_run(dict(request_id='cancel_ui',idempotency_key='cancel_ui_run_001',payload=dict(workflow_id=workflow['workflow_id'],workflow_version=1,inputs={})),f.x.a)
 assert ui.cancel(f.x.a,doc['composition_id'],created['run_id'],{})['status']=='cancelled'
 assert rt.get_run(created['run_id'],f.x.a)['status']=='cancelled'


def test_deleted_canonical_workflow_cannot_execute_again(composition):
 f=composition;_,ui,rt=setup(f);doc=prepare(f);workflow=approve(f,f.c.workflow(f.x.a,doc['composition_id']))
 assert ui.delete(f.x.a,doc['composition_id'],{'confirmed':True})['deleted']
 from runtime.service import RuntimeFailure
 with pytest.raises(RuntimeFailure) as exc:rt.create_run(dict(request_id='deleted_ui',idempotency_key='deleted_ui_001',payload=dict(workflow_id=workflow['workflow_id'],workflow_version=1,inputs={})),f.x.a)
 assert exc.value.code=='WORKFLOW_DELETED'


def test_explicit_action_cannot_silently_disappear_from_model_plan(composition):
 f=composition;jobs,_,_=setup(f)
 from tests.test_business_composition import install_external
 install_external(f,'extension_mail_draft')
 job=jobs.submit(f.x.a,dict(kind='compose',request_key='explicit_job_001',payload=dict(objective='Compare complaint C123 and draft the result.',request_key='explicit_action_001',planning_mode='model',operations=[dict(capability_id='tool.extension_mail_draft',inputs=dict(to='fixture@example.test',subject='Review',body='Fixture'))])))
 assert jobs.tick()
 finished=jobs.get(f.x.a,job['job_id']);assert finished['state']=='succeeded',finished
 doc=f.c.get(f.x.a,finished['composition_id'])
 assert doc['state']=='unsupported'
 assert any(g['reason']=='EXPLICIT_CAPABILITY_NOT_PLANNED' for g in doc['gaps'])


def test_strict_capability_selection_does_not_require_a_model_generated_graph(composition):
 f=composition;setup(f);calls=[]
 class Selector:
  def select_capabilities(self,objective,context):calls.append(context);return {'capability_requests':[{'capability_id':'business.compare','inputs':{}}],'unresolved_requirements':[]}
  def generate(self,*args):raise AssertionError('A model-generated graph is not needed for registered operation selection.')
 f.general.planner.provider=Selector()
 doc=f.c.prepare(f.x.a,dict(objective='Compare complaint C123 with inspection.',request_key='strict_selection_001',planning_mode='model'))
 assert doc['state']=='ready' and calls
 assert {t['capability_id'] for t in doc['tasks']}=={'business.compare','business.read.complaints','business.read.inspection','business.report'}


def test_provider_selection_is_closed_and_disables_response_storage():
 from planner.provider import OpenAIStructuredOutputProvider
 from types import SimpleNamespace
 calls=[]
 def response(**kwargs):calls.append(kwargs);return SimpleNamespace(output_text='{"capability_ids":["business.compare"],"unresolved_requirements":[]}',status='completed')
 provider=OpenAIStructuredOutputProvider(SimpleNamespace(responses=SimpleNamespace(create=response)),model='configured')
 result=provider.select_capabilities('Compare observations.',{'capability_composition_catalog':{'business.compare':{'business_purpose':'Compare'}}})
 assert result['capability_requests']==[{'capability_id':'business.compare','inputs':{}}]
 assert calls[0]['store'] is False and calls[0]['text']['format']['strict']
 assert 'max_output_tokens' not in calls[0]


def test_master_is_shown_only_the_task_id_delegation_schema(composition):
 f=composition;setup(f);doc=prepare(f);agents=DiagnosticAgents();result,_,_=run(f,doc,agents)
 assert result['status']=='completed'
 proposals=[a['input_schema'] for context in agents.contexts if 'available_agents' in context for a in context['available_agents']]
 assert proposals and all(set(s['properties'])=={'task_id'} and s['additionalProperties'] is False for s in proposals)


def test_procurement_decorator_preserves_registered_selection():
 from types import SimpleNamespace
 from workflow_api.procurement import ProcurementPlanner
 calls=[]
 expected={'capability_requests':[{'capability_id':'business.compare','inputs':{}}],'unresolved_requirements':[]}
 fallback=SimpleNamespace(select_capabilities=lambda objective,context:(calls.append((objective,context)) or expected))
 provider=ProcurementPlanner(fallback,None,'configured',None)
 context={'capability_composition_catalog':{'business.compare':{}}}
 assert provider.select_capabilities('Compare an inspection, not procurement.',context)==expected
 assert calls==[('Compare an inspection, not procurement.',context)]


@pytest.mark.parametrize('enforce',[True,False])
def test_confirmed_usage_honors_server_owned_token_policy(composition,enforce):
 f=composition;doc=prepare(f)
 from runtime.delegation import DECISION_SCHEMA
 class Accounted(DiagnosticAgents):
  def invoke_accounted(self,agent,inputs,invocation_id,schema=None):
   if schema is DECISION_SCHEMA:output=self.invoke_decision(agent,inputs,invocation_id,schema)
   elif schema is not None:output=self.invoke_tool_decision(agent,inputs,invocation_id,schema)
   else:output=self.invoke(agent,inputs,invocation_id)
   return output,dict(llm_calls=1,tokens=100000,estimated_cost_usd=0)
 w=approve(f,f.c.workflow(f.x.a,doc['composition_id']));rt=RuntimeService(f.general);rt.enforce_usage_budgets=enforce
 created=rt.create_run(dict(request_id='usage_check',idempotency_key='usage_check_001',payload=dict(workflow_id=w['workflow_id'],workflow_version=1,inputs={})),f.x.a)
 result=GraphRunner(rt,agents=Accounted(),connectors=f.connectors).advance(created['run_id'],f.x.a)
 assert result['status']==('failed' if enforce else 'completed')
 if not enforce:
  with rt.store.transaction(write=False) as db:persisted=rt.load(db,result['run_id'],f.x.a)
  assert persisted['usage']['workflow']['tokens']>w['execution_policy']['limits']['max_tokens']


def test_analysis_schema_allows_only_observed_record_field_pairs():
 from jsonschema import Draft202012Validator
 from runtime.capability_composition import analysis_schema
 schema=analysis_schema({'records':[{'record_id':'r1','values':{'mapping:serial':'S1'}},{'record_id':'r2','values':{'mapping:symptom':'Smoke'}}]})
 def output(rid,mid):return dict(summary='Recorded observation.',findings=[dict(kind='observation',statement='Source observation.',references=[dict(record_id=rid,mapping_id=mid)])],missing_information=[])
 assert Draft202012Validator(schema).is_valid(output('r1','mapping:serial'))
 assert not Draft202012Validator(schema).is_valid(output('r1','mapping:symptom'))
 assert not Draft202012Validator(schema).is_valid(output('invented','mapping:serial'))
 assert not Draft202012Validator(analysis_schema({})).is_valid(output('r1','mapping:serial'))
