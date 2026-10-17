"""Cloud boundary fixtures; never connect to or mutate a real cloud database."""
import copy
import json
import socket
from unittest.mock import patch

import pytest
from cryptography.fernet import Fernet

from workflow_api.data_sources import DataSources
from workflow_api.data_source_adapters import configuration, observed_fields, stable_id, public_addresses, CloudAdapters
from workflow_api.storage import WorkflowStore
from workflow_api.service import ApiFailure


def auth(owner='alice',workspace='one',write=True):
    return {'subject':{'subject_id':owner,'workspace_id':workspace},'decision':'allow','permissions':['tools.read']+(['tools.assign'] if write else [])}


def config(engine='mongodb'):
    return {'name':'Cloud test','engine':engine,'uri':'mongodb+srv://demo:private-value@cluster.mongodb.net/workshop' if engine=='mongodb' else 'postgresql://demo:private-value@db.example.supabase.co:5432/postgres','database':'workshop' if engine=='mongodb' else 'postgres','schemas':['public'],'description':'Test database','mode':'direct'}


class Adapter:
    def __init__(self):self.failure=None;self.hook=None;self.calls=[];self.field='customer_id'
    def test(self,c):
        self.calls.append(('test',c['engine']))
        if self.failure:raise self.failure
    def profile(self,c,cid):
        self.calls.append(('profile',c['engine']))
        if self.hook:self.hook()
        if self.failure:raise self.failure
        did=stable_id(cid,c['database'],'customers')
        return {'datasets':[{'dataset_id':did,'name':'customers','database':c['database'],'schema':None,'kind':'collection','fields':[{'field_id':stable_id(cid,did,self.field),'name':self.field,'types':['string'],'discovery_method':'sampled'}],'indexes':[],'constraints':[],'sample_count':1,'discovery_method':'sampled'}],'warnings':[],'coverage':'sampled','limits':{'datasets':100}}


@pytest.fixture
def manager(tmp_path):
    key=tmp_path/'key';key.write_bytes(Fernet.generate_key())
    return DataSources(WorkflowStore(tmp_path/'data.sqlite'),{'BUILDER_DATA_SOURCE_KEY_FILE':str(key)},Adapter())


@pytest.mark.parametrize('engine',['mongodb','postgresql'])
def test_connection_is_encrypted_owned_and_profiles(manager,engine):
    m=manager;record=m.connect(auth(),config(engine));cid=record['connection_id']
    assert record['profiling_status']=='queued' and record['metadata_revision']==0
    assert 'private-value' not in json.dumps(m.list(auth()))
    with m.store.transaction(write=False) as db:
        secret,doc=db.execute('SELECT secret,document FROM data_source_connections').fetchone()
        assert 'private-value' not in secret and 'uri' not in doc
    assert m.tick()
    result=m.metadata(auth(),cid)
    assert result['connection']['profiling_status']=='ready' and result['snapshot']['revision']==1
    assert not m.tick()
    for other in [auth('bob'),auth(workspace='two')]:
        with pytest.raises(ApiFailure,match='not found'):m.metadata(other,cid)
        assert m.list(other)['items']==[]


def test_refresh_preserves_previous_snapshot_on_failure(manager):
    m=manager;cid=m.connect(auth(),config())['connection_id'];m.tick()
    m.action(auth(),cid,'refresh-metadata');m.adapter.failure=RuntimeError('password=private-value')
    m.tick();result=m.metadata(auth(),cid)
    assert result['snapshot']['revision']==1 and result['connection']['profiling_status']=='failed'
    assert 'private-value' not in json.dumps(result)
    m.adapter.failure=None;m.adapter.field='new_field';m.action(auth(),cid,'refresh-metadata');m.tick()
    result=m.metadata(auth(),cid)
    assert result['snapshot']['revision']==2
    assert result['snapshot']['changes']['added']==['customers.new_field']
    assert result['snapshot']['changes']['removed']==['customers.customer_id']


def test_disconnect_during_profile_never_publishes(manager):
    m=manager;cid=m.connect(auth(),config())['connection_id']
    m.adapter.hook=lambda:m.action(auth(),cid,'disconnect')
    m.tick();result=m.metadata(auth(),cid)
    assert result['connection']['connection_status']=='disconnected' and result['snapshot'] is None
    with m.store.transaction(write=False) as db:assert db.execute('SELECT secret FROM data_source_connections').fetchone()[0] is None
    with pytest.raises(ApiFailure):m.action(auth(),cid,'refresh-metadata')


