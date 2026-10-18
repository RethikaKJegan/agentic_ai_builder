"""Metadata-only integration tests; no cloud business reads/writes."""
import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from test_data_relationships import auth, built, dataset, manager, sources
from workflow_api.data_relationships import build_graph
from workflow_api.service import ApiFailure


def review(manager, node='pg_orders', **patch):
    graph=manager.detailed.get(auth())['graph']
    body=dict(revision=graph['revision'],entity_name='Customer',role='represents',status='confirmed')
    body.update(patch)
    return manager.detailed.edit(auth(),node,body)


def replace_snapshot(manager, source):
    cid=source['connection']['connection_id']
    with manager.store.transaction() as db:
        source['connection']['metadata_revision']+=1
        revision=source['connection']['metadata_revision']
        db.execute('UPDATE data_source_connections SET document=? WHERE connection_id=?',(json.dumps(source['connection']),cid))
        db.execute('INSERT INTO data_source_snapshots VALUES (?,?,?)',(cid,revision,json.dumps(source['snapshot'])))


def test_versioned_containment_and_v1_compatibility(manager):
    before=built(manager);view=manager.detailed.get(auth());graph=view['graph']
    assert view['version']==2
    assert {n['node_id'] for n in before['graph']['nodes']} <= {n['node_id'] for n in graph['nodes']}
    nodes={n['node_id']:n for n in graph['nodes']}
    order=nodes['pg_orders'];schema=nodes[order['parent_id']];database=nodes[schema['parent_id']]
    assert (schema['kind'],schema['label'],database['kind'],database['label'])==('schema','northwind','database','demo')
    mongo=nodes['mongo_customers'];assert nodes[mongo['parent_id']]['kind']=='database'
    assert manager.get(auth())==before
    assert all(n['kind'] in ('connection','dataset','field') for n in manager.get(auth())['graph']['nodes'])


def test_entity_identity_reference_and_shared_concept(manager):
    built(manager);graph=manager.detailed.get(auth())['graph'];m={m['node_id']:m for m in graph['mappings']}
    assert m['pg_orders_customerID']['role']=='reference'
    assert m['mongo_customers_customerID']['role']=='identifier'
    assert m['mongo_customers']['entity_id']==m['pg_orders_customerID']['entity_id']
    assert all(v['status']=='suggested' for v in m.values())
    assert all(n['metadata']['execution_authority'] is False for n in graph['nodes'] if n['kind']=='entity')


def test_review_persists_reset_reject_and_audit(manager):
    built(manager)
    view=review(manager);assert view['graph']['revision']==2
    get=lambda:next(m for m in manager.detailed.get(auth())['graph']['mappings'] if m['node_id']=='pg_orders')
    assert get()['status']=='confirmed' and get()['entity_name']=='Customer'
    manager.request(auth());manager.tick();assert get()['status']=='confirmed'
    review(manager,status='rejected');assert get()['status']=='rejected'
    review(manager,status='suggested');assert get()['status']=='suggested' and get()['entity_name']=='Order'
    with manager.store.transaction(write=False) as db:
        assert db.execute('SELECT count(*) FROM data_graph_audit').fetchone()[0]==3


def test_changed_structural_evidence_needs_review_and_stale_edit_fails(manager):
    built(manager);review(manager)
    source=sources()[0];source['snapshot']['datasets'][0]['fields'][0]['types']=['bigint']
    replace_snapshot(manager,source)
    historical=manager.detailed.get(auth());assert historical['stale']
    # A historical graph must display its old matching snapshot, not the new one.
    assert next(n for n in historical['graph']['nodes'] if n['node_id']=='pg_orders_tenantID')['types']==['integer']
    with pytest.raises(ApiFailure) as error:review(manager)
    assert error.value.code=='DATA_RELATIONSHIP_STALE'
    manager.request(auth());manager.tick()
    assert next(m for m in manager.detailed.get(auth())['graph']['mappings'] if m['node_id']=='pg_orders')['status']=='needs_review'


