"""Offline behavior tests; cloud fixtures do not establish live data relationships."""
import json
from unittest.mock import patch

import pytest
from cryptography.fernet import Fernet
from jsonschema import Draft202012Validator
from pathlib import Path

from workflow_api.data_sources import DataSources
from workflow_api.data_relationships import DataRelationships, build_graph
from workflow_api.storage import WorkflowStore
from workflow_api.service import ApiFailure


def auth(owner='alice',workspace='one',write=True):
    return {'subject':{'subject_id':owner,'workspace_id':workspace},'decision':'allow','permissions':['tools.read']+(['tools.assign'] if write else [])}


def dataset(cid,name,fields,schema=None,constraints=None):
    return dict(dataset_id=cid+'_'+name,name=name,schema=schema,database='demo',kind='table' if schema else 'collection',
                fields=[dict(field_id=cid+'_'+name+'_'+field,name=field,types=types,discovery_method='declared' if schema else 'sampled') for field,types in fields],
                constraints=constraints or [],indexes=[],sample_count=0,discovery_method='declared' if schema else 'sampled')


def sources():
    fk=dict(name='orders_customer',kind='foreign_key',columns=['tenantID','customerID'],referenced_schema='northwind',referenced_table='customers',referenced_columns=['tenantID','customerID'])
    return [dict(connection=dict(connection_id='pg',name='Postgres',connection_status='connected',metadata_revision=1,generation=1),snapshot=dict(revision=1,coverage='declared',warnings=[],datasets=[
        dataset('pg','orders',[('tenantID',['integer']),('customerID',['text']),('employeeID',['integer'])],'northwind',[fk]),
        dataset('pg','customers',[('tenantID',['integer']),('customerID',['text'])],'northwind')])),
        dict(connection=dict(connection_id='mongo',name='Atlas',connection_status='connected',metadata_revision=1,generation=1),snapshot=dict(revision=1,coverage='sampled',warnings=[],datasets=[
            dataset('mongo','customers',[('customerID',['string']),('employee_id',['integer']),('id',['string']),('nested.customerID',['string']),('items[].customerID',['string'])])]))]


@pytest.fixture
def manager(tmp_path):
    key=tmp_path/'key';key.write_bytes(Fernet.generate_key())
    m=DataSources(WorkflowStore(tmp_path/'data.sqlite'),{'BUILDER_DATA_SOURCE_KEY_FILE':str(key)})
    with m.store.transaction() as db:
        for source in sources():
            cid=source['connection']['connection_id']
            db.execute('INSERT INTO data_source_connections VALUES (?,?,?,?,?)',(cid,'one','alice','encrypted',json.dumps(source['connection'])))
            db.execute('INSERT INTO data_source_snapshots VALUES (?,?,?)',(cid,1,json.dumps(source['snapshot'])))
    return m.relationships


def built(manager):
    manager.request(auth());assert manager.tick()
    return manager.get(auth())


def test_declared_composite_order_and_suggestions():
    graph=build_graph(sources())
    edge=next(e for e in graph['relationships'] if e['kind']=='declared')
    assert edge['field_pairs']==[
        dict(source_field_id='pg_orders_tenantID',target_field_id='pg_customers_tenantID'),
        dict(source_field_id='pg_orders_customerID',target_field_id='pg_customers_customerID')]
    suggestions=[e for e in graph['relationships'] if e['kind']=='suggested']
    assert len(suggestions)==3 and all(e['status']=='proposed' for e in suggestions)
    assert all('unverified' in ' '.join(e['evidence']) for e in suggestions)
    assert not any('nested.' in str(e['field_pairs']) or 'items[]' in str(e['field_pairs']) for e in suggestions)


def test_no_type_guessing_or_uncovered_target():
    data=sources();data[1]['snapshot']['datasets'][0]['fields'][0]['types']=['integer']
    data[1]['snapshot']['datasets'][0]['fields'][1]['types']=['integer','string']
    data[0]['snapshot']['datasets'].pop()
    graph=build_graph(data)
    assert graph['relationships']==[] and any('outside' in w for w in graph['warnings'])


