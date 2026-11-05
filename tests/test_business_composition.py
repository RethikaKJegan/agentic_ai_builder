"""Phase 2: actual Registry/runtime with deterministic model and connector transports."""
from copy import deepcopy
import json
from types import SimpleNamespace
import pytest
from tests.test_business_investigations import investigation
from tests.test_business_retrieval import retrieval
from tests.test_business_knowledge import knowledge
from tests.test_business_reference import reference
from tests.test_business_generation import generation
from tests.test_business_ontology import foundation,auth
from tests.test_business_environments import release
from workflow_api.business_preparation import BusinessEvidenceConnector,retrieval_tool_definition
from workflow_api.business_composition import BusinessComposition,verify_composition
from workflow_api.service import WorkflowService,ApiFailure
from workflow_api.registry_adapter import RegistryAdapter
from registry import RegistryService,WorkspacePolicy
from planner import PlannerService
from planner.provider import RuleBasedStructuredOutputProvider
from runtime import RuntimeService
from runtime.graph import GraphRunner
from runtime.crew import CrewExecutor
from runtime.model import BoundedLLM


@pytest.fixture
def composition(investigation):
 x=investigation
 for a in (x.a,x.current):
  a['roles']=['admin','approver'];a['permissions']=sorted(set(a['permissions'])|{'workflow.plan','workflow.view','workflow.edit','workflow.execute','tools.manage','tools.assign','runs.view','workflow.approve'})
  a['scopes']=sorted(set(a['scopes'])|{'tools.read'})
 policy=WorkspacePolicy('one',agent_permissions={'workflow.read_input','tools.read'},approved_providers={'builder_business'},remaining_quota={'business_retrieve_evidence':100})
 registry=RegistryService(policy);r=registry.register_tool(retrieval_tool_definition(),x.a);assert r['status']==200,r
 adapter=RegistryAdapter(registry);general=WorkflowService(x.f.store,PlannerService(RuleBasedStructuredOutputProvider()),registry_adapter=adapter)
 general.business_preparation=x.service.coverage.preparation
 connectors={'business_retrieve_evidence':BusinessEvidenceConnector(general.business_preparation)}
 c=BusinessComposition(general,general.business_preparation,connectors,model_id='offline-test-model');general.business_composition=c
 return SimpleNamespace(x=x,c=c,general=general,adapter=adapter,registry=registry,connectors=connectors)


def prepare(f,objective='Compare complaint C123 with its linked inspection.',**kw):
 return f.c.prepare(f.x.a,dict(objective=objective,request_key='compose_'+__import__('secrets').token_hex(8),planning_mode='offline',**kw))

@pytest.mark.parametrize('objective,include,exclude',[
 ('Show history for engine E123.',{'business.review_history'},{'business.assess_warranty','business.compare'}),
 ('Compare complaint C123 with its linked inspection.',{'business.compare'},{'business.assess_warranty'}),
 ('Assess warranty readiness for complaint C123.',{'business.assess_warranty'},{'business.compare'}),
 ('Review replacement evidence for complaint C123.',{'business.review_replacement'},{'business.assess_warranty'}),
])
def test_different_goals_generate_registered_temporary_configurations(composition,objective,include,exclude):
 f=composition;d=prepare(f,objective)
 assert d['state']=='ready',d['gaps']
 caps={t['capability_id'] for t in d['tasks']};assert include<=caps and not exclude&caps
 assert len(d['configurations'])==len(d['tasks'])
 for c in d['configurations']:
  assert c['definition']['agent_id'] in f.adapter.agents
  assert c['permitted_tools']==[] and c['definition']['allowed_tool_ids']==[]
 assert f.c.get(f.x.a,d['composition_id'])==d
 w=f.c.workflow(f.x.a,d['composition_id'])
 assert w['metadata']['dynamic_delegation']
 with f.x.f.store.transaction(write=False) as db:verify_composition(db,f.x.a,w)


def approve(f,w):
 review=f.adapter.review(w,f.x.a);assert review['ready'],review
 grants=f.adapter.execution_assignments(w,f.x.a)
 for agent in w['agents']:agent['allowed_tool_ids']=[g['tool_id'] for g in grants if g['agent_id']==agent['agent_id']]
 w['status']='approved';w['metadata'].update(approved_by='reviewer',validation_state='validated')
 with f.x.f.store.transaction() as db:f.x.f.store.put(db,'one',w)
 return w


