"""Bounded explicit source graphs with independent identities and no policy engine."""
from copy import deepcopy
import json
from types import SimpleNamespace
from cryptography.fernet import Fernet
import pytest
from tests.test_business_compiler import compiled_draft
from tests.test_business_generation import generation
from tests.test_business_ontology import foundation,auth
from workflow_api.business_graph import BusinessGraph,specs
from workflow_api.service import ApiFailure

class Reader:
    def __init__(self):self.calls=[];self.hook=None;self.rows={
        'enginedetails':[dict(_id='invoice1',engineSerialNumber='SER-1',engineModel='M',listNo='L',oem='o1')],
        'tickets':[dict(_id='ticket1',engineNo='SER-1',oem='o1',oemOrg='org1',hmr=12)],
        'claims':[dict(_id='claim1',engineSerialNumber='SER-1',hoursCovered='12')],
        'claimsftps':[dict(_id='sap1',engineSerialNumber='SER-1')],
        'failedengineanalyses':[dict(_id='qa1',engineSerialNumber='SER-1',listNo='L',engineModel='M',oem='o1')],
        'jointinspectionreports':[dict(_id='jir1',ticketId='ticket1')],
        'enginereplacements':[dict(_id='replace1',ticket='ticket1')],
        'oems':[dict(_id='o1')],'oemnames':[dict(_id='org1')],
        'internalcutins':[dict(_id='cutin1',listNo='L',engineModel='M',oem='o1')],
        'icacapas':[dict(_id='capa1',listNo='L',engineModel='M',oem='o1')],
    }
    def read(self,config,collection,fields,query,deadline):
        self.calls.append(dict(collection=collection,fields=fields,query=query,database=config['database']))
        if self.hook:self.hook()
        # Match any member of the safe $in domain, not arbitrary operators.
        rows=[{k:v for k,v in row.items() if k in fields} for row in self.rows.get(collection,[]) if all(any(type(row.get(f)) is type(v) and row.get(f)==v for v in clause['$in']) for f,clause in query.items())]
        return deepcopy(rows[:21])

@pytest.fixture
def graph(compiled_draft,tmp_path):
    f,compiler,snapshot=compiled_draft
    from workflow_api.data_sources import DataSources
    key=tmp_path/'key';key.write_bytes(Fernet.generate_key());manager=DataSources(f.store,{'BUILDER_DATA_SOURCE_KEY_FILE':str(key)})
    with f.store.transaction() as db:
        for cid,role in [('service','service'),('quality','quality')]:
            secret=manager.cipher.encrypt(json.dumps(dict(engine='mongodb',database=cid)).encode()).decode()
            db.execute('UPDATE data_source_connections SET secret=? WHERE connection_id=?',(secret,cid))
            datasets=[]
            for spec in specs():
                if spec['role']!=role:continue
                fields=[dict(name=name,types=['integer'] if name=='hmr' else ['string']) for name in spec['fields']]
                datasets.append(dict(name=spec['collection'],fields=fields))
            db.execute('INSERT INTO data_source_snapshots VALUES (?,?,?)',(cid,1,json.dumps(dict(datasets=datasets))))
    compiler.compile(auth(),snapshot['version_id'],{})
    reader=Reader();current=auth();service=BusinessGraph(f,compiler,manager,lambda *args:current,reader)
    return SimpleNamespace(f=f,service=service,snapshot=snapshot,reader=reader,current=current,manager=manager)

def request(x,**changes):
    return dict(plan_hash=x.service.plan(auth(),x.snapshot['version_id'])['plan_hash'],serial='SER-1',request_key='graph_request_001',bindings={'enginedetails':{'concept_id':'warranty:engine','attributes':{}},'tickets':{'concept_id':'warranty:engine','attributes':{'hours':'hmr'}}},**changes)

def build(x,body=None):return x.service.build(auth(),x.snapshot['version_id'],body or request(x))

