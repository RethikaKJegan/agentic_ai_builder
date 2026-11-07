"""Source-backed ontology browsing, using real projection code and isolated data."""
from contextlib import contextmanager
from copy import deepcopy
import json
from types import SimpleNamespace

from bson import ObjectId
from cryptography.fernet import Fernet
import pytest

from tests.test_data_relationships import auth, dataset
from tests.test_ontology_foundation import put, accept, published, concept
from workflow_api.data_queries import QueryReader
from workflow_api.data_sources import DataSources
from workflow_api.ontology_objects import OntologyObjects
from workflow_api.service import ApiFailure
from workflow_api.storage import WorkflowStore


class Cursor:
    def __init__(self, rows): self.rows=rows
    def sort(self, keys):
        self.rows.sort(key=lambda r:tuple(str(r[k]) for k,_ in keys));return self
    def skip(self,n):self.rows=self.rows[n:];return self
    def limit(self,n):self.rows=self.rows[:n];return self
    def batch_size(self,n):return self
    def max_time_ms(self,n):return self
    def __iter__(self):return iter(self.rows)
    def close(self):pass


class Cloud:
    def __init__(self):self.rows={};self.calls=[];self.after=None
    @contextmanager
    def connection(self, config):yield self
    def __getitem__(self,name):self.name=name;return self
    def find(self,filters,projection):
        self.calls.append((self.name,filters,projection))
        rows=[{k:v for k,v in r.items() if projection.get(k)==1} for r in deepcopy(self.rows[self.name])
              if all(type(r.get(k)) is type(v['$eq']) and r.get(k)==v['$eq'] for k,v in filters.items())]
        if self.after:self.after()
        return Cursor(rows)


@pytest.fixture
def explorer(tmp_path):
    key=tmp_path/'key';key.write_bytes(Fernet.generate_key());cloud=Cloud()
    manager=DataSources(WorkflowStore(tmp_path/'objects.db'),{'BUILDER_DATA_SOURCE_KEY_FILE':str(key)},cloud)
    datasets=[dataset('mongo','tickets',[('_id',['ObjectId']),('serial',['string']),('account',['ObjectId']),('status',['string']),('password',['string']),('notes',['object'])]),
              dataset('mongo','invoices',[('_id',['ObjectId']),('serial',['string']),('company',['string'])]),
              dataset('mongo','accounts',[('_id',['ObjectId']),('name',['string'])])]
    with manager.store.transaction() as db:
        c=dict(connection_id='mongo',name='Isolated source',engine='mongodb',connection_status='connected',metadata_revision=1,generation=1)
        db.execute('INSERT INTO data_source_connections VALUES (?,?,?,?,?)',('mongo','one','alice',manager.cipher.encrypt(json.dumps({'engine':'mongodb','database':'test'}).encode()).decode(),json.dumps(c)))
        db.execute('INSERT INTO data_source_snapshots VALUES (?,?,?)',('mongo',1,json.dumps(dict(revision=1,coverage='sampled',datasets=datasets))))
    f=manager.ontology_foundation
    for d in datasets:
        rid=d['name'];r=concept(rid);r['source_refs']=[d['dataset_id']];put(f,r);accept(f,rid)
        for field in d['fields']:
            r=concept(rid+':'+field['name']);r.update(kind='attribute',source_refs=[field['field_id']],properties=dict(source=rid,datatype='string'))
            put(f,r);accept(f,r['id'])
    def edge(rid,target,a,b,predicate,label):
        r=concept(rid);r.update(kind='relationship',label=label,source_refs=[a,b],properties=dict(source='tickets',target=target,predicate=predicate,field_pairs=[dict(source_field_id=a,target_field_id=b)]))
        put(f,r);accept(f,rid)
    edge('serial_link','invoices','mongo_tickets_serial','mongo_invoices_serial','has_candidate_serial_match','Candidate invoice association')
    edge('account_link','accounts','mongo_tickets_account','mongo_accounts__id','filed_under','Filed under account')
    version=published(f)
    ids=[ObjectId('00000000000000000000000'+str(i)) for i in range(1,7)]
    cloud.rows={'tickets':[dict(_id=ids[0],serial='DUP',account=ids[4],password='NEVER_RETURN',notes={'secret':'nested'}) ,dict(_id=ids[1],serial='MISSING',status=None)],
                'invoices':[dict(_id=ids[2],serial='DUP',company='A'),dict(_id=ids[3],serial='DUP',company='B')],
                'accounts':[dict(_id=ids[4],name='Account A')]}
    user=auth();user['scopes']=['workspace:read']
    objects=OntologyObjects(f,QueryReader(manager))
    return SimpleNamespace(service=objects,auth=user,version=version,cloud=cloud,foundation=f,ids=ids)


