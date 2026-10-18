"""Semantic proposals are evidence-anchored inferences, never query grants."""
from copy import deepcopy
import json
from types import SimpleNamespace
from pathlib import Path
import pytest
from jsonschema import Draft202012Validator
from tests.test_data_relationships import manager,built,auth
from workflow_api.semantic_kg import SemanticKnowledgeGraph
from workflow_api.data_sources import DataSources
from workflow_api.service import ApiFailure


def authority(owner='alice'):
    return {**auth(owner),'permissions':['tools.read','tools.assign','workflow.plan'],'roles':['admin'],'scopes':['workspace:read','workspace:write']}


class Provider:
    configured=True
    calls=[]
    def generate(self,packages):
        self.calls.append(deepcopy(packages))
        return {'relationships':[dict(relationship_id=p['relationship_id'],predicate='places' if 'orders' in p['source']['label'] else None,reversed=True,
            evidence_refs=[p['structural_relationship_id'],p['source']['dataset_id'],p['target']['dataset_id'],*[pair[k] for pair in p['field_pairs'] for k in ('source_field_id','target_field_id')]],
            rationale='Naming and supplied field mappings suggest this interpretation; it requires business review.',alternatives=[]) for p in packages]}


@pytest.fixture
def semantic(manager):
    built(manager)
    s=SemanticKnowledgeGraph(SimpleNamespace(store=manager.store,relationships=manager,env={'BUILDER_KG_SEMANTIC_INFERENCE_ENABLED':'1'}),Provider())
    s.provider.calls=[];s.authenticate=lambda w,o:authority(o) if w=='one' else None
    return s


def test_automatic_proposals_preserve_provenance_direction_and_no_join_grant(semantic):
    before=semantic.manager.relationships.get(auth())
    initial=semantic.get(authority())
    assert all(e['predicate'] is None and e['status']=='ambiguous' for e in initial['relationships'])
    assert semantic.tick()
    result=semantic.get(authority())
    edge=next(e for e in result['relationships'] if e['technical_status']=='declared')
    names={n['entity_id']:n['label'] for n in result['entities']}
    assert (names[edge['source_entity_id']],edge['predicate'],names[edge['target_entity_id']])==('Customer','places','Order')
    assert edge['status']=='inferred' and edge['confidence'] is None
    assert edge['provenance']['field_pairs']==edge['field_pairs']
    assert semantic.manager.relationships.get(auth())==before
    assert not semantic.tick() and len(semantic.provider.calls)==1
    assert all('secret' not in json.dumps(p) and 'password' not in json.dumps(p) for p in semantic.provider.calls)


def test_review_staleness_reset_and_description_changes(semantic):
    semantic.tick();view=semantic.get(authority());edge=next(e for e in view['relationships'] if e['predicate'])
    body=dict(revision=view['revision'],predicate='submits',reversed=True,status='confirmed')
    updated=semantic.review(authority(),edge['relationship_id'],body)
    assert next(e for e in updated['relationships'] if e['relationship_id']==edge['relationship_id'])['status']=='confirmed'
    with pytest.raises(ApiFailure):semantic.review(authority(),edge['relationship_id'],body)
    graph=semantic.manager.relationships.get(auth())['graph']
    semantic.manager.relationships.edit(auth(),'annotation',edge['source_dataset_id'],dict(revision=graph['revision'],description='Changed business definition'))
    changed=semantic.get(authority())
    assert next(e for e in changed['relationships'] if e['relationship_id']==edge['relationship_id'])['status']=='needs_review'
    assert semantic.tick()
    changed=semantic.get(authority())
    # Regeneration never silently re-confirms an old owner review.
    assert next(e for e in changed['relationships'] if e['relationship_id']==edge['relationship_id'])['status']=='needs_review'
    reset=semantic.review(authority(),edge['relationship_id'],dict(revision=changed['revision'],predicate='submits',reversed=True,status='suggested'))
    assert next(e for e in reset['relationships'] if e['relationship_id']==edge['relationship_id'])['status']=='inferred'