def test_review_annotation_persist_and_concurrent_edit_is_rejected(manager):
    view=built(manager);graph=view['graph'];edge=next(e for e in graph['relationships'] if e['kind']=='suggested')
    view=manager.edit(auth(),'review',edge['relationship_id'],dict(revision=1,status='accepted'))
    assert view['graph']['revision']==2
    with pytest.raises(ApiFailure,match='changed'):
        manager.edit(auth(),'review',edge['relationship_id'],dict(revision=1,status='rejected'))
    view=manager.edit(auth(),'annotation','pg_orders',dict(revision=2,description='Customer sales orders'))
    restarted=DataRelationships(manager.store)
    assert next(n for n in restarted.get(auth())['graph']['nodes'] if n['node_id']=='pg_orders')['description']=='Customer sales orders'
    manager.request(auth());manager.tick()
    assert next(e for e in manager.get(auth())['graph']['relationships'] if e['relationship_id']==edge['relationship_id'])['status']=='accepted'


def test_changed_evidence_requires_new_review(manager):
    graph=built(manager)['graph'];edge=next(e for e in graph['relationships'] if e['kind']=='suggested' and any(p['target_field_id'].endswith('customerID') for p in e['field_pairs']))
    manager.edit(auth(),'review',edge['relationship_id'],dict(revision=1,status='accepted'))
    with manager.store.transaction() as db:
        source=sources()[1];source['connection']['metadata_revision']=2
        source['snapshot']['datasets'][0]['fields'][0]['native_type']='varchar'
        db.execute('UPDATE data_source_connections SET document=? WHERE connection_id=?',(json.dumps(source['connection']),'mongo'))
        db.execute('INSERT INTO data_source_snapshots VALUES (?,?,?)',('mongo',2,json.dumps(source['snapshot'])))
    assert manager.get(auth())['stale']
    with pytest.raises(ApiFailure,match='changed'):
        manager.edit(auth(),'review',edge['relationship_id'],dict(revision=2,status='accepted'))
    manager.request(auth());manager.tick()
    assert next(e for e in manager.get(auth())['graph']['relationships'] if e['relationship_id']==edge['relationship_id'])['status']=='proposed'


def test_isolation_and_permissions(manager):
    built(manager)
    for other in [auth('bob'),auth(workspace='two')]:
        assert manager.get(other)['graph'] is None
        with pytest.raises(ApiFailure):manager.edit(other,'annotation','pg_orders',dict(revision=1,description='x'))
    with pytest.raises(ApiFailure):manager.request(auth(write=False))
    with pytest.raises(ApiFailure):manager.edit(auth(write=False),'annotation','pg_orders',dict(revision=1,description='x'))
    denied=auth();denied['permissions']=[]
    with pytest.raises(ApiFailure):manager.get(denied)


def test_disconnect_hides_nodes_immediately(manager):
    built(manager)
    with manager.store.transaction() as db:
        doc=sources()[1]['connection'];doc['connection_status']='disconnected'
        db.execute('UPDATE data_source_connections SET document=? WHERE connection_id=?',(json.dumps(doc),'mongo'))
    view=manager.get(auth())
    assert view['stale'] and all(n['connection_id']!='mongo' for n in view['graph']['nodes'])
    assert all(e['kind']=='declared' for e in view['graph']['relationships'])


@pytest.mark.parametrize('status',['queued','running','failed'])
def test_unverified_metadata_is_hidden_and_reviews_survive_unchanged_reprofile(manager,status):
    graph=built(manager)['graph']
    edge=next(e for e in graph['relationships'] if e['kind']=='suggested')
    manager.edit(auth(),'review',edge['relationship_id'],dict(revision=graph['revision'],status='accepted'))
    with manager.store.transaction() as db:
        raw=db.execute("SELECT document FROM data_source_connections WHERE connection_id='mongo'").fetchone()[0]
        doc=json.loads(raw);doc['profiling_status']=status;doc['generation']+=1
        db.execute("UPDATE data_source_connections SET document=? WHERE connection_id='mongo'",(json.dumps(doc),))
    assert all(n['connection_id']!='mongo' for n in manager.get(auth())['graph']['nodes'])
    with manager.store.transaction() as db:
        doc['profiling_status']='ready'
        db.execute("UPDATE data_source_connections SET document=? WHERE connection_id='mongo'",(json.dumps(doc),))
    manager.request(auth());manager.tick()
    current=next(e for e in manager.get(auth())['graph']['relationships'] if e['relationship_id']==edge['relationship_id'])
    assert current['status']=='accepted'


