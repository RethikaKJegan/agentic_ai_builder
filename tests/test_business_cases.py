"""Persistent lifecycle acceptance using real stores/runtime and deterministic transports."""
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from types import SimpleNamespace
from threading import Barrier
import json
import pytest
from workflow_api.storage import WorkflowStore
from workflow_api.business_cases import BusinessCases, TRANSITIONS
from workflow_api.evidence_completion import EvidenceCompletion, artifact
from workflow_api.service import ApiFailure
from runtime.service import RuntimeFailure
from tests.test_registry import auth as registry_auth


def auth():
    return registry_auth(workspace='one', subject='alice', permissions=['tools.read','tools.assign','workflow.view','workflow.edit','workflow.plan','workflow.execute','workflow.approve','tools.manage','events.ingest'], scopes=['workspace:read','workspace:write','tools.read'])


def binding(source='user', path='value'):
    return dict(source=source,path=path)


def stage(sid='first', dependencies=(), **changes):
    value=dict(stage_definition_id='analysis',stage_instance_id=sid,version=1,name=sid,description='Configured analytical stage',domain='manufacturing',
        required_capabilities=[],required_ontology_concepts=[],required_inputs={'value':dict(schema={'type':'string'},binding=binding())},optional_inputs={},
        output_schema={'type':'object','required':['value'],'additionalProperties':False,'properties':{'value':{'type':'string'}}},output_bindings={'value':binding('input')},
        dependency_definitions=list(dependencies),preconditions=[],allowed_tools=[],side_effect_classification='none',completion_criteria=[],transition_rules=[],
        timeout_policy=dict(seconds=60,action='block'),retry_policy=dict(max_retries=1,backoff_seconds=0),external_event_requirements=[],evidence_requirements=[],
        provisional_continuation_policy={'allowed':True})
    value.update(changes);return value


def process(*stages,version=1):
    return dict(process_definition_id='warranty',version=version,client_id='simpson',domain_id='manufacturing',stages=list(stages or [stage()]))


@pytest.fixture
def service(tmp_path):
    store=WorkflowStore(tmp_path/'cases.sqlite')
    return BusinessCases(SimpleNamespace(store=store,runtime_runner=None),clock=lambda:1793808000)


def create(service,definition=None,**kw):
    definition=definition or process();service.publish(auth(),definition)
    return service.create(auth(),dict(request_key='create_case_001',process_definition_id=definition['process_definition_id'],process_definition_version=definition['version'],original_user_goal='Resolve this business request.',inputs={'value':'source value','reference':'C123'},**kw))


def command(service,case,op,**kw):
    return service.command(auth(),case['case_id'],op,dict(request_key=f'{op}_{case["revision"]:08d}',expected_revision=case['revision'],**kw))


def ready(service,definition=None,**kw):
    return command(service,create(service,definition,**kw),'prepare')


def test_case_survives_store_and_service_restart_and_pins_versions(service):
    case=ready(service);case=command(service,case,'start')
    assert case['case_status']=='COMPLETED' and case['execution_status']=='COMPLETED'
    changed=process(stage(name='new version'),version=2);service.publish(auth(),changed)
    restarted=BusinessCases(SimpleNamespace(store=WorkflowStore(service.store.path),runtime_runner=None))
    assert restarted.get(auth(),case['case_id'])==case
    assert case['process_definition_version']==1 and case['process_definition']['stages'][0]['name']=='first'
    with pytest.raises(ApiFailure,match='immutable'):service.publish(auth(),process(stage(name='mutated')))


def test_authorized_configuration_snapshot_survives_restart_without_caller_authority(service):
    service.configuration={('one','alice'):{'business_value':'configured evidence'}}
    s=stage(required_inputs={'value':dict(schema={'type':'string'},binding=binding('config','business_value'))})
    case=ready(service,process(s))
    restarted=BusinessCases(service.service,clock=service.clock)
    case=command(restarted,case,'start')
    assert case['case_status']=='COMPLETED' and case['configuration_version']
    entry=case['stages']['first']['outputs']['value']
    assert entry['value']=='configured evidence' and entry['generation_method']=='authorized_configuration'


