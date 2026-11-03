"""Generation contracts and failure isolation; fixtures are not business evidence."""
from copy import deepcopy
import json
from types import SimpleNamespace
from unittest.mock import Mock
import pytest
from tests.test_business_ontology import foundation, auth, initialize
from workflow_api.business_documents import BusinessDocuments
from workflow_api.business_extraction import OpenAIExtraction, validate_result, OUTPUT_SCHEMA, generation_schema, prepare_result
from workflow_api.business_generation import BusinessGeneration
from workflow_api.service import ApiFailure


TEXT='An engine has a warranty contract. Eligibility requires an invoice date and an operating-hour observation. Missing coverage information requires review.'


class Provider:
    configured=True
    def __init__(self):self.calls=[];self.hook=None;self.modify=None
    def generate(self,payload):
        self.calls.append(payload)
        if self.hook:self.hook()
        module=payload['module_id'];source=payload['documents'][0]
        common=dict(label='Engine',definition='A physical engine mentioned by the source.',layer='domain',evidence=[dict(source_id=source['source_id'],quote='An engine has a warranty contract.')],confidence=.8,unknowns=[])
        result=dict(concepts=[dict(id=module+':engine',parent_id=None,properties=[],**common)],relationships=[],rules=[],questions=['Which policy exclusions apply?'])
        if self.modify:self.modify(result)
        return result,dict(model='fixture',input_tokens=100,output_tokens=100,prompt_version='fixture',schema_version='fixture',prompt_sha256='fixture')


@pytest.fixture
def generation(foundation):
    f,m=foundation;initialize(f)
    docs=BusinessDocuments(f)
    source=docs.add(auth(),dict(title='Process evidence',kind='process',module_ids=['warranty','engines','quality'],text=TEXT))
    provider=Provider();jobs=BusinessGeneration(f,lambda w,o:auth() if (w,o)==('one','alice') else None,provider=provider)
    return f,m,docs,source,provider,jobs


def submit(g,module='warranty',key='request_001',revision=None):
    f,_,_,_,_,jobs=g
    return jobs.submit(auth(),dict(module_id=module,expected_revision=revision or f.get(auth())['workspace']['revision'],request_key=key))


def test_valid_generation_is_immutable_and_idempotent(generation):
    f,m,docs,source,provider,jobs=generation
    old=f.get(auth())['versions'][0]['version_id']
    job=submit(generation);assert submit(generation)==job
    assert jobs.tick()
    finished=jobs.get(auth(),job['job_id']);assert finished['state']=='succeeded'
    view=f.get(auth());assert view['counts']['concepts']==1 and view['workspace']['revision']==2
    assert view['generation_status']=='draft_available' and view['definitions']['concepts'][0]['status']=='draft'
    assert view['questions']['warranty']==['Which policy exclusions apply?']
    assert f.version(auth(),old)['concepts']==[]
    assert f.version(auth(),finished['version_id'])['sources'][0]['sha256']==source['sha256']
    assert submit(generation,revision=1)==finished
    assert len(provider.calls)==1
    assert not jobs.tick()
    assert BusinessGeneration(f,jobs.authenticate,provider=provider).get(auth(),job['job_id'])==finished


@pytest.mark.parametrize('mutation',[
 lambda r:r['concepts'][0]['evidence'][0].update(quote='Invented business policy quotation'),
 lambda r:r['concepts'][0].update(parent_id='missing:parent'),
 lambda r:r['concepts'][0].update(parent_id='warranty:engine'),
 lambda r:r['concepts'][0].update(id='other:engine'),
 lambda r:r['concepts'][0].update(confidence=99),
 lambda r:r['concepts'][0].update(definition='password=private-value'),
 lambda r:r.update(concepts=[]),
])
def test_invalid_result_never_changes_current_version(generation,mutation):
    f,_,_,_,provider,jobs=generation;before=f.get(auth());provider.modify=mutation
    job=submit(generation);jobs.tick()
    result=jobs.get(auth(),job['job_id']);assert result['state']=='failed'
    assert 'private-value' not in json.dumps(result)
    assert f.get(auth())==before


