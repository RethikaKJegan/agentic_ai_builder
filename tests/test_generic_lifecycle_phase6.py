"""Phase 6: same case engine, real storage/Registry/CrewAI, controlled transports."""
from copy import deepcopy
from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
from types import SimpleNamespace
import pytest
from tests.test_simpson_lifecycle import (composition,investigation,retrieval,knowledge,reference,generation,foundation,auth,release,
    configure,complete,approve_waiting)
from tests.test_business_cases import service,stage,process,command,ready,auth as case_auth
from workflow_api.business_cases import BusinessCases
from workflow_api.lifecycle_driver import LifecycleDriver
from workflow_api.lifecycle_reassessment import LifecycleReassessment
from workflow_api.lifecycle_learning import LifecycleLearning,VALIDATOR
from workflow_api.client_packages import PackageEvidenceConnector,package_tool_definition
from workflow_api.service import ApiFailure
from runtime.memory import WorkingMemory,knowledge_pin
from runtime.service import RuntimeFailure
from runtime import RuntimeService
from runtime.graph import GraphRunner

ROOT=Path(__file__).resolve().parents[1]


def retail(f,cases,key='retail_create_001',verified=True):
    package=json.loads((ROOT/'ontology/client-packages/retail-complaint-fixture-v1.json').read_text())
    f.registry._policy.remaining_quota['client_package_read']=100
    assert f.registry.register_tool(package_tool_definition(),f.x.a)['status']==200
    packages=f.c.packages;packages.publish(f.x.a,package)
    calls=[]
    def read(current,binding):
        assert current['subject']==f.x.a['subject'];calls.append(binding['source_id'])
        return [dict(id='fixture_order_1',complaint_id='RETAIL-C1',order_id='ORDER-1',purchase_verified=verified,product_observation='Customer reported an incorrect item; defect unconfirmed.')]
    packages.register_source(f.x.a,'retail_orders_fixture',read)
    f.connectors['client_package_read']=PackageEvidenceConnector(packages)
    case=cases.create(f.x.a,dict(request_key=key,process_definition_id='retail_complaint_fixture',process_definition_version=1,
        client_package_id=package['package_id'],client_package_revision=1,original_user_goal='Analyse retail fixture complaint RETAIL-C1 with order verification and proposed resolution.',
        inputs={'complaint_id':'RETAIL-C1','resolution':'replacement_proposal','monitoring_required':True}))
    return case,calls


