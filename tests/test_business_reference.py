"""Grounded twelve-module reference drafts preserve prior work and scopes."""
from copy import deepcopy
import json
import pytest
from tests.test_business_generation import generation,submit
from tests.test_business_ontology import foundation,auth
from workflow_api.business_reference import BusinessReference,load_kit,additions
from workflow_api.business_compiler import compile_snapshot
from workflow_api.service import ApiFailure

@pytest.fixture
def reference(generation,monkeypatch):
    f,_,_,_,_,jobs=generation
    kit,bundle=load_kit();bundle=deepcopy(bundle);bundle['required_sources']={'service':'service','quality':'quality'}
    monkeypatch.setattr('workflow_api.business_reference.load_kit',lambda:(deepcopy(kit),deepcopy(bundle)))
    current=auth();service=BusinessReference(f,lambda *args:current)
    return f,jobs,service,current


def test_all_twelve_reference_modules_are_cited_and_compile(reference):
    f,jobs,service,_=reference;before=f.get(auth());old=before['current_version_id']
    coverage=service.coverage(auth(),old);assert len(coverage['modules'])==12 and len(coverage['missing_modules'])==12
    result=service.apply(auth(),dict(expected_revision=1,request_key='reference_001'))
    snapshot=f.version(auth(),result['version_id'])
    assert {c['module_id'] for c in snapshot['concepts']}=={m['module_id'] for m in coverage['modules']}
    assert len(snapshot['concepts'])==67 and all(c['parent_id'] is None for c in snapshot['concepts'])
    assert snapshot['reference_import']['source_basis']=='curated_supplied_blueprint_drafts'
    assert all(r['executable'] is False for r in snapshot['rules'])
    assert compile_snapshot(snapshot)[0]['status']=='passed'
    assert f.version(auth(),old)['concepts']==[]
    assert not service.coverage(auth(),result['version_id'])['missing_modules']


def test_import_preserves_existing_module_and_is_idempotent(reference,generation):
    f,jobs,service,_=reference;submit(generation);jobs.tick()
    prior=f.version(auth(),f.get(auth())['current_version_id'])
    body=dict(expected_revision=2,request_key='reference_002');result=service.apply(auth(),body)
    current=f.version(auth(),result['version_id'])
    assert [c for c in current['concepts'] if c['module_id']=='warranty']==prior['concepts']
    assert 'warranty' not in current['reference_import']['added_modules']
    assert f.version(auth(),prior['version_id'])==prior
    assert service.apply(auth(),body)==result
    with pytest.raises(ApiFailure):service.apply(auth(),{**body,'expected_revision':3})
    assert compile_snapshot(current)[0]['status']=='passed'


def test_reference_scope_revision_authority_and_active_job(reference,generation):
    f,jobs,service,current=reference;before=f.get(auth())
    for authority in [auth(write=False),auth(owner='bob'),auth(workspace='two')]:
        with pytest.raises(ApiFailure):service.apply(authority,dict(expected_revision=1,request_key='reference_003'))
    with pytest.raises(ApiFailure):service.apply(auth(),dict(expected_revision=999,request_key='reference_003'))
    submit(generation)
    with pytest.raises(ApiFailure) as exc:service.apply(auth(),dict(expected_revision=1,request_key='reference_003'))
    assert exc.value.code=='BUSINESS_GENERATION_ACTIVE' and f.get(auth())==before


@pytest.mark.parametrize('body',[None,{},dict(expected_revision=True,request_key='reference_004'),dict(expected_revision=1,request_key='bad'),dict(expected_revision=1,request_key='reference_004',extra=True)])
def test_invalid_reference_payloads_fail_before_write(reference,body):
    f,_,service,_=reference;before=f.get(auth())
    with pytest.raises(ApiFailure):service.apply(auth(),body)
    assert f.get(auth())==before