def request(x,**changes):return dict(version_id=x.version,concept_id='tickets',**changes)


def test_native_key_safe_projection_missing_states_and_pagination(explorer):
    x=explorer;r=x.service.run(x.auth,request(x,limit=1))
    assert r['objects'][0]['key']=={'_id':str(x.ids[0])} and r['next_cursor']
    assert {f['name']:f['state'] for f in r['objects'][0]['fields']}['status']=='not_returned'
    assert 'NEVER_RETURN' not in json.dumps(r) and not {'password','notes'}&set(x.cloud.calls[0][2])
    page=x.service.run(x.auth,request(x,limit=1,cursor=r['next_cursor']))
    assert page['objects'][0]['key']=={'_id':str(x.ids[1])} and page['next_cursor'] is None
    assert next(f for f in page['objects'][0]['fields'] if f['name']=='status')['state']=='not_recorded'
    detail=x.service.run(x.auth,request(x,key={'_id':str(x.ids[0])}))
    assert detail['objects'][0]['object_id']==r['objects'][0]['object_id']


def test_candidate_keeps_duplicate_serials_separate_and_reference_resolution(explorer):
    x=explorer;body=request(x,key={'_id':str(x.ids[0])},relationship_id='serial_link')
    r=x.service.run(x.auth,body,True)
    assert len(r['objects'])==2 and r['classification']=='candidate' and r['link_state']=='candidate'
    assert len({o['object_id'] for o in r['objects']})==2
    body['relationship_id']='account_link';r=x.service.run(x.auth,body,True)
    assert r['classification']=='source_reference' and r['link_state']=='resolved' and len(r['objects'])==1
    assert isinstance(x.cloud.calls[-1][1]['_id']['$eq'],ObjectId)
    x.cloud.rows['accounts']=[];assert x.service.run(x.auth,body,True)['link_state']=='not_found'
    body['key']={'_id':str(x.ids[1])};assert x.service.run(x.auth,body,True)['link_state']=='not_recorded'


@pytest.mark.parametrize('changes',[{'limit':True},{'limit':101},{'filter':{'password':'NEVER_RETURN'}},{'filter':{'serial':{'$ne':''}}},{'key':{'serial':'DUP'}},{'key':{'_id':{'$gt':''}}},{'concept_id':'not-owned'},{'cursor':'invalid'}])
def test_rejects_hostile_or_invalid_input(explorer,changes):
    x=explorer
    with pytest.raises(ApiFailure):x.service.run(x.auth,{**request(x),**changes})


def test_permissions_revocation_and_wrong_scope(explorer):
    x=explorer
    for user in ({**x.auth,'scopes':[]},{**x.auth,'permissions':[]},{**x.auth,'decision':'deny'}, {**x.auth,'subject':{'subject_id':'other','workspace_id':'one'}}):
        with pytest.raises(ApiFailure):x.service.run(user,request(x))
    assert not x.cloud.calls
    current=deepcopy(x.auth);x.service.resolve=lambda *args:current
    x.cloud.after=lambda:current.update(decision='deny')
    with pytest.raises(ApiFailure) as e:x.service.run(x.auth,request(x))
    assert e.value.status==403


def test_correction_and_schema_drift_reject_published_record_reads(explorer):
    x=explorer
    r=next(r for r in x.foundation.get(x.auth)['records'] if r['id']=='tickets')
    x.foundation.review(x.auth,'tickets',dict(action='correct',expected_revision=r['revision'],reason='Test correction',record={k:v for k,v in r.items() if k in ('id','kind','layer','domain','label','definition','dependencies','source_refs','evidence_class','properties')}))
    with pytest.raises(ApiFailure) as e:x.service.run(x.auth,request(x))
    assert e.value.status==409 and not x.cloud.calls


def test_cursor_cannot_change_search_or_concept(explorer):
    x=explorer;cursor=x.service.run(x.auth,request(x,limit=1))['next_cursor']
    with pytest.raises(ApiFailure):x.service.run(x.auth,request(x,limit=1,cursor=cursor,filter={'serial':'DUP'}))
    with pytest.raises(ApiFailure):x.service.run(x.auth,{**request(x,limit=1,cursor=cursor),'concept_id':'invoices'})


