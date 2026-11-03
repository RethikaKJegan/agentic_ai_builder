"""Business foundation isolation and API contracts; no company/model calls."""
from copy import deepcopy
import json
import pytest
from workflow_api.business_ontology import BusinessOntology
from workflow_api.data_sources import DataSources
from workflow_api.storage import WorkflowStore
from workflow_api.service import ApiFailure
from tests.test_data_relationships import auth as base_auth


def auth(**kwargs):
    return {**base_auth(**kwargs), 'scopes':['workspace:read','workspace:write']}


@pytest.fixture
def foundation(tmp_path):
    manager = DataSources(WorkflowStore(tmp_path/'business.sqlite'), {})
    with manager.store.transaction() as db:
        for cid in ['service','quality','other']:
            doc = dict(connection_id=cid,name=cid,engine='mongodb',connection_status='connected',metadata_revision=1)
            db.execute('INSERT INTO data_source_connections VALUES (?,?,?,?,?)',(cid,'one','alice','private-encrypted-value',json.dumps(doc)))
    return BusinessOntology(manager.store), manager


def initialize(f):
    return f.initialize(auth(), {'sources':{'service':'service','quality':'quality'}})


def test_read_does_not_initialize_and_returns_catalogue(foundation):
    f,_ = foundation
    result=f.get(auth())
    assert result['workspace'] is None and result['versions']==[]
    assert len(result['layers'])==5 and len(result['modules'])==12
    assert result['counts']==dict(concepts=0,relationships=0,rules=0)
    assert 'private-encrypted-value' not in json.dumps(result)
    with f.store.transaction(write=False) as db:
        assert db.execute('SELECT COUNT(*) FROM business_ontology_workspaces').fetchone()[0]==0


def test_persistence_idempotence_and_immutable_snapshot(foundation):
    f,_ = foundation
    first=initialize(f)
    assert initialize(f)==first
    restarted=BusinessOntology(f.store)
    assert restarted.get(auth())==first
    version=first['versions'][0]['version_id']
    saved=restarted.version(auth(),version)
    assert saved['workspace']==first['workspace'] and saved['concepts']==[]
    saved['layers'].clear()
    assert len(restarted.version(auth(),version)['layers'])==5
    with f.store.transaction(write=False) as db:
        assert db.execute('SELECT COUNT(*) FROM business_ontology_versions').fetchone()[0]==1
        assert db.execute('SELECT COUNT(*) FROM business_ontology_events').fetchone()[0]==1
    with pytest.raises(ApiFailure) as exc:
        f.initialize(auth(), {'sources':{'service':'other','quality':'quality'}})
    assert exc.value.status==409


def test_owner_workspace_permission_scope_and_version_isolation(foundation):
    f,_=foundation
    version=initialize(f)['versions'][0]['version_id']
    for other in [auth(owner='bob'),auth(workspace='two')]:
        assert f.get(other)['workspace'] is None
        assert f.get(other)['available_sources']==[]
        with pytest.raises(ApiFailure):f.version(other,version)
        with pytest.raises(ApiFailure):f.initialize(other,{'sources':{'service':'service','quality':'quality'}})
    with pytest.raises(ApiFailure):f.initialize(auth(write=False),{'sources':{'service':'service','quality':'quality'}})
    for bad in [{**auth(),'decision':'deny'},{**auth(),'permissions':[]},{**auth(),'scopes':[]}]:
        with pytest.raises(ApiFailure):f.get(bad)


@pytest.mark.parametrize('body',[None,{}, {'sources':{}}, {'sources':{'service':'service','quality':'service'}}, {'sources':{'service':[], 'quality':'quality'}}, {'sources':{'service':'service','quality':'quality'},'namespace':'injected'}, {'sources':{'service':'service','quality':'quality','extra':'other'}}])
def test_payloads_fail_before_writes(foundation,body):
    f,_=foundation
    with pytest.raises(ApiFailure):f.initialize(auth(),body)
    assert f.get(auth())['workspace'] is None


def test_disconnect_and_metadata_changes_are_explicit(foundation):
    f,_=foundation
    initialize(f)
    with f.store.transaction() as db:
        raw=db.execute('SELECT document FROM data_source_connections WHERE connection_id=?',('quality',)).fetchone()[0]
        doc=json.loads(raw);doc['metadata_revision']=2
        db.execute('UPDATE data_source_connections SET document=? WHERE connection_id=?',(json.dumps(doc),'quality'))
    assert next(s for s in f.get(auth())['source_bindings'] if s['role']=='quality')['status']=='metadata_changed'
    with f.store.transaction() as db:
        doc['connection_status']='disconnected'
        db.execute('UPDATE data_source_connections SET document=? WHERE connection_id=?',(json.dumps(doc),'quality'))
    assert next(s for s in f.get(auth())['source_bindings'] if s['role']=='quality')['status']=='unavailable'
    with pytest.raises(ApiFailure):initialize(f)


def test_legacy_ontology_and_connection_documents_unchanged(foundation):
    f,manager=foundation
    with f.store.transaction() as db:
        db.execute('INSERT INTO ontology_records VALUES (?,?,?,?)',('one','alice','historic','{"audit":"preserved"}'))
        legacy=db.execute('SELECT * FROM ontology_records').fetchall()
        before=db.execute('SELECT * FROM data_source_connections ORDER BY connection_id').fetchall()
    initialize(f)
    with f.store.transaction(write=False) as db:
        assert db.execute('SELECT * FROM ontology_records').fetchall()==legacy
        assert db.execute('SELECT * FROM data_source_connections ORDER BY connection_id').fetchall()==before


def test_api_session_origin_validation_and_snapshot(tmp_path):
    from fastapi.testclient import TestClient
    from workflow_api.main import create_app
    app=create_app(database=tmp_path/'api.sqlite',dev_auth=True,start_workers=False)
    client=TestClient(app)
    assert client.get('/business-ontology/v1').status_code==401
    client.get('/session')
    client.cookies.set('builder_dev_session',client.cookies.get('builder_dev_session'),path='/')
    assert client.get('/business-ontology/v1').json()['data']['workspace'] is None
    assert client.post('/business-ontology/v1/initialize',json={},headers={'origin':'https://untrusted.example'}).status_code==403
    assert client.post('/business-ontology/v1/initialize',content='not-json').status_code==422
    manager=app.state.data_sources
    with manager.store.transaction() as db:
        for cid in ['a','b']:
            doc=dict(connection_id=cid,name=cid,engine='mongodb',connection_status='connected',metadata_revision=1)
            db.execute('INSERT INTO data_source_connections VALUES (?,?,?,?,?)',(cid,'local-workspace','local-builder','private',json.dumps(doc)))
    response=client.post('/business-ontology/v1/initialize',json={'sources':{'service':'a','quality':'b'}})
    assert response.status_code==200
    data=response.json()['data']
    assert data['workspace']['revision']==1
    assert response.headers['cache-control']=='no-store'
    version=data['versions'][0]['version_id']
    assert client.get('/business-ontology/v1/versions/'+version).json()['data']['kind']=='foundation'
    assert client.get('/business-ontology/v1/versions/missing').status_code==404
