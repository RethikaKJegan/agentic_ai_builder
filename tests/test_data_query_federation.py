"""Phase 5 equivalence against complete scalar inputs and isolated real engines."""
import copy
import json
import time
from contextlib import contextmanager
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace

import pytest
from jsonschema import Draft202012Validator

from tests.test_data_query_pushdown import postgres, mongo, logical, catalog, expressions, seed_mongo, ROWS
from tests.test_postgres_backend import test_dsn as postgres_dsn
from tests.test_data_queries import queries, joined_plan
from tests.test_data_relationships import auth
from workflow_api.data_query_engine import compute, expression, join_rows
from workflow_api.data_query_federation import execute_federated, execute_average, merge_states, state_plan
from workflow_api.data_query_pushdown import physical_plan
from workflow_api.service import ApiFailure


def setup_federation(postgres, mongo, rows=None, dimensions=None):
    from psycopg import sql
    conn, schema = postgres
    conn.execute(sql.SQL('DELETE FROM {}.lines').format(sql.Identifier(schema)))
    rows = rows if rows is not None else [dict(category='a',price=Decimal('1'),qty=1,discount=Decimal('0')) for _ in range(6000)] + [dict(category='b',price=Decimal('100'),qty=1,discount=Decimal('0'))]
    with conn.cursor() as cur:
        cur.executemany(sql.SQL('INSERT INTO {}.lines VALUES (%s,%s,%s,%s)').format(sql.Identifier(schema)), [tuple(r.values()) for r in rows])
    conn.commit()
    dims = dimensions if dimensions is not None else [dict(code='a',name='Shared'),dict(code='b',name='Shared')]
    seed_mongo(mongo,dims)
    needed, datasets = catalog(schema)
    needed['dim'] = [dict(field_id='code',name='code',types=['string']),dict(field_id='name',name='name',types=['string'])]
    datasets['dim'] = dict(name='categories',connection=dict(connection_id='two',engine='mongodb'))
    p=logical(joins=[dict(relationship_id='r',target_dataset_id='dim')],group_by=['name'],metrics=[
        dict(label='mean',op='avg',expression='price'),dict(label='sum',op='sum',expression='price'),
        dict(label='count',op='count',expression=''),dict(label='present',op='count',expression='price'),
        dict(label='min',op='min',expression='price'),dict(label='max',op='max',expression='price')],order_by=[dict(column='mean',direction='desc')])
    exprs={m['label']:expression(m['expression'],{'price','qty','discount'})[0] for m in p['metrics'] if m['expression']}
    joins=[('dim',[('category','code')],'r')]
    @contextmanager
    def connection(config):
        if config['engine']=='postgresql':yield conn
        else:yield {'test':{'categories':mongo}}
    manager=SimpleNamespace(adapter=SimpleNamespace(connection=connection))
    configs={'lines':{'engine':'postgresql'},'dim':{'engine':'mongodb','database':'test'}}
    return manager,configs,p,needed,datasets,joins,exprs,rows,dims


def execute(fixture,fresh=lambda:None):
    return execute_federated(*fixture[:7],time.monotonic()+45,fresh)


def expected(fixture):
    rows,_=join_rows(fixture[7],fixture[8],[('category','code')])
    return compute(rows,fixture[2],fixture[6])


def test_large_federation_matches_complete_rows_and_weighted_average(postgres,mongo):
    f=setup_federation(postgres,mongo)
    assert physical_plan(f[2],f[3],f[4],f[6],f[5])['strategy']=='federated'
    actual=execute(f)
    assert actual[:3]==expected(f)
    assert actual[3]=={'lines':6001,'dim':2}
    assert actual[4][0]['matched_rows']==6001
    assert actual[6]==6 and actual[5]<2000
    assert [v['purpose'] for v in actual[7]]==['complete dimension','complete join key domain','partial aggregates']
    assert actual[0][0]['mean']!=Decimal('50.5')
    assert f[0].adapter is not None