def test_verify_cannot_restore_disconnected_connection(manager):
    m=manager;cid=m.connect(auth(),config())['connection_id']
    original=m.adapter.test
    def test(c):m.action(auth(),cid,'disconnect');original(c)
    m.adapter.test=test
    with pytest.raises(ApiFailure,match='changed'):m.action(auth(),cid,'verify')
    assert m.metadata(auth(),cid)['connection']['connection_status']=='disconnected'


def test_lease_recovery_and_refresh_coalescing(manager):
    m=manager;cid=m.connect(auth(),config())['connection_id']
    m.action(auth(),cid,'refresh-metadata')
    with m.store.transaction() as db:
        assert db.execute('SELECT COUNT(*) FROM data_source_profile_jobs').fetchone()[0]==1
        db.execute("UPDATE data_source_profile_jobs SET state='running',lease_until=0,token='dead',attempts=1")
    assert m.tick() and m.metadata(auth(),cid)['snapshot']['revision']==1


def test_permissions_and_missing_key(manager):
    with pytest.raises(ApiFailure):manager.connect(auth(write=False),config())
    manager.cipher=None
    with pytest.raises(ApiFailure,match='Fernet'):manager.connect(auth(),config())


@pytest.mark.parametrize('uri',[
    'mongodb+srv://u:p@localhost/db','mongodb+srv://u:p@cluster.mongodb.net/db?tls=false',
    'postgresql://u:p@127.0.0.1/db','postgresql://u:p@db.test.supabase.co/db?sslmode=disable',
    'postgresql://u:p@db.test.supabase.co/db?hostaddr=127.0.0.1',
    'postgresql://u:p@db.test.supabase.co/db?options=-csearch_path=private',
])
def test_cloud_target_validation(uri):
    body=config('postgresql' if uri.startswith('postgres') else 'mongodb');body['uri']=uri
    with pytest.raises(ApiFailure):configuration(body)


def test_public_dns_validation():
    for address in ['127.0.0.1','10.0.0.2','169.254.169.254','::1']:
        with patch('socket.getaddrinfo',return_value=[(0,0,0,'',(address,5432))]):
            with pytest.raises(ApiFailure):public_addresses('db.test.supabase.co',5432)
    with patch('socket.getaddrinfo',return_value=[(0,0,0,'',('8.8.8.8',5432))]):assert public_addresses('x',5432)==['8.8.8.8']


def test_nested_fields_arrays_mixed_types_and_stability():
    docs=[{'id':'a','nested':{'n':1},'items':[{'sku':'a'},{'sku':'b'}]},{'id':2,'nested':{'n':None}}]
    fields,partial=observed_fields(docs,'cid','did');by={f['name']:f for f in fields}
    assert by['id']['types']==['integer','string']
    assert by['items[].sku']['present_in_samples']==1
    assert by['nested.n']['types']==['integer','null'] and not partial
    assert by['id']['field_id']==observed_fields(docs,'cid','did')[0][0]['field_id']
    assert 'sku' not in json.dumps(by['id'])


def test_postgres_discovery_preserves_composite_foreign_key():
    class Cursor:
        def __init__(self):self.calls=[];self.rows=[]
        def __enter__(self):return self
        def __exit__(self,*args):pass
        def execute(self,sql,args):
            self.calls.append((sql,args))
            if 'information_schema.tables' in sql:self.rows=[('public','orders','BASE TABLE')]
            elif 'information_schema.columns' in sql:self.rows=[('customer_id','text','text','NO',None),('tenant_id','text','text','NO',None)]
            elif 'pg_constraint' in sql:self.rows=[('fk_customer','f','FOREIGN KEY (tenant_id,customer_id) REFERENCES customers(tenant_id,id)',['tenant_id','customer_id'],'public','customers',['tenant_id','id'])]
            else:self.rows=[('orders_pkey','CREATE UNIQUE INDEX orders_pkey ON public.orders (customer_id)')]
        def fetchall(self):return self.rows
    cursor=Cursor()
    class Conn:
        def cursor(self):return cursor
    result=CloudAdapters.postgres(Conn(),config('postgresql'),'cid')
    table=result['datasets'][0]
    assert table['constraints'][0]['referenced_columns']==['tenant_id','id']
    assert table['fields'][0]['nullable'] is False and table['indexes']
    assert all(not sql.lstrip().upper().startswith(('INSERT','UPDATE','DELETE')) for sql,_ in cursor.calls)