def test_commands_idempotent_and_revision_concurrent_conflict(service):
    case=ready(service);body=dict(request_key='start_once_001',expected_revision=case['revision'])
    result=service.command(auth(),case['case_id'],'start',body)
    service.command(auth(),case['case_id'],'start',body)
    assert service.get(auth(),case['case_id'])==result
    with pytest.raises(ApiFailure) as e:service.command(auth(),case['case_id'],'advance',body)
    assert e.value.code=='CASE_COMMAND_CONFLICT'


def test_parallel_instances_same_definition_and_binding(service):
    definition=process(stage('a'),stage('b'),stage('c',['a','b'],required_inputs={'value':dict(schema={'type':'string'},binding=binding('stage:a'))}))
    case=ready(service,definition)
    original=service.execute_stage;barrier=Barrier(2)
    def concurrent(a,c,s,t,r):
        if s in ('a','b'):barrier.wait(timeout=5)
        return original(a,c,s,t,r)
    service.execute_stage=concurrent
    case=command(service,case,'start')
    assert set(case['completed_stage_ids'])=={'a','b'} and case['stages']['c']['execution_status']=='READY'
    case=command(service,case,'advance')
    assert case['case_status']=='COMPLETED' and case['stages']['c']['outputs']['value']['value']=='source value'


def test_conditional_branch_is_data_driven(service):
    selected=stage('selected',transition_rules=[dict(source='user',path='value',operator='eq',value='source value')])
    skipped=stage('skipped',transition_rules=[dict(source='user',path='value',operator='eq',value='different')])
    case=command(service,ready(service,process(selected,skipped)),'start')
    assert case['stages']['skipped']['business_outcome_status']=='SKIPPED'
    assert case['stages']['selected']['outputs']['value']['value']=='source value'


def test_unknown_branch_condition_waits_instead_of_skipping(service):
    s=stage(transition_rules=[dict(source='user',path='decision',operator='eq',value=True)])
    case=ready(service,process(s));assert case['case_status']=='WAITING_FOR_INPUT'
    case=command(service,case,'input',inputs={'decision':True})
    case=command(service,case,'start');assert case['case_status']=='COMPLETED'


@pytest.mark.parametrize('field', ['workspace_id','subject_id'])
def test_cross_tenant_and_owner_isolation(service,field):
    case=create(service);other=auth();other['subject'][field]='outsider'
    with pytest.raises(ApiFailure) as e:service.get(other,case['case_id'])
    assert e.value.status==404
    with pytest.raises(ApiFailure):service.process(other,'warranty',1)


@pytest.mark.parametrize('permission',['workflow.execute','tools.assign'])
def test_permissions_rechecked_for_idempotent_commands(service,permission):
    case=ready(service);body=dict(request_key='start_permission',expected_revision=case['revision'])
    service.command(auth(),case['case_id'],'start',body)
    other=auth();other['permissions'].remove(permission)
    with pytest.raises((ApiFailure,RuntimeFailure)):service.command(other,case['case_id'],'start',body)


def test_missing_input_waits_and_resumes_without_manual_downstream_input(service):
    s=stage(required_inputs={'value':dict(schema={'type':'string'},binding=binding('user','missing'))})
    case=ready(service,process(s));assert case['case_status']=='WAITING_FOR_INPUT'
    case=command(service,case,'input',inputs={'missing':'supplied'})
    case=command(service,case,'advance');assert case['case_status']=='COMPLETED'


def test_schema_seeded_synthetic_policy_is_stable_and_case_local(service):
    spec=dict(schema={'type':'string','minLength':3},synthetic_fallback=True,policy=True)
    s=stage(required_inputs={'value':spec})
    case=ready(service,process(s));entry=case['assumptions']['first:value']
    assert entry['provenance_type']=='SYNTHETIC' and entry['commercial_authorization'] is False
    assert entry['validity_scope']==case['case_id'] and entry['policy_version']
    restarted=BusinessCases(service.service,clock=service.clock)
    case=command(restarted,case,'start')
    assert case['business_outcome_status']=='PROVISIONAL' and case['execution_status']=='COMPLETED'
    assert case['stages']['first']['outputs']['value']==entry


