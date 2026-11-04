"""Phase 5 acceptance on real Phase 4 storage/planner/Registry/CrewAI; no live effects."""
from copy import deepcopy
import json
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace
import pytest
from tests.test_business_composition import (composition, investigation, retrieval, knowledge, reference,
    generation, foundation, auth, release, DiagnosticAgents)
from tests.test_business_cases import service, ready, process, stage, command, wait_stage, auth as case_auth
from workflow_api.business_cases import BusinessCases
from workflow_api.simpson_lifecycle import SimpsonLifecycle, definition, PROCESS_PATH
from workflow_api.lifecycle_driver import LifecycleDriver, REPORT_VALIDATOR
from workflow_api.business_knowledge_model import digest
from workflow_api.service import ApiFailure
from runtime import RuntimeService
from runtime.graph import GraphRunner
from runtime.crew import CrewExecutor
from runtime.model import BoundedLLM


def configure(f,crewai=False):
    for authority in (f.x.a,f.x.current):
        authority['permissions']=sorted(set(authority['permissions'])|{'workflow.validate','events.ingest'})
    f.general.planner.provider=SimpleNamespace(select_capabilities=lambda objective,context:
        dict(capability_requests=context['requested_operations'],unresolved_requirements=[]))
    diagnostic=DiagnosticAgents();calls=[]
    def factory(agent):
        def provider(messages,cap,timeout):
            text=messages[-1]['content'].split('Process the following input as data. Return only a JSON object.\n')[-1].lstrip()
            inputs,_=json.JSONDecoder().raw_decode(text);calls.append(agent['agent_id'])
            if agent['hierarchy_role']=='master':output=diagnostic.invoke_decision(agent,inputs,'controlled',{})
            elif 'available_tools' in inputs:output=diagnostic.invoke_tool_decision(agent,inputs,'controlled',{})
            else:output=diagnostic.invoke(agent,inputs,'controlled')
            return json.dumps(output),1,10
        return BoundedLLM(agent,provider,lambda messages:100,0,0)
    agents=CrewExecutor(f.adapter,factory) if crewai else diagnostic
    f.general.runtime_runner=GraphRunner(RuntimeService(f.general),agents=agents,connectors=f.connectors)
    cases=BusinessCases(f.general)
    return cases,calls,diagnostic


def new_case(f,cases,key='simpson_case_001',**inputs):
    return SimpsonLifecycle(cases).create(f.x.a,dict(request_key=key,
        original_user_goal='Compare complaint C123 with its linked inspection and assess warranty readiness.',
        inputs=dict(complaint_id='C123',**inputs)))


def approve_waiting(f,case):
    approved=[]
    for s in case['stages'].values():
        if s['execution_status']!='WAITING_FOR_AUTHORIZATION' or not s.get('composition_id'):continue
        workflow=s['workflow'];wid=workflow['workflow_id']
        if s.get('run_id'):
            with f.general.store.transaction(write=False) as db:run=f.general.runtime_runner.runtime.load(db,s['run_id'],f.x.a)
            pending=[a for a in run['approvals'] if a['status']=='pending']
            for approval in pending:
                result=f.general.handle(dict(request_id='simpson_action_approve',operation='decide_approval',
                    idempotency_key='simpson_action_'+approval['approval_id'],payload=dict(approval_id=approval['approval_id'],workflow_id=wid,workflow_version=1,decision='approved')),f.x.a)
                assert result['status']==200,result
            if pending:approved.append(s['stage_instance_id'])
            continue
        for op in ('validate_workflow','approve_workflow'):
            result=f.general.handle(dict(request_id='simpson_'+op,operation=op,idempotency_key='simpson_'+op+'_'+wid,
                payload=dict(workflow_id=wid,workflow_version=1)),f.x.a)
            assert result['status']==200,result
        approved.append(s['stage_instance_id'])
    return approved


def complete(f,cases,case,prefix='acceptance',hook=None):
    results=[]
    for i in range(12):
        result=LifecycleDriver(cases).drive(f.x.a,case['case_id'],dict(request_key=f'{prefix}_drive_{i:03d}',max_commands=32,max_seconds=240,max_stage_executions=64))
        results.append(result);case=cases.get(f.x.a,case['case_id'])
        assert not case['blocked_stage_ids'],[(s['stage_instance_id'],s.get('error'),s.get('missing_inputs')) for s in case['stages'].values() if s['execution_status'] in ('FAILED','BLOCKED')]
        if hook:cases=hook(i,cases,case)
        if result['stop_reason']=='terminal':return cases,cases.get(f.x.a,case['case_id']),results
        assert approve_waiting(f,case),(result['stop_reason'],[(s['stage_instance_id'],s['execution_status']) for s in case['stages'].values()])
    pytest.fail('Driver did not converge through the existing approval boundaries.')


