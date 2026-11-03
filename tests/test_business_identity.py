"""Company/account scopes and native identifier evidence prevent false merges."""
from copy import deepcopy
from hashlib import sha256
import json
from unittest.mock import patch
import pytest
from tests.test_business_graph import graph,build
from tests.test_business_compiler import compiled_draft
from tests.test_business_generation import generation
from tests.test_business_ontology import foundation,auth
from workflow_api.business_compiler import canonical
from workflow_api.business_identity import BusinessIdentity,resolve
from workflow_api.service import ApiFailure


def configured(x):
    x.reader.rows['enginedetails'][0]['oem']='org1'
    x.reader.rows['oems'][0]['oemNameId']='org1'
    x.reader.rows['tickets'][0]['engineModal']='M'
    return x

def ticket(g):return next(r for r in g['records'] if r['collection']=='tickets')
def report(x,g):return resolve(x.snapshot,g,dict(ticket_node_id=ticket(g)['node_id']))


def test_company_and_account_paths_resolve_without_claiming_engine_identity(graph):
    x=configured(graph);g=build(x);before=deepcopy(g);calls=len(x.reader.calls);service=BusinessIdentity(x.f,x.service)
    with patch('socket.create_connection',side_effect=AssertionError('No network')):
        r=service.run(auth(write=False),x.snapshot['version_id'],g['graph_id'],dict(ticket_node_id=ticket(g)['node_id']))
    assert r['invoice_resolution']=='single_scope_supported_candidate'
    assert r['physical_engine_identity']=='unresolved' and r['selected_invoice_node_id'] is None
    assert r['eligibility']=='not_evaluated' and r['identity_merges']==r['company_queries']==r['model_calls']==0
    assert len(x.reader.calls)==calls and g==before
    assert r['company_paths']['direct_company_nodes']==r['company_paths']['account_company_nodes']
    invoice=next(c for c in r['candidates'] if c['collection']=='enginedetails')
    assert invoice['company_alignment']=='same_company_record' and invoice['serial_comparison']=='match'
    assert invoice['company_associations'][0]['source_field']=='oem'
    assert all(c['classification']=='unresolved_candidate' for c in r['candidates'] if c['role']=='quality')
    assert all(e['verification']=='native_reference_checked' for e in r['direct_associations'])
    assert {e['source_field'] for e in r['direct_associations']} >= {'oem','oemOrg','oemNameId','ticketId','ticket'}


def test_company_conflict_does_not_choose_a_path(graph):
    x=configured(graph);x.reader.rows['oems'][0]['oemNameId']='org2';x.reader.rows['oemnames'].append(dict(_id='org2'))
    r=report(x,build(x))
    assert r['conflicts'][0]['code']=='COMPANY_PATH_CONFLICT' and not r['scope_supported_invoice_nodes']
    assert r['invoice_resolution']=='company_conflict'


def test_multiple_scoped_invoices_never_auto_select(graph):
    x=configured(graph);x.reader.rows['enginedetails'].append({**x.reader.rows['enginedetails'][0],'_id':'invoice2'})
    r=report(x,build(x));assert r['invoice_resolution']=='multiple_scope_supported_candidates' and len(r['scope_supported_invoice_nodes'])==2 and r['selected_invoice_node_id'] is None


def test_native_objectid_and_string_are_not_equal(graph):
    from bson import ObjectId
    x=configured(graph);oid='000000000000000000000001'
    x.reader.rows['oems'][0]['oemNameId']=oid;x.reader.rows['oemnames']=[dict(_id=ObjectId(oid))]
    g=build(x)
    assert any(u['field']=='oemNameId' for u in g['unresolved'])
    # Test token distinction even when projected public strings are identical.
    source=next(r for r in g['records'] if r['collection']=='tickets');target=next(r for r in g['records'] if r['collection']=='enginedetails')
    left=next(f for f in source['fields'] if f['name']=='engineNo');right=next(f for f in target['fields'] if f['name']=='engineSerialNumber')
    right['native_token']='0'*64;target['record_sha256']=sha256(canonical(target['fields']).encode()).hexdigest()
    assert left['value']==right['value'] and next(c for c in report(x,g)['candidates'] if c['collection']=='enginedetails')['serial_comparison']=='different'


def test_legacy_public_equality_never_becomes_native_equality(graph):
    x=configured(graph);g=build(x)
    for node in g['records']:
        for cell in node['fields']:cell.pop('native_token',None)
        node['record_sha256']=sha256(canonical(node['fields']).encode()).hexdigest()
    for edge in g['edges']:edge.pop('source_field',None)
    r=report(x,g);invoice=next(c for c in r['candidates'] if c['collection']=='enginedetails')
    assert invoice['serial_comparison']=='public_match_unverified_types' and not r['scope_supported_invoice_nodes']
    assert any(e['verification']=='saved_reference_unverified_types' for e in r['direct_associations'])


def test_replacement_serial_is_a_distinct_observation(graph):
    x=configured(graph);x.reader.rows['floatengines']=[dict(_id='dispatch1',ticketId='ticket1',replacementEngineNumber='REPLACEMENT-7')]
    r=report(x,build(x));assert r['replacement_context'][0]['observation']['value']=='REPLACEMENT-7'
    assert r['replacement_context'][0]['identity']=='separate_observation' and r['identity_merges']==0


