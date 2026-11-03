"""Saved monitoring observations never become recurrence or population facts."""
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
from workflow_api.business_monitoring import report,BusinessMonitoring
from workflow_api.service import ApiFailure


def request(**changes):return {**dict(change_node_id=None,period_start='2026-01-01',period_end='2026-12-31',limit=50,offset=0),**changes}


def test_qualified_observations_are_not_failures_or_exposure(graph):
    x=graph;x.reader.rows['claims'][0].update(dateOfFailure='2026-01-01',status='POST_CUT_IN',hoursCovered='0')
    x.reader.rows['claimsftps'][0].update(failureDate='2026-12-31T23:00:00-12:00',status='APPROVED')
    x.reader.rows['jointinspectionreports'][0].update(dateOfFailure='not-a-date',potentialCause='possible gasket issue')
    g=build(x);before=deepcopy(g);calls=len(x.reader.calls);change=next(r['node_id'] for r in g['records'] if r['collection']=='internalcutins')
    with patch('socket.create_connection',side_effect=AssertionError('No network')):result=BusinessMonitoring(x.f,x.service).run(auth(write=False),x.snapshot['version_id'],g['graph_id'],request(change_node_id=change))
    assert result['status']=='requires_evidence' and all(v is None for v in result['metrics'].values())
    assert result['summary']['failure_date_observations']==dict(before_period=0,within_period=2,after_period=0,invalid_date=1,unavailable=0)
    rows=[];offset=0
    while True:
        page=report(x.snapshot,g,request(change_node_id=change,offset=offset));rows+=page['rows']
        if not page['has_more']:break
        offset=page['next_offset']
    assert next(r for r in rows if r['collection']=='claims' and r['field']=='hoursCovered')['normalized']=='0'
    assert next(r for r in rows if r['field']=='potentialCause')['value']=='possible gasket issue'
    assert next(p for p in result['prerequisites'] if p['prerequisite_id']=='exposure')['status']=='unavailable'
    assert {r['role'] for r in rows}=={'service','quality'} and all(r['record_sha256'] for r in rows)
    assert len(x.reader.calls)==calls and g==before and result['company_queries']==result['model_calls']==result['source_writes']==0
    assert result==report(x.snapshot,g,request(change_node_id=change))


@pytest.mark.parametrize('value,bucket',[('2025-12-31','before_period'),('2027-01-01','after_period'),('2026-01-01','within_period'),('2026-12-31','within_period'),('2026-02-30','invalid_date'),('2026-01-01T12:00:00','within_period'),(None,'unavailable'),(123,'invalid_date')])
def test_calendar_windows_preserve_invalid_missing_and_precision(graph,value,bucket):
    x=graph;x.reader.rows['claims'][0]['dateOfFailure']=value;g=build(x)
    result=report(x.snapshot,g,request());assert result['summary']['failure_date_observations'][bucket]>=1
    assert all(v is None for v in result['metrics'].values())


@pytest.mark.parametrize('change',[{'period_start':'2026-02-30'},{'period_end':'2025-01-01'},{'period_start':'20260101'},{'period_end':'2026-01-01T00:00:00Z'},{'limit':True},{'limit':51},{'offset':-1},{'offset':20001},{'change_node_id':'foreign'},{'incorporated':True},{'population':100}])
def test_invalid_requests_and_overrides(graph,change):
    g=build(graph)
    with pytest.raises(ApiFailure):report(graph.snapshot,g,{**request(),**change})


def test_pages_empty_and_full_looking_snapshot_cannot_yield_zero_rates(graph):
    x=graph;g=build(x);first=report(x.snapshot,g,{**request(),'limit':3});second=report(x.snapshot,g,{**request(),'limit':3,'offset':3})
    assert first['has_more'] and first['rows']+second['rows']==report(x.snapshot,g,request())['rows'][:6]
    full=deepcopy(g)
    for item in full['outcomes']:item.update(status='matched',truncated=False)
    assert next(p for p in report(x.snapshot,full,request())['prerequisites'] if p['prerequisite_id']=='source_coverage')['status']=='observed_unverified'
    g['records']=[];g['edges']=[];empty=report(x.snapshot,g,request())
    assert empty['total_rows']==0 and empty['summary']['failure_date_observations']['within_period']==0 and empty['metrics']['failure_rate'] is None
    assert 'not zero failures' in ' '.join(empty['limits'])