def test_twelve_stage_end_to_end_actual_crewai_event_restart_and_report(composition,tmp_path):
    f=composition;cases,calls,diagnostic=configure(f,True);original=deepcopy(f.x.reader.rows)
    case=new_case(f,cases,resolution_path='replacement',capa_required=True,monitoring_required=True)
    assert case['process_definition_version']==1 and len(case['stages'])==12
    assert [s['name'] for s in case['process_definition']['stages']]==[
        'OEM complaint initiation','Ticket registration and validation','Warranty assessment','Investigation initiation',
        'Joint inspection scheduling','Field inspection and diagnosis','Technical disposition',
        'Commercial and authorization decision','Replacement and logistics','QA investigation',
        'Corrective engineering action','Post-change monitoring']
    state={'restarted':False,'event':False,'initial_wait':False}
    def hook(index,current,saved):
        if index==0:
            assert not calls and saved['stages']['oem_complaint']['execution_status']=='WAITING_FOR_AUTHORIZATION'
            state['initial_wait']=True
        waits=[w for w in saved['waits'].values() if w['event_type']=='inspection_schedule_confirmation']
        if waits and not state['event']:
            event=dict(request_key='simpson_schedule_event',event_id='schedule_fixture_1',event_type='inspection_schedule_confirmation',source='simpson.field_service',
                correlation_keys=waits[0]['correlation_keys'],payload={'confirmation_reference':'explicit-test-transport-report'})
            with pytest.raises(ApiFailure):current.event(f.x.a,saved['case_id'],{**event,'correlation_keys':{'complaint_id':'C999'}})
            saved=current.event(f.x.a,saved['case_id'],event)
            assert current.event(f.x.a,saved['case_id'],{**event,'request_key':'simpson_event_duplicate'})==saved
            assert saved['stages']['inspection_scheduling']['real_world_status']=='REPORTED_BY_AUTHENTICATED_SOURCE'
            state['event']=True
            # A genuinely independent Python process reads the same durable case.
            root=Path(__file__).resolve().parents[1]
            result=subprocess.run([sys.executable,str(root/'scripts/business_cases.py'),'--database',f.general.store.path,
                '--workspace','one','--owner','alice','inspect','--case-id',saved['case_id']],cwd=root,text=True,capture_output=True,timeout=45)
            assert result.returncode==0,result.stdout+result.stderr
            observed=json.loads(result.stdout)
            assert observed['process_sha256']==saved['process_sha256'] and observed['waits']==saved['waits']
            current=BusinessCases(f.general)
            f.general.runtime_runner=GraphRunner(RuntimeService(f.general),agents=f.general.runtime_runner.agents,connectors=f.connectors)
            state['restarted']=True
        return current
    cases,case,results=complete(f,cases,case,hook=hook)
    assert all(state.values()) and calls and f.x.reader.calls
    assert case['case_status']=='COMPLETED_PROVISIONALLY' and case['execution_status']=='COMPLETED'
    assert case['business_outcome_status']=='PROVISIONAL' and len(case['completed_stage_ids'])==12
    assert f.x.reader.rows==original
    report=case['analytical_report'];REPORT_VALIDATOR.validate(report)
    assert len(report['stages'])==12 and all(s['status'] in ('COMPLETED','COMPLETED_PROVISIONALLY') for s in report['stages'])
    assert [s['stage_instance_id'] for s in report['stages']]==[s['stage_instance_id'] for s in definition()['stages']]
    assert report['pending_real_world_waits'] and any(w['event_type']=='commercial_authorization' for w in report['pending_real_world_waits'])
    assert any(w['event_type']=='monitoring_observations' for w in report['pending_real_world_waits'])
    assert case['stages']['oem_complaint']['outputs']['complaint_id']['provenance_type']=='ACTUAL'
    assert case['stages']['ticket_validation']['outputs']['ticket_reference']['provenance_type']=='DERIVED'
    assert case['assumptions']['warranty_assessment:policy_assumption']['provenance_type']=='SYNTHETIC'
    assert case['assumptions']['warranty_assessment:policy_assumption']['commercial_authorization'] is False
    assert case['stages']['replacement_logistics']['real_world_status']=='UNVERIFIED'
    assert any(s['tool_execution_records'] for s in report['stages'])
    assert case['stages']['post_change_monitoring']['outputs']['effectiveness_status']['value']=='unverified'
    assert BusinessCases(f.general).get(f.x.a,case['case_id'])['analytical_report']==report
    for name,value in [('report',report),('timeline',case['execution_history']),('case',case),('driver-receipts',results)]:
        (tmp_path/f'phase5-{name}.json').write_text(json.dumps(value,indent=2)+'\n')