@pytest.mark.parametrize('case',['empty','all_null','local_filter','dimension_filter','top_one','count_only','composite'])
def test_federation_semantics(postgres,mongo,case):
    rows=[dict(category='a',price=Decimal('10'),qty=1,discount=Decimal(0)),dict(category='b',price=None,qty=2,discount=Decimal(0)),dict(category='b',price=Decimal('100'),qty=3,discount=Decimal(0))]
    f=setup_federation(postgres,mongo,rows=rows,dimensions=[dict(code='a',name='A'),dict(code='b',name='B')])
    p=f[2]
    if case=='empty':p['filters']=[dict(field_id='qty',op='gt',value=100)];p['group_by']=[]
    elif case=='all_null':p['filters']=[dict(field_id='qty',op='eq',value=2)]
    elif case=='local_filter':p['filters']=[dict(field_id='qty',op='gt',value=1)]
    elif case=='dimension_filter':p['filters']=[dict(field_id='name',op='eq',value='B')]
    elif case=='top_one':p['limit']=1
    elif case=='count_only':p['metrics']=[dict(label='count',op='count',expression='')];p['order_by']=[]
    elif case=='composite':f[5][0][1].append(('category','name'));seed_mongo(mongo,[dict(code='a',name='a'),dict(code='b',name='b')]);f=(*f[:8],[dict(code='a',name='a'),dict(code='b',name='b')])
    actual=execute(f)
    if case=='composite':
        joined,_=join_rows(f[7],f[8],f[5][0][1]);comparison=compute(joined,p,f[6])
    else:comparison=expected(f)
    assert actual[:3]==comparison


@pytest.mark.parametrize('bad',['duplicate_unused','null_target','unmatched_filtered','null_source_filtered'])
def test_complete_cross_source_checks_precede_filters(postgres,mongo,bad):
    rows=[dict(category='a',price=Decimal(1),qty=1,discount=Decimal(0)),dict(category=None if bad=='null_source_filtered' else 'b',price=Decimal(1),qty=2,discount=Decimal(0))]
    dims=[dict(code='a',name='A'),dict(code='b',name='B')]
    if bad=='duplicate_unused':dims += [dict(code='z',name='Unused'),dict(code='z',name='Unused')]
    elif bad=='null_target':dims += [dict(code=None,name='Unused')]
    elif bad=='unmatched_filtered':dims.pop()
    f=setup_federation(postgres,mongo,rows,dims);f[2]['filters']=[dict(field_id='qty',op='eq',value=1)]
    with pytest.raises(ApiFailure) as error:execute(f)
    assert error.value.code=='DATA_QUERY_JOIN_INVALID'


def test_intermediate_limits_deadline_and_freshness(postgres,mongo,monkeypatch):
    f=setup_federation(postgres,mongo)
    with monkeypatch.context() as patch:
        patch.setattr('workflow_api.data_query_federation.MAX_BYTES',1)
        with pytest.raises(ApiFailure) as error:execute(f)
        assert error.value.code=='DATA_QUERY_LIMIT'
    def stale():raise ApiFailure('DATA_QUERY_STALE','Changed review',409)
    with pytest.raises(ApiFailure) as error:execute(f,stale)
    assert error.value.code=='DATA_QUERY_STALE'
    with pytest.raises(ApiFailure) as error:execute_federated(*f[:7],time.monotonic()-1,lambda:None)
    assert error.value.code=='DATA_QUERY_TIMEOUT'


def test_dimension_and_group_limits_no_partial_totals(postgres,mongo):
    f=setup_federation(postgres,mongo,dimensions=[dict(code=str(i),name='A') for i in range(5001)])
    with pytest.raises(ApiFailure) as error:execute(f)
    assert error.value.code=='DATA_QUERY_LIMIT'
    rows=[dict(category=str(i),price=Decimal(1),qty=1,discount=Decimal(0)) for i in range(5001)]
    f=setup_federation(postgres,mongo,rows=rows)
    with pytest.raises(ApiFailure) as error:execute(f)
    assert error.value.code=='DATA_QUERY_LIMIT'


