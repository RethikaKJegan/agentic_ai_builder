"""Authorized base sorting is independent of displayed detail projection."""
from copy import deepcopy
import pytest
from tests.test_subway_full_queries import engine,installed,AUTH,plan,field
from tests.test_subway_intelligence import subway,overview,selection,execute
from runtime.action_plans import validate_content
from workflow_api.service import ApiFailure


def sorted_details(q,**changes):
    return plan(q,fields=[field(q,'finance.purchaseorders','poNumber')],metrics=[],
                order_by=[dict(column=field(q,'finance.purchaseorders','_id'),direction='desc')],**changes)


def test_unprojected_base_sort_orders_entire_population_before_pagination(engine):
    q,_=engine;query=sorted_details(q,offset=1,limit=2);before=deepcopy(query)
    out=q.execute(AUTH,query);number=query['fields'][0];sort=query['order_by'][0]['column']
    assert out['rows']==[{number:'PO99'},{number:'PO98'}]
    assert [column['id'] for column in out['columns']]==[number]
    assert sort not in out['rows'][0] and sort in out['field_ids']
    assert out['coverage']['complete_scan'] and out['coverage']['matched_records']==100
    assert out['coverage']['has_more'] and query==before


def test_model_boundary_accepts_valid_unprojected_sort_without_mutating_query(engine):
    q,_=engine;query=sorted_details(q)
    workflow={'metadata':{'connected_action_plan':{'actions':[{'action_id':'plan','capability_id':'subway.plan_query'}]}}}
    output=dict(query=deepcopy(query))
    validate_content(workflow,dict(node_id='plan'),output,dict(context=dict(subway_query_catalog=q.catalog(AUTH,'Purchase orders'))))
    assert output['query']==query


def test_unprojected_base_sort_preserves_left_join_rows_and_coverage(engine):
    q,_=engine;query=sorted_details(q,limit=2);catalog=q.catalog(AUTH)
    edge=next(r for r in catalog['relationships'].values() if r['source_dataset_id']==query['base_dataset_id'] and catalog['datasets'][r['target_dataset_id']]['label']=='finance.companies')
    name=field(q,'finance.companies','name')
    query['joins']=[edge['relationship_id']];query['fields'].append(name)
    out=q.execute(AUTH,query);number=query['fields'][0]
    assert out['rows']==[{number:'PO100',name:'Company One'},{number:'PO99',name:None}]
    assert out['coverage']['matched_records']==100
    assert out['join_checks'][0]['matched_rows']==67 and out['join_checks'][0]['unmatched_reference_rows']==33


@pytest.mark.parametrize('kind',['unknown','unjoined','joined','aggregate'])
def test_invalid_sort_scope_remains_rejected_before_source_reads(engine,kind):
    q,_=engine;query=sorted_details(q)
    if kind=='unknown':query['order_by'][0]['column']='unavailable:sort-field'
    if kind in ('unjoined','joined'):
        catalog=q.catalog(AUTH)
        query['order_by'][0]['column']=field(q,'finance.companies','name')
        if kind=='joined':
            edge=next(r for r in catalog['relationships'].values() if r['source_dataset_id']==query['base_dataset_id'] and catalog['datasets'][r['target_dataset_id']]['label']=='finance.companies')
            query['joins']=[edge['relationship_id']]
    if kind=='aggregate':query=plan(q,order_by=query['order_by'])
    with pytest.raises(ApiFailure):q.validate(query,q.catalog(AUTH))


def test_real_crewai_query_and_executor_complete_with_unprojected_sort(subway):
    f=subway;f.query=sorted_details(f.q,limit=2)
    result=overview(f,'Show purchase-order numbers ordered by descending recorded ID.',selection(f.q,['finance.purchaseorders']))
    _,_,run=execute(f,result)
    assert run['status']=='completed'
    out=run['action_instances']['read']['output'];number=f.query['fields'][0]
    assert out['rows']==[{number:'PO100'},{number:'PO99'}]
    assert out['coverage']['matched_records']==100