class DiagnosticAgents:
 retry_safe=external_write=False
 def __init__(self):self.contexts=[]
 def reservation(self,agent):return dict(llm_calls=1,tokens=10,estimated_cost_usd=0)
 def invoke_decision(self,agent,inputs,invocation_id,schema):
  self.contexts.append(deepcopy(inputs))
  if inputs['available_agents']:
   return dict(action='delegate',reason='Execute ready registered tasks.',tasks=[dict(agent_id=a['agent_id'],inputs={'task_id':a['input_schema']['properties']['task_id']['const']},reason='Required task.') for a in inputs['available_agents']])
  return dict(action='finish',reason='Required results returned.',output=dict(summary='Prepared investigation completed.'))
 def invoke_tool_decision(self,agent,inputs,invocation_id,schema):
  if not inputs['tool_results']:
   return dict(action='tool',reason='Read exact prepared source.',tool_id=inputs['available_tools'][0]['tool_id'],inputs=inputs['request']['context']['operation_inputs'])
  return dict(action='finish',reason='Read returned.',output=dict(summary='Read source evidence.',findings=[],missing_information=[]))
 def invoke(self,agent,inputs,invocation_id):
  self.contexts.append(deepcopy(inputs))
  return dict(summary='Compared supplied evidence.',findings=[],missing_information=[])


def run(f,d,agents=None):
 w=approve(f,f.c.workflow(f.x.a,d['composition_id']));runtime=RuntimeService(f.general)
 created=runtime.create_run(dict(request_id='composition_run',operation='execute_workflow',idempotency_key='composition_run_001',payload=dict(workflow_id=w['workflow_id'],workflow_version=1,inputs={})),f.x.a)
 runner=GraphRunner(runtime,agents=agents or DiagnosticAgents(),connectors=f.connectors)
 result=runner.advance(created['run_id'],f.x.a)
 return result,runtime.events(result['run_id'],f.x.a)['items'],runtime


def test_existing_master_delegates_parallel_reads_then_comparison_and_report(composition):
 f=composition;d=prepare(f);agents=DiagnosticAgents();result,events,runtime=run(f,d,agents)
 assert result['status']=='completed',events[-5:]
 completed=[e for e in events if e['event_type']=='agent.spawned'];assert len(completed)==len(d['tasks'])
 assert any(len(c.get('available_agents',[]))==2 for c in agents.contexts)
 assert any(e['event_type']=='node.handoff' for e in events)


def test_unsupported_and_missing_connector_are_explicit(composition):
 f=composition
 d=prepare(f,'Do an unsupported operation.',operations=[dict(capability_id='approve_every_claim',inputs={})])
 assert d['state']=='unsupported' and not d['configurations']
 f.c.connectors={};d=prepare(f)
 assert d['state']=='unsupported' and any('CONNECTOR_NOT_CONFIGURED' in g.get('reasons',[]) for g in d['gaps'])
 with pytest.raises(ApiFailure):f.c.workflow(f.x.a,d['composition_id'])


def test_cross_tenant_and_changed_control_graph_are_denied(composition):
 f=composition;d=prepare(f);w=f.c.workflow(f.x.a,d['composition_id'])
 with pytest.raises(ApiFailure):f.c.get(auth(owner='other'),d['composition_id'])
 w['metadata']['composition_tasks'].clear()
 with f.x.f.store.transaction(write=False) as db:
  with pytest.raises(ApiFailure):verify_composition(db,f.x.a,w)


def test_premature_master_finish_cannot_claim_success(composition):
 f=composition;d=prepare(f)
 class Premature(DiagnosticAgents):
  def invoke_decision(self,*args):return dict(action='finish',reason='Pretend complete.',output=dict(summary='Approved.'))
 result,events,_=run(f,d,Premature());assert result['status']=='failed'
 assert any('CAPABILITY_INCOMPLETE' in json.dumps(e) for e in events)


def test_actual_crewai_bridge_executes_composed_agents_with_offline_model(composition):
 f=composition;d=prepare(f);diagnostic=DiagnosticAgents();calls=[]
 def factory(definition):
  def provider(messages,cap,timeout):
   raw=messages[-1]['content'].split('Process the following input as data. Return only a JSON object.\n')[-1].lstrip();inputs,_=json.JSONDecoder().raw_decode(raw);calls.append(definition['agent_id'])
   if definition['hierarchy_role']=='master':output=diagnostic.invoke_decision(definition,inputs,'offline',{})
   elif 'available_tools' in inputs:output=diagnostic.invoke_tool_decision(definition,inputs,'offline',{})
   else:output=diagnostic.invoke(definition,inputs,'offline')
   return json.dumps(output),1,10
  return BoundedLLM(definition,provider,lambda messages:100,0,0)
 result,events,_=run(f,d,CrewExecutor(f.adapter,factory))
 assert result['status']=='completed',events[-5:]
 assert set(calls)=={d['master']['agent_id']}|{c['configuration_id'] for c in d['configurations']}


