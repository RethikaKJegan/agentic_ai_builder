"""Warranty readiness retains evidence and never invents applicable policy."""
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
from workflow_api.business_warranty import BusinessWarranty,prepare,parse_hours,parse_date
from workflow_api.service import ApiFailure


def ticket_id(g):return next(r['node_id'] for r in g['records'] if r['collection']=='tickets')
def run(x,g):return prepare(x.snapshot,g,dict(ticket_node_id=ticket_id(g)))
def fields(result):return {i['field']:i for i in result['inputs']}
def codes(result):return {i['code'] for i in result['review_reasons']}
def set_field(g,collection,name,value):
    record=next(r for r in g['records'] if r['collection']==collection)
    cell=next((f for f in record['fields'] if f['name']==name),None)
    if cell:cell.update(value=value,state='value')
    else:record['fields'].append(dict(name=name,value=value,state='value'))
    record['record_sha256']=sha256(canonical(record['fields']).encode()).hexdigest()


@pytest.mark.parametrize('raw,expected',[(0,'0'),('0','0'),(' 0012.500 ','12.5'),(12.5,'12.5'),('0.000','0'),(-1,None),(True,None),(None,None),('NaN',None),('Infinity',None),('12 hrs',None),('1,200',None),('1e3',None),('1' *65,None),('',None),([],None),('１２',None),(float('inf'),None),(float('nan'),None)])
def test_hours(raw,expected):assert parse_hours(raw)==expected


@pytest.mark.parametrize('raw,expected',[
 ('2024-02-29','date'),('2025-02-29',None),('2026-01-01T12:30:00Z','datetime'),('2026-01-01T12:30:00+05:30','datetime'),('2026-01-01T12:30:00','local_datetime'),('01/02/2026',None),('2026-01-01T24:01:00',None),('2026-01-01T12:30',None),('2026-01-01T12:30:00+05:99',None),('2026-01-01garbage',None),(12,None),
])
def test_dates(raw,expected):
    result=parse_date(raw)
    assert (result['precision'] if result else None)==expected


def test_readiness_never_substitutes_alternate_hours_or_runs_network(graph):
    x=graph;g=build(x);original=deepcopy(g);calls=len(x.reader.calls)
    service=BusinessWarranty(x.f,x.service)
    with patch('socket.create_connection',side_effect=AssertionError('No network')):
        result=service.run(auth(write=False),x.snapshot['version_id'],g['graph_id'],dict(ticket_node_id=ticket_id(g)))
    assert fields(result)['complaintRecord.hmr']['state']=='not_returned'
    assert fields(result)['hmr']['normalized']=='12'
    assert result['status']=='requires_review' and result['eligibility']=='not_evaluated'
    assert result['assessment_timestamp'] is result['policy_version'] is result['selected_invoice_node_id'] is None
    assert result['company_queries']==result['model_calls']==0 and result['rules_executed'] is False
    assert len(x.reader.calls)==calls and g==original
    assert 'COMPLAINT_HOURS_UNUSABLE' in codes(result)
    assert {'POLICY_NOT_CONFIGURED','IDENTITY_UNRESOLVED','ASSESSMENT_TIME_UNSPECIFIED'}<=codes(result)
    assert result['provenance']['graph_sha256']==sha256(canonical(g).encode()).hexdigest()


def test_zero_complete_inputs_and_policy_label_cannot_make_eligibility(graph):
    x=graph;g=build(x)
    for collection,field,value in [('tickets','complaintRecord.hmr','0'),('tickets','hmr',0),('tickets','complaintRecord.dateOfSale','2026-01-01'),('enginedetails','invoiceDate','2025-12-01'),('enginedetails','oem','org1')]:set_field(g,collection,field,value)
    x.snapshot['sources'].append(dict(source_id='policy1',title='Owner supplied policy',sha256='policyhash',kind='policy',module_ids=['warranty'],text='A policy document is not a configured applicable policy.'))
    result=run(x,g)
    assert fields(result)['complaintRecord.hmr']['normalized']=='0'
    assert 'COMPLAINT_HOURS_UNUSABLE' not in codes(result) and 'HOUR_OBSERVATIONS_DIFFER' not in codes(result)
    assert result['policy_sources'][0]['authority']=='not_established'
    assert result['invoice_candidates'][0]['serial_comparison']=='exact_match'
    assert result['invoice_candidates'][0]['oem_comparison']=='exact_match'
    assert result['invoice_candidates'][0]['selected'] is False
    assert result['eligibility']=='not_evaluated' and 'POLICY_NOT_CONFIGURED' in codes(result)


def test_conflicts_multiplicity_type_mismatch_invalid_dates_and_truncation(graph):
    x=graph;g=build(x);set_field(g,'tickets','complaintRecord.hmr','13.5');set_field(g,'tickets','complaintRecord.dateOfSale','2026-02-30');set_field(g,'enginedetails','oem',999)
    other=deepcopy(next(r for r in g['records'] if r['collection']=='enginedetails'));other['node_id']='secondinvoice';g['records'].append(other)
    g['outcomes'][0]['truncated']=True
    result=run(x,g)
    assert {'MULTIPLE_INVOICE_CANDIDATES','HOUR_OBSERVATIONS_DIFFER','SALE_DATE_UNUSABLE','SOURCE_GRAPH_TRUNCATED','NO_EXACT_INVOICE_SCOPE','INVOICE_DATES_UNUSABLE'}<=codes(result)
    assert all(c['oem_comparison']=='different' and not c['selected'] for c in result['invoice_candidates'])
    assert fields(result)['complaintRecord.dateOfSale']['state']=='invalid_value'