def test_second_domain_actual_crewai_persistence_feedback_and_memory(composition,tmp_path):
    f=composition;cases,calls,agents=configure(f,True)
    case,reads=retail(f,cases)
    cases,case,results=complete(f,cases,case,prefix='retail_full')
    assert case['case_status']=='COMPLETED_PROVISIONALLY'
    assert len(case['completed_stage_ids'])==8 and reads and calls
    assert case['process_definition_id']=='retail_complaint_fixture'
    assert case['stages']['order']['outputs']['order_id']['value']=='ORDER-1'
    assert case['stages']['purchase']['outputs']['purchase_verified']['provenance_type']=='ACTUAL'
    assert any(w['current_status']=='PENDING' for w in case['waits'].values())
    learning=LifecycleLearning(cases).metrics(f.x.a,case['case_id'])
    assert learning['items'] and all(i['rewards']['independently_verified_business_outcome'] is None for i in learning['items'])
    assert any(i['signals']['provenance_counts']['SYNTHETIC'] for i in learning['items'])
    for item in learning['items']:VALIDATOR.validate(item)
    restarted=BusinessCases(f.general)
    assert restarted.get(f.x.a,case['case_id'])==case
    assert LifecycleLearning(restarted).metrics(f.x.a,case['case_id'])==learning
    rt=f.general.runtime_runner.runtime
    with rt.store.transaction(write=False) as db:
        entries=[json.loads(r[0]) for r in db.execute('SELECT document FROM runtime_experiences').fetchall()]
    assert entries and all(e['schema_version']=='operational-experience-v1' for e in entries)
    for e in entries:
        assert 'synthetic_assumptions' not in e and 'findings' not in e
        assert e['verified_outcome']['business_outcome_verified'] is False
    child=[c['context'] for c in agents.contexts if 'context' in c]
    assert child and all(c['business_case']['working_memory']['case_id']==case['case_id'] for c in child)
    for context in child:
        memory=context['business_case']['working_memory']
        sid=memory['stage_instance_id']
        assert set(memory['prior_conclusions'])<=set(case['stages'][sid]['definition']['dependency_definitions'])
    (tmp_path/'phase6-retail-report.json').write_text(json.dumps(case['analytical_report'],indent=2)+'\n')
    (tmp_path/'phase6-retail-feedback.json').write_text(json.dumps(learning,indent=2)+'\n')
    original=deepcopy(case);wait=next(w for w in case['waits'].values() if w['event_type']=='retail_quality_report')
    case=cases.event(f.x.a,case['case_id'],dict(request_key='retail_late_quality_001',event_id='quality_report_1',event_type=wait['event_type'],source=wait['expected_source'],
        correlation_keys=wait['correlation_keys'],payload={'observation':'Authenticated test source reports the item mismatch; physical cause remains unconfirmed.'}))
    case=LifecycleReassessment(cases).reassess(f.x.a,case['case_id'],dict(request_key='retail_reassess_001',expected_revision=case['revision'],event_id='quality_report_1',source=wait['expected_source'],input_bindings={'quality_observation':'observation'}))
    cases,case,_=complete(f,cases,case,prefix='retail_reassessed')
    assert case['stages']['monitoring']['run_id']!=original['stages']['monitoring']['run_id']
    assert case['stages']['complaint']==original['stages']['complaint']
    assert case['stages']['quality']['outputs']['quality_observation']['provenance_type']=='ACTUAL'
    assert case['reassessments'][0]['status']=='COMPLETED'
    archive=LifecycleReassessment(cases).revision(f.x.a,case['case_id'],case['reassessments'][0]['original_revision'])
    assert archive['stages']['monitoring']==original['stages']['monitoring']
    (tmp_path/'phase6-retail-reassessed-report.json').write_text(json.dumps(case['analytical_report'],indent=2)+'\n')


def test_verified_memory_ranking_scope_versions_current_permissions(composition):
    f=composition;cases,_,_=configure(f)
    case,_=retail(f,cases);cases,case,_=complete(f,cases,case,prefix='rank_case')
    rt=f.general.runtime_runner.runtime;packages=f.c.packages
    pins=packages.prepare(f.x.a,'retail_complaint_fixture',1,'fixture')['pins']
    kwargs=dict(domain='retail_food_service',pins=pins,contracts=case['capability_contracts'],tool_references=[t['definition'] for t in f.c.tools(f.x.a)])
    hints=rt.experience_memory.ranked(f.x.a,**kwargs)
    assert any(h['capability_id']=='retail.complaint.read' and h['tool_id']=='client_package_read' for h in hints)
    assert rt.experience_memory.ranked(f.x.a,**kwargs)==hints
    assert RuntimeService(f.general).experience_memory.ranked(f.x.a,**kwargs)==hints
    for key in ('workspace_id','subject_id'):
        other=deepcopy(f.x.a);other['subject'][key]='other'
        assert rt.experience_memory.ranked(other,**kwargs)==[]
    for pin in ('ontology_version','mapping_sha256','package_sha256'):
        assert rt.experience_memory.ranked(f.x.a,**{**kwargs,'pins':{**pins,pin:'changed'}})==[]
    changed=deepcopy(case['capability_contracts']);changed['retail.complaint.read']['business_purpose']='changed'
    assert not any(h['capability_id']=='retail.complaint.read' for h in rt.experience_memory.ranked(f.x.a,**{**kwargs,'contracts':changed}))
    contexts=[]
    f.general.planner.provider=SimpleNamespace(select_capabilities=lambda objective,context:(contexts.append(context) or dict(capability_requests=context['requested_operations'],unresolved_requirements=[])))
    doc=f.c.prepare(f.x.a,dict(objective='Review the retail complaint fixture.',request_key='ranked_prepare_001',client_package_id='retail_complaint_fixture',client_package_revision=1,operations=[{'capability_id':'retail.product.review','inputs':{}}]))
    assert contexts[0]['verified_experience_recommendations'] and doc['memory_recommendations']
    assert any(c['memory_recommendations'] for c in doc['configurations'])
    revoked=deepcopy(f.x.a);revoked['permissions'].remove('tools.read')
    with pytest.raises(Exception):f.c.prepare(revoked,dict(objective='Read fixture',request_key='ranked_revoked_001',client_package_id='retail_complaint_fixture',client_package_revision=1,operations=[{'capability_id':'retail.complaint.read','inputs':{}}]))