def test_sample_counts_do_not_invalidate_reviews(manager):
    built(manager);review(manager,'mongo_customers')
    source=sources()[1];source['snapshot']['datasets'][0]['sample_count']=25
    source['snapshot']['datasets'][0]['fields'][0]['present_in_samples']=24
    replace_snapshot(manager,source);manager.request(auth());manager.tick()
    assert next(m for m in manager.detailed.get(auth())['graph']['mappings'] if m['node_id']=='mongo_customers')['status']=='confirmed'


def test_explicit_attribute_mapping(manager):
    source=sources()[0];source['snapshot']['datasets'][0]['fields'].append(dict(field_id='amount',name='amount',types=['numeric'],discovery_method='declared'))
    replace_snapshot(manager,source);built(manager)
    review(manager,'amount',role='attribute')
    mapped=next(m for m in manager.detailed.get(auth())['graph']['mappings'] if m['node_id']=='amount')
    assert mapped['status']=='confirmed' and mapped['role']=='attribute'


def test_permission_owner_revision_and_validation(manager):
    built(manager)
    assert manager.detailed.get(auth('bob'))['graph'] is None
    assert manager.detailed.get(auth(workspace='other'))['graph'] is None
    for context in [auth(write=False),dict(auth(),permissions=[])]:
        with pytest.raises(ApiFailure):manager.detailed.edit(context,'pg_orders',{})
    for patch in [dict(revision=True),dict(entity_name=''),dict(entity_name='x'*81),dict(entity_name='bad\nname'),dict(role='attribute'),dict(status='accepted'),dict(revision=0)]:
        with pytest.raises(ApiFailure):review(manager,**patch)
    review(manager)
    with pytest.raises(ApiFailure):review(manager,revision=1)


def test_confirmation_does_not_grant_join_authority(manager):
    before=built(manager)['graph']['relationships'];review(manager,'pg_orders_customerID',role='reference')
    assert manager.get(auth())['graph']['relationships']==before
    assert not any(e['status']=='accepted' for e in before)


def test_disconnect_removes_dependent_entities(manager):
    built(manager)
    with manager.store.transaction() as db:
        source=sources()[1]['connection'];source['connection_status']='disconnected'
        db.execute('UPDATE data_source_connections SET document=? WHERE connection_id=?',(json.dumps(source),'mongo'))
    graph=manager.detailed.get(auth())['graph']
    assert all(n['connection_id']!='mongo' for n in graph['nodes'])
    assert all(m['node_id']!='mongo_customers' for m in graph['mappings'])


def test_mongo_specific_identifiers_and_qualified_id_references():
    data=sources();mongo=data[1]['snapshot']['datasets']
    mongo.append(dataset('mongo','purchases',[('customerID',['string']),('customer_id',['string']),('id',['string'])]))
    mongo[0]['fields'].append(dict(field_id='customer_pk',name='_id',types=['string'],discovery_method='sampled'))
    graph=build_graph(data)
    assert any(e['source_dataset_id']=='mongo_customers' and e['target_dataset_id']=='mongo_purchases' for e in graph['relationships'])
    assert any(e['target_dataset_id']=='mongo_customers' and e['field_pairs'][0]['target_field_id']=='customer_pk' for e in graph['relationships'])
    assert not any(p['source_field_id']=='mongo_purchases_id' or p['target_field_id']=='mongo_purchases_id' for e in graph['relationships'] for p in e['field_pairs'])


def test_qualification_never_invents_cardinality(manager):
    built(manager);edges=manager.detailed.get(auth())['graph']['relationships']
    declared=next(e for e in edges if e['kind']=='declared')['qualification']
    suggested=next(e for e in edges if e['kind']=='suggested')['qualification']
    assert declared['confidence']=='database_declaration' and declared['direction']=='source_references_target'
    assert suggested['direction']=='unknown' and suggested['value_overlap']=='not_checked'
    assert 'Unknown' in suggested['cardinality']