def test_unsupported_shapes_fall_back(postgres,mongo):
    f=setup_federation(postgres,mongo);_,_,p,needed,datasets,joins,exprs,*_=f
    for change in ('division','remote_expression','projection','unsupported_type','fact_after_dimension'):
        q,ns,ds,js,es=copy.deepcopy((p,needed,datasets,joins,exprs))
        if change=='division':es['mean']=expression('price / qty',{'price','qty'})[0]
        elif change=='remote_expression':es['mean']=expression('remote',{'remote'})[0]
        elif change=='projection':q.update(metrics=[],group_by=[],fields=['price'])
        elif change=='unsupported_type':ns['dim'][0]['types']=['object']
        else:ds['again']=ds['lines'];ns['again']=ns['lines'];js.append(('again',[('price','price')],'later'))
        assert physical_plan(q,ns,ds,es,js)['strategy']=='application'


@pytest.mark.parametrize('engine',['postgresql','mongodb'])
def test_native_average_finalizes_before_order_and_limit(postgres,mongo,engine):
    conn,schema=postgres;needed,datasets=catalog(schema,engine)
    if engine=='postgresql':conn.commit()
    else:seed_mongo(mongo,ROWS)
    @contextmanager
    def connection(config):yield conn if engine=='postgresql' else {'test':{'lines':mongo}}
    manager=SimpleNamespace(adapter=SimpleNamespace(connection=connection))
    p=logical(metrics=[dict(label='mean',op='avg',expression='price'),dict(label='present',op='count',expression='price')],order_by=[dict(column='mean',direction='desc')],limit=2)
    result=execute_average(manager,{'engine':engine,'database':'test'},p,needed,datasets,[],expressions(p),time.monotonic()+45)
    assert result[:3]==compute(ROWS,p,expressions(p))


def test_saved_federation_uses_current_permissions_and_contract(queries,postgres,mongo):
    f=setup_federation(postgres,mongo,rows=[dict(category='a',price=Decimal('10.20'),qty=2,discount=Decimal('.1'))])
    # Service fixture catalog uses different field IDs and physical column names.
    conn,schema=postgres
    from psycopg import sql
    conn.execute(sql.SQL('ALTER TABLE {}.lines RENAME COLUMN category TO "categoryID"').format(sql.Identifier(schema)))
    conn.execute(sql.SQL('ALTER TABLE {}.lines ALTER COLUMN "categoryID" TYPE integer USING 1').format(sql.Identifier(schema)));conn.commit()
    seed_mongo(mongo,[dict(categoryID=1,name='Food')])
    with queries.store.transaction() as db:
        snapshot=json.loads(db.execute('SELECT document FROM data_source_snapshots WHERE connection_id=?',('pg',)).fetchone()[0]);snapshot['datasets'][0]['schema']=schema
        db.execute('UPDATE data_source_snapshots SET document=? WHERE connection_id=?',(json.dumps(snapshot),'pg'))
        for cid,config in [('pg',{'engine':'postgresql'}),('mongo',{'engine':'mongodb','database':'test'})]:
            db.execute('UPDATE data_source_connections SET secret=? WHERE connection_id=?',(queries.manager.cipher.encrypt(json.dumps(config).encode()).decode(),cid))
    queries.manager.relationships.request(auth());queries.manager.relationships.tick()
    saved=joined_plan(queries);queries.pushdown_enabled=True
    queries.manager.adapter=f[0].adapter
    assert saved['physical_plan']['strategy']=='federated'
    result=queries.execute(auth(),{'plan_id':saved['plan_id']})
    assert result['rows']==[{'mongo_categories_name':'Food','sales':'18.360'}]
    assert result['execution']['strategy']=='federated'
    assert len(result['execution']['fragments'])==3
    contract=json.loads((Path(__file__).resolve().parents[1]/'shared/contracts/data-sources/queries-v1.schema.json').read_text())
    for value in (saved,result):Draft202012Validator(contract).validate(value)
    with pytest.raises(ApiFailure):queries.execute(auth(write=False),{'plan_id':saved['plan_id']})
    with queries.store.transaction(write=False) as db:
        document=db.execute('SELECT document FROM data_query_plans WHERE plan_id=?',(saved['plan_id'],)).fetchone()[0]
    assert '18.360' not in document


