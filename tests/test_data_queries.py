"""Offline correctness, authorization and hostile-plan checks for Phase 3."""
import copy
import json
import time
from decimal import Decimal
from pathlib import Path
from unittest.mock import patch

import pytest
from cryptography.fernet import Fernet
from fastapi.testclient import TestClient
from jsonschema import Draft202012Validator

from workflow_api.data_queries import DataQueries, QueryPlanner, QueryReader, SCHEMA
from workflow_api.data_query_engine import compute, expression, join_rows, scalar
from workflow_api.data_sources import DataSources
from workflow_api.storage import WorkflowStore
from workflow_api.service import ApiFailure
from tests.test_data_relationships import auth, dataset


def plan(**overrides):
    return dict(base_dataset_id='pg_lines',joins=[],fields=[],filters=[],group_by=[],
                metrics=[dict(label='sales',op='sum',expression='pg_lines_price * pg_lines_qty * (1 - pg_lines_discount)')],
                order_by=[],limit=100,explanation='Discounted line sales, excluding freight.',clarification='',**overrides)


class Planner:
    configured=True
    output=None
    calls=[]
    def generate(self, question, catalog):
        self.calls.append((question,catalog))
        return copy.deepcopy(self.output or plan())


class Reader:
    def __init__(self):
        self.calls=[]
        self.rows={'pg_lines':[
            {'pg_lines_categoryID':1,'pg_lines_price':Decimal('10.20'),'pg_lines_qty':2,'pg_lines_discount':Decimal('.1')},
            {'pg_lines_categoryID':2,'pg_lines_price':Decimal('5'),'pg_lines_qty':3,'pg_lines_discount':Decimal('0')},
            {'pg_lines_categoryID':1,'pg_lines_price':None,'pg_lines_qty':4,'pg_lines_discount':Decimal('0')}],
            'mongo_categories':[{'mongo_categories_categoryID':1,'mongo_categories_name':'Food'},{'mongo_categories_categoryID':2,'mongo_categories_name':'Drink'}]}
    def read(self, config,dataset,fields,deadline):
        self.calls.append(dataset['dataset_id'])
        return [{f['field_id']:scalar(r.get(f['field_id'])) for f in fields} for r in self.rows[dataset['dataset_id']]],100


@pytest.fixture
def queries(tmp_path):
    key=tmp_path/'key';key.write_bytes(Fernet.generate_key())
    manager=DataSources(WorkflowStore(tmp_path/'queries.sqlite'),{'BUILDER_DATA_SOURCE_KEY_FILE':str(key)})
    data=[('pg','postgresql',dataset('pg','lines',[('categoryID',['integer']),('price',['numeric']),('qty',['integer']),('discount',['numeric'])],'northwind')),
          ('mongo','mongodb',dataset('mongo','categories',[('categoryID',['integer']),('name',['string'])]))]
    with manager.store.transaction() as db:
        for cid,engine,ds in data:
            doc=dict(connection_id=cid,name=cid,engine=engine,connection_status='connected',metadata_revision=1,generation=1)
            db.execute('INSERT INTO data_source_connections VALUES (?,?,?,?,?)',(cid,'one','alice',manager.cipher.encrypt(json.dumps({'engine':engine}).encode()).decode(),json.dumps(doc)))
            db.execute('INSERT INTO data_source_snapshots VALUES (?,?,?)',(cid,1,json.dumps(dict(revision=1,coverage='declared',warnings=[],datasets=[ds]))))
    manager.relationships.request(auth());manager.relationships.tick()
    return DataQueries(manager,Planner(),Reader())


def saved(queries): return queries.plan(auth(),{'question':'Calculate discounted line sales excluding freight.'})