def test_rules_remain_non_executable_and_unsupported_authority_is_normalized(generation):
    f,_,_,_,provider,jobs=generation
    def rule(result):
        c=result['concepts'][0]
        result['rules']=[{k:v for k,v in c.items() if k not in ('parent_id','properties')} | dict(id='warranty:review',label='Missing information',inputs=['warranty:engine'],conditions=['Coverage information is missing'],outcome='Requires review',basis='proposed_logic')]
    provider.modify=rule;job=submit(generation);jobs.tick()
    assert jobs.get(auth(),job['job_id'])['state']=='succeeded'
    assert f.get(auth())['definitions']['rules'][0]['executable'] is False
    def wrong(result):rule(result);result['rules'][0]['basis']='policy_statement'
    provider.modify=wrong;job=submit(generation,key='request_002');jobs.tick()
    assert jobs.get(auth(),job['job_id'])['state']=='succeeded'
    assert f.get(auth())['workspace']['revision']==3
    rule=f.get(auth())['definitions']['rules'][0]
    assert rule['basis']=='proposed_logic' and rule['executable'] is False
    assert jobs.get(auth(),job['job_id'])['usage']['classification_adjustments'][0]['original_basis']=='policy_statement'


def test_module_regeneration_preserves_other_modules(generation):
    f,_,_,_,_,jobs=generation
    submit(generation);jobs.tick();submit(generation,'engines','request_002');jobs.tick()
    assert f.get(auth())['counts']['concepts']==2
    submit(generation,key='request_003');jobs.tick()
    assert {c['id'] for c in f.get(auth())['definitions']['concepts']}=={'warranty:engine','engines:engine'}
    assert f.get(auth())['workspace']['revision']==4


def test_retained_dependency_cannot_be_dropped(generation):
    f,_,_,_,provider,jobs=generation
    submit(generation);jobs.tick()
    provider.modify=lambda r:r['concepts'][0].update(parent_id='warranty:engine')
    submit(generation,'engines','request_002');jobs.tick()
    provider.modify=lambda r:r['concepts'][0].update(id='warranty:new_engine')
    job=submit(generation,key='request_003');jobs.tick()
    assert jobs.get(auth(),job['job_id'])['state']=='failed'
    assert f.get(auth())['workspace']['revision']==3


@pytest.mark.parametrize('change',['source','revision','authority','cancel'])
def test_late_results_cannot_override_changed_state(generation,change):
    f,_,_,_,provider,jobs=generation
    job=submit(generation)
    def hook():
        if change=='cancel':jobs.cancel(auth(),job['job_id']);return
        if change=='authority':jobs.authenticate=lambda w,o:None;return
        with f.store.transaction() as db:
            if change=='source':
                raw=db.execute("SELECT document FROM data_source_connections WHERE connection_id='service'").fetchone()[0]
                doc=json.loads(raw);doc['generation']=2
                db.execute("UPDATE data_source_connections SET document=? WHERE connection_id='service'",(json.dumps(doc),))
            else:
                doc=f.document(db,('one','alice'));doc['revision']=8
                db.execute('UPDATE business_ontology_workspaces SET document=?',(json.dumps(doc),))
    provider.hook=hook;jobs.tick()
    assert jobs.get(auth(),job['job_id'])['state']==('cancelled' if change=='cancel' else 'failed')
    assert f.get(auth())['counts']['concepts']==0


def test_queue_scope_conflicts_and_expiry_no_replay(generation):
    f,_,_,_,provider,jobs=generation
    job=submit(generation)
    with pytest.raises(ApiFailure):submit(generation,key='request_002')
    with pytest.raises(ApiFailure):submit(generation,module='engines')
    assert jobs.list(auth(owner='bob'))['items']==[]
    with pytest.raises(ApiFailure):jobs.get(auth(owner='bob'),job['job_id'])
    with pytest.raises(ApiFailure):jobs.cancel(auth(write=False),job['job_id'])
    with f.store.transaction() as db:
        db.execute("UPDATE business_ontology_jobs SET state='running',claim='lost',deadline=0 WHERE job_id=?",(job['job_id'],))
    assert not jobs.tick()
    assert jobs.get(auth(),job['job_id'])['error']['code']=='BUSINESS_GENERATION_INTERRUPTED'
    assert not provider.calls