@pytest.mark.parametrize('schema',[{'type':'integer','minimum':4},{'type':'boolean'},{'type':'string','format':'date'},
    {'type':'object','required':['id'],'properties':{'id':{'type':'string'}}},{'type':'array','minItems':2,'items':{'type':'integer'}}, {'type':'string','enum':['a','b']}])
def test_schema_driven_generator(service,schema):
    s=stage(required_inputs={'value':dict(schema=schema,synthetic_fallback=True)},output_schema={'type':'object','properties':{'value':schema},'required':['value']})
    case=command(service,ready(service,process(s)),'start')
    assert case['case_status']=='COMPLETED_PROVISIONALLY'


def resolver_case(service, spec, sources=None):
    source=spec.get('binding',{}).get('source','')
    if source.startswith('stage:'):
        upstream=source[6:]
        definition=process(stage(upstream,output_schema={'type':'object'}),stage(dependencies=[upstream],required_inputs={'value':spec}))
    else:
        definition=process(stage(required_inputs={'value':spec}))
    case=create(service,definition)
    case['source_evidence']=sources or {}
    s=case['stages']['first']
    return EvidenceCompletion(case,s,service.timestamp()),case


def test_actual_evidence_wins_and_conflict_is_retained(service):
    spec=dict(schema={'type':'string'},evidence_mapping='mapped',synthetic_fallback=True)
    resolver,case=resolver_case(service,spec)
    synthetic=resolver.resolve('value',spec)
    case['source_evidence']={'complaints':{'records':[dict(record_id='real',collection='tickets',values={'mapped':{'state':'value','value':'actual'}})]}}
    chosen=resolver.resolve('value',spec)
    assert chosen['value']=='actual' and chosen['provenance_type']=='ACTUAL'
    assert case['assumptions']['first:value']==synthetic and case['conflicts']
    assert case['source_evidence']['complaints']['records'][0]['values']['mapped']['value']=='actual'


def test_conflicting_actual_and_invalid_actual_do_not_fall_back(service):
    spec=dict(schema={'type':'string'},evidence_mapping='mapped',synthetic_fallback=True)
    resolver,case=resolver_case(service,spec,{'a':{'records':[{'record_id':'1','values':{'mapped':'one'}},{'record_id':'2','values':{'mapped':'two'}}]}})
    assert resolver.resolve('value',spec) is None and case['conflicts']
    case['source_evidence']['a']['records']=[{'record_id':'1','values':{'mapped':123}}]
    assert resolver.resolve('value',spec) is None


def test_deterministic_derivation_and_grounded_inference(service):
    resolver,case=resolver_case(service,{"schema":{"type":"string"}})
    case['inputs'].update(a=4,b=7)
    derived=resolver.resolve('total',dict(schema={'type':'integer'},derivation=dict(operation='sum',inputs=[binding('user','a'),binding('user','b')])))
    assert derived['value']==11 and derived['provenance_type']=='DERIVED'
    inferred=resolver.resolve('hypothesis',dict(schema={'type':'string'},inference=dict(basis=[binding('user','a')],value='potential issue',explanation='Configured diagnostic hypothesis',confidence=.6)))
    assert inferred['provenance_type']=='INFERRED' and inferred['source_references'] and inferred['confidence']==.6
    assert resolver.resolve('missing',dict(schema={'type':'string'},inference=dict(basis=[binding('user','absent')],value='bad',explanation='No basis'))) is None


@pytest.mark.parametrize('bound_kind',['INFERRED','SYNTHETIC'])
def test_derived_evidence_outranks_lower_provenance_from_upstream_binding(service,bound_kind):
    spec=dict(schema={'type':'integer'},binding=binding('stage:upstream'),derivation=dict(operation='sum',inputs=[binding('user','a'),binding('user','b')]))
    resolver,case=resolver_case(service,spec);case['inputs'].update(a=3,b=4)
    case['stages']['upstream']={'outputs':{'value':artifact(999,bound_kind,[],'previous_hypothesis',service.timestamp(),case['case_id'])}}
    entry=resolver.resolve('value',spec)
    assert entry['value']==7 and entry['provenance_type']=='DERIVED'