def test_exact_decimal_aggregate_and_no_values_in_model_context(queries):
    item=saved(queries)
    result=queries.execute(auth(),{'plan_id':item['plan_id']})
    assert result['rows']==[{'sales':'33.360'}]
    assert result['matched_rows']==3 and result['sources'][0]['rows_read']==3
    response_schema=json.loads((Path(__file__).resolve().parents[1]/'shared/contracts/data-sources/queries-v1.schema.json').read_text())
    Draft202012Validator.check_schema(response_schema)
    for value in (item,result,queries.status(auth())):Draft202012Validator(response_schema).validate(value)
    assert result['join_checks']==[]
    assert '10.20' not in json.dumps(queries.planner.calls[-1])
    with queries.store.transaction(write=False) as db:
        stored=db.execute('SELECT document FROM data_query_plans').fetchone()[0]
        assert '10.20' not in stored and '33.360' not in stored
    assert len(queries.reader.calls)==1


def joined_plan(queries):
    graph=queries.manager.relationships.get(auth())['graph']
    edge=graph['relationships'][0]
    queries.manager.relationships.edit(auth(),'review',edge['relationship_id'],dict(revision=graph['revision'],status='accepted'))
    p=plan();p['joins']=[dict(relationship_id=edge['relationship_id'],target_dataset_id='mongo_categories')]
    p['group_by']=['mongo_categories_name'];p['order_by']=[dict(column='sales',direction='desc')]
    queries.planner.output=p
    return saved(queries)


def test_cross_source_join_and_grouping(queries):
    item=joined_plan(queries)
    result=queries.execute(auth(),{'plan_id':item['plan_id']})
    assert result['rows']==[{'mongo_categories_name':'Food','sales':'18.360'},{'mongo_categories_name':'Drink','sales':'15'}]
    assert result['join_checks'][0]['matched_rows']==3
    assert len(result['sources'])==2


@pytest.mark.parametrize('problem',['duplicate','unmatched','null_target','null_source'])
def test_join_failures_never_return_partial_totals(queries,problem):
    item=joined_plan(queries)
    if problem=='duplicate':queries.reader.rows['mongo_categories'].append(queries.reader.rows['mongo_categories'][0])
    elif problem=='unmatched':queries.reader.rows['mongo_categories'].pop()
    elif problem=='null_target':queries.reader.rows['mongo_categories'][0]['mongo_categories_categoryID']=None
    else:queries.reader.rows['pg_lines'][0]['pg_lines_categoryID']=None
    with pytest.raises(ApiFailure) as error:queries.execute(auth(),{'plan_id':item['plan_id']})
    assert error.value.code=='DATA_QUERY_JOIN_INVALID'


def test_unreviewed_and_rejected_relationships_cannot_plan(queries):
    graph=queries.manager.relationships.get(auth())['graph'];edge=graph['relationships'][0]
    for status in ('proposed','rejected'):
        graph=queries.manager.relationships.get(auth())['graph']
        queries.manager.relationships.edit(auth(),'review',edge['relationship_id'],dict(revision=graph['revision'],status=status))
        p=plan();p['joins']=[dict(relationship_id=edge['relationship_id'],target_dataset_id='mongo_categories')];queries.planner.output=p
        with pytest.raises(ApiFailure):saved(queries)
    assert not queries.reader.calls


@pytest.mark.parametrize('change',['review','refresh','disconnect','expire'])
def test_saved_plan_invalidated(queries,change):
    item=saved(queries)
    with queries.store.transaction() as db:
        if change=='expire':
            stored=json.loads(db.execute('SELECT document FROM data_query_plans').fetchone()[0]);stored['expires_at']=time.time()-1
            db.execute('UPDATE data_query_plans SET document=?',(json.dumps(stored),))
        elif change in ('refresh','disconnect'):
            doc=json.loads(db.execute("SELECT document FROM data_source_connections WHERE connection_id='pg'").fetchone()[0])
            if change=='refresh':doc['generation']+=1
            else:doc['connection_status']='disconnected'
            db.execute("UPDATE data_source_connections SET document=? WHERE connection_id='pg'",(json.dumps(doc),))
    if change=='review':
        graph=queries.manager.relationships.get(auth())['graph']
        queries.manager.relationships.edit(auth(),'annotation','pg_lines',dict(revision=graph['revision'],description='Changed context'))
    with pytest.raises(ApiFailure) as error:queries.execute(auth(),{'plan_id':item['plan_id']})
    assert error.value.code=='DATA_QUERY_STALE' and not queries.reader.calls