def test_document_scope_validation_and_reference_guard(generation):
    f,_,docs,source,_,_=generation
    assert docs.get(auth(),source['source_id'])['text']==TEXT
    with pytest.raises(ApiFailure):docs.get(auth(owner='bob'),source['source_id'])
    with pytest.raises(ApiFailure):docs.add(auth(),dict(title='unsafe',kind='process',module_ids=['warranty'],text='password=private-value here in this document'))
    with pytest.raises(ApiFailure):docs.import_reference(auth(),{})
    with pytest.raises(ApiFailure):docs.add(auth(write=False),dict(title='x',kind='process',module_ids=['warranty'],text=TEXT))


def test_metadata_context_uses_both_sources_without_values(generation):
    f,_,_,_,provider,jobs=generation
    with f.store.transaction() as db:
        for cid,name in [('service','tickets'),('quality','claimsftps')]:
            snapshot=dict(datasets=[dict(name=name,fields=[dict(name='invoiceDate',types=['date'],examples=['PRIVATE_SOURCE_VALUE']),dict(name='password',types=['string'])])])
            db.execute('INSERT INTO data_source_snapshots VALUES (?,?,?)',(cid,1,json.dumps(snapshot)))
    submit(generation);jobs.tick()
    text=json.dumps(provider.calls[0])
    assert 'tickets' in text and 'claimsftps' in text
    assert 'PRIVATE_SOURCE_VALUE' not in text and 'password' not in text


def test_provider_uses_configured_model_strict_schema_and_no_storage():
    client=Mock();client.responses.create.return_value=SimpleNamespace(status='completed',output_text='{}',usage=SimpleNamespace(input_tokens=10,output_tokens=2))
    provider=OpenAIExtraction({},client=client,model='configured-model')
    _,usage=provider.generate({'module_id':'warranty'})
    args=client.responses.create.call_args.kwargs
    assert args['model']=='configured-model' and args['store'] is False and args['max_output_tokens']==8000
    assert args['text']['format']['strict'] is True and args['text']['format']['schema']==generation_schema([])
    assert usage['input_tokens']==10
    client.responses.create.return_value.status='incomplete'
    with pytest.raises(ApiFailure):provider.generate({})
    client.responses.create.side_effect=RuntimeError('provider-secret-private')
    with pytest.raises(ApiFailure) as exc:provider.generate({})
    assert 'private' not in str(exc.value)


def test_generation_http_endpoints_keep_source_text_scoped(tmp_path):
    from fastapi.testclient import TestClient
    from workflow_api.main import create_app
    app=create_app(database=tmp_path/'http.sqlite',dev_auth=True,start_workers=False,planning_worker_enabled=False)
    app.state.business_generation.provider=Provider()
    client=TestClient(app);client.get('/session');client.cookies.set('builder_dev_session',client.cookies.get('builder_dev_session'),path='/')
    with app.state.workflow_service.store.transaction() as db:
        for cid in ('service','quality'):
            document=dict(connection_id=cid,name=cid,engine='mongodb',connection_status='connected',metadata_revision=1)
            db.execute('INSERT INTO data_source_connections VALUES (?,?,?,?,?)',(cid,'local-workspace','local-builder',None,json.dumps(document)))
    assert client.post('/business-ontology/v1/initialize',json={'sources':{'service':'service','quality':'quality'}}).status_code==200
    added=client.post('/business-ontology/v1/documents',json=dict(title='Process evidence',kind='process',module_ids=['warranty'],text=TEXT))
    assert added.status_code==200
    document_id=added.json()['data']['source_id']
    assert client.get('/business-ontology/v1/documents/'+document_id).json()['data']['text']==TEXT
    job=client.post('/business-ontology/v1/jobs',json=dict(module_id='warranty',expected_revision=1,request_key='http_request_001'))
    assert job.status_code==200 and job.json()['data']['state']=='queued'
    assert app.state.business_generation.tick()
    result=client.get('/business-ontology/v1/jobs/'+job.json()['data']['job_id'])
    assert result.json()['data']['state']=='succeeded' and result.headers['cache-control']=='no-store'
    assert client.get('/business-ontology/v1').json()['data']['counts']['concepts']==1
    app.state.workflow_auth['subject']['subject_id']='other'
    assert client.get('/business-ontology/v1/documents/'+document_id).status_code==404
    assert client.get('/business-ontology/v1/jobs/'+job.json()['data']['job_id']).status_code==404