def test_integrity_scope_historical_and_no_mutation(graph):
    x=graph;g=build(x);service=BusinessMonitoring(x.f,x.service)
    for who in [auth(owner='other'),auth(workspace='other')]:
        with pytest.raises(ApiFailure):service.run(who,x.snapshot['version_id'],g['graph_id'],request())
    bad=deepcopy(g);bad['records'][0]['fields'][0]['value']='tampered'
    with pytest.raises(ApiFailure):report(x.snapshot,bad,request())
    ticket=next(r['node_id'] for r in g['records'] if r['collection']=='tickets')
    with pytest.raises(ApiFailure):report(x.snapshot,g,request(change_node_id=ticket))
    with x.f.store.transaction() as db:db.execute("UPDATE data_source_connections SET document=? WHERE connection_id='quality'",(json.dumps(dict(connection_status='disconnected',metadata_revision=10)),))
    with x.f.store.transaction(write=False) as db:before={name:db.execute('SELECT * FROM '+name).fetchall() for name in ['business_ontology_versions','business_ontology_graphs','business_ontology_events','data_source_connections']}
    assert service.run(auth(write=False),x.snapshot['version_id'],g['graph_id'],request())['provenance']['graph_sha256']==sha256(canonical(g).encode()).hexdigest()
    with x.f.store.transaction(write=False) as db:assert all(db.execute('SELECT * FROM '+name).fetchall()==rows for name,rows in before.items())


def test_monitoring_http_transport(tmp_path,graph):
    from fastapi.testclient import TestClient
    from workflow_api.main import create_app
    x=graph;g=build(x);app=create_app(database=tmp_path/'monitoring.sqlite',dev_auth=True,start_workers=False,planning_worker_enabled=False)
    client=TestClient(app);root='/business-ontology/v1';path=root+'/versions/x/graphs/x/monitoring-readiness'
    assert client.post(path,json=request()).status_code==401
    client.get('/session');client.cookies.set('builder_dev_session',client.cookies.get('builder_dev_session'),path='/')
    with app.state.workflow_service.store.transaction() as db:
        for cid in ('service','quality'):
            doc=dict(connection_id=cid,name=cid,engine='mongodb',connection_status='connected',metadata_revision=1)
            db.execute('INSERT INTO data_source_connections VALUES (?,?,?,?,?)',(cid,'local-workspace','local-builder',None,json.dumps(doc)))
    version=client.post(root+'/initialize',json={'sources':{'service':'service','quality':'quality'}}).json()['data']['current_version_id'];g['version_id']=version
    with app.state.workflow_service.store.transaction() as db:db.execute('INSERT INTO business_ontology_graphs VALUES (?,?,?,?,?,?,?)',('local-workspace','local-builder',version,g['graph_id'],'monitor_http_graph','fixture',json.dumps(g)))
    path=root+'/versions/'+version+'/graphs/'+g['graph_id']+'/monitoring-readiness'
    with app.state.workflow_service.store.transaction(write=False) as db:before=db.execute('SELECT * FROM business_ontology_events').fetchall()
    with patch('socket.create_connection',side_effect=AssertionError('No network')):response=client.post(path,json=request())
    assert response.status_code==200 and response.headers['cache-control']=='no-store' and response.json()['data']['metrics']['failure_rate'] is None
    change=next(r['node_id'] for r in g['records'] if r['collection']=='internalcutins')
    selected=client.post(path,json=request(change_node_id=change))
    assert selected.status_code==200 and selected.json()['data']['change_node_id']==change
    assert client.post(path,json=request(),headers={'origin':'https://untrusted.example'}).status_code==403
    assert client.post(path,content='bad-json').status_code==422
    assert client.post(path,json={**request(),'rate':0}).status_code==422
    with app.state.workflow_service.store.transaction(write=False) as db:assert db.execute('SELECT * FROM business_ontology_events').fetchall()==before
    app.state.workflow_auth['subject']['subject_id']='other';assert client.post(path,json=request()).status_code==404