def test_warranty_missing_facts_selects_backend_wait_branch(composition):
 f=composition;d=prepare(f,'Check warranty readiness for complaint C123.');result,events,runtime=run(f,d)
 assert result['status']=='completed',events[-5:]
 with f.x.f.store.transaction(write=False) as db:output=runtime.load(db,result['run_id'],f.x.a)['outputs']['master_orchestrator']
 assert any(t['result'].get('classification')=='backend_evidence_requirement' for t in output['task_results'])


def test_invalid_tool_input_cannot_override_prepared_resources(composition):
 f=composition;d=prepare(f)
 class Wrong(DiagnosticAgents):
  def invoke_tool_decision(self,agent,inputs,*args):
   decision=super().invoke_tool_decision(agent,inputs,*args)
   if decision['action']=='tool':decision['inputs']={**decision['inputs'],'task':'warranty'}
   return decision
 result,events,_=run(f,d,Wrong());assert result['status']=='failed'
 assert any('CAPABILITY_TOOL_SCOPE' in json.dumps(e) for e in events)


def test_model_selection_uses_existing_provider_and_rejects_unregistered_requests(composition):
 f=composition
 class Provider:
  def __init__(self):self.context=None
  def generate(self,objective,context):
   self.context=context
   w=RuleBasedStructuredOutputProvider().generate('Write a report',{})
   w['metadata']['capability_requests']=[dict(capability_id='imaginary_approval',inputs={})]
   return w
 provider=Provider();f.general.planner.provider=provider
 d=f.c.prepare(f.x.a,dict(objective='Review a new goal.',request_key='model_selection_001',planning_mode='model'))
 assert d['state']=='unsupported' and d['planning']['model_calls']==1
 assert provider.context['capability_composition_catalog']


def install_external(f,tool_id,automatic=False):
 from connector_extension.catalog import CATALOG
 tool=deepcopy(CATALOG[tool_id]);tool['availability']='enabled'
 if automatic:tool['approval_required']=False
 policy=deepcopy(f.registry._policy);policy.version+=1;policy.approved_providers.add(tool['provider_id']);policy.agent_permissions.update(tool['permission_scopes']);policy.allowed_destinations.update(tool.get('allowed_destinations',[]));policy.remaining_quota[tool_id]=20
 scope=set(tool['permission_scopes'])|set(tool['authentication']['scopes'])
 policy.credential_references['cred_test_'+tool_id]=dict(provider_id=tool['provider_id'],scopes=list(scope))
 for a in (f.x.a,f.x.current):a['permissions']=sorted(set(a['permissions'])|set(tool['permission_scopes']));a['scopes']=sorted(set(a['scopes'])|scope)
 assert f.registry.update_policy(policy,f.x.a)['status']==200
 assert f.registry.register_tool(tool,f.x.a,'cred_test_'+tool_id)['status']==200
 class Fake:
  external_write=tool['approval_required'];retry_safe=False;timeout=1
  def __init__(self):self.calls=[]
  def reservation(self,grant):return dict(tool_calls=1,tokens=0,llm_calls=0,estimated_cost_usd=0)
  def invoke(self,grant,inputs,effect_id):
   self.calls.append(deepcopy(inputs))
   if tool['capability']=='mail_draft':return dict(message_id='message-1',thread_id=None,rfc_message_id='rfc-1',draft_id='draft-1')
   if tool['capability']=='calendar_create':return dict(event_id='event-1',status='confirmed')
   return dict(events=[],next_page_token=None)
 fake=Fake();f.connectors[tool_id]=fake
 return tool,fake


def test_inspection_coordination_requires_explicit_resources_and_supported_tools(composition):
 f=composition;tool,fake=install_external(f,'extension_calendar_create')
 op=dict(capability_id='tool.extension_calendar_create',inputs={})
 d=prepare(f,'Coordinate an inspection.',operations=[op],resources={'destination':'extension_calendars'})
 assert d['state']=='needs_input' and fake.calls==[]
 assert any(g.get('reason')=='ENGINEER_REFERENCE_REQUIRED' for g in d['gaps'])
 op['inputs']=dict(calendar_id='calendar-explicit',event={'summary':'Joint inspection','start':{'dateTime':'2027-01-04T10:00:00+05:30','timeZone':'Asia/Kolkata'},'end':{'dateTime':'2027-01-04T11:00:00+05:30','timeZone':'Asia/Kolkata'}})
 d=prepare(f,'Coordinate an inspection.',operations=[op],resources=dict(destination='extension_calendars',engineer_id='explicit-engineer'))
 assert d['state']=='ready',d['gaps']
 w=f.c.workflow(f.x.a,d['composition_id']);assert w['approval_gates'] and w['execution_policy']['allow_external_writes']
 assert fake.calls==[]