def test_two_workers_cannot_publish_same_job_twice(manager):
    m=manager;cid=m.connect(auth(),config())['connection_id']
    m.adapter.hook=lambda:pytest.fail('job should not be claimed twice') if m.tick() else None
    m.tick();assert m.metadata(auth(),cid)['snapshot']['revision']==1


def test_authenticated_routes_do_not_echo_secret_errors(manager):
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from workflow_api.data_source_routes import install
    from types import SimpleNamespace
    from unittest.mock import patch
    class Service:
        store=manager.store
        def envelope(self,ref,status,data):return {'data':data}
        def failure(self,ref,exc):return {'error':{'error_code':exc.code,'message':str(exc)}}
    app=FastAPI()
    with patch('workflow_api.data_source_routes.DataSources',return_value=manager):install(app,Service(),auth(),{},lambda:'test')
    client=TestClient(app)
    result=client.post('/data-sources',json=config())
    assert result.status_code==200 and 'private-value' not in result.text
    cid=result.json()['data']['connection_id']
    assert client.get('/data-sources/'+cid+'/metadata').status_code==200
    bad=client.post('/data-sources/test',content='not-json')
    assert bad.status_code==400 and 'not-json' not in bad.text
    manager.adapter.failure=RuntimeError('password=private-value')
    response=client.post('/data-sources/test',json=config())
    assert response.status_code==400 and 'private-value' not in response.text
    assert client.post('/data-sources/'+cid+'/disconnect').status_code==200


def test_real_mongo_discovery_records_indexes_without_document_values():
    class Cursor:
        def __iter__(self):return iter([{'customer_id':'private-business-value','address':{'city':'Chennai'}}])
        def max_time_ms(self,value):return self
    class Collection:
        def find(self,*args,**kwargs):return Cursor()
        def list_indexes(self):return iter([{'name':'customer_unique','key':{'customer_id':1},'unique':True}])
    class DB:
        def list_collections(self,*,maxTimeMS):return iter([{'name':'customers','type':'collection','options':{}}])
        def __getitem__(self,name):return Collection()
    result=CloudAdapters.mongo(DB(),config(),'cid')
    assert result['datasets'][0]['indexes'][0]['unique']
    assert 'private-business-value' not in json.dumps(result)
    assert result['datasets'][0]['sample_count']==1


def test_mongo_connection_test_uses_supported_collection_command_options():
    from contextlib import contextmanager
    calls=[]
    class DB:
        def list_collections(self,*,nameOnly,maxTimeMS):
            calls.append((nameOnly,maxTimeMS))
            return iter([])
    class Client:
        def __getitem__(self,name):return DB()
    class Adapter(CloudAdapters):
        @contextmanager
        def connection(self,config):yield Client()
    Adapter({}).test(config())
    assert calls==[(True,8000)]


def test_metadata_matches_versioned_contract(manager):
    from pathlib import Path
    from jsonschema import Draft202012Validator
    schema=json.loads((Path(__file__).resolve().parents[1]/'shared/contracts/data-sources/cloud-metadata-v1.schema.json').read_text())
    Draft202012Validator.check_schema(schema)
    cid=manager.connect(auth(),config())['connection_id'];manager.tick()
    Draft202012Validator(schema).validate(manager.metadata(auth(),cid))


def test_credentials_update_retains_identity_and_invalidates_old_job(manager):
    m=manager;cid=m.connect(auth(),config())['connection_id'];m.tick()
    body=config();body['uri']=body['uri'].replace('private-value','replacement-value')
    result=m.credentials(auth(),cid,body)
    assert result['metadata_revision']==1 and result['profiling_status']=='queued'
    m.tick();assert m.metadata(auth(),cid)['snapshot']['revision']==2
    body['database']='different'
    with pytest.raises(ApiFailure,match='new connection'):m.credentials(auth(),cid,body)


def test_relationships_follow_profile_and_disconnect(manager):
    cid=manager.connect(auth(),config())['connection_id']
    manager.tick()
    assert manager.relationships.get(auth())['build_status']=='queued'
    assert manager.relationships.tick()
    assert len(manager.relationships.get(auth())['graph']['nodes'])==3
    manager.action(auth(),cid,'disconnect')
    view=manager.relationships.get(auth())
    assert view['stale'] and view['build_status']=='queued' and not view['graph']['nodes']
    manager.relationships.tick()
    assert manager.relationships.get(auth())['graph']['nodes']==[]
