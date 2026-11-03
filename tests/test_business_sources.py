"""Replacement lifecycle tests; synthetic data only, no model or cloud calls."""
from copy import deepcopy
import json
import pytest
from tests.test_data_sources import manager,config
from tests.test_business_ontology import auth
from workflow_api.business_ontology import BusinessOntology
from workflow_api.business_sources import BusinessSources
from workflow_api.source_evidence import SourceEvidence
from workflow_api.service import ApiFailure


class Reader:
    def __init__(self):self.calls=[];self.hook=None
    def objects(self,config,dataset,fields,keys,filters,offset,limit,deadline):
        self.calls.append((config,dataset,fields,offset,limit))
        if self.hook:self.hook()
        return [{'_id':str(i),'engineNo':'SYNTHETIC','password':'must never escape'} for i in range(offset,offset+limit)]


@pytest.fixture
def sources(manager):
    ids={}
    for role,name in [('service','tickets'),('quality','claims')]:
        body=config();body['database']=role;body['uri']=body['uri'].replace('workshop',role)
        cid=manager.connect(auth(),body)['connection_id'];manager.tick();ids[role]=cid
        with manager.store.transaction() as db:
            snapshot=json.loads(db.execute('SELECT document FROM data_source_snapshots WHERE connection_id=? AND revision=1',(cid,)).fetchone()[0])
            d=snapshot['datasets'][0];d['name']=name
            d['fields']=[dict(field_id=name+'_'+f,name=f,types=['string'],discovery_method='sampled') for f in ('_id','engineNo','password')]
            db.execute('UPDATE data_source_snapshots SET document=? WHERE connection_id=? AND revision=1',(json.dumps(snapshot),cid))
    ontology=BusinessOntology(manager.store);ontology.initialize(auth(),{'sources':ids})
    reader=Reader();service=BusinessSources(ontology,manager,reader)
    return service,manager,reader,ids


def request(service):
    s=service.get(auth())['sources'][0]
    return dict(connection_id=s['connection_id'],dataset_id=s['datasets'][0]['dataset_id'],metadata_revision=s['metadata_revision'],generation=s['generation'],offset=0,limit=2)


def test_both_sources_metadata_and_no_implicit_record_reads(sources):
    s,m,r,ids=sources;result=s.get(auth())
    assert {x['role'] for x in result['sources']}=={'service','quality'}
    assert not r.calls and result['model_calls']==0
    assert all(x['status']=='current' for x in result['sources'])
    assert 'password' not in json.dumps(result) and 'private-value' not in json.dumps(result)
    assert all(x['datasets'][0]['module_ids'] for x in result['sources'])


def test_changed_field_types_and_module_impacts_are_evidence_not_policy(sources):
    s,m,r,ids=sources;cid=ids['service']
    with m.store.transaction() as db:
        old=json.loads(db.execute('SELECT document FROM data_source_snapshots WHERE connection_id=? AND revision=1',(cid,)).fetchone()[0]);new=deepcopy(old)
        new['revision']=2;new['datasets'][0]['fields'][1]['types']=['number']
        db.execute('INSERT INTO data_source_snapshots VALUES (?,?,?)',(cid,2,json.dumps(new)))
        doc=json.loads(db.execute('SELECT document FROM data_source_connections WHERE connection_id=?',(cid,)).fetchone()[0]);doc['metadata_revision']=2
        db.execute('UPDATE data_source_connections SET document=? WHERE connection_id=?',(json.dumps(doc),cid))
    source=next(x for x in s.get(auth())['sources'] if x['role']=='service')
    assert source['status']=='metadata_changed' and source['changes'][0]['type_changes'][0]['current_types']==['number']
    assert 'complaints' in source['impacts']['modules'] and 'warranty' in source['impacts']['modules']
    assert s.ontology.get(auth())['workspace']['source_revisions']['service']==1


def test_bounded_records_projection_pagination_and_provenance(sources):
    s,m,r,ids=sources;body=request(s);result=s.records(auth(),body)
    assert len(result['records'])==2 and result['next_offset']==2 and result['has_more']
    assert result['source']['dataset_id']==body['dataset_id'] and result['model_calls']==0
    assert 'password' not in json.dumps(result)
    assert r.calls[0][-1]==3
    body['offset']=2
    assert s.records(auth(),body)['records'][0]['_id']=='2'