def test_retail_purchase_branch_and_package_immutability(composition):
    f=composition;cases,_,_=configure(f)
    case,_=retail(f,cases,verified=False);cases,case,_=complete(f,cases,case,prefix='unverified_purchase')
    assert case['stages']['fulfillment']['business_outcome_status']=='SKIPPED'
    p=f.c.packages.get(f.x.a,'retail_complaint_fixture',1);p.pop('sha256');p['memory_policy']['enabled']=False
    with pytest.raises(ApiFailure):f.c.packages.publish(f.x.a,p)
    p['revision']=2;p['client_id']='wrong_client'
    with pytest.raises(ApiFailure):f.c.packages.publish(f.x.a,p)


def late_case(cases,event_type='inspection_findings',authorize=False):
    first=stage('origin',required_inputs={'value':dict(schema={'type':'string'},synthetic_fallback=True,fallback_value='previous assumption')},
        external_event_requirements=[dict(event_type=event_type,expected_source='fixture.source',correlation_keys={'reference':{'source':'user','path':'reference'}},
            schema={'type':'object','required':['finding'],'properties':{'finding':{'type':'string'}}},requires_authorization=authorize,blocking=False)])
    downstream=stage('dependent',['origin'],required_inputs={'value':dict(schema={'type':'string'},binding={'source':'stage:origin','path':'value'})})
    case=ready(cases,process(first,downstream,stage('independent')))
    result=LifecycleDriver(cases).drive(case_auth(),case['case_id'],{'request_key':'initial_drive_001'})
    case=cases.get(case_auth(),case['case_id']);assert result['stop_reason']=='terminal'
    original=deepcopy(case)
    event=dict(request_key='late_event_001',event_id='event_1',event_type=event_type,source='fixture.source',correlation_keys={'reference':'C123'},payload={'finding':'actual reported evidence'})
    case=cases.event(case_auth(),case['case_id'],event)
    body=dict(request_key='reassess_once_001',expected_revision=case['revision'],event_id='event_1',source='fixture.source',input_bindings={'value':'finding'})
    return case,original,body


@pytest.mark.parametrize('event_type,authorize',[('inspection_findings',False),('commercial_authorization',True),('qa_results',False),('monitoring_observations',False)])
def test_late_evidence_reassesses_only_dependencies_preserves_history(service,event_type,authorize):
    case,original,body=late_case(service,event_type,authorize)
    reassessment=LifecycleReassessment(service);started=reassessment.reassess(case_auth(),case['case_id'],body)
    assert started['stages']['independent']==original['stages']['independent']
    item=started['reassessments'][0]
    assert item['affected_stage_ids']==['dependent','origin']
    assert item['comparisons'][0]['changed']
    archived=reassessment.revision(case_auth(),case['case_id'],item['original_revision'])
    assert archived['stages']['origin']['outputs']['value']['value']=='previous assumption'
    assert reassessment.reassess(case_auth(),case['case_id'],body)==started
    result=LifecycleDriver(service).drive(case_auth(),case['case_id'],{'request_key':'reassessed_drive_001'})
    current=service.get(case_auth(),case['case_id'])
    assert current['stages']['dependent']['outputs']['value']['value']=='actual reported evidence'
    assert current['stages']['origin']['outputs']['value']['provenance_type']=='ACTUAL'
    assert current['stages']['independent']==original['stages']['independent']
    assert current['reassessments'][0]['status']=='COMPLETED'
    assert result['report']['reassessments'][0]['original_revision']==archived['revision']
    assert service.section(case_auth(),case['case_id'],'report')['observed_revision']==current['revision']
    restarted=BusinessCases(service.service,clock=service.clock)
    assert LifecycleReassessment(restarted).history(case_auth(),case['case_id'])['items']