def test_mongo_objectid_reference_is_metadata_only_and_no_string_coercion():
    data=sources();mongo=data[1]['snapshot']['datasets']
    mongo[0]['fields'].append(dict(field_id='customer_pk',name='_id',types=['ObjectId'],discovery_method='sampled'))
    mongo.append(dataset('mongo','purchases',[('customer_id',['ObjectId']),('customerID',['string'])]))
    graph=build_graph(data)
    edges=[e for e in graph['relationships'] if any(p['target_field_id']=='customer_pk' for p in e['field_pairs'])]
    assert len(edges)==1 and edges[0]['field_pairs'][0]['source_field_id']=='mongo_purchases_customer_id'
    assert any('ObjectId' in w for w in graph['warnings'])


def test_contracts_and_metadata_details(manager):
    built(manager)
    root=Path(__file__).resolve().parents[1]/'shared/contracts/data-sources'
    for version,value in [(1,manager.get(auth())),(2,manager.detailed.get(auth()))]:
        schema=json.loads((root/f'relationships-v{version}.schema.json').read_text())
        Draft202012Validator.check_schema(schema);Draft202012Validator(schema).validate(value)
    node=next(n for n in manager.detailed.get(auth())['graph']['nodes'] if n['node_id']=='pg_orders')
    assert node['metadata']['constraints'][0]['columns']==['tenantID','customerID']


def test_http_v2_uses_current_authority_and_safe_envelopes(manager):
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from types import SimpleNamespace
    from unittest.mock import patch
    from workflow_api.data_source_routes import install
    class Service:
        store=manager.store
        def envelope(self,ref,status,data):
            from workflow_api.service import WorkflowService
            return WorkflowService.envelope(ref,status,data)
        def failure(self,ref,exc):return {'error':{'error_code':exc.code}}
    app=FastAPI()
    with patch('workflow_api.data_source_routes.DataSources',return_value=SimpleNamespace(relationships=manager,store=manager.store,env={},semantic=manager.ontology.semantic)):
        install(app,Service(),auth(),{},lambda:'test')
    built(manager);client=TestClient(app)
    response=client.get('/data-relationships/v2');assert response.status_code==200 and response.headers['cache-control']=='no-store'
    assert response.json()['data']['version']==2
    schema=json.loads((Path(__file__).resolve().parents[1]/'shared/contracts/data-sources/relationships-v2.schema.json').read_text())
    Draft202012Validator(schema).validate(response.json()['data'])
    body=dict(revision=1,entity_name='Sale',role='represents',status='confirmed')
    assert client.post('/data-relationships/v2/mapping/pg_orders',json=body).status_code==200
    app.state.workflow_auth=auth(write=False)
    assert client.post('/data-relationships/v2/mapping/pg_orders',json=body).status_code==403


def test_entity_review_invalidates_an_existing_query_plan(tmp_path):
    from test_data_queries import queries as make_queries, saved
    queries=make_queries.__wrapped__(tmp_path)
    item=saved(queries)
    graph=queries.manager.relationships.detailed.get(auth())['graph']
    queries.manager.relationships.detailed.edit(auth(),'pg_lines',dict(revision=graph['revision'],entity_name='Line item',role='represents',status='confirmed'))
    with pytest.raises(ApiFailure) as failure:
        queries.execute(auth(),dict(plan_id=item['plan_id']))
    assert failure.value.code=='DATA_QUERY_STALE' and queries.reader.calls==[]


def test_composite_uniqueness_is_not_mistaken_for_single_field_uniqueness():
    from workflow_api.data_graph_v2 import qualify
    table=dataset('pg','customers',[('tenantID',['integer']),('customerID',['text'])],'northwind',
                  [dict(kind='unique',columns=['tenantID','customerID'])])
    edge=dict(source_dataset_id='other',target_dataset_id=table['dataset_id'],kind='suggested',status='proposed',
              field_pairs=[dict(source_field_id='source',target_field_id='pg_customers_customerID')])
    assert 'No applicable' in qualify(edge,{table['dataset_id']:table})['target_key_evidence']