def test_safe_two_source_graph_preserves_identity_provenance_and_limits(graph):
    x=graph;plan=x.service.plan(auth(),x.snapshot['version_id']);assert len(plan['mappings'])==21 and not x.reader.calls
    result=build(x)
    assert {c['database'] for c in x.reader.calls}=={'service','quality'}
    assert len({r['node_id'] for r in result['records']})==len(result['records'])
    assert any(e['classification']=='candidate' and e['predicate']=='candidate_serial_match' for e in result['edges'])
    assert any(e['classification']=='source_reference' for e in result['edges'])
    assert result['monitoring']['status']=='unavailable' and result['physical_engine_identity']=='unresolved' and result['warranty_evaluation']=='not_run'
    assert result['validation']['status']=='failed' # invoice has no mapped required hours
    assert result['validation']['issues'] and result['validation']['mapped_records']==2
    assert not {'password','photos','attachments'} & {f for c in x.reader.calls for f in c['fields']}
    assert x.service.get(auth(write=False),x.snapshot['version_id'],result['graph_id'])==result


def test_graph_idempotency_and_scoped_snapshots(graph):
    x=graph;body=request(x);first=build(x,body);calls=len(x.reader.calls)
    assert build(x,body)==first and len(x.reader.calls)==calls
    assert x.service.plan(auth(),x.snapshot['version_id'])['snapshots'][0]['graph_id']==first['graph_id']
    with pytest.raises(ApiFailure):build(x,{**body,'serial':'OTHER'})
    for foreign in (auth(owner='bob'),auth(workspace='two')):
        with pytest.raises(ApiFailure):x.service.get(foreign,x.snapshot['version_id'],first['graph_id'])
    with pytest.raises(ApiFailure):x.service.build(auth(write=False),x.snapshot['version_id'],body)
    assert len(x.reader.calls)==calls

@pytest.mark.parametrize('change',['metadata','secret','authority'])
def test_late_drift_or_revocation_never_commits(graph,change):
    x=graph;body=request(x)
    def hook():
        x.reader.hook=None
        if change=='authority':x.current['decision']='deny'
        else:
            with x.f.store.transaction() as db:
                if change=='secret':db.execute("UPDATE data_source_connections SET secret='changed' WHERE connection_id='quality'")
                else:
                    raw=db.execute("SELECT document FROM data_source_connections WHERE connection_id='quality'").fetchone()[0];doc=json.loads(raw);doc['generation']=2
                    db.execute("UPDATE data_source_connections SET document=? WHERE connection_id='quality'",(json.dumps(doc),))
    x.reader.hook=hook
    with pytest.raises(ApiFailure):build(x,body)
    with x.f.store.transaction(write=False) as db:assert db.execute('SELECT COUNT(*) FROM business_ontology_graphs').fetchone()[0]==0


def test_wrong_reference_type_and_scope_remain_unresolved(graph):
    x=graph;x.reader.rows['enginereplacements'][0]['ticket']=999
    x.reader.rows['internalcutins'][0]['oem']='different'
    result=build(x)
    assert any(u['state']=='scope_not_established' for u in result['unresolved'])
    # A non-matching reference is not retrieved by a typed exact domain query.
    assert not any(r['collection']=='enginereplacements' for r in result['records'])
    assert next(o for o in result['outcomes'] if o['collection']=='enginereplacements')['status']=='no_matches'


def test_truncation_is_explicit_not_population_count(graph):
    x=graph;x.reader.rows['claims']=[dict(_id='claim'+str(i),engineSerialNumber='SER-1') for i in range(25)]
    result=build(x)
    outcome=next(o for o in result['outcomes'] if o['collection']=='claims')
    assert outcome['truncated'] and outcome['records']==20
    assert sum(r['collection']=='claims' for r in result['records'])==20

@pytest.mark.parametrize('change',[
 {'serial':{'$ne':''}},{'serial':' bad '},{'bindings':{}},{'bindings':{'tickets':{'concept_id':'foreign','attributes':{}}}},
 {'bindings':{'tickets':{'concept_id':'warranty:engine','attributes':{'hours':'password'}}}}, {'plan_hash':'stale'}, {'request_key':'bad'},
])
def test_invalid_mappings_never_read_sources(graph,change):
    x=graph;body={**request(x),**change}
    with pytest.raises(ApiFailure):build(x,body)
    assert not x.reader.calls