def test_concurrent_reassessment_revision_cas_and_idempotency(service):
    case,_,body=late_case(service);r=LifecycleReassessment(service)
    def invoke(key):
        try:return r.reassess(case_auth(),case['case_id'],{**body,'request_key':key})
        except ApiFailure as e:return e.code
    with ThreadPoolExecutor(max_workers=2) as pool:results=list(pool.map(invoke,['concurrent_reassess_1','concurrent_reassess_2']))
    assert sum(isinstance(v,dict) for v in results)==1 and 'CASE_CONFLICT' in results
    assert len(r.history(case_auth(),case['case_id'])['items'])==1


def test_reassessment_no_uncertain_write_replay_and_preserves_receipts(service):
    case,_,body=late_case(service)
    with service.store.transaction() as db:
        current=service._load(db,('one','alice'),case['case_id'])
        write=deepcopy(current['stages']['dependent']);write['stage_instance_id']='write';write['definition']['stage_instance_id']='write'
        write['definition']['side_effect_classification']='write';write['definition']['dependency_definitions']=['origin']
        write.update(execution_status='FAILED',error={'category':'uncertain_external_write'},run_id='existing_write_run',outputs={'receipt':{'value':'provider-id','provenance_type':'ACTUAL'}})
        # Test an existing uncertain runtime state, without dispatching any fixture write.
        write['outputs']=deepcopy(current['stages']['origin']['outputs'])
        current['stages']['write']=write;service._save(db,('one','alice'),current)
    current=service.get(case_auth(),case['case_id']);body['expected_revision']=current['revision']
    with pytest.raises(ApiFailure) as exc:LifecycleReassessment(service).reassess(case_auth(),case['case_id'],body)
    assert exc.value.code=='CASE_UNCERTAIN_EFFECT'
    assert service.get(case_auth(),case['case_id'])==current
    with service.store.transaction() as db:
        current=service._load(db,('one','alice'),case['case_id']);current['stages']['write'].pop('error');current['stages']['write']['execution_status']='COMPLETED'
        service._save(db,('one','alice'),current)
    body['expected_revision']=current['revision']
    saved=LifecycleReassessment(service).reassess(case_auth(),case['case_id'],body)
    assert saved['stages']['write']==current['stages']['write']
    assert saved['reassessments'][0]['preserved_write_stage_ids']==['write']


def test_synthetic_completion_is_not_a_business_reward_or_experience(service):
    s=stage(required_inputs={'value':{'schema':{'type':'string'},'synthetic_fallback':True,'fallback_value':'hypothesis'}})
    case=ready(service,process(s));LifecycleDriver(service).drive(case_auth(),case['case_id'],{'request_key':'synthetic_drive_001'})
    metrics=LifecycleLearning(service).metrics(case_auth(),case['case_id'])['items']
    assert len(metrics)==1
    assert metrics[0]['rewards']=={'execution_quality':0,'independently_verified_business_outcome':None}
    assert not metrics[0]['categories']['operational_execution']