def test_local_postgres_prefix_and_multiple_remote_dimensions(postgres,mongo):
    from psycopg import sql
    f=setup_federation(postgres,mongo)
    manager,configs,p,needed,datasets,joins,exprs,rows,dims=f
    conn,schema=postgres
    conn.execute(sql.SQL('CREATE TABLE {}.products (product_code text, product_label text)').format(sql.Identifier(schema)))
    conn.execute(sql.SQL("INSERT INTO {}.products VALUES ('a','Alpha'),('b','Beta')").format(sql.Identifier(schema)));conn.commit()
    needed['products']=[dict(field_id='product_code',name='product_code',types=['text']),dict(field_id='product_label',name='product_label',types=['text'])]
    datasets['products']=dict(schema=schema,name='products',connection=datasets['lines']['connection'])
    configs['products']=configs['lines']
    joins.insert(0,('products',[('category','product_code')],'local'))
    p['joins'].insert(0,dict(relationship_id='local',target_dataset_id='products'))
    # A second independently read remote dimension joins a key from the first.
    collection=mongo.database['labels'];seed_mongo(collection,[dict(label_code='Shared',region='Worldwide')])
    original=manager.adapter.connection
    @contextmanager
    def connection(config):
        if config['engine']=='postgresql':
            with original(config) as db:yield db
        else:yield {'test':{'categories':mongo,'labels':collection}}
    manager.adapter.connection=connection
    needed['labels']=[dict(field_id='label_code',name='label_code',types=['string']),dict(field_id='region',name='region',types=['string'])]
    datasets['labels']=dict(name='labels',connection=datasets['dim']['connection']);configs['labels']=configs['dim']
    joins.append(('labels',[('name','label_code')],'remote2'));p['joins'].append(dict(relationship_id='remote2',target_dataset_id='labels'))
    p['group_by']=['region','product_label']
    actual=execute(f)
    complete,_=join_rows(rows,[dict(product_code='a',product_label='Alpha'),dict(product_code='b',product_label='Beta')],[('category','product_code')])
    complete,_=join_rows(complete,dims,[('category','code')]);complete,_=join_rows(complete,[dict(label_code='Shared',region='Worldwide')],[('name','label_code')])
    assert actual[:3]==compute(complete,p,exprs)
    assert [c['matched_rows'] for c in actual[4]]==[6001,6001,6001]
    assert actual[3]=={'lines':6001,'products':2,'dim':2,'labels':1}


def test_empty_fact_still_validates_unused_dimension_duplicates(postgres,mongo):
    f=setup_federation(postgres,mongo,rows=[],dimensions=[dict(code='z',name='A'),dict(code='z',name='B')])
    with pytest.raises(ApiFailure) as error:execute(f)
    assert error.value.code=='DATA_QUERY_JOIN_INVALID'


def test_external_postgres_dimension_is_read_only(postgres,mongo):
    import psycopg
    from psycopg import sql
    f=setup_federation(postgres,mongo)
    conn,schema=postgres
    conn.execute(sql.SQL("CREATE TABLE {}.categories AS SELECT 'a'::text code,'Shared'::text name UNION ALL SELECT 'b','Shared'").format(sql.Identifier(schema)));conn.commit()
    f[4]['dim'].update(schema=schema,connection=dict(connection_id='two',engine='postgresql'))
    for field in f[3]['dim']:field['types']=['text']
    f[1]['dim']={'engine':'postgresql','dimension':True}
    @contextmanager
    def connection(config):
        if config.get('dimension'):
            with psycopg.connect(postgres_dsn()) as other:yield other
        else:yield conn
    f[0].adapter.connection=connection
    assert execute(f)[:3]==expected(f)