@pytest.mark.parametrize('change',['generation','metadata_revision','disconnect','revoke'])
def test_authority_is_rechecked_after_io(sources,change):
    s,m,r,ids=sources;body=request(s)
    def hook():
        if change=='revoke':s.resolve=lambda *args:None;return
        with m.store.transaction() as db:
            doc=json.loads(db.execute('SELECT document FROM data_source_connections WHERE connection_id=?',(body['connection_id'],)).fetchone()[0])
            if change=='disconnect':doc['connection_status']='disconnected'
            else:doc[change]+=1
            db.execute('UPDATE data_source_connections SET document=? WHERE connection_id=?',(json.dumps(doc),body['connection_id']))
    r.hook=hook
    with pytest.raises(ApiFailure):s.records(auth(),body)
    assert len(r.calls)==1


def test_scope_stale_and_invalid_requests_do_not_read(sources):
    s,m,r,ids=sources;body=request(s)
    for other in (auth(owner='other'),auth(workspace='other'),{**auth(),'scopes':[]}):
        with pytest.raises(ApiFailure):s.records(other,body)
    for bad in ({**body,'limit':26},{**body,'offset':-1},{**body,'generation':-1},{**body,'dataset_id':'invented'},{**body,'sql':'select *'}):
        with pytest.raises(ApiFailure):s.records(auth(),bad)
    assert not r.calls


def test_profile_jobs_are_owned_explicit_and_coalesced(sources):
    s,m,r,ids=sources
    with pytest.raises(ApiFailure):s.profile(auth(write=False),ids['service'])
    job=s.profile(auth(),ids['service']);assert job['status']=='queued'
    with m.store.transaction(write=False) as db:assert db.execute('SELECT 1 FROM source_profile_requests WHERE job_id=?',(job['job_id'],)).fetchone()
    with pytest.raises(ApiFailure):s.profile(auth(),ids['service'])
    assert not r.calls


def test_provenance_migration_does_not_overwrite_or_remove_history(sources):
    s,m,r,ids=sources
    with m.store.transaction() as db:
        db.execute('INSERT INTO ontology_source_observations VALUES (?,?)',(ids['service'],'{"legacy":true}'))
    s.evidence.import_profile_evidence();s.evidence.import_profile_evidence()
    with m.store.transaction(write=False) as db:
        assert db.execute('SELECT document FROM source_observations WHERE connection_id=?',(ids['service'],)).fetchone()[0]=='{"legacy":true}'
        assert db.execute('SELECT document FROM ontology_source_observations WHERE connection_id=?',(ids['service'],)).fetchone()


def test_replacement_routes_are_authenticated_and_owned(tmp_path):
    from fastapi.testclient import TestClient
    from workflow_api.main import create_app
    app=create_app(database=tmp_path/'api.sqlite',dev_auth=True,start_workers=False,planning_worker_enabled=False)
    with TestClient(app) as client:
        assert client.get('/business-ontology/v1/sources').status_code==401
        client.get('/session');client.cookies.set('builder_dev_session',client.cookies.get('builder_dev_session'),path='/')
        result=client.get('/business-ontology/v1/sources')
        assert result.status_code==200 and result.json()['data']['sources']==[]
        assert client.post('/business-ontology/v1/source-records',json={}).status_code==422
        assert client.post('/business-ontology/v1/sources/invented/profile',json={}).status_code==404


def test_profile_button_completes_through_existing_worker_and_exposes_statistics(sources):
    s,m,r,ids=sources;cid=ids['service']
    with m.store.transaction(write=False) as db:
        snapshot=json.loads(db.execute('SELECT document FROM data_source_snapshots WHERE connection_id=? AND revision=1',(cid,)).fetchone()[0])
    def profile(config,connection_id):
        assert config['_ontology_profile'] is True and connection_id==cid
        from workflow_api.data_profiles import summarize
        result=deepcopy(snapshot);d=result['datasets'][0]
        result['ontology_profiles']={d['dataset_id']:dict(fields=summarize([{'_id':'1','engineNo':'E1'},{'_id':'2','engineNo':None}],d['fields']),basis='bounded_sample',rows=2)}
        return result
    m.adapter.profile=profile
    job=s.profile(auth(),cid)
    assert m.tick()
    with m.store.transaction(write=False) as db:
        assert db.execute('SELECT state FROM data_source_profile_jobs WHERE job_id=?',(job['job_id'],)).fetchone()[0]=='succeeded'
    source=next(x for x in s.get(auth())['sources'] if x['connection_id']==cid)
    assert source['profile']['current'] and source['datasets'][0]['profile_rows']==2
    assert source['metadata_revision']==1 and source['status']=='current'
    assert source['datasets'][0]['statistics']['engineNo']['nulls']==1
    assert 'key_hashes' not in json.dumps(source) and 'password' not in json.dumps(source)
