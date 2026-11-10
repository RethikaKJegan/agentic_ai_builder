"""Real Mongo equivalence for bounded integer/double population aggregates."""
import time
from contextlib import contextmanager
from types import SimpleNamespace
from decimal import Decimal,localcontext
import pytest
from tests.test_data_query_pushdown import mongo,seed_mongo
from workflow_api.data_query_pushdown import physical_plan,MongoCompiler
from workflow_api.data_query_engine import expression,scalar,compute
from workflow_api.service import ApiFailure


def specification(types=None,engine='mongodb'):
    fields=[dict(field_id='hmr',name='hmr',types=types or ['integer','number'])]
    datasets={'tickets':dict(name='tickets',schema='test',connection=dict(connection_id='one',engine=engine))}
    p=dict(base_dataset_id='tickets',joins=[],fields=[],group_by=[],filters=[dict(field_id='hmr',op='gte',value=0),dict(field_id='hmr',op='lte',value=100)],metrics=[dict(label='count',op='count',expression=''),*[dict(label=op,op=op,expression='hmr') for op in ['min','max','avg']]],order_by=[],limit=1,explanation='Inclusive numeric HMR population.',clarification='')
    expr={m['label']:expression(m['expression'],{'hmr'})[0] for m in p['metrics'] if m['expression']}
    return p,fields,datasets,expr


@pytest.mark.parametrize('types',[['integer','number'],['number','integer'],['number'],['double'],['integer','decimal','number']])
def test_numeric_mongo_families_select_database_aggregation(types):
    p,f,d,e=specification(types);assert physical_plan(p,{'tickets':f},d,e)['strategy']=='mongodb'


@pytest.mark.parametrize('types,engine',[(['integer','string'],'mongodb'),(['number'],'postgresql'),(['integer','number'],'postgresql'),(['number','object'],'mongodb')])
def test_unsupported_types_do_not_gain_pushdown(types,engine):
    p,f,d,e=specification(types,engine);assert physical_plan(p,{'tickets':f},d,e)['strategy']=='application'


def test_full_population_beyond_5000_matches_independent_decimal_statistics(mongo):
    values=[0,0.5,25,99.5,100.0,101,-1,None]*751+[1.23456789,0.1]
    rows=[{'hmr':v} for v in values]+[{}]
    seed_mongo(mongo,rows);p,f,d,e=specification()
    from workflow_api.data_query_federation import execute_average
    @contextmanager
    def connection(config):yield mongo.database.client
    manager=SimpleNamespace(adapter=SimpleNamespace(connection=connection))
    d['tickets']['name']=mongo.name
    actual,total,matched,counts,checks,size,transferred=execute_average(manager,{'database':mongo.database.name},p,{'tickets':f},d,[],e,time.monotonic()+45)
    count=counts['tickets']
    expected=compute([{k:scalar(v) for k,v in r.items()} for r in rows],p,e)
    assert (actual,total,matched)==expected
    selected=[Decimal(str(v)) for v in values if v is not None and 0<=v<=100]
    assert actual[0]['count']==len(selected)
    assert actual[0]['min']==min(selected) and actual[0]['max']==max(selected)
    with localcontext() as ctx:
        ctx.prec=38
        assert actual[0]['avg']==sum(selected)/len(selected)
    assert count==len(rows)>5000 and matched==len(selected) and total==1


@pytest.mark.parametrize('value',[1.0000000000000002,1000000000000000.5,1.234567891,float('nan'),float('inf'),'12',True,{'unexpected':1}])
def test_lossy_nonfinite_outside_envelope_or_type_drift_is_rejected(mongo,value):
    seed_mongo(mongo,[{'hmr':1},{'hmr':value}]);p,f,d,e=specification()
    with pytest.raises(ApiFailure) as caught:MongoCompiler(p,f,e).execute(mongo,time.monotonic()+45)
    assert caught.value.code=='DATA_QUERY_TYPE'
