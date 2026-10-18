"""Equivalence checks using isolated real PostgreSQL and MongoDB data."""
import copy
import json
import shutil
import subprocess
import time
from contextlib import contextmanager
from decimal import Decimal
from uuid import uuid4

import pytest

from tests.test_postgres_backend import test_dsn as postgres_dsn
from workflow_api.data_query_engine import compute, expression, scalar
from workflow_api.data_query_pushdown import PostgresCompiler, MongoCompiler, physical_plan, execute_postgres
from workflow_api.service import ApiFailure
from tests.test_data_queries import queries
from tests.test_data_relationships import auth


def logical(**changes):
    value=dict(base_dataset_id='lines', joins=[], fields=[], filters=[], group_by=['category'],
        metrics=[dict(label='sales',op='sum',expression='price * qty * (1 - discount)'),dict(label='rows',op='count',expression='')],
        order_by=[dict(column='sales',direction='desc')],limit=100,explanation='Test',clarification='')
    value.update(changes)
    return value


def catalog(schema='unused',engine='postgresql'):
    fields=[dict(field_id=k,name=k,types=[t]) for k,t in [('category','text' if engine=='postgresql' else 'string'),('price','numeric' if engine=='postgresql' else 'decimal'),('qty','integer'),('discount','numeric' if engine=='postgresql' else 'decimal')]]
    return {'lines':fields}, {'lines':dict(schema=schema,name='lines',connection=dict(connection_id='one',engine=engine))}


def expressions(plan):
    return {m['label']:expression(m['expression'],{'category','price','qty','discount'})[0] for m in plan['metrics'] if m['expression']}


ROWS=[dict(category='Food',price=Decimal('10.20'),qty=2,discount=Decimal('.1')),
      dict(category='Drink',price=Decimal('5'),qty=3,discount=Decimal('0')),
      dict(category=None,price=None,qty=4,discount=Decimal('0'))]


@pytest.fixture
def postgres():
    import psycopg
    from psycopg import sql
    dsn=postgres_dsn(); schema='pushdown_'+uuid4().hex
    with psycopg.connect(dsn,autocommit=True) as conn:
        conn.execute(sql.SQL('CREATE SCHEMA {}').format(sql.Identifier(schema)))
        conn.execute(sql.SQL('CREATE TABLE {}.lines (category text, price numeric, qty integer, discount numeric)').format(sql.Identifier(schema)))
        with conn.cursor() as cur:cur.executemany(sql.SQL('INSERT INTO {}.lines VALUES (%s,%s,%s,%s)').format(sql.Identifier(schema)),[tuple(r.values()) for r in ROWS])
    try:
        with psycopg.connect(dsn) as conn:yield conn,schema
    finally:
        with psycopg.connect(dsn,autocommit=True) as conn:conn.execute(sql.SQL('DROP SCHEMA {} CASCADE').format(sql.Identifier(schema)))


def run_pg(postgres,plan,joins=(),extra=None):
    conn,schema=postgres;needed,datasets=catalog(schema)
    if extra:
        needed.update(extra[0]);datasets.update(extra[1])
    return PostgresCompiler(plan,needed,datasets,joins,expressions(plan)).execute(conn,time.monotonic()+45)


@pytest.mark.parametrize('changes',[
 {}, {'filters':[dict(field_id='qty',op='gt',value=2)]},
 {'group_by':[]}, {'filters':[dict(field_id='qty',op='gt',value=100)]},
 {'fields':['category','qty'],'metrics':[],'group_by':[],'order_by':[dict(column='category',direction='asc')]},
 {'metrics':[dict(label='least',op='min',expression='-price'),dict(label='greatest',op='max',expression='price')],'order_by':[]},
 {'metrics':[dict(label='present',op='count',expression='price')],'order_by':[]},
 {'limit':1},
])
def test_postgres_matches_scalar_engine(postgres,changes):
    plan=logical(**changes)
    actual,total,matched,*_=run_pg(postgres,plan)
    expected=compute(ROWS,plan,expressions(plan))
    if not plan['order_by']:
        actual=sorted(actual,key=lambda r:str(r.get('category')))
        expected=(sorted(expected[0],key=lambda r:str(r.get('category'))),*expected[1:])
    assert (actual,total,matched)==expected