def test_isolation_and_permissions(queries):
    item=saved(queries)
    for other in (auth('bob'),auth(workspace='two'),auth(write=False)):
        with pytest.raises(ApiFailure):queries.execute(other,{'plan_id':item['plan_id']})
    with pytest.raises(ApiFailure):queries.plan(auth(write=False),{'question':'Count rows'})
    assert not queries.reader.calls


def test_metadata_changed_mid_read_discards_result(queries):
    item=saved(queries);read=queries.reader.read
    def changed(*args):
        result=read(*args)
        graph=queries.manager.relationships.get(auth())['graph']
        queries.manager.relationships.edit(auth(),'annotation','pg_lines',dict(revision=graph['revision'],description='change'))
        return result
    queries.reader.read=changed
    with pytest.raises(ApiFailure) as error:queries.execute(auth(),{'plan_id':item['plan_id']})
    assert error.value.code=='DATA_QUERY_STALE'


def test_clarification_performs_no_reads(queries):
    p=plan();p.update(base_dataset_id='',metrics=[],clarification='Should revenue include freight?');queries.planner.output=p
    item=saved(queries)
    with pytest.raises(ApiFailure):queries.execute(auth(),{'plan_id':item['plan_id']})
    assert not queries.reader.calls


@pytest.mark.parametrize('value',["__import__('os').system('id')",'pg_lines_price.__class__','2 ** 100','pg_lines_price[0]','unknown + 1','True','1e999'])
def test_hostile_expression_rejected(queries,value):
    p=plan();p['metrics'][0]['expression']=value;queries.planner.output=p
    with pytest.raises(ApiFailure):saved(queries)
    assert not queries.reader.calls


def test_bad_plan_fields_and_limit(queries):
    for mutate in (lambda p:p.update(limit=501),lambda p:p.update(fields=['foreign']),lambda p:p.update(order_by=[dict(column='unknown',direction='asc')])):
        p=plan();mutate(p);queries.planner.output=p
        with pytest.raises(ApiFailure):saved(queries)


def test_grouping_nulls_and_empty_count():
    p=plan();p.update(group_by=['a','b'],metrics=[dict(label='n',op='count',expression='')])
    result,total,_=compute([{'a':None,'b':1},{'a':None,'b':2}],p,{})
    assert total==2 and [r['n'] for r in result]==[1,1]
    p['group_by']=[]
    assert compute([],p,{})[0]==[{'n':0}]


def test_filter_sort_limit_and_division_by_zero(queries):
    p=plan();p.update(metrics=[],fields=['pg_lines_qty'],filters=[dict(field_id='pg_lines_qty',op='gte',value=3)],order_by=[dict(column='pg_lines_qty',direction='desc')],limit=1);queries.planner.output=p
    result=queries.execute(auth(),{'plan_id':saved(queries)['plan_id']})
    assert result['rows']==[{'pg_lines_qty':4}] and result['limited'] and result['total_result_rows']==2
    p=plan();p['metrics'][0]['expression']='pg_lines_price / 0';queries.planner.output=p
    with pytest.raises(ApiFailure):queries.execute(auth(),{'plan_id':saved(queries)['plan_id']})


def test_source_errors_are_sanitized(queries):
    item=saved(queries)
    def error(*args):raise RuntimeError('postgres://user:password@private')
    queries.reader.read=error
    with pytest.raises(ApiFailure) as exc:queries.execute(auth(),{'plan_id':item['plan_id']})
    assert 'password' not in str(exc.value)


def test_combined_size_limit_and_concurrency(queries):
    item=joined_plan(queries);read=queries.reader.read
    queries.reader.read=lambda *args:(read(*args)[0],1_100_000)
    with pytest.raises(ApiFailure) as exc:queries.execute(auth(),{'plan_id':item['plan_id']})
    assert exc.value.code=='DATA_QUERY_LIMIT'
    queries.active.add(('one','alice'))
    with pytest.raises(ApiFailure) as exc:saved(queries)
    assert exc.value.status==429