def test_company_search_values_are_deduplicated_and_domain_clipping_visible(graph):
    x=configured(graph)
    for i in range(19):
        x.reader.rows['tickets'].append(dict(_id='ticket'+str(i+2),engineNo='SER-1',oem='account'+str(i),oemOrg='company'+str(i)))
        x.reader.rows['enginedetails'].append(dict(_id='invoice'+str(i+2),engineSerialNumber='SER-1',oem='invoicecompany'+str(i)))
    g=build(x);queries=[c for c in x.reader.calls if c['collection']=='oemnames']
    assert len(queries)==1 and len(queries[0]['query']['_id']['$in'])==20
    assert next(o for o in g['outcomes'] if o['collection']=='oemnames')['truncated']
    assert any('truncated' in reason for reason in report(x,g)['review_reasons'])


@pytest.mark.parametrize('body',[None,{},dict(ticket_node_id='foreign'),dict(ticket_node_id=True),dict(ticket_node_id=[]),dict(ticket_node_id='x',same_engine=True)])
def test_invalid_requests_and_foreign_scope(graph,body):
    x=graph;g=build(x)
    with pytest.raises(ApiFailure):resolve(x.snapshot,g,body)
    service=BusinessIdentity(x.f,x.service)
    for foreign in [auth(owner='bob'),auth(workspace='two')]:
        with pytest.raises(ApiFailure):service.run(foreign,x.snapshot['version_id'],g['graph_id'],dict(ticket_node_id=ticket(g)['node_id']))


def test_reference_with_wrong_source_field_is_not_trusted(graph):
    x=configured(graph);g=build(x)
    for edge in g['edges']:
        if edge['classification']=='source_reference':edge['source_field']='wrongField'
    r=report(x,g);assert r['rejected_references'] and not r['direct_associations'] and not r['scope_supported_invoice_nodes']


def test_actual_http_association_endpoint_is_scoped_and_read_only(tmp_path,graph):
    from fastapi.testclient import TestClient
    from workflow_api.main import create_app
    x=configured(graph);g=build(x);app=create_app(database=tmp_path/'identity.sqlite',dev_auth=True,start_workers=False,planning_worker_enabled=False)
    client=TestClient(app);root='/business-ontology/v1'
    assert client.post(root+'/versions/foreign/graphs/foreign/associations',json={}).status_code==401
    client.get('/session');client.cookies.set('builder_dev_session',client.cookies.get('builder_dev_session'),path='/')
    with app.state.workflow_service.store.transaction() as db:
        for cid in ('service','quality'):
            doc=dict(connection_id=cid,name=cid,engine='mongodb',connection_status='connected',metadata_revision=1)
            db.execute('INSERT INTO data_source_connections VALUES (?,?,?,?,?)',(cid,'local-workspace','local-builder',None,json.dumps(doc)))
    version=client.post(root+'/initialize',json={'sources':{'service':'service','quality':'quality'}}).json()['data']['current_version_id'];g['version_id']=version
    with app.state.workflow_service.store.transaction() as db:db.execute('INSERT INTO business_ontology_graphs VALUES (?,?,?,?,?,?,?)',('local-workspace','local-builder',version,g['graph_id'],'identity_http_graph','fixture',json.dumps(g)))
    endpoint=root+'/versions/'+version+'/graphs/'+g['graph_id']+'/associations';body=dict(ticket_node_id=ticket(g)['node_id'])
    with app.state.workflow_service.store.transaction(write=False) as db:before={name:db.execute('SELECT * FROM '+name).fetchall() for name in ['business_ontology_graphs','business_ontology_versions','business_ontology_events','data_source_connections']}
    with patch('socket.create_connection',side_effect=AssertionError('No network')):response=client.post(endpoint,json=body)
    assert response.status_code==200 and response.headers['cache-control']=='no-store' and response.json()['data']['physical_engine_identity']=='unresolved'
    assert client.post(endpoint,json=body,headers={'origin':'https://untrusted.example'}).status_code==403
    assert client.post(endpoint,json={**body,'same_engine':True}).status_code==422
    assert client.post(endpoint,json={'ticket_node_id':g['records'][0]['node_id']}).status_code==422
    with app.state.workflow_service.store.transaction(write=False) as db:assert all(db.execute('SELECT * FROM '+name).fetchall()==rows for name,rows in before.items())
    app.state.workflow_auth['subject']['subject_id']='foreign'
    assert client.post(endpoint,json=body).status_code==404


def test_historical_disconnection_and_bad_token_integrity(graph):
    x=configured(graph);g=build(x);service=BusinessIdentity(x.f,x.service)
    with x.f.store.transaction() as db:db.execute("UPDATE data_source_connections SET document=? WHERE connection_id='quality'",(json.dumps(dict(connection_status='disconnected',metadata_revision=10)),))
    assert service.run(auth(write=False),x.snapshot['version_id'],g['graph_id'],dict(ticket_node_id=ticket(g)['node_id']))['status']=='requires_review'
    g['records'][0]['fields'][0]['native_token']='invalid';g['records'][0]['record_sha256']=sha256(canonical(g['records'][0]['fields']).encode()).hexdigest()
    with pytest.raises(ApiFailure):report(x,g)