@pytest.mark.parametrize('path,assessment,expected_skipped',[
    ('repair_only','undetermined',{'replacement_logistics','qa_investigation','corrective_engineering','post_change_monitoring'}),
    ('replacement','rejected',{'investigation_initiation','inspection_scheduling','field_diagnosis','technical_disposition','commercial_decision','replacement_logistics','qa_investigation','corrective_engineering','post_change_monitoring'})])
def test_repair_only_and_warranty_rejected_paths(composition,path,assessment,expected_skipped,tmp_path):
    f=composition;cases,_,_=configure(f)
    case=new_case(f,cases,resolution_path=path,warranty_assessment=assessment,capa_required=False,monitoring_required=False)
    cases,case,_=complete(f,cases,case,prefix='branch_'+path)
    skipped={s['stage_instance_id'] for s in case['analytical_report']['stages'] if s['status']=='SKIPPED'}
    assert skipped==expected_skipped
    assert case['case_status']=='COMPLETED_PROVISIONALLY'
    assert all(s['real_world_status']!='CONNECTOR_CONFIRMED' for s in case['stages'].values())
    (tmp_path/'branch-report.json').write_text(json.dumps(case['analytical_report'],indent=2)+'\n')


def test_nonblocking_wait_keeps_real_activity_pending(service):
    s=wait_stage();s['external_event_requirements'][0]['blocking']=False
    case=command(service,ready(service,process(s)),'start')
    assert case['case_status']=='COMPLETED_PROVISIONALLY'
    assert next(iter(case['waits'].values()))['current_status']=='PENDING'
    assert case['stages']['first']['real_world_status']=='UNVERIFIED'


def test_nonblocking_authorization_cannot_grant_a_business_approval(service):
    s=wait_stage();s['external_event_requirements'][0].update(blocking=False,requires_authorization=True)
    s['required_inputs']={'value':dict(schema={'type':'string'},binding={'source':'event','path':'value'},protected_activity=True)}
    case=command(service,ready(service,process(s)),'start')
    assert case['case_status']=='WAITING_FOR_INPUT' and not case['stages']['first']['outputs']
    unsafe=deepcopy(s);unsafe.update(side_effect_classification='write',required_capabilities=['business.report'])
    with pytest.raises(ApiFailure):service.publish(case_auth(),process(unsafe,version=2))


def test_driver_budget_idempotency_and_stop_at_genuine_event_wait(service):
    a=case_auth()
    case=ready(service,process(wait_stage()))
    driver=LifecycleDriver(service);body={'request_key':'drive_wait_001','max_commands':4}
    result=driver.drive(a,case['case_id'],body)
    assert result['stop_reason']=='external_or_input_wait' and result['commands_used']==0
    assert driver.drive(a,case['case_id'],body)==result
    with pytest.raises(ApiFailure):driver.drive(a,case['case_id'],{**body,'max_commands':5})
    for invalid in [0,65,True]:
        with pytest.raises(ApiFailure):driver.drive(a,case['case_id'],{'request_key':'drive_bad_001','max_commands':invalid})


def test_driver_preserves_budget_across_interrupted_process(service):
    a=case_auth()
    case=ready(service);original=service.command
    def interrupted(*args,**kwargs):
        original(*args,**kwargs);raise OSError('Crash after durable case command')
    service.command=interrupted
    with pytest.raises(OSError):LifecycleDriver(service).drive(a,case['case_id'],{'request_key':'drive_crash_001','max_seconds':10})
    assert service.get(a,case['case_id'])['case_status']=='COMPLETED'
    service.command=original;service.clock=lambda:1793810000
    result=LifecycleDriver(service).drive(a,case['case_id'],{'request_key':'drive_crash_001','max_seconds':10})
    assert result['stop_reason']=='budget_exhausted'
    assert service.get(a,case['case_id'])['stages']['first']['attempts']==1


