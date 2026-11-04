"""Phase 4 integration through the existing real composition, Registry and graph runner."""
from copy import deepcopy
from types import SimpleNamespace
import json
import pytest
from tests.test_business_composition import (composition, investigation, retrieval, knowledge, reference,
    generation, foundation, auth, release, approve, DiagnosticAgents)
from tests.test_business_cases import stage, process
from workflow_api.business_cases import BusinessCases
from workflow_api.service import ApiFailure
from runtime import RuntimeService
from runtime.graph import GraphRunner


def setup(f,stages=None,case_inputs=None,resources=None):
    f.general.planner.provider=SimpleNamespace(select_capabilities=lambda objective,context:dict(capability_requests=context['requested_operations'],unresolved_requirements=[]))
    f.agents=DiagnosticAgents()
    f.general.runtime_runner=GraphRunner(RuntimeService(f.general),agents=f.agents,connectors=f.connectors)
    service=BusinessCases(f.general)
    definition=process(*(stages or [stage(required_inputs={},required_capabilities=['business.compare'],allowed_tools=['business_retrieve_evidence'],side_effect_classification='read',
        output_schema={'type':'object','required':['summary'],'properties':{'summary':{'type':'string'}}},
        output_bindings={'summary':{'source':'runtime','path':'master_orchestrator.summary'}})]))
    service.publish(f.x.a,definition)
    case=service.create(f.x.a,dict(request_key='runtime_case_001',process_definition_id='warranty',process_definition_version=1,original_user_goal='Compare complaint C123 with its linked inspection.',inputs=case_inputs or {},resources=resources or {}))
    return service,step(service,f.x.a,case,'prepare')


def step(service,auth,case,op):
    return service.command(auth,case['case_id'],op,dict(request_key=f'{op}_{case["revision"]:08d}',expected_revision=case['revision']))


def test_actual_mapped_preparation_and_existing_master_child_execution(composition):
    f=composition;service,case=setup(f)
    assert case['ontology_version'] and case['mapping_version'] and case['capability_registry_version']
    assert case['source_evidence'] and f.x.reader.calls
    original_sources=deepcopy(f.x.reader.rows)
    case=step(service,f.x.a,case,'start');s=case['stages']['first']
    assert s['execution_status']=='WAITING_FOR_AUTHORIZATION',s
    assert s['run_id'] is None and s['agent_configurations']
    w=approve(f,f.c.workflow(f.x.a,s['composition_id']))
    case=step(service,f.x.a,case,'advance');s=case['stages']['first']
    assert case['case_status']=='COMPLETED_PROVISIONALLY',s
    assert s['runtime_checkpoints'] and s['tool_execution_records']
    assert any(ref.get('run_id')==s['run_id'] for ref in case['evidence_references'])
    assert s['outputs']['summary']['provenance_type']=='INFERRED'
    assert f.x.reader.rows==original_sources
    assert any(c.get('context',{}).get('business_case',{}).get('case_id')==case['case_id'] for c in f.agents.contexts)
    with f.general.store.transaction(write=False) as db:
        assert len(db.execute('SELECT run_id FROM runtime_runs').fetchall())==1
    # Pinned assumptions cannot be changed by editing workflow metadata.
    from workflow_api.business_composition import verify_composition
    changed=deepcopy(w);changed['metadata']['lifecycle_context']['case_id']='forged'
    with f.general.store.transaction(write=False) as db:
        with pytest.raises(ApiFailure):verify_composition(db,f.x.a,changed)


def test_actual_source_binding_without_agent_is_not_synthetic(composition):
    f=composition;s=stage(required_inputs={'value':dict(schema={'type':'string'},evidence_mapping='mapping:ticket_id',synthetic_fallback=True)})
    service,case=setup(f,[s]);case=step(service,f.x.a,case,'start')
    assert case['case_status']=='COMPLETED'
    entry=case['stages']['first']['outputs']['value']
    assert entry['value']=='C123' and entry['provenance_type']=='ACTUAL' and entry['source_references'][0]['record_id']


def test_two_instances_of_same_capability_are_distinct_runtime_runs(composition):
    f=composition
    s=stage(required_inputs={},required_capabilities=['business.compare'],allowed_tools=['business_retrieve_evidence'],side_effect_classification='read',output_schema={'type':'object'},output_bindings={})
    service,case=setup(f,[{**s,'stage_instance_id':'one'},{**s,'stage_instance_id':'two'}])
    case=step(service,f.x.a,case,'start')
    assert all(s['execution_status']=='WAITING_FOR_AUTHORIZATION' for s in case['stages'].values()),case['stages']
    for s in case['stages'].values():approve(f,f.c.workflow(f.x.a,s['composition_id']))
    case=step(service,f.x.a,case,'advance')
    assert all(s['execution_status'] in ('COMPLETED','COMPLETED_PROVISIONALLY') for s in case['stages'].values()),case['stages']
    assert len({s['run_id'] for s in case['stages'].values()})==2
    assert len({s['composition_id'] for s in case['stages'].values()})==2