def test_grounded_inference_outranks_upstream_synthetic_binding(service):
    spec=dict(schema={'type':'string'},binding=binding('stage:upstream'),inference=dict(basis=[binding('user','value')],value='grounded hypothesis',explanation='Configured evidence-grounded interpretation'))
    resolver,case=resolver_case(service,spec)
    case['stages']['upstream']={'outputs':{'value':artifact('synthetic assumption','SYNTHETIC',[],'previous_hypothesis',service.timestamp(),case['case_id'])}}
    entry=resolver.resolve('value',spec)
    assert entry['value']=='grounded hypothesis' and entry['provenance_type']=='INFERRED'


def test_protected_activities_never_generated_or_user_asserted_as_verified(service):
    spec=dict(schema={'type':'boolean'},synthetic_fallback=True,protected_activity=True,binding=binding('user','approval'))
    resolver,case=resolver_case(service,spec);case['inputs']['approval']=True
    assert resolver.resolve('approved',spec) is None
    case['inputs'].pop('approval');assert resolver.resolve('approved',spec) is None


def wait_stage(**kw):
    return stage(external_event_requirements=[dict(event_type='inspection',expected_source='field_service',correlation_keys={'ticket':binding('user','reference')},schema={'type':'object','required':['value'],'properties':{'value':{'type':'string'}}},requires_authorization=False)],
        required_inputs={'value':dict(schema={'type':'string'},binding=binding('event'),synthetic_fallback=True)},**kw)


def event_body(**kw):
    return dict(request_key='event_request_001',event_id='inspection_001',event_type='inspection',source='field_service',correlation_keys={'ticket':'C123'},payload={'value':'reported findings'},**kw)


def test_wait_correlation_duplicates_and_restart_resume(service):
    case=ready(service,process(wait_stage()));assert case['case_status']=='WAITING_FOR_EVENT'
    with pytest.raises(ApiFailure):service.event(auth(),case['case_id'],{**event_body(),'correlation_keys':{'ticket':'other'}})
    case=BusinessCases(service.service,clock=service.clock).event(auth(),case['case_id'],event_body())
    again=service.event(auth(),case['case_id'],{**event_body(),'request_key':'different_event_key'})
    assert again==case and len(case['external_events'])==1
    with pytest.raises(ApiFailure):service.event(auth(),case['case_id'],{**event_body(),'request_key':'changed_event_001','payload':{'value':'different'}})
    case=command(service,case,'advance')
    assert case['case_status']=='COMPLETED' and case['stages']['first']['real_world_status']=='REPORTED_BY_AUTHENTICATED_SOURCE'
    assert case['stages']['first']['outputs']['value']['generation_method']=='authenticated_event_assertion'
    assert case['conflicts'] # Earlier provisional assumption remains visible.


def test_timeout_analytical_continuation_keeps_physical_activity_unverified(service):
    case=ready(service,process(wait_stage(timeout_policy={'seconds':10,'action':'continue_provisionally'},provisional_continuation_policy={'allowed':True,'allow_event_timeout':True})))
    service.clock=lambda:1793808020
    case=command(service,case,'advance')
    assert case['case_status']=='COMPLETED_PROVISIONALLY'
    assert case['stages']['first']['real_world_status']=='UNVERIFIED'
    assert next(iter(case['waits'].values()))['current_status']=='TIMED_OUT'
    late=service.event(auth(),case['case_id'],event_body())
    assert late['business_outcome_status']=='PROVISIONAL' and late['conflicts'][-1]['reason']=='late_event_requires_downstream_reassessment'


def test_authorization_wait_never_synthesized(service):
    s=wait_stage(timeout_policy={'seconds':1,'action':'continue_provisionally'},provisional_continuation_policy={'allowed':True,'allow_event_timeout':True})
    s['external_event_requirements'][0]['requires_authorization']=True
    case=ready(service,process(s));assert case['case_status']=='WAITING_FOR_AUTHORIZATION'
    service.clock=lambda:1793808020
    case=command(service,case,'advance');assert case['case_status']=='BLOCKED'