def test_conversion_errors_and_secret_values_are_not_silently_mapped(graph):
    x=graph;x.reader.rows['tickets'][0]['hmr']='not a number';result=build(x)
    assert result['validation']['conversion_issues']
    x.reader.rows['tickets'][0]['hmr']='password=private-test-value'
    with pytest.raises(Exception):build(x,{**request(x),'request_key':'graph_request_002'})
    assert len(x.service.plan(auth(),x.snapshot['version_id'])['snapshots'])==1


def test_graph_http_plan_and_foreign_snapshot(tmp_path):
    from fastapi.testclient import TestClient
    from workflow_api.main import create_app
    app=create_app(database=tmp_path/'graph_http.sqlite',dev_auth=True,start_workers=False,planning_worker_enabled=False)
    client=TestClient(app);client.get('/session');client.cookies.set('builder_dev_session',client.cookies.get('builder_dev_session'),path='/')
    with app.state.workflow_service.store.transaction() as db:
        for cid in ('service','quality'):
            doc=dict(connection_id=cid,name=cid,engine='mongodb',connection_status='connected',metadata_revision=1)
            db.execute('INSERT INTO data_source_connections VALUES (?,?,?,?,?)',(cid,'local-workspace','local-builder',None,json.dumps(doc)))
    response=client.post('/business-ontology/v1/initialize',json={'sources':{'service':'service','quality':'quality'}})
    version=response.json()['data']['versions'][0]['version_id'];root='/business-ontology/v1/versions/'+version
    plan=client.get(root+'/graph-plan');assert plan.status_code==200 and plan.headers['cache-control']=='no-store'
    assert len(plan.json()['data']['mappings'])==21 and not plan.json()['data']['available']
    assert client.post(root+'/graphs',json={'serial':{'$ne':''}}).status_code==422
    assert client.get(root+'/graphs/foreign').status_code==404
    app.state.workflow_auth['subject']['subject_id']='other'
    assert client.get(root+'/graph-plan').status_code==404


def test_equal_native_keys_in_different_sources_are_not_merged(graph):
    x=graph;x.reader.rows['claims'][0]['_id']='invoice1'
    result=build(x);nodes=[r for r in result['records'] if r['key']['_id']=='invoice1']
    assert len(nodes)==2 and len({r['node_id'] for r in nodes})==2
    assert {r['role'] for r in nodes}=={'service','quality'}
    assert any(e['classification']=='candidate' for e in result['edges'])


def test_native_reference_types_are_not_coerced_into_direct_links(graph):
    from bson import ObjectId
    x=graph;key='000000000000000000000001';x.reader.rows['tickets'][0]['oem']=key;x.reader.rows['oems'][0]['_id']=ObjectId(key)
    result=build(x);ticket=next(r for r in result['records'] if r['collection']=='tickets')
    assert any(u['node_id']==ticket['node_id'] and u['field']=='oem' for u in result['unresolved'])


def test_source_failure_does_not_save_partial_graph(graph):
    x=graph
    def error():raise RuntimeError('private-source-driver-message')
    x.reader.hook=error
    with pytest.raises(ApiFailure) as exc:build(x)
    assert exc.value.code=='BUSINESS_GRAPH_SOURCE_FAILED' and 'private-source' not in str(exc.value)
    with x.f.store.transaction(write=False) as db:assert db.execute('SELECT COUNT(*) FROM business_ontology_graphs').fetchone()[0]==0



def test_independent_builders_commit_one_idempotent_snapshot(graph):
    x=graph;body=request(x);completed=[]
    def overlap():
        x.reader.hook=None
        other=BusinessGraph(x.f,x.service.compiler,x.manager,x.service.resolve,x.reader)
        completed.append(other.build(auth(),x.snapshot['version_id'],body))
    x.reader.hook=overlap
    result=build(x,body)
    assert result==completed[0]
    with x.f.store.transaction(write=False) as db:
        assert db.execute('SELECT COUNT(*) FROM business_ontology_graphs').fetchone()[0]==1
        events=[json.loads(r[0]) for r in db.execute('SELECT document FROM business_ontology_events')]
        assert sum(e['action']=='build_source_graph' for e in events)==1