def test_postgres_large_complete_aggregate(postgres):
    conn,schema=postgres
    from psycopg import sql
    conn.execute(sql.SQL('INSERT INTO {}.lines SELECT %s,1.25,2,0 FROM generate_series(1,6001)').format(sql.Identifier(schema)),('Bulk',))
    result,total,matched,counts,checks,size=run_pg(postgres,logical(group_by=[]))
    assert result[0]['sales']==Decimal('15035.860') and result[0]['rows']==6004
    assert counts['lines']==6004 and matched==6004 and total==1 and size<200


@pytest.mark.parametrize('bad', ['NaN','Infinity','1000000000000000001','0.000000001'])
def test_postgres_rejects_numeric_envelope(postgres,bad):
    conn,schema=postgres
    from psycopg import sql
    conn.execute(sql.SQL('UPDATE {}.lines SET price=%s').format(sql.Identifier(schema)),(Decimal(bad),))
    with pytest.raises(ApiFailure) as caught:run_pg(postgres,logical())
    assert caught.value.code=='DATA_QUERY_TYPE'


def test_postgres_complete_join_checks_before_filters(postgres):
    conn,schema=postgres
    from psycopg import sql
    conn.execute(sql.SQL('CREATE TABLE {}.categories (name text)').format(sql.Identifier(schema)))
    conn.execute(sql.SQL('INSERT INTO {}.categories VALUES (%s)').format(sql.Identifier(schema)),('Food',))
    needed,ds=catalog(schema);ds['categories']=dict(schema=schema,name='categories',connection=ds['lines']['connection'])
    needed['categories']=[dict(field_id='name',name='name',types=['text'])]
    plan=logical(filters=[dict(field_id='category',op='eq',value='Food')])
    compiler=PostgresCompiler(plan,needed,ds,[('categories',[('category','name')],'r1')],expressions(plan))
    with pytest.raises(ApiFailure) as caught:compiler.execute(conn,time.monotonic()+45)
    assert caught.value.code=='DATA_QUERY_JOIN_INVALID'


def test_postgres_rejects_budget_without_partial_totals(postgres,monkeypatch):
    monkeypatch.setattr('workflow_api.data_query_pushdown.SERVER_ROWS',2)
    with pytest.raises(ApiFailure) as caught:run_pg(postgres,logical())
    assert caught.value.code=='DATA_QUERY_LIMIT'


@pytest.mark.parametrize('target_values', [('Food','Food'),('Food',None)])
def test_postgres_duplicate_and_null_targets(postgres,target_values):
    conn,schema=postgres
    from psycopg import sql
    conn.execute(sql.SQL('UPDATE {}.lines SET category=%s').format(sql.Identifier(schema)),('Food',))
    conn.execute(sql.SQL('CREATE TABLE {}.categories(name text)').format(sql.Identifier(schema)))
    with conn.cursor() as cur:cur.executemany(sql.SQL('INSERT INTO {}.categories VALUES(%s)').format(sql.Identifier(schema)),[(v,) for v in target_values])
    needed,datasets=catalog(schema)
    needed['categories']=[dict(field_id='name',name='name',types=['text'])]
    datasets['categories']=dict(schema=schema,name='categories',connection=datasets['lines']['connection'])
    p=logical();compiler=PostgresCompiler(p,needed,datasets,[('categories',[('category','name')],'r1')],expressions(p))
    with pytest.raises(ApiFailure) as caught:compiler.execute(conn,time.monotonic()+45)
    assert caught.value.code=='DATA_QUERY_JOIN_INVALID'


def test_postgres_valid_join_retains_complete_counts(postgres):
    conn,schema=postgres
    from psycopg import sql
    conn.execute(sql.SQL('UPDATE {}.lines SET category=%s WHERE category IS NULL').format(sql.Identifier(schema)),('Food',))
    conn.execute(sql.SQL("CREATE TABLE {}.categories AS SELECT unnest(ARRAY['Food','Drink']) AS name").format(sql.Identifier(schema)))
    needed,datasets=catalog(schema)
    needed['categories']=[dict(field_id='name',name='name',types=['text'])]
    datasets['categories']=dict(schema=schema,name='categories',connection=datasets['lines']['connection'])
    p=logical();result=PostgresCompiler(p,needed,datasets,[('categories',[('category','name')],'r1')],expressions(p)).execute(conn,time.monotonic()+45)
    assert result[2]==3 and result[4][0]['source_rows']==3 and result[4][0]['target_rows']==2
    assert result[0][0]['sales']==Decimal('18.360')