def test_reference_bundle_is_secret_screened_and_idempotent(generation,tmp_path,monkeypatch):
    from workflow_api import business_documents as module
    from pathlib import Path
    from registry.safety import reject_secrets
    bundle=json.loads(module.REFERENCE.read_text())
    reject_secrets(bundle)
    assert {m for d in bundle['documents'] for m in d['module_ids']}==set(module.TARGETS)
    for d in bundle['documents']:
        assert module.sha256(d['text'].encode()).hexdigest()==d['sha256']
    # Fixture changes only the binding declaration so the same import path is exercised.
    bundle['required_sources']={'service':'service','quality':'quality'}
    path=tmp_path/'reference.json';path.write_text(json.dumps(bundle));monkeypatch.setattr(module,'REFERENCE',path)
    f,_,docs,_,_,_=generation
    first=docs.import_reference(auth(),{});second=docs.import_reference(auth(),{})
    assert len(first['documents'])==len(second['documents'])==25


def test_regeneration_supplies_required_target_ids_and_preserves_links(generation):
    f,_,_,_,provider,jobs=generation
    submit(generation);jobs.tick()
    provider.modify=lambda r:r['concepts'][0].update(parent_id='warranty:engine')
    submit(generation,'engines','dependency_other');jobs.tick()
    provider.modify=None
    job=submit(generation,key='dependency_regenerate');jobs.tick()
    assert jobs.get(auth(),job['job_id'])['state']=='succeeded'
    required=provider.calls[-1]['required_concepts']
    assert [c['id'] for c in required]==['warranty:engine'] and required[0]['evidence']
    assert next(c for c in f.get(auth())['definitions']['concepts'] if c['id']=='engines:engine')['parent_id']=='warranty:engine'


def test_dependency_failure_explains_reason_without_applying_output(generation):
    f,_,_,_,provider,jobs=generation
    submit(generation);jobs.tick()
    provider.modify=lambda r:r['concepts'][0].update(parent_id='warranty:engine')
    submit(generation,'engines','dependency_setup');jobs.tick();before=f.get(auth())
    provider.modify=lambda r:r['concepts'][0].update(id='warranty:new_engine')
    job=submit(generation,key='dependency_invalid');jobs.tick();result=jobs.get(auth(),job['job_id'])
    assert result['state']=='failed' and 'omitted existing concepts referenced by other modules' in result['error']['message']
    assert f.get(auth())==before


def source_rule(result,basis,source_id=None):
    c=result['concepts'][0]
    rule={k:deepcopy(v) for k,v in c.items() if k not in ('parent_id','properties')}
    rule.update(id=c['id'].split(':')[0]+':source_check',label='Source check',inputs=[c['id']],conditions=['Coverage information is missing'],outcome='Requires review',basis=basis)
    if source_id:rule['evidence']=[dict(source_id=source_id,quote='An engine has a warranty contract.')]
    result['rules']=[rule]