def test_driver_command_and_stage_budgets_bound_dispatch(service):
    a=case_auth()
    manifest=process(stage('a'),stage('b'))
    service.publish(a,manifest)
    case=service.create(a,dict(request_key='budget_create_001',process_definition_id='warranty',process_definition_version=1,original_user_goal='Resolve business request.',inputs={'value':'actual input'}))
    first=LifecycleDriver(service).drive(a,case['case_id'],dict(request_key='budget_prepare_001',max_commands=1))
    assert first['stop_reason']=='budget_exhausted' and first['commands_used']==1
    assert not service.get(a,case['case_id'])['completed_stage_ids']
    second=LifecycleDriver(service).drive(a,case['case_id'],dict(request_key='budget_dispatch_001',max_stage_executions=1))
    saved=service.get(a,case['case_id'])
    assert second['stop_reason']=='budget_exhausted' and sum(s['attempts'] for s in saved['stages'].values())==1
    final=LifecycleDriver(service).drive(a,case['case_id'],dict(request_key='budget_finish_001'))
    assert final['stop_reason']=='terminal'


def test_driver_never_replays_an_uncertain_external_effect(service):
    from runtime.recovery import classify
    a=case_auth();case=ready(service)
    with service.store.transaction() as db:
        current=service._load(db,('one','alice'),case['case_id']);s=current['stages']['first']
        service.transition(current,s,'RUNNING');service.transition(current,s,'FAILED')
        s['error']=classify('SMTP_DELIVERY_UNCERTAIN',external_write=True)
        service._save(db,('one','alice'),current)
    result=LifecycleDriver(service).drive(a,case['case_id'],dict(request_key='uncertain_drive_001',resume=True))
    assert result['commands_used']==1 and result['stop_reason']=='no_eligible_progress'
    assert service.get(a,case['case_id'])['stages']['first']['attempts']==0


def test_configured_blocking_simpson_event_resumes_with_same_pinned_process(composition):
    f=composition;cases,_,_=configure(f);manifest=definition();manifest['version']=2
    manifest['stages'][4]['external_event_requirements'][0]['blocking']=True
    cases.publish(f.x.a,manifest)
    case=cases.create(f.x.a,dict(request_key='blocking_simpson_001',process_definition_id=manifest['process_definition_id'],process_definition_version=2,
        original_user_goal='Compare complaint C123 with inspection and assess warranty.',inputs={'complaint_id':'C123','resolution_path':'repair_only'}))
    for index in range(5):
        result=LifecycleDriver(cases).drive(f.x.a,case['case_id'],dict(request_key=f'blocking_drive_{index:03d}'))
        case=cases.get(f.x.a,case['case_id'])
        if case['stages']['inspection_scheduling']['execution_status']=='WAITING_FOR_EVENT':break
        assert approve_waiting(f,case)
    assert result['stop_reason']=='external_or_input_wait'
    wait=next(w for w in case['waits'].values() if w['event_type']=='inspection_schedule_confirmation')
    case=cases.event(f.x.a,case['case_id'],dict(request_key='blocking_event_001',event_id='schedule_report_2',event_type=wait['event_type'],source=wait['expected_source'],correlation_keys=wait['correlation_keys'],payload={'confirmation_reference':'explicit-fixture-reference'}))
    cases=BusinessCases(f.general)
    cases,case,_=complete(f,cases,case,prefix='blocking_resumed')
    assert case['process_definition_version']==2 and case['case_status']=='COMPLETED_PROVISIONALLY'


def test_simpson_api_authentication_budgeted_drive_report_and_isolation(tmp_path):
    from fastapi.testclient import TestClient
    from workflow_api.main import create_app
    app=create_app(database=tmp_path/'simpson-api.sqlite',dev_auth=True,roles=['admin'],runtime_enabled=True,start_workers=False,planning_worker_enabled=False)
    client=TestClient(app);base='/business-ontology/v1'
    assert client.get(base+'/simpson-lifecycle/process').status_code==401
    client.get('/session');client.cookies.set('builder_dev_session',client.cookies.get('builder_dev_session'),path='/')
    response=client.get(base+'/simpson-lifecycle/process');assert response.status_code==200,response.text
    assert len(response.json()['data']['stages'])==12
    body=dict(request_key='http_simpson_001',original_user_goal='Review complaint C123.',inputs={'complaint_id':'C123'})
    assert client.post(base+'/simpson-lifecycle/cases',json=body,headers={'origin':'https://untrusted.example'}).status_code==403
    response=client.post(base+'/simpson-lifecycle/cases',json=body);assert response.status_code==200,response.text
    cid=response.json()['data']['case_id']
    response=client.post(f'{base}/cases/{cid}/drive',json={'request_key':'http_driver_001','max_commands':1})
    assert response.status_code==200,response.text
    assert response.json()['data']['stop_reason']=='budget_exhausted'
    response=client.get(f'{base}/cases/{cid}/sections/report');assert response.status_code==200,response.text
    assert len(response.json()['data']['stages'])==12
    app.state.workflow_auth['subject']['subject_id']='different-owner'
    assert client.get(f'{base}/cases/{cid}/sections/report').status_code==404