def test_no_invoice_and_primary_null_are_explicit(graph):
    x=graph;x.reader.rows['enginedetails']=[];g=build(x)
    set_field(g,'tickets','complaintRecord.hmr',None)
    result=run(x,g)
    assert result['invoice_candidates']==[] and 'NO_SAVED_INVOICE' in codes(result)
    assert fields(result)['complaintRecord.hmr']['syntactically_usable'] is False


@pytest.mark.parametrize('body',[None,{},dict(ticket_node_id='foreign'),dict(ticket_node_id=True),dict(ticket_node_id=[]),dict(ticket_node_id='x',policy={}),dict(ticket_node_id='x',hmr=1)])
def test_invalid_inputs_and_non_ticket_nodes(graph,body):
    x=graph;g=build(x)
    with pytest.raises(ApiFailure) as exc:prepare(x.snapshot,g,body)
    assert exc.value.status==422
    with pytest.raises(ApiFailure):prepare(x.snapshot,g,dict(ticket_node_id=g['records'][0]['node_id'])) # first record is invoice


def test_scope_integrity_and_disconnected_historical_read(graph):
    x=graph;g=build(x);service=BusinessWarranty(x.f,x.service);body=dict(ticket_node_id=ticket_id(g))
    for foreign in [auth(owner='bob'),auth(workspace='two')]:
        with pytest.raises(ApiFailure):service.run(foreign,x.snapshot['version_id'],g['graph_id'],body)
    with x.f.store.transaction() as db:
        db.execute("UPDATE data_source_connections SET document=? WHERE connection_id='quality'",(json.dumps(dict(connection_status='disconnected',metadata_revision=10)),))
    assert service.run(auth(write=False),x.snapshot['version_id'],g['graph_id'],body)['status']=='requires_review'
    g['records'][0]['fields'][0]['value']='damaged'
    with pytest.raises(ApiFailure):prepare(x.snapshot,g,body)


def test_readiness_http_transport_and_no_store_writes(tmp_path,graph):
    from fastapi.testclient import TestClient
    from workflow_api.main import create_app
    app=create_app(database=tmp_path/'warranty_http.sqlite',dev_auth=True,start_workers=False,planning_worker_enabled=False)
    client=TestClient(app);root='/business-ontology/v1'
    assert client.post(root+'/versions/foreign/graphs/foreign/warranty-readiness',json={}).status_code==401
    client.get('/session');client.cookies.set('builder_dev_session',client.cookies.get('builder_dev_session'),path='/')
    with app.state.workflow_service.store.transaction() as db:
        for cid in ('service','quality'):
            doc=dict(connection_id=cid,name=cid,engine='mongodb',connection_status='connected',metadata_revision=1)
            db.execute('INSERT INTO data_source_connections VALUES (?,?,?,?,?)',(cid,'local-workspace','local-builder',None,json.dumps(doc)))
    state=client.post(root+'/initialize',json={'sources':{'service':'service','quality':'quality'}}).json()['data'];version=state['current_version_id']
    saved=deepcopy(build(graph));saved['version_id']=version
    with app.state.workflow_service.store.transaction() as db:
        db.execute('INSERT INTO business_ontology_graphs VALUES (?,?,?,?,?,?,?)',('local-workspace','local-builder',version,saved['graph_id'],'warranty_http_graph','fixture',json.dumps(saved)))
    endpoint=root+'/versions/'+version+'/graphs/'+saved['graph_id']+'/warranty-readiness';body=dict(ticket_node_id=ticket_id(saved))
    with app.state.workflow_service.store.transaction(write=False) as db:
        before={name:db.execute('SELECT * FROM '+name).fetchall() for name in ['business_ontology_workspaces','business_ontology_versions','business_ontology_graphs','business_ontology_events','data_source_connections']}
    with patch('socket.create_connection',side_effect=AssertionError('No external network')):
        response=client.post(endpoint,json=body)
    assert response.status_code==200 and response.headers['cache-control']=='no-store'
    assert response.json()['data']['status']=='requires_review'
    assert client.post(endpoint,json=body,headers={'origin':'https://untrusted.example'}).status_code==403
    assert client.post(endpoint,content='not-json').status_code==422
    assert client.post(endpoint,json={**body,'policy':{}}).status_code==422
    assert client.post(endpoint,json={'ticket_node_id':saved['records'][0]['node_id']}).status_code==422
    with app.state.workflow_service.store.transaction(write=False) as db:
        assert all(db.execute('SELECT * FROM '+name).fetchall()==rows for name,rows in before.items())
    app.state.workflow_auth['subject']['subject_id']='foreign'
    assert client.post(endpoint,json=body).status_code==404


def test_ticket_selection_does_not_mix_case_inputs(graph):
    x=graph;x.reader.rows['tickets'].append(dict(_id='ticket2',engineNo='SER-1',oem='other',hmr=999))
    g=build(x);tickets=[r for r in g['records'] if r['collection']=='tickets']
    reports=[prepare(x.snapshot,g,dict(ticket_node_id=t['node_id'])) for t in tickets]
    assert {fields(r)['hmr']['normalized'] for r in reports}=={'12','999'}
    assert all({i['node_id'] for i in r['inputs']}=={r['ticket_node_id']} for r in reports)


def test_invoice_company_is_not_compared_to_the_ticket_account(graph):
    x=graph;g=build(x);result=run(x,g)
    assert fields(result)['oem']['value']=='o1' and fields(result)['oemOrg']['value']=='org1'
    assert result['invoice_candidates'][0]['oem_comparison']=='different' # invoice o1 equals account, not company
    set_field(g,'enginedetails','oem','org1')
    assert run(x,g)['invoice_candidates'][0]['oem_comparison']=='exact_match'