def test_stage_tool_allowlist_denial_does_not_execute(composition):
    f=composition;s=stage(required_inputs={},required_capabilities=['business.compare'],allowed_tools=[],side_effect_classification='read')
    service,case=setup(f,[s]);case=step(service,f.x.a,case,'start')
    assert case['stages']['first']['error']['error_code']=='CASE_TOOL_DENIED'
    assert not f.agents.contexts
    with f.general.store.transaction(write=False) as db:assert not db.execute('SELECT run_id FROM runtime_runs').fetchall()


def test_process_prepares_all_future_capability_dependencies_before_pinning(composition):
    f=composition
    base=stage(required_inputs={},required_capabilities=['business.read.complaints'],allowed_tools=['business_retrieve_evidence'],side_effect_classification='read',output_schema={'type':'object'},output_bindings={})
    later={**base,'stage_instance_id':'warranty','dependency_definitions':['first'],'required_capabilities':['business.assess_warranty']}
    service,case=setup(f,[base,later])
    prepared=f.general.business_preparation.checked(f.x.a,case['preparation_id'])
    assert 'warranty' in prepared['tasks']
    assert case['capability_contracts']['business.read.warranty']['required_ontology']
    case=step(service,f.x.a,case,'start');s=case['stages']['first']
    assert s['execution_status']=='WAITING_FOR_AUTHORIZATION',s


def test_existing_run_reconciled_after_case_checkpoint_interruption(composition):
    f=composition;service,case=setup(f)
    case=step(service,f.x.a,case,'start');s=case['stages']['first'];approve(f,f.c.workflow(f.x.a,s['composition_id']))
    original=service.finish
    def crash(*args,**kw):raise OSError('Simulated process interruption after run completion')
    service.finish=crash
    with pytest.raises(OSError):step(service,f.x.a,case,'advance')
    case=service.get(f.x.a,case['case_id']);assert case['stages']['first']['run_id']
    calls=len(f.x.reader.calls);rt=f.general.runtime_runner.runtime
    restarted=BusinessCases(f.general,clock=lambda:service.clock()+100)
    restarted.clock=lambda:service.clock()+1000
    case=step(restarted,f.x.a,case,'resume')
    assert case['case_status']=='COMPLETED_PROVISIONALLY' and len(f.x.reader.calls)==calls
    with f.general.store.transaction(write=False) as db:assert len(db.execute('SELECT run_id FROM runtime_runs').fetchall())==1


def test_cancel_paused_case_cancels_existing_runtime(composition):
    f=composition;service,case=setup(f)
    case=step(service,f.x.a,case,'start');s=case['stages']['first'];approve(f,f.c.workflow(f.x.a,s['composition_id']))
    original=service.finish
    service.finish=lambda *args,**kw:(_ for _ in ()).throw(OSError('interrupt'))
    with pytest.raises(OSError):step(service,f.x.a,case,'advance')
    service.finish=original;case=service.get(f.x.a,case['case_id'])
    case=step(service,f.x.a,case,'cancel')
    assert case['case_status']=='CANCELLED'
    assert service.get(f.x.a,case['case_id'])['case_status']=='CANCELLED'


def test_uncertain_effect_is_never_replayed_by_case_resume(composition):
    f=composition;service,case=setup(f)
    case=step(service,f.x.a,case,'start');s=case['stages']['first'];approve(f,f.c.workflow(f.x.a,s['composition_id']))
    rt=f.general.runtime_runner.runtime;calls=[]
    def uncertain(rid,auth):
        calls.append(rid)
        with rt.store.transaction() as db:
            run=rt.load(db,rid,auth);run['error_code']='SMTP_DELIVERY_UNCERTAIN';rt.transition(db,run,'failed')
        return rt.public(run)
    f.general.runtime_runner.advance=uncertain
    case=step(service,f.x.a,case,'advance')
    assert case['stages']['first']['error']['category']=='uncertain_external_write'
    case=step(service,f.x.a,case,'resume')
    assert len(calls)==1 and case['stages']['first']['execution_status']=='FAILED'