def test_simpson_manifest_pins_verified_existing_mapping_ids():
    manifest=definition();knowledge=json.loads((PROCESS_PATH.parents[1]/'business-reference/knowledge-pack.json').read_text())['knowledge']
    installed={m['id'] for m in knowledge['source_mappings']}
    used={spec['evidence_mapping'] for stage in manifest['stages'] for spec in stage['required_inputs'].values() if 'evidence_mapping' in spec}
    assert used<=installed
    assert not any(s['side_effect_classification'] in ('write','draft') for s in manifest['stages'])


@pytest.mark.parametrize('kind',['mail','calendar'])
def test_optional_coordination_uses_registered_tools_actual_resources_and_action_gates(composition,kind):
    f=composition
    if kind=='calendar':
        from tests.test_business_composition import install_external
        tool,connector=install_external(f,'extension_calendar_create')
        inputs=dict(calendar_id='explicit-test-calendar',event={'summary':'Proposed joint inspection','start':{'dateTime':'2027-01-04T10:00:00+05:30','timeZone':'Asia/Kolkata'},'end':{'dateTime':'2027-01-04T11:00:00+05:30','timeZone':'Asia/Kolkata'}})
        resources=dict(destination='extension_calendars',engineer_id='explicit-engineer')
        receipt='event_id'
    else:
        root=Path(__file__).resolve().parents[1]
        tool=json.loads((root/'shared/contracts/examples/tools/smtp-send-email.json').read_text());tool['retry_policy']={'max_retries':0,'retryable_errors':[]}
        policy=deepcopy(f.registry._policy);policy.version+=1;policy.approved_providers.add('smtp')
        policy.agent_permissions.add('communication.send');policy.allowed_destinations.add('verified_recipients');policy.remaining_quota[tool['tool_id']]=10
        policy.credential_references['cred_phase5_mail']=dict(provider_id='smtp',scopes=['communication.send','email.send'])
        for a in (f.x.a,f.x.current):
            a['permissions']=sorted(set(a['permissions'])|{'communication.send'})
            a['scopes']=sorted(set(a['scopes'])|{'communication.send','email.send'})
        assert f.registry.update_policy(policy,f.x.a)['status']==200
        assert f.registry.register_tool(tool,f.x.a,'cred_phase5_mail')['status']==200
        class Mail:
            external_write=True;retry_safe=False;timeout=1
            def __init__(self):self.calls=[]
            def reservation(self,_):return dict(tool_calls=1,tokens=0,llm_calls=0,estimated_cost_usd=0)
            def invoke(self,grant,inputs,key):self.calls.append(deepcopy(inputs));return {'message_id':'phase5-confirmed-message'}
        connector=Mail();f.connectors[tool['tool_id']]=connector
        inputs=dict(to='actual-fixture-recipient@example.test',subject='Coordinate inspection',body='Please provide an actual inspection report.')
        resources={'destination':'verified_recipients'};receipt='message_id'
    cases,_,_=configure(f);f.adapter.auto_resolve_planner=True
    case=SimpsonLifecycle(cases).create(f.x.a,dict(request_key='optional_coordination_001',original_user_goal='Compare complaint C123 with inspection and assess warranty.',
        coordination_tool_id=tool['tool_id'],inputs=dict(complaint_id='C123',resolution_path='repair_only',coordination_inputs=inputs),resources=resources))
    observed=[]
    def hook(index,current,saved):
        scheduling=saved['stages']['inspection_scheduling']
        if scheduling['execution_status']=='WAITING_FOR_AUTHORIZATION' and scheduling.get('run_id'):
            assert not connector.calls;observed.append('action_wait')
        return current
    cases,case,_=complete(f,cases,case,prefix='optional_'+kind,hook=hook)
    assert observed==['action_wait'] and connector.calls==[inputs]
    assert case['stages']['inspection_scheduling']['real_world_status']=='CONNECTOR_CONFIRMED'
    value=case['stages']['inspection_scheduling']['outputs'][receipt]
    assert value['provenance_type']=='ACTUAL' and value['generation_method']=='connector_receipt'
    wait=next(w for w in case['waits'].values() if w['event_type']=='inspection_findings')
    assert wait['correlation_keys'][receipt]==value['value'] and wait['current_status']=='PENDING'
    assert case['stages']['field_diagnosis']['real_world_status']=='UNVERIFIED'