def test_old_case_without_phase6_fields_and_feedback_replay(service):
    case=command(service,ready(service),'start');before=deepcopy(case)
    assert 'reassessments' not in case and 'memory_policy' not in case
    result=LifecycleDriver(service).drive(case_auth(),case['case_id'],{'request_key':'old_case_drive_001'})
    assert result['stop_reason']=='terminal'
    assert service.get(case_auth(),case['case_id'])['stages']==before['stages']
    metrics=LifecycleLearning(service).metrics(case_auth(),case['case_id'])
    LifecycleDriver(service).drive(case_auth(),case['case_id'],{'request_key':'old_case_drive_002'})
    assert LifecycleLearning(service).metrics(case_auth(),case['case_id'])==metrics
    assert WorkingMemory.case_view(case)['case_id']==case['case_id']


def test_missing_package_rows_never_become_verified_evidence(composition):
    f=composition;cases,_,_=configure(f);retail(f,cases)
    f.c.packages.providers[('one','alice','retail_orders_fixture')]=lambda a,b:[]
    result=f.c.packages.read(f.x.a,dict(package_id='retail_complaint_fixture',revision=1,capability_id='retail.complaint.read'))
    assert not result['coverage']['conclusion_ready'] and result['coverage']['state']=='needs_input'
    assert result['records']==[]


def test_legacy_composition_compiler_does_not_require_learning_metadata(composition):
    from tests.test_business_composition import prepare
    from workflow_api.business_composition import compile_workflow
    f=composition;doc=prepare(f)
    doc.pop('learning_features_version',None);doc.pop('memory_recommendations',None)
    for config in doc['configurations']:config.pop('memory_recommendations',None)
    compiled=compile_workflow(doc)
    assert 'composition_contracts' not in compiled['metadata']
    assert 'composition_tool_fingerprints' not in compiled['metadata']


def test_api_phase6_sections_reassessment_origin_and_tenant_boundaries(tmp_path):
    from fastapi.testclient import TestClient
    from workflow_api.main import create_app
    app=create_app(database=tmp_path/'api-phase6.sqlite',dev_auth=True,roles=['admin'],runtime_enabled=True,start_workers=False,planning_worker_enabled=False)
    client=TestClient(app);base='/business-ontology/v1'
    assert client.post(base+'/cases/unknown/reassess',json={}).status_code==401
    client.get('/session');client.cookies.set('builder_dev_session',client.cookies.get('builder_dev_session'),path='/')
    # Publish/create/drive through actual authenticated routes; no direct auth injection.
    p=process(stage());assert client.post(base+'/process-definitions',json=p).status_code==200
    response=client.post(base+'/cases',json={'request_key':'api_phase6_create','process_definition_id':'warranty','process_definition_version':1,'original_user_goal':'Analyse fixture','inputs':{'value':'actual user assertion'}})
    assert response.status_code==200,response.text
    case=response.json()['data'];cid=case['case_id']
    assert client.post(base+f'/cases/{cid}/drive',json={'request_key':'api_phase6_drive'},headers={'Origin':'https://untrusted.invalid'}).status_code==403
    assert client.post(base+f'/cases/{cid}/drive',json={'request_key':'api_phase6_drive'}).status_code==200
    for section in ('history','reassessments','memory','learning','recovery','report'):
        response=client.get(base+f'/cases/{cid}/sections/{section}')
        assert response.status_code==200,(section,response.text)
        assert response.headers['cache-control']=='no-store'
    assert client.post(base+f'/cases/{cid}/reassess',json={}).status_code==422
    assert client.get(base+f'/cases/{cid}/revisions/1').status_code==404
    isolated=create_app(database=tmp_path/'other-api-phase6.sqlite',dev_auth=True,roles=['admin'],runtime_enabled=False,start_workers=False,planning_worker_enabled=False)
    other=TestClient(isolated);other.get('/session');other.cookies.set('builder_dev_session',other.cookies.get('builder_dev_session'),path='/')
    assert other.get(base+f'/cases/{cid}/sections/learning').status_code==404