def test_cancel_racing_run_creation_cannot_leave_an_orphan_run(composition):
    f=composition;service,case=setup(f)
    case=step(service,f.x.a,case,'start');s=case['stages']['first'];approve(f,f.c.workflow(f.x.a,s['composition_id']))
    rt=f.general.runtime_runner.runtime;original=rt.create_run
    def cancel_before_create(request,auth,**kwargs):
        current=service.get(auth,case['case_id']);step(service,auth,current,'cancel')
        return original(request,auth,**kwargs)
    rt.create_run=cancel_before_create
    case=step(service,f.x.a,case,'advance')
    assert case['case_status']=='CANCELLED'
    with rt.store.transaction(write=False) as db:
        assert not db.execute('SELECT run_id FROM runtime_runs').fetchall()
        assert not db.execute('SELECT document FROM runtime_events').fetchall()


def test_case_recovery_reuses_existing_runtime_checkpoints(composition):
    from tests.test_agent_memory_recovery import InterruptRead
    f=composition
    connector=InterruptRead(f.connectors['business_retrieve_evidence']);f.connectors['business_retrieve_evidence']=connector
    service,case=setup(f)
    case=step(service,f.x.a,case,'start');s=case['stages']['first'];approve(f,f.c.workflow(f.x.a,s['composition_id']))
    case=step(service,f.x.a,case,'advance');s=case['stages']['first']
    assert s['execution_status']=='FAILED' and s['error']['retry_eligible']
    rt=f.general.runtime_runner.runtime
    with rt.store.transaction() as db:
        run=rt.load(db,s['run_id'],f.x.a);run['lease_until']=0;rt.save(db,run)
    case=step(service,f.x.a,case,'resume')
    assert case['case_status']=='COMPLETED_PROVISIONALLY',case['stages']['first']
    assert case['stages']['first']['run_id']==s['run_id']
    assert connector.state['calls'].count('complaints')==1 and connector.state['calls'].count('inspection')==2
    assert len(case['stages']['first']['retry_history'])==1


def test_second_client_case_uses_actual_crewai_and_same_registry_runtime(composition):
    from tests.test_agent_memory_recovery import setup_retail
    from runtime.crew import CrewExecutor
    from runtime.model import BoundedLLM
    f=composition;setup_retail(f);diagnostic=DiagnosticAgents();calls=[]
    def factory(definition):
        def provider(messages,cap,timeout):
            raw=messages[-1]['content'].split('Process the following input as data. Return only a JSON object.\n')[-1].lstrip()
            inputs,_=json.JSONDecoder().raw_decode(raw);calls.append(definition['agent_id'])
            if definition['hierarchy_role']=='master':out=diagnostic.invoke_decision(definition,inputs,'fixture',{})
            elif 'available_tools' in inputs:out=diagnostic.invoke_tool_decision(definition,inputs,'fixture',{})
            else:out=diagnostic.invoke(definition,inputs,'fixture')
            return json.dumps(out),1,10
        return BoundedLLM(definition,provider,lambda messages:100,0,0)
    f.general.planner.provider=SimpleNamespace(select_capabilities=lambda objective,context:dict(capability_requests=context['requested_operations'],unresolved_requirements=[]))
    f.general.runtime_runner=GraphRunner(RuntimeService(f.general),agents=CrewExecutor(f.adapter,factory),connectors=f.connectors)
    service=BusinessCases(f.general)
    definition=process(stage(domain='retail',required_inputs={},required_capabilities=['retail.review'],allowed_tools=['client_package_read'],side_effect_classification='read',
        output_schema={'type':'object','required':['summary'],'properties':{'summary':{'type':'string'}}},output_bindings={'summary':{'source':'runtime','path':'master_orchestrator.summary'}}))
    definition.update(client_id='isolated-retailer',domain_id='retail')
    service.publish(f.x.a,definition)
    case=service.create(f.x.a,dict(request_key='retail_case_001',process_definition_id='warranty',process_definition_version=1,original_user_goal='Review inventory and replenishment thresholds.',client_package_id='retail_fixture',client_package_revision=1))
    case=step(service,f.x.a,case,'prepare')
    assert case['ontology_version']=='retail_v1' and case['source_evidence']['retail.read']['records'][0]['values']['mapping:stock']==3
    case=step(service,f.x.a,case,'start');s=case['stages']['first']
    assert s['execution_status']=='WAITING_FOR_AUTHORIZATION',s
    approve(f,f.c.workflow(f.x.a,s['composition_id']))
    case=step(service,f.x.a,case,'advance')
    assert case['case_status']=='COMPLETED_PROVISIONALLY',case['stages']['first']
    assert calls and case['stages']['first']['tool_execution_records']
    assert case['client_id']=='isolated-retailer'