def test_postgres_schema_type_drift_fails_before_numeric_coercion(postgres):
    conn,schema=postgres
    from psycopg import sql
    conn.execute(sql.SQL('ALTER TABLE {}.lines ALTER COLUMN price TYPE text USING price::text').format(sql.Identifier(schema)))
    with pytest.raises(ApiFailure) as caught:run_pg(postgres,logical())
    assert caught.value.code=='DATA_QUERY_STALE'


def test_postgres_deadline_and_transfer_budget(postgres,monkeypatch):
    conn,schema=postgres;needed,datasets=catalog(schema);p=logical()
    with pytest.raises(ApiFailure) as caught:PostgresCompiler(p,needed,datasets,[],expressions(p)).execute(conn,time.monotonic()-1)
    assert caught.value.code=='DATA_QUERY_TIMEOUT'
    monkeypatch.setattr('workflow_api.data_query_pushdown.MAX_BYTES',10)
    with pytest.raises(ApiFailure) as caught:run_pg(postgres,p)
    assert caught.value.code=='DATA_QUERY_LIMIT'


def test_postgres_values_are_bound_and_identifiers_quoted():
    needed,datasets=catalog();needed['lines'][0]['name']='odd"; DROP TABLE lines;--'
    p=logical(filters=[dict(field_id='category',op='eq',value="x' OR true--")])
    compiler=PostgresCompiler(p,needed,datasets,[],expressions(p))
    assert "x' OR true--" not in compiler.filtered and compiler.params==["x' OR true--"]
    assert '"odd""; DROP TABLE lines;--"' in compiler.prefix


def test_capabilities_are_conservative():
    needed,datasets=catalog()
    p=logical();assert physical_plan(p,needed,datasets,expressions(p))['strategy']=='postgresql'
    p=logical(metrics=[dict(label='mean',op='avg',expression='price')]);assert physical_plan(p,needed,datasets,expressions(p))['strategy']=='postgresql'
    for metric in [dict(label='ratio',op='sum',expression='price / qty')]:
        p=logical(metrics=[metric]);assert physical_plan(p,needed,datasets,expressions(p))['strategy']=='application'
    p=logical();needed['other']=needed['lines'];datasets['other']={**datasets['lines'],'connection':dict(connection_id='two',engine='mongodb')}
    assert physical_plan(p,needed,datasets,expressions(p))['strategy']=='application'