def test_model_output_validation_rejects_invented_ids_refs_generic_labels_and_confidence(semantic):
    with semantic.store.transaction(write=False) as db:packages=semantic.inputs(db,'one','alice')[2]
    proposal=semantic.provider.generate(packages)
    for mutate in [lambda p:p['relationships'][0].update(relationship_id='invented'),lambda p:p['relationships'][0]['evidence_refs'].append('invented_field'),lambda p:p['relationships'][0].update(predicate='references'),lambda p:p['relationships'][0].update(confidence=.99),lambda p:p['relationships'].pop()]:
        bad=deepcopy(proposal);mutate(bad)
        with pytest.raises(Exception):semantic.validate(bad,packages)
    semantic.provider.generate=lambda packages:{'relationships':[]}
    assert semantic.tick()
    view=semantic.get(authority())
    assert view['semantic_status']['state']=='failed'
    assert all(e['status']=='ambiguous' for e in view['relationships'])
    assert not semantic.tick()  # Failure does not repeatedly bill the model.


def test_owner_lease_fencing_and_no_unmeasured_scores(semantic):
    semantic.tick();view=semantic.get(authority());edge=view['relationships'][0]
    assert semantic.get(authority('other'))['relationships']==[]
    with pytest.raises(ApiFailure):semantic.review(auth(write=False),edge['relationship_id'],dict(revision=view['revision'],predicate='supplies',reversed=False,status='confirmed'))
    with pytest.raises(ApiFailure):semantic.review(authority(),edge['relationship_id'],dict(revision=view['revision'],predicate='suggested',reversed=False,status='confirmed'))
    assert all(e['confidence'] is None for e in view['relationships'])


def test_auth_revoked_during_inference_cannot_publish(semantic):
    original=semantic.provider.generate
    def generate(packages):
        result=original(packages);semantic.authenticate=lambda w,o:None;return result
    semantic.provider.generate=generate
    semantic.tick()
    assert all(e['status']=='ambiguous' for e in semantic.get(authority())['relationships'])


def test_semantic_graph_contract(semantic):
    semantic.tick()
    path=Path(__file__).resolve().parents[1]/'shared/contracts/data-sources/semantic-kg-v1.schema.json'
    Draft202012Validator(json.loads(path.read_text())).validate(semantic.get(authority()))


def test_legacy_confirmations_keep_their_evidence_basis_after_regeneration(semantic):
    legacy=semantic.manager.relationships.ontology
    view=legacy.get(auth());edge=next(e for e in view['relationships'] if e['technical_status']=='declared')
    legacy.edit(auth(),edge['relationship_id'],dict(revision=view['revision'],predicate='supplies',reversed=False,status='confirmed'))
    assert next(e for e in semantic.get(authority())['relationships'] if e['relationship_id']==edge['relationship_id'])['status']=='confirmed'
    graph=semantic.manager.relationships.get(auth())['graph']
    semantic.manager.relationships.edit(auth(),'annotation',edge['source_dataset_id'],dict(revision=graph['revision'],description='A different business interpretation'))
    semantic.tick()
    assert next(e for e in semantic.get(authority())['relationships'] if e['relationship_id']==edge['relationship_id'])['status']=='needs_review'


def test_live_extraction_is_strictly_disabled_without_explicit_flag(semantic,monkeypatch):
    from workflow_api.semantic_kg import SemanticProvider
    inactive=SemanticKnowledgeGraph(SimpleNamespace(store=semantic.store,relationships=semantic.manager.relationships,env={}),Provider())
    inactive.authenticate=semantic.authenticate
    assert not inactive.enabled and not inactive.tick()
    with pytest.raises(ApiFailure) as error:inactive.request(authority())
    assert error.value.code=='KG_INFERENCE_DISABLED'
    # Even a configured API key and an injected SDK cannot bypass the gate.
    calls=[]
    monkeypatch.setattr('openai.OpenAI',lambda **kwargs:calls.append(kwargs))
    live=SemanticProvider({'OPENAI_API_KEY':'test-only-placeholder','OPENAI_MODEL':'test-model'})
    with pytest.raises(ApiFailure) as error:live.generate([])
    assert error.value.code=='KG_INFERENCE_DISABLED' and calls==[]
