"""Ontology meaning remains independent of technical query authority."""
import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator
from tests.test_data_relationships import auth, built, manager, sources
from tests.test_data_graph_v2 import replace_snapshot
from workflow_api.service import ApiFailure


def edit(manager, **values):
    view=manager.ontology.get(auth())
    edge=next(e for e in view['relationships'] if e['technical_status']=='declared')
    body=dict(revision=view['revision'],predicate='places',reversed=True,status='confirmed')
    body.update(values)
    return manager.ontology.edit(auth(),edge['relationship_id'],body)


def test_business_projection_keeps_sources_evidence_and_contract(manager):
    before=built(manager)
    view=manager.ontology.get(auth())
    assert {e['label'] for e in view['entities']} >= {'Order','Customer'}
    edge=next(e for e in view['relationships'] if e['technical_status']=='declared')
    assert len(edge['field_pairs'])==2 and 'Postgres / demo / northwind / orders' in edge['field_pairs'][0]['source_label']
    assert edge['predicate']=='references' and edge['status']=='suggested'
    assert manager.get(auth())==before
    schema=json.loads((Path(__file__).resolve().parents[1]/'shared/contracts/data-sources/ontology-v1.schema.json').read_text())
    Draft202012Validator.check_schema(schema)
    Draft202012Validator(schema).validate(view)


def test_predicate_direction_persistence_reset_and_no_join_grant(manager):
    before=built(manager)
    view=edit(manager)
    edge=next(e for e in view['relationships'] if e['technical_status']=='declared')
    names={e['entity_id']:e['label'] for e in view['entities']}
    assert (names[edge['source_entity_id']],edge['predicate'],names[edge['target_entity_id']])==('Customer','places','Order')
    assert edge['status']=='confirmed'
    assert manager.get(auth())==before
    manager.request(auth());manager.tick()
    assert any(e['status']=='confirmed' for e in manager.ontology.get(auth())['relationships'])
    assert next(e for e in edit(manager,status='rejected')['relationships'] if e['technical_status']=='declared')['status']=='rejected'
    assert next(e for e in edit(manager,status='suggested')['relationships'] if e['technical_status']=='declared')['predicate']=='references'


def test_stale_and_concurrent_review_and_changed_mapping(manager):
    built(manager);old=manager.ontology.get(auth());edit(manager)
    with pytest.raises(ApiFailure) as error:
        edit(manager,revision=old['revision'])
    assert error.value.status==409
    detailed=manager.detailed.get(auth())
    manager.detailed.edit(auth(),'pg_orders',dict(revision=detailed['graph']['revision'],entity_name='Purchase order',role='represents',status='confirmed'))
    assert any(e['status']=='needs_review' for e in manager.ontology.get(auth())['relationships'])
    source=sources()[0];source['snapshot']['datasets'][0]['fields'][0]['types']=['bigint'];replace_snapshot(manager,source)
    assert manager.ontology.get(auth())['stale']
    with pytest.raises(ApiFailure):edit(manager)


def test_owner_permissions_disconnect_and_input_validation(manager):
    built(manager);view=manager.ontology.get(auth());edge=view['relationships'][0]
    assert not manager.ontology.get(auth('other'))['entities']
    body=dict(revision=view['revision'],predicate='works for',reversed=False,status='confirmed')
    with pytest.raises(ApiFailure):manager.ontology.edit(auth(write=False),edge['relationship_id'],body)
    with pytest.raises(ApiFailure):manager.ontology.edit(auth(),edge['relationship_id'],{**body,'predicate':'bad\nlabel'})
    with manager.store.transaction() as db:
        raw=db.execute("SELECT document FROM data_source_connections WHERE connection_id='mongo'").fetchone()[0]
        doc=json.loads(raw);doc['connection_status']='disconnected'
        db.execute("UPDATE data_source_connections SET document=? WHERE connection_id='mongo'",(json.dumps(doc),))
    assert all(s['connection_id']!='mongo' for e in manager.ontology.get(auth())['entities'] for s in e['sources'])


def test_http_ontology_and_refresh_routes(manager):
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from unittest.mock import patch
    from workflow_api.data_source_routes import install
    from workflow_api.data_sources import DataSources
    from workflow_api.service import WorkflowService
    built(manager)
    app=FastAPI();service=WorkflowService(manager.store)
    service.registry._policy.workspace_id='one'
    with patch('workflow_api.data_source_routes.DataSources',return_value=DataSources(manager.store,{})):
        install(app,service,auth(),{},lambda:'req_ontology')
    with TestClient(app) as client:
        r=client.get('/data-ontology');assert r.status_code==200 and r.headers['cache-control']=='no-store'
        view=r.json()['data'];edge=view['relationships'][0]
        r=client.post('/data-ontology/'+edge['relationship_id'],json=dict(revision=view['revision'],predicate='relates to',reversed=False,status='confirmed'))
        assert r.status_code==200,r.text
        assert client.get('/data-refresh').status_code==200
        assert client.post('/data-refresh/pg',json=dict(enabled=False,interval_seconds=300)).status_code==200
        assert client.post('/data-refresh/foreign',json=dict(enabled=True,interval_seconds=60)).status_code==404