@pytest.fixture(scope='module')
def mongo(tmp_path_factory):
    from pymongo import MongoClient
    if not shutil.which('mongod'):pytest.skip('mongod is required for the isolated snapshot integration test')
    root=tmp_path_factory.mktemp('query-mongo');port=27249
    process=subprocess.Popen(['mongod','--dbpath',str(root),'--port',str(port),'--bind_ip','127.0.0.1','--replSet','query_test','--logpath',str(root/'mongo.log')],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    client=MongoClient('mongodb://127.0.0.1:'+str(port),directConnection=True,serverSelectionTimeoutMS=500)
    try:
        for _ in range(80):
            try:client.admin.command('ping');break
            except Exception:time.sleep(.1)
        client.admin.command('replSetInitiate',{'_id':'query_test','members':[{'_id':0,'host':'127.0.0.1:'+str(port)}]})
        for _ in range(150):
            if client.admin.command('hello')['isWritablePrimary']:break
            time.sleep(.1)
        yield client['query_test']['lines']
    finally:
        client.close();process.terminate();process.wait(timeout=15)


def seed_mongo(collection,rows):
    from bson.decimal128 import Decimal128
    collection.delete_many({})
    if rows:collection.insert_many([{k:Decimal128(v) if isinstance(v,Decimal) else v for k,v in r.items()} for r in rows])


@pytest.mark.parametrize('changes',[
 {}, {'group_by':[]}, {'filters':[dict(field_id='qty',op='gt',value=2)]},
 {'filters':[dict(field_id='qty',op='gt',value=100)],'group_by':[]},
 {'fields':['category','qty'],'metrics':[],'group_by':[],'order_by':[dict(column='category',direction='asc')]},
 {'metrics':[dict(label='least',op='min',expression='price'),dict(label='greatest',op='max',expression='price')],'order_by':[]},
 {'metrics':[dict(label='present',op='count',expression='price')],'order_by':[]}, {'limit':1},
])
def test_mongo_matches_scalar_engine(mongo,changes):
    seed_mongo(mongo,ROWS);p=logical(**changes);needed,_=catalog(engine='mongodb')
    actual,total,matched,*_=MongoCompiler(p,needed['lines'],expressions(p)).execute(mongo,time.monotonic()+45)
    expected=compute(ROWS,p,expressions(p))
    if not p['order_by']:
        actual=sorted(actual,key=lambda r:str(r.get('category')))
        expected=(sorted(expected[0],key=lambda r:str(r.get('category'))),*expected[1:])
    assert (actual,total,matched)==expected


def test_mongo_large_aggregate_missing_and_null(mongo):
    rows=ROWS+[dict(category='Bulk',price=Decimal('1.25'),qty=2,discount=Decimal(0)) for _ in range(6001)]
    seed_mongo(mongo,rows);p=logical(group_by=[]);needed,_=catalog(engine='mongodb')
    result,total,matched,count,size=MongoCompiler(p,needed['lines'],expressions(p)).execute(mongo,time.monotonic()+45)
    assert result[0]['sales']==Decimal('15035.860') and result[0]['rows']==6004 and count==6004 and size<200
    seed_mongo(mongo,[dict(qty=1,discount=Decimal(0)),dict(category=None,qty=2,price=None,discount=Decimal(0))])
    p=logical();actual=MongoCompiler(p,needed['lines'],expressions(p)).execute(mongo,time.monotonic()+45)
    assert actual[0]==[dict(category=None,sales=None,rows=2)]


@pytest.mark.parametrize('value',[True,'12',[1],{'v':1},Decimal('NaN'),Decimal('0.000000001')])
def test_mongo_rejects_runtime_type_drift(mongo,value):
    rows=copy.deepcopy(ROWS);rows[0]['price']=value;seed_mongo(mongo,rows)
    p=logical();needed,_=catalog(engine='mongodb')
    with pytest.raises(ApiFailure) as caught:MongoCompiler(p,needed['lines'],expressions(p)).execute(mongo,time.monotonic()+45)
    assert caught.value.code=='DATA_QUERY_TYPE'


def test_native_mongo_saved_plan_executes_through_service(queries,mongo):
    seed_mongo(mongo,[{'categoryID':1,'name':'Food'},{'categoryID':2,'name':'Drink'}])
    queries.pushdown_enabled=True
    queries.planner.output=logical(base_dataset_id='mongo_categories',group_by=[],metrics=[dict(label='count',op='count',expression='')],order_by=[])
    @contextmanager
    def connection(config):yield {'test':{'categories':mongo}}
    queries.manager.adapter.connection=connection
    with queries.store.transaction() as db:
        db.execute('UPDATE data_source_connections SET secret=? WHERE connection_id=?',(queries.manager.cipher.encrypt(json.dumps({'engine':'mongodb','database':'test'}).encode()).decode(),'mongo'))
    saved=queries.plan(auth(),{'question':'Count categories'})
    result=queries.execute(auth(),{'plan_id':saved['plan_id']})
    assert saved['physical_plan']['strategy']=='mongodb'
    assert result['rows']==[{'count':2}] and result['execution']['strategy']=='mongodb'
    assert result['execution']['transferred_rows']==1 and result['sources'][0]['rows_read']==2


def test_postgres_wrapper_uses_read_only_repeatable_snapshot(postgres):
    conn,schema=postgres
    @contextmanager
    def connection(config):yield conn
    from types import SimpleNamespace
    manager=SimpleNamespace(adapter=SimpleNamespace(connection=connection))
    p=logical(group_by=[]);needed,datasets=catalog(schema)
    result=execute_postgres(manager,{},p,needed,datasets,[],expressions(p),time.monotonic()+45)
    assert result[0][0]['sales']==Decimal('33.360')
    assert conn.execute('SHOW transaction_read_only').fetchone()[0]=='on'
    assert conn.execute('SHOW transaction_isolation').fetchone()[0]=='repeatable read'