def test_read_limits_and_no_storage_mutation(explorer):
    x=explorer
    def state():
        with x.foundation.store.transaction(write=False) as db:
            return {t:db.execute('SELECT * FROM '+t).fetchall() for t in ('ontology_records','ontology_versions','ontology_events','data_source_connections')}
    before=state();x.service.run(x.auth,request(x));assert state()==before
    x.cloud.rows['tickets'][0]['serial']='x'*70000
    with pytest.raises(ApiFailure):x.service.run(x.auth,request(x))


def test_ordinary_bidirectional_traversal_is_bounded(explorer):
    x=explorer;result=x.service.run(x.auth,{**request(x),'concept_id':'accounts','key':{'_id':str(x.ids[4])},'relationship_id':'account_link'},True)
    assert len(result['objects'])==1 and result['concept_id']=='tickets'
    assert len(x.cloud.calls)==2


def test_source_generation_change_during_read_discards_values(explorer):
    x=explorer
    def change():
        with x.foundation.store.transaction() as db:
            c=json.loads(db.execute('SELECT document FROM data_source_connections').fetchone()[0]);c['generation']+=1
            db.execute('UPDATE data_source_connections SET document=?',(json.dumps(c),))
    x.cloud.after=change
    with pytest.raises(ApiFailure) as e:x.service.run(x.auth,request(x))
    assert e.value.status==409


def test_http_read_routes_and_error_contract(explorer):
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from unittest.mock import patch
    from workflow_api.data_source_routes import install
    from workflow_api.service import WorkflowService
    from registry import RegistryService, WorkspacePolicy
    x=explorer
    class Service(WorkflowService):
        def envelope(self,ref,status,data):return {'request_id':ref,'status':status,'data':data}
        def failure(self,ref,exc):return {'request_id':ref,'status':exc.status,'data':{'error':{'error_code':exc.code,'message':str(exc)}}}
    app=FastAPI()
    with patch('workflow_api.data_source_routes.DataSources',return_value=x.foundation.manager):
        install(app,Service(x.foundation.store,registry=RegistryService(WorkspacePolicy(x.auth['subject']['workspace_id']))),x.auth,{},lambda:'req_objects')
    client=TestClient(app)
    r=client.post('/ontology/v1/objects',json=request(x,limit=1))
    assert r.status_code==410 and r.json()['data']['error']['error_code']=='LEGACY_ONTOLOGY_RETIRED'
    assert 'NEVER_RETURN' not in r.text and r.headers['cache-control']=='no-store'
    r=client.post('/ontology/v1/objects/expand',json=request(x,key={'_id':str(x.ids[0])},relationship_id='serial_link'))
    assert r.status_code==410 and r.json()['data']['error']['error_code']=='LEGACY_ONTOLOGY_RETIRED'
    r=client.post('/ontology/v1/objects',json=request(x,filter={'password':'NEVER_RETURN'}))
    assert r.status_code==410 and r.json()['data']['error']['error_code']=='LEGACY_ONTOLOGY_RETIRED'


def test_postgres_projection_uses_quoted_catalogue_and_bound_native_parameters():
    class SQLCursor:
        def __enter__(self):return self
        def __exit__(self,*args):pass
        def execute(self,sql,params):self.sql,self.params=sql.as_string(),params
        def __iter__(self):return iter([(7,'safe')])
    cursor=SQLCursor()
    class Connection:
        def cursor(self):return cursor
    class Adapter:
        @contextmanager
        def connection(self,config):yield Connection()
    reader=QueryReader(SimpleNamespace(adapter=Adapter()))
    fields=[dict(name='id',types=['integer']),dict(name='value',types=['text'])]
    rows=reader.objects({'engine':'postgresql'},dict(schema='public',name='orders'),fields,['id'],{'value':"x'; DROP TABLE orders;--"},0,26,10**20)
    assert rows==[dict(id=7,value='safe')]
    assert 'DROP' not in cursor.sql and '"public"."orders"' in cursor.sql
    assert cursor.params==["x'; DROP TABLE orders;--",0,26]


def test_mongo_decimal_search_uses_native_bson_numeric_filter():
    from bson import BSON
    from bson.decimal128 import Decimal128
    cloud=Cloud();cloud.rows['amounts']=[{'_id':'one','amount':Decimal128('1.25')}]
    fields=[dict(name='_id',types=['string']),dict(name='amount',types=['Decimal128'])]
    rows=QueryReader(SimpleNamespace(adapter=cloud)).objects({'engine':'mongodb','database':'test'},dict(name='amounts'),fields,['_id'],{'amount':'1.25'},0,2,10**20)
    assert len(rows)==1 and isinstance(cloud.calls[0][1]['amount']['$eq'],Decimal128)
    assert BSON.encode(cloud.calls[0][1])