def test_case_cancel_and_deadline_escalation(service):
    case=ready(service,process(wait_stage()))
    case=command(service,case,'cancel')
    assert case['case_status']=='CANCELLED' and all(w['current_status']=='CANCELLED' for w in case['waits'].values())
    with pytest.raises(ApiFailure):command(service,case,'advance')


def test_process_rejects_cycles_unknown_bindings_and_external_native_writes(service):
    for definition in [process(stage('a',['b']),stage('b',['a'])),process(stage(required_inputs={'value':{'schema':{'type':'string'},'binding':binding('stage:unknown')}})),process(stage(side_effect_classification='write'))]:
        with pytest.raises(ApiFailure):service.publish(auth(),definition)


def test_failed_stage_preserves_independent_completed_stage(service):
    bad=stage('bad',output_schema={'type':'object','required':['number'],'properties':{'number':{'type':'integer'}}})
    case=command(service,ready(service,process(stage('good'),bad)),'start')
    assert case['stages']['good']['execution_status']=='COMPLETED'
    assert case['stages']['bad']['execution_status']=='FAILED'
    assert case['stages']['bad']['errors'][0]['error_code']=='CASE_OUTPUT_INVALID'


def test_concurrent_commands_do_not_double_dispatch(service):
    case=ready(service);barrier=Barrier(2)
    def start(i):
        barrier.wait(timeout=5)
        try:return service.command(auth(),case['case_id'],'start',dict(request_key=f'parallel_command_{i}',expected_revision=case['revision']))
        except ApiFailure as exc:return exc.code
    with ThreadPoolExecutor(max_workers=2) as pool:results=list(pool.map(start,[1,2]))
    assert sum(r=='CASE_CONFLICT' for r in results if isinstance(r,str))==1
    assert service.get(auth(),case['case_id'])['stages']['first']['attempts']==1


def test_intra_stage_derivation_resolves_dependencies_independent_of_field_order(service):
    s=stage(required_inputs={
        'value':dict(schema={'type':'string'},derivation=dict(operation='concat',inputs=[binding('input','a'),binding('input','b')])),
        'b':dict(schema={'type':'string'},binding=binding('user','reference')),
        'a':dict(schema={'type':'string'},binding=binding())})
    case=command(service,ready(service,process(s)),'start')
    assert case['case_status']=='COMPLETED'
    assert case['stages']['first']['outputs']['value']['value']=='source valueC123'
    assert case['stages']['first']['outputs']['value']['provenance_type']=='DERIVED'


def test_http_routes_use_existing_auth_origin_checks_and_scoped_storage(tmp_path):
    from fastapi.testclient import TestClient
    from workflow_api.main import create_app
    app=create_app(database=tmp_path/'phase4-api.sqlite',dev_auth=True,roles=['admin'],runtime_enabled=True,start_workers=False,planning_worker_enabled=False)
    client=TestClient(app)
    base='/business-ontology/v1'
    assert client.post(base+'/cases',json={}).status_code==401
    client.get('/session');client.cookies.set('builder_dev_session',client.cookies.get('builder_dev_session'),path='/')
    assert client.post(base+'/process-definitions',json=process(),headers={'origin':'https://untrusted.example'}).status_code==403
    response=client.post(base+'/process-definitions',json=process());assert response.status_code==200,response.text
    assert client.get(base+'/process-definitions/warranty/1').status_code==200
    response=client.post(base+'/cases',json=dict(request_key='http_create_001',process_definition_id='warranty',process_definition_version=1,original_user_goal='Resolve business request',inputs={'value':'real'}))
    assert response.status_code==200,response.text
    case=response.json()['data'];cid=case['case_id']
    for op in ('prepare','start'):
        response=client.post(f'{base}/cases/{cid}/{op}',json={'request_key':f'http_{op}_001','expected_revision':case['revision']})
        assert response.status_code==200,response.text
        case=response.json()['data']
    assert case['case_status']=='COMPLETED'
    for section in ('stages','evidence','assumptions','agents','tools','waits','timeline','outcomes','conflicts'):
        response=client.get(f'{base}/cases/{cid}/sections/{section}')
        assert response.status_code==200,(section,response.text)
        assert response.headers['cache-control']=='no-store'
    assert client.get(f'{base}/cases/{cid}/sections/unknown').status_code==422
    assert client.post(f'{base}/cases/{cid}/unknown',json={'request_key':'http_bad_001','expected_revision':case['revision']}).status_code==422
    app.state.workflow_auth['subject']['subject_id']='another-owner'
    assert client.get(f'{base}/cases/{cid}').status_code==404