def test_lease_recovery_and_no_obsolete_publication(manager):
    manager.request(auth())
    with manager.store.transaction() as db:db.execute("UPDATE data_relationship_jobs SET state='running',token='expired',lease_until=0,attempts=1")
    assert manager.tick() and manager.get(auth())['graph']['revision']==1
    manager.request(auth())
    original=build_graph
    def interrupted(data):
        with manager.store.transaction() as db:
            doc=sources()[1]['connection'];doc['generation']=2
            db.execute('UPDATE data_source_connections SET document=? WHERE connection_id=?',(json.dumps(doc),'mongo'))
        return original(data)
    with patch('workflow_api.data_relationships.build_graph',side_effect=interrupted):assert manager.tick()
    assert manager.get(auth())['graph']['revision']==1 and manager.get(auth())['build_status']=='queued'
    assert manager.tick() and not manager.get(auth())['stale']


def test_failed_build_preserves_graph_and_retries_bounded(manager):
    built(manager);manager.request(auth())
    with manager.store.transaction() as db:db.execute('UPDATE data_relationship_jobs SET attempts=3')
    manager.tick();view=manager.get(auth())
    assert view['build_status']=='failed' and view['graph']['revision']==1
    manager.request(auth());manager.tick();assert manager.get(auth())['build_status']=='ready'


def test_invalid_edits_and_declared_constraints_not_reviewable(manager):
    graph=built(manager)['graph'];edge=next(e for e in graph['relationships'] if e['kind']=='declared')
    with pytest.raises(ApiFailure):manager.edit(auth(),'review',edge['relationship_id'],dict(revision=1,status='accepted'))
    for body in [dict(revision=True,description='x'),dict(revision=1,description=3),dict(revision=1,description='x'*1001),dict(revision=1,description='x',owner='bob')]:
        with pytest.raises(ApiFailure):manager.edit(auth(),'annotation','pg_orders',body)


def test_limits_are_explicit():
    with patch('workflow_api.data_relationships.MAX_NODES',2):
        assert 'limit' in ' '.join(build_graph(sources())['warnings'])
    with patch('workflow_api.data_relationships.MAX_CANDIDATE_PAIRS',0):
        assert 'limit' in ' '.join(build_graph(sources())['warnings'])


def test_contract(manager):
    schema=json.loads((Path(__file__).resolve().parents[1]/'shared/contracts/data-sources/relationships-v1.schema.json').read_text())
    Draft202012Validator.check_schema(schema)
    Draft202012Validator(schema).validate(built(manager))


def test_http_build_and_review_envelopes(manager):
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from types import SimpleNamespace
    from workflow_api.data_source_routes import install
    class Service:
        store=manager.store
        def envelope(self,ref,status,data):return {'data':data}
        def failure(self,ref,exc):return {'error':{'error_code':exc.code,'message':str(exc)}}
    app=FastAPI()
    with patch('workflow_api.data_source_routes.DataSources',return_value=SimpleNamespace(relationships=manager,store=manager.store,env={},semantic=manager.ontology.semantic)):
        install(app,Service(),auth(),{},lambda:'test')
    client=TestClient(app)
    response=client.get('/data-relationships')
    assert response.status_code==200 and response.headers['cache-control']=='no-store'
    assert client.post('/data-relationships/build').json()['data']['build_status']=='queued'
    manager.tick()
    graph=client.get('/data-relationships').json()['data']['graph']
    edge=next(e for e in graph['relationships'] if e['kind']=='suggested')
    result=client.post('/data-relationships/review/'+edge['relationship_id'],json=dict(revision=graph['revision'],status='accepted'))
    assert result.status_code==200 and result.json()['data']['graph']['revision']==2
    assert client.post('/data-relationships/annotation/pg_orders',content='bad-json').status_code==400


def test_non_identifiers_do_not_create_false_links():
    data=sources()
    for source in data:
        for table in source['snapshot']['datasets']:
            for name,types in [('paid',['string']),('valid',['boolean']),('timestampID',['timestamp']),('mixedID',['integer','string'])]:
                table['fields'].append(dict(field_id=table['dataset_id']+'_'+name+'_noise',name=name,types=types,discovery_method='sampled'))
    graph=build_graph(data)
    assert all('_noise' not in str(edge['field_pairs']) for edge in graph['relationships'])


def test_active_build_coalesces_and_second_worker_cannot_claim(manager):
    manager.request(auth());manager.request(auth())
    original=build_graph
    def during(data):
        assert not manager.tick()
        manager.request(auth())
        return original(data)
    with patch('workflow_api.data_relationships.build_graph',side_effect=during):assert manager.tick()
    assert manager.get(auth())['graph']['revision']==1 and not manager.tick()