def test_reader_mongo_boundaries_and_row_cap(queries):
    from contextlib import contextmanager
    class Cursor:
        closed=False
        def limit(self,n):assert n==5001;return self
        def batch_size(self,n):assert n==25;return self
        def max_time_ms(self,n):assert n==10000;return self
        def __iter__(self):return iter({'name':'a'} for _ in range(5001))
        def close(self):self.closed=True
    cursor=Cursor()
    class DB:
        def __getitem__(self,key):return self
        def find(self,where,projection):assert where=={} and projection=={'name':1,'_id':0};return cursor
    @contextmanager
    def connection(config):yield DB()
    queries.manager.adapter.connection=connection
    with pytest.raises(ApiFailure) as exc:
        QueryReader(queries.manager).read({'engine':'mongodb','database':'x'},{'name':'categories'},[dict(field_id='name',name='name')],time.monotonic()+45)
    assert exc.value.code=='DATA_QUERY_LIMIT' and cursor.closed


def test_model_contract_and_failure_sanitization():
    Draft202012Validator.check_schema(SCHEMA)
    with patch('openai.OpenAI') as client:
        client.return_value.responses.create.return_value.output_text=json.dumps(plan())
        client.return_value.responses.create.return_value.status='completed'
        model=QueryPlanner({'OPENAI_API_KEY':'private','OPENAI_MODEL':'configured-model'})
        assert model.generate('question',{})==plan()
        request=client.return_value.responses.create.call_args.kwargs
        assert request['text']['format']['strict'] is True
        assert 'private' not in json.dumps(request)
        client.return_value.responses.create.side_effect=RuntimeError('private')
        with pytest.raises(ApiFailure) as exc:model.generate('question',{})
        assert 'private' not in str(exc.value)


def test_http_query_routes(tmp_path):
    from workflow_api.main import create_app
    app=create_app(database=tmp_path/'http.sqlite',dev_auth=True,roles=['admin'])
    with TestClient(app) as client:
        from workflow_api.main import COOKIE
        session=client.get('/session')
        client.cookies.set(COOKIE,session.cookies[COOKIE],path='/')
        response=client.get('/data-queries')
        assert response.status_code==200 and response.headers['cache-control']=='no-store'
        assert response.json()['data']['max_result_rows']==500
        response=client.post('/data-queries/plan',json={'question':'Count orders'},headers={'Origin':'http://localhost:3000'})
        assert response.status_code==409


def test_timestamp_filters_normalize_and_reject_ambiguous_values():
    import datetime
    from workflow_api.data_queries import normalize_date_filter, query_types
    field={'types':['timestamp with time zone']}
    assert query_types(field)=={'datetime'}
    assert normalize_date_filter(field,'1997-01-01T05:30:00+05:30')=='1997-01-01T00:00:00+00:00'
    assert normalize_date_filter({'types':['datetime']},'1997-01-01T05:30:00+05:30')=='1997-01-01T00:00:00+00:00'
    assert scalar(datetime.datetime(1997,1,1,tzinfo=datetime.timezone.utc))=='1997-01-01T00:00:00+00:00'
    for value in ('1997','1997-01-01T00:00:00','not-a-date'):
        with pytest.raises(ApiFailure):normalize_date_filter(field,value)


def test_postgres_reader_quotes_identifiers_and_bounds_fetches(queries):
    from contextlib import contextmanager
    class Cursor:
        def __enter__(self):return self
        def __exit__(self,*args):pass
        def execute(self,query):
            sql=query.as_string(None)
            assert '"northwind"."odd""name"' in sql and '"price"' in sql and 'LIMIT 5001' in sql
        def fetchmany(self,n):assert n==50;return []
    class Connection:
        def cursor(self,*,name):assert name.startswith('data_query_');return Cursor()
    @contextmanager
    def connection(config):yield Connection()
    queries.manager.adapter.connection=connection
    assert QueryReader(queries.manager).read({'engine':'postgresql'},dict(schema='northwind',name='odd"name'),[dict(field_id='p',name='price')],time.monotonic()+45)==([],0)


def test_large_integer_result_is_preserved_and_huge_constants_fail():
    from workflow_api.data_queries import wire
    assert wire(9007199254740993)=='9007199254740993'
    with pytest.raises(ApiFailure):expression('9'*1000,set())
