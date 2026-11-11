"""Actual isolated Mongo snapshot execution for full-source timestamp filters."""
from datetime import datetime, timezone, timedelta
import time
import pytest
from tests.test_data_query_pushdown import mongo,seed_mongo
from workflow_api.data_query_pushdown import physical_plan,MongoCompiler
from workflow_api.service import ApiFailure


def specification():
    f=[dict(field_id='created',name='created',types=['datetime','null'])]
    d={'records':dict(name='records',schema='test',connection=dict(connection_id='one',engine='mongodb'))}
    p=dict(base_dataset_id='records',joins=[],fields=[],group_by=[],filters=[dict(field_id='created',op='gte',value='2026-11-09T18:30:00+00:00'),dict(field_id='created',op='lt',value='2026-11-10T18:30:00+00:00')],metrics=[dict(label='count',op='count',expression='')],order_by=[],limit=1,explanation='One local reporting day.',clarification='')
    return p,f,d


def test_mongo_date_query_counts_full_source_beyond_fallback_limit(mongo):
    start=datetime(2026,11,9,18,30,tzinfo=timezone.utc);end=start+timedelta(days=1)
    rows=[{'created':start-timedelta(days=3)} for _ in range(6001)]
    rows += [{'created':start},{'created':start+timedelta(hours=3)},{'created':end-timedelta(milliseconds=1)},{'created':end},{'created':None},{}]
    seed_mongo(mongo,rows);p,f,d=specification()
    assert physical_plan(p,{'records':f},d,{})['strategy']=='mongodb'
    actual,total,matched,read,size=MongoCompiler(p,f,{}).execute(mongo,time.monotonic()+45)
    assert actual==[{'count':3}] and total==1 and matched==3 and read==len(rows)>5000


@pytest.mark.parametrize('bad',['2026-11-10','2026-11-10T00:00:00', '2026-11-10T00:00:00.000001+00:00'])
def test_timestamp_filter_requires_timezone_and_exact_bson_precision(bad):
    p,f,d=specification();p['filters'][0]['value']=bad
    with pytest.raises(ApiFailure):MongoCompiler(p,f,{})


def test_wrong_bson_type_outside_matching_window_does_not_hide_source_drift(mongo):
    seed_mongo(mongo,[{'created':datetime(2026,11,10,tzinfo=timezone.utc)},{'created':'2020-01-01'}])
    p,f,d=specification()
    with pytest.raises(ApiFailure) as caught:MongoCompiler(p,f,{}).execute(mongo,time.monotonic()+45)
    assert caught.value.code=='DATA_QUERY_TYPE'