def test_gmail_draft_uses_actual_receipt_only_after_existing_approval(composition):
 f=composition;tool,fake=install_external(f,'extension_mail_draft')
 inputs=dict(to='explicit@example.test',subject='Inspection coordination',body='Please review the proposed inspection slot.')
 d=prepare(f,'Prepare an inspection message draft.',operations=[dict(capability_id='tool.extension_mail_draft',inputs=inputs)],resources=dict(destination='extension_recipients'))
 assert d['state']=='ready',d['gaps']
 w=f.c.workflow(f.x.a,d['composition_id']);f.adapter.auto_resolve_planner=True
 review=f.adapter.approve_pending(w,f.x.a);assert review['ready'],review
 w=approve(f,w);runtime=RuntimeService(f.general)
 request=dict(request_id='draft_run',operation='execute_workflow',idempotency_key='draft_run_001',payload=dict(workflow_id=w['workflow_id'],workflow_version=1,inputs={}))
 created=runtime.create_run(request,f.x.a);runner=GraphRunner(runtime,agents=DiagnosticAgents(),connectors=f.connectors)
 result=runner.advance(created['run_id'],f.x.a)
 assert result['status']=='paused_for_approval',runtime.events(result['run_id'],f.x.a)
 assert fake.calls==[]
 # The existing approval gate, not an agent statement, authorizes the exact action.
 with f.x.f.store.transaction(write=False) as db:stored=runtime.load(db,created['run_id'],f.x.a)
 gate=w['approval_gates'][0]['approval_gate_id']
 response=runner.decide(dict(request_id='approve_draft',operation='decide_approval',idempotency_key='approve_draft_001',payload=dict(approval_id=stored['approvals'][-1]['approval_id'],workflow_id=w['workflow_id'],workflow_version=1,decision='approved')),f.x.a)
 result=runner.advance(created['run_id'],f.x.a)
 assert result['status']=='completed',runtime.events(result['run_id'],f.x.a)
 assert fake.calls==[inputs]


def test_current_tool_permission_denial_blocks_composition(composition):
 f=composition
 f.x.a['scopes'].remove('tools.read');f.x.current['scopes'].remove('tools.read')
 d=prepare(f)
 assert d['state']=='unsupported' and not d['configurations']



def test_model_cannot_invent_a_calendar_or_recipient(composition):
 f=composition;_,fake=install_external(f,'extension_mail_draft')
 class Provider:
  def generate(self,objective,context):
   w=RuleBasedStructuredOutputProvider().generate('Write a report',{})
   w['metadata']['unresolved_requirements']=[]
   w['metadata']['capability_requests']=[dict(capability_id='tool.extension_mail_draft',inputs=dict(to='invented@example.test',subject='Invented',body='Unsupported content'))]
   return w
 f.general.planner.provider=Provider()
 d=f.c.prepare(f.x.a,dict(objective='Prepare a coordination draft.',request_key='invented_recipient_001',planning_mode='model',resources={'destination':'extension_recipients'}))
 assert d['state']=='needs_input' and fake.calls==[]
 assert next(t for t in d['tasks'] if t['side_effect']=='draft')['operation_inputs']=={}


def test_agent_configuration_respects_reviewed_budget(composition):
 f=composition;policy=deepcopy(f.registry._policy);policy.version+=1;policy.agent_limits['max_llm_calls']=1
 assert f.registry.update_policy(policy,f.x.a)['status']==200
 with pytest.raises(ApiFailure) as exc:prepare(f)
 assert exc.value.code=='CAPABILITY_AGENT_LIMIT'


def test_arbitrary_agent_claims_need_actual_supplied_citations(composition):
 f=composition;d=prepare(f)
 class Wrong(DiagnosticAgents):
  def invoke(self,*args):return dict(summary='Unsupported.',findings=[dict(kind='observation',statement='Confirmed approval.',references=[dict(record_id='invented',mapping_id='invented')])],missing_information=[])
 result,events,_=run(f,d,Wrong());assert result['status']=='failed'
 assert any('INVESTIGATION_AGENT_REFERENCE' in json.dumps(e) for e in events)