@pytest.mark.parametrize('grouped',[False,True])
@pytest.mark.parametrize('engine',['postgresql','mongodb'])
def test_native_average_empty_input(postgres,mongo,engine,grouped):
    conn,schema=postgres;needed,datasets=catalog(schema,engine)
    if engine=='postgresql':conn.commit()
    else:seed_mongo(mongo,ROWS)
    @contextmanager
    def connection(config):yield conn if engine=='postgresql' else {'test':{'lines':mongo}}
    p=logical(group_by=['category'] if grouped else [],metrics=[dict(label='mean',op='avg',expression='price'),dict(label='count',op='count',expression='')],filters=[dict(field_id='qty',op='gt',value=999)],order_by=[])
    manager=SimpleNamespace(adapter=SimpleNamespace(connection=connection))
    result=execute_average(manager,{'database':'test'},p,needed,datasets,[],expressions(p),time.monotonic()+45)
    assert result[:3]==compute(ROWS,p,expressions(p))


def test_cumulative_budget_counts_each_fragment(postgres,mongo,monkeypatch):
    f=setup_federation(postgres,mongo)
    total=execute(f)[5]
    assert max(v['transferred_bytes'] for v in execute(f)[7])<total
    monkeypatch.setattr('workflow_api.data_query_federation.MAX_BYTES',total-1)
    with pytest.raises(ApiFailure) as error:execute(f)
    assert error.value.code=='DATA_QUERY_LIMIT'


def test_partial_group_limit_is_checked_after_complete_key_validation(postgres,mongo):
    rows=[dict(category='a',price=Decimal(1),qty=i,discount=Decimal(0)) for i in range(5001)]
    f=setup_federation(postgres,mongo,rows=rows);f[2]['group_by']=['qty']
    with pytest.raises(ApiFailure) as error:execute(f)
    assert error.value.code=='DATA_QUERY_LIMIT'


def test_large_native_average_and_complete_group_limit(postgres,mongo):
    f=setup_federation(postgres,mongo)
    p=logical(group_by=[],metrics=[dict(label='mean',op='avg',expression='price')],order_by=[])
    raw=execute_average(f[0],f[1]['lines'],p,{'lines':f[3]['lines']},f[4],[],expressions(p),time.monotonic()+45)
    assert raw[:3]==compute(f[7],p,expressions(p)) and raw[6]==1
    from psycopg import sql
    conn,schema=postgres;conn.rollback();conn.read_only=False
    conn.execute(sql.SQL('UPDATE {}.lines SET qty=number FROM (SELECT ctid,row_number() OVER () AS number FROM {}.lines) numbered WHERE lines.ctid=numbered.ctid').format(sql.Identifier(schema),sql.Identifier(schema)));conn.commit()
    p['group_by']=['qty']
    with pytest.raises(ApiFailure) as error:execute_average(f[0],f[1]['lines'],p,{'lines':f[3]['lines']},f[4],[],expressions(p),time.monotonic()+45)
    assert error.value.code=='DATA_QUERY_LIMIT'


def test_federated_arithmetic_and_dimension_filter_match_scalar(postgres,mongo):
    rows=[dict(category='a' if i%2 else 'b',price=Decimal(i)/100,qty=i%7,discount=Decimal('0.15')) for i in range(1,301)]
    f=setup_federation(postgres,mongo,rows=rows,dimensions=[dict(code='a',name='Keep'),dict(code='b',name='Drop')])
    f[2]['filters']=[dict(field_id='name',op='eq',value='Keep'),dict(field_id='qty',op='gt',value=1)]
    f[2]['metrics']=[dict(label='revenue',op='sum',expression='price * qty * (1 - discount)'),dict(label='mean',op='avg',expression='price * qty * (1 - discount)')]
    f[2]['order_by']=[dict(column='revenue',direction='desc')]
    for metric in f[2]['metrics']:f[6][metric['label']]=expression(metric['expression'],{'price','qty','discount'})[0]
    assert execute(f)[:3]==expected(f)