def test_email_receipt_binds_reply_wait_only_after_existing_action_approval(composition):
    from pathlib import Path
    f=composition
    tool=json.loads((Path(__file__).resolve().parents[1]/'shared/contracts/examples/tools/smtp-send-email.json').read_text())
    tool['retry_policy']={'max_retries':0,'retryable_errors':[]}
    policy=deepcopy(f.registry._policy);policy.version+=1;policy.approved_providers.add('smtp')
    policy.agent_permissions.add('communication.send');policy.allowed_destinations.add('verified_recipients');policy.remaining_quota['smtp_send_email']=10
    policy.credential_references['cred_case_mail']=dict(provider_id='smtp',scopes=['communication.send','email.send'])
    for a in (f.x.a,f.x.current):
        a['permissions']=sorted(set(a['permissions'])|{'communication.send','events.ingest'})
        a['scopes']=sorted(set(a['scopes'])|{'communication.send','email.send'})
    assert f.registry.update_policy(policy,f.x.a)['status']==200
    assert f.registry.register_tool(tool,f.x.a,'cred_case_mail')['status']==200
    class Mail:
        external_write=True;retry_safe=False;timeout=1
        def __init__(self):self.calls=[]
        def reservation(self,grant):return dict(tool_calls=1,tokens=0,llm_calls=0,estimated_cost_usd=0)
        def invoke(self,grant,inputs,effect_id):
            self.calls.append(deepcopy(inputs));return {'message_id':'confirmed_message_1'}
    mail=Mail();f.connectors['smtp_send_email']=mail
    inputs=dict(to='explicit@example.test',subject='Inspection coordination',body='Please provide the actual inspection findings.')
    send=stage(required_inputs={name:dict(schema={'type':'string'},binding={'source':'user','path':name}) for name in inputs},required_capabilities=['tool.smtp_send_email'],allowed_tools=['smtp_send_email'],side_effect_classification='write',
        output_schema={'type':'object','required':['message_id'],'properties':{'message_id':{'type':'string'}}},output_bindings={'message_id':{'source':'receipt','path':'action_task_1.message_id'}})
    reply=stage('reply',['first'],required_inputs={'value':dict(schema={'type':'string'},binding={'source':'event','path':'reply'})},
        external_event_requirements=[dict(event_type='email_reply',expected_source='mail_gateway',correlation_keys={'message_id':{'source':'stage:first','path':'message_id'}},schema={'type':'object','required':['reply'],'properties':{'reply':{'type':'string'}}},requires_authorization=False)])
    service,case=setup(f,[send,reply],inputs,{'destination':'verified_recipients'})
    case=step(service,f.x.a,case,'start');s=case['stages']['first']
    assert s['execution_status']=='WAITING_FOR_AUTHORIZATION' and not mail.calls,s.get('capability_gaps',s)
    w=f.c.workflow(f.x.a,s['composition_id']);f.adapter.auto_resolve_planner=True
    assert f.adapter.approve_pending(w,f.x.a)['ready']
    approve(f,w)
    case=step(service,f.x.a,case,'advance');s=case['stages']['first']
    assert s['execution_status']=='WAITING_FOR_AUTHORIZATION' and not mail.calls,s
    runner=f.general.runtime_runner;rt=runner.runtime
    with rt.store.transaction(write=False) as db:saved=rt.load(db,s['run_id'],f.x.a)
    runner.decide(dict(request_id='case_mail_approve',operation='decide_approval',idempotency_key='case_mail_approve_001',payload=dict(approval_id=saved['approvals'][-1]['approval_id'],workflow_id=w['workflow_id'],workflow_version=1,decision='approved')),f.x.a)
    case=step(service,f.x.a,case,'advance')
    assert mail.calls==[inputs] and case['stages']['first']['real_world_status']=='CONNECTOR_CONFIRMED'
    receipt=case['stages']['first']['outputs']['message_id']
    assert receipt['provenance_type']=='ACTUAL' and receipt['value']=='confirmed_message_1'
    assert case['stages']['reply']['execution_status']=='WAITING_FOR_EVENT'
    case=service.event(f.x.a,case['case_id'],dict(request_key='reply_event_001',event_id='reply_1',event_type='email_reply',source='mail_gateway',correlation_keys={'message_id':'confirmed_message_1'},payload={'reply':'An actual report assertion from the deterministic fixture.'}))
    case=step(service,f.x.a,case,'advance');assert case['case_status']=='COMPLETED'


@pytest.mark.parametrize('receipt',[{}, {'message_id':''}])
def test_email_completion_requires_a_nonempty_connector_receipt(receipt):
    from runtime.capability_composition import verify_action
    from runtime.service import RuntimeFailure
    with pytest.raises(RuntimeFailure):verify_action('message_id',receipt)