def test_isolated_cli_persists_across_actual_process_restarts(tmp_path):
    import subprocess
    import sys
    from pathlib import Path
    root=Path(__file__).resolve().parents[1]
    database=tmp_path/'cli.sqlite'
    count=0
    def cli(operation,payload=None,cid=None):
        nonlocal count
        args=[sys.executable,str(root/'scripts/business_cases.py'),'--database',str(database),operation]
        if cid:args+=['--case-id',cid]
        if payload is not None:
            request=tmp_path/'request.json';request.write_text(json.dumps(payload));args+=['--json',str(request)]
        result=subprocess.run(args,cwd=root,capture_output=True,text=True,timeout=45)
        assert result.returncode==0,result.stdout+result.stderr
        count+=1;return json.loads(result.stdout)
    definition=json.loads((root/'shared/contracts/examples/business-lifecycle-v1.json').read_text())
    cli('publish',definition)
    case=cli('create',dict(request_key='cli_create_001',process_definition_id=definition['process_definition_id'],process_definition_version=1,original_user_goal='Resolve field service request.',inputs={'complaint_id':'diagnostic_reference'}))
    cid=case['case_id']
    for operation in ('prepare','start'):
        case=cli(operation,dict(request_key='cli_'+operation+'_001',expected_revision=case['revision']),cid)
    assert case['case_status']=='WAITING_FOR_EVENT'
    case=cli('inspect',cid=cid)
    case=cli('event',dict(request_key='cli_event_001',event_id='diagnostic_report',event_type='inspection_report',source='field_service',correlation_keys={'complaint_id':'diagnostic_reference'},payload={'findings':'Explicit diagnostic report assertion.'}),cid)
    case=cli('advance',dict(request_key='cli_advance_001',expected_revision=case['revision']),cid)
    saved=cli('inspect',cid=cid)
    assert saved==case and case['case_status']=='COMPLETED_PROVISIONALLY'
    assert case['stages']['inspection']['real_world_status']=='REPORTED_BY_AUTHENTICATED_SOURCE'
    assert case['assumptions']['policy:policy']['provenance_type']=='SYNTHETIC' and count==8


@pytest.mark.parametrize('operation,section,path,method',[('advance','all','/cases/case_example/advance','POST'),('inspect','agents','/cases/case_example/sections/agents','GET')])
def test_cli_configured_backend_uses_existing_session_without_new_authority(tmp_path,monkeypatch,operation,section,path,method):
    import io
    from scripts.business_cases import remote
    cookie=tmp_path/'session';cookie.write_text('existing_session=diagnostic_fixture')
    calls=[]
    def opened(request,timeout):
        calls.append(request)
        return io.StringIO(json.dumps({'status':200,'data':{'case_id':'case_example'}}))
    monkeypatch.setattr('urllib.request.build_opener',lambda *_:SimpleNamespace(open=opened))
    args=SimpleNamespace(api_url='https://builder.example/api/backend',cookie_file=cookie,operation=operation,case_id='case_example',section=section)
    body={'request_key':'remote_command_001','expected_revision':7} if method=='POST' else None
    assert remote(args,body)=={'case_id':'case_example'}
    assert calls[0].full_url=='https://builder.example/api/backend/business-ontology/v1'+path
    assert calls[0].get_method()==method and calls[0].get_header('Cookie')=='existing_session=diagnostic_fixture'
    if body:assert json.loads(calls[0].data)==body
    args.api_url='http://untrusted.example'
    with pytest.raises(ValueError):remote(args,body)