@pytest.mark.parametrize('basis,kind,cite_matching,expected',[
 ('policy_statement','process',True,'proposed_logic'),
 ('descriptive_implementation','process',True,'proposed_logic'),
 ('policy_statement','policy',True,'policy_statement'),
 ('descriptive_implementation','application_code',True,'descriptive_implementation'),
 ('policy_statement','policy',False,'proposed_logic'),
 ('descriptive_implementation','application_code',False,'proposed_logic'),
 ('policy_statement','application_code',True,'proposed_logic'),
 ('proposed_logic','policy',True,'proposed_logic'),
])
def test_first_attempt_classification_uses_cited_source_not_global_availability(generation,basis,kind,cite_matching,expected):
    f,_,docs,process,provider,jobs=generation
    other=docs.add(auth(),dict(title='Additional source',kind=kind,module_ids=['warranty'],text=TEXT))
    source_id=other['source_id'] if cite_matching else process['source_id']
    provider.modify=lambda r:source_rule(r,basis,source_id)
    job=submit(generation);jobs.tick();finished=jobs.get(auth(),job['job_id'])
    assert finished['state']=='succeeded' and len(provider.calls)==1
    view=f.get(auth());rule=view['definitions']['rules'][0]
    assert rule['basis']==expected and rule['executable'] is False and rule['evidence'][0]['source_id']==source_id
    adjustments=finished['usage']['classification_adjustments']
    assert len(adjustments)==(1 if basis!=expected else 0)
    version=f.version(auth(),finished['version_id']);assert version['extraction']['classification_adjustments']==adjustments
    from workflow_api.business_compiler import check_snapshot
    check_snapshot(version)


@pytest.mark.parametrize('damage',['quote','source','dependency'])
def test_normalization_never_accepts_invalid_evidence_or_missing_dependencies(generation,damage):
    f,_,_,_,provider,jobs=generation;before=f.get(auth())
    def invalid(result):
        source_rule(result,'policy_statement')
        if damage=='quote':result['rules'][0]['evidence'][0]['quote']='A quotation absent from the actual source.'
        elif damage=='source':result['rules'][0]['evidence'][0]['source_id']='unknown_source'
        else:result['rules'][0]['inputs']=['warranty:missing_concept']
    provider.modify=invalid;job=submit(generation);jobs.tick()
    assert jobs.get(auth(),job['job_id'])['state']=='failed' and len(provider.calls)==1 and f.get(auth())==before


def test_normalization_does_not_mutate_input_and_strict_validator_still_rejects_false_authority(generation):
    _,_,docs,source,provider,_=generation
    source=docs.get(auth(),source['source_id'])
    raw,_=provider.generate(dict(module_id='warranty',documents=[source]));source_rule(raw,'policy_statement');original=deepcopy(raw);retained=dict(concepts=[],relationships=[],rules=[])
    with pytest.raises(ApiFailure,match='policy or implementation'):validate_result(raw,'warranty',[source],retained)
    cleaned,adjustments=prepare_result(raw,'warranty',[source],retained)
    assert raw==original and cleaned['rules'][0]['basis']=='proposed_logic' and adjustments
    assert cleaned['rules'][0]['definition']==raw['rules'][0]['definition'] and cleaned['rules'][0]['evidence']==raw['rules'][0]['evidence']


@pytest.mark.parametrize('kinds,allowed',[
 ([],['proposed_logic']),(['blueprint','schema','process'],['proposed_logic']),
 (['policy'],['proposed_logic','policy_statement']),
 (['application_code'],['proposed_logic','descriptive_implementation']),
 (['policy','application_code'],['proposed_logic','descriptive_implementation','policy_statement']),
])
def test_provider_schema_prevents_absent_source_authority(kinds,allowed):
    client=Mock();client.responses.create.return_value=SimpleNamespace(status='completed',output_text='{}',usage=None)
    OpenAIExtraction({},client=client,model='configured-model').generate(dict(documents=[dict(kind=k) for k in kinds]))
    schema=client.responses.create.call_args.kwargs['text']['format']['schema']
    assert schema['properties']['rules']['items']['properties']['basis']['enum']==allowed
    assert len(OUTPUT_SCHEMA['properties']['rules']['items']['properties']['basis']['enum'])==3
    assert client.responses.create.call_count==1


def test_reported_engine_policy_label_saves_on_first_call(generation):
    f,_,_,_,provider,jobs=generation
    provider.modify=lambda r:source_rule(r,'policy_statement')
    job=submit(generation,module='engines');jobs.tick();finished=jobs.get(auth(),job['job_id'])
    assert finished['state']=='succeeded' and len(provider.calls)==1
    version=f.version(auth(),finished['version_id']);assert version['rules'][0]['id']=='engines:source_check'
    assert version['rules'][0]['basis']=='proposed_logic' and version['rules'][0]['executable'] is False
    assert len(version['extraction']['classification_adjustments'])==1