def test_general_planning_entry_uses_composition_and_refuses_control_removal(composition):
 f=composition;d=prepare(f)
 request=dict(request_id='cap_plan',operation='plan_workflow',idempotency_key='cap_plan_key_001',payload=dict(objective=d['objective'],context={'composition_id':d['composition_id']}))
 response=f.general.handle(request,f.x.a);assert response['status']==200,response
 w=response['data']['workflow'];assert w['metadata']['composition_id']==d['composition_id']
 w['metadata'].pop('composition_id')
 with f.x.f.store.transaction(write=False) as db:
  with pytest.raises(ApiFailure):verify_composition(db,f.x.a,w)


def test_task_context_is_scoped_and_immutable_request_is_idempotent(composition):
 f=composition;body=dict(objective='Show history for engine E123.',request_key='composition_idempotency',planning_mode='offline')
 d=f.c.prepare(f.x.a,body);count=len(f.registry._agents)
 assert f.c.prepare(f.x.a,body)==d and len(f.registry._agents)==count
 with pytest.raises(ApiFailure):f.c.prepare(f.x.a,{**body,'objective':'Compare complaint C123.'})
 agents=DiagnosticAgents();result,events,_=run(f,d,agents)
 assert result['status']=='completed',events[-5:]
 contexts=[c['context'] for c in agents.contexts if 'context' in c]
 assert contexts and all(not {'warranty','inspection'}&set(c.get('ontology_context',{})) for c in contexts)


def test_invalid_child_schema_never_becomes_a_verified_result(composition):
 f=composition;d=prepare(f)
 class Wrong(DiagnosticAgents):
  def invoke(self,*args):return dict(summary='Malformed result',findings='not-an-array',missing_information=[])
 result,events,_=run(f,d,Wrong());assert result['status']=='failed'
 assert any(any(code in json.dumps(e) for code in ('CAPABILITY_RESULT_INVALID','AGENT_OUTPUT_INVALID')) for e in events)


def test_repeated_generation_does_not_invalidate_registered_agents_or_grants(composition):
 f=composition;d=prepare(f);w=f.c.workflow(f.x.a,d['composition_id']);versions={a:r['version'] for a,r in f.adapter.agents.items()};bindings=len(f.adapter.bindings)
 f.c.workflow(f.x.a,d['composition_id'])
 assert {a:r['version'] for a,r in f.adapter.agents.items()}==versions
 assert len(f.adapter.bindings)==bindings
 assert any(c['evidence_references'] for c in d['configurations'])


def test_action_verification_rejects_failure_and_wrong_resource():
 from runtime.capability_composition import verify_action
 from runtime.service import RuntimeFailure
 for method,result,inputs in [('draft_id',{'draft_id':''},{}),('event_id',{'event_id':'different','status':'confirmed'},{'event_id':'requested'}),('cancelled_event',{'event_id':'requested','status':'confirmed'},{})]:
  with pytest.raises(RuntimeFailure):verify_action(method,result,inputs)


def test_missing_case_anchor_waits_before_any_source_tool_runs(composition):
 f=composition;before=len(f.x.reader.calls);d=prepare(f,'Compare complaint with its inspection.')
 assert d['state']=='needs_input' and d['configurations']==[]
 assert any(g.get('reason')=='CASE_IDENTIFIER_REQUIRED' for g in d['gaps'])
 assert len(f.x.reader.calls)==before
 with pytest.raises(ApiFailure):f.c.workflow(f.x.a,d['composition_id'])


@pytest.mark.parametrize('variant',['complete','rejected_authorization','conflicting_identity'])
def test_scenario_decisions_preserve_negative_outcomes_and_conflict_branches(composition,variant):
 f=composition;environment=release(f.x,(variant,));objective='Review replacement evidence for complaint C123.'
 p=f.c.preparation.prepare(f.x.a,dict(objective=objective,evidence_context=dict(dataset_id=environment['dataset_id'],case_id=environment['cases'][0]['case_id'])))
 d=prepare(f,objective,preparation_id=p['preflight_id']);assert d['state']=='ready',d['gaps']
 result,events,runtime=run(f,d);assert result['status']=='completed',events[-5:]
 with f.x.f.store.transaction(write=False) as db:output=runtime.load(db,result['run_id'],f.x.a)['outputs']['master_orchestrator']
 results=[r['result'] for r in output['task_results']]
 if variant=='conflicting_identity':assert any(r.get('state')=='conflicting_evidence' for r in results)
 if variant=='rejected_authorization':assert any(r.get('coverage',{}).get('business_outcomes',{}).get('authorization_outcome')=='rejected' for r in results)
 assert all(r.get('coverage',{}).get('official_approval') is not True for r in results)
