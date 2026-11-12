"""Routing source bounds cannot expand through global field/relationship hints."""
from copy import deepcopy
import pytest
from jsonschema import Draft202012Validator
from workflow_api.subway_queries import dataset_selection_schema,SELECTION,schema_identity_budget
from workflow_api.overview_automation import ROUTE
from workflow_api.service import ApiFailure
from tests.test_subway_intelligence import engine,installed,subway,selection,overview,execute
from tests.test_subway_full_queries import field,plan


def test_new_transport_cannot_choose_global_fields_or_edges_outside_four_sources():
    discovery=dict(sources=[dict(dataset_id='source_'+str(i),fields=[dict(field_id='field_'+str(i),name='amount',types=['number'])]) for i in range(6)],relationships=[dict(relationship_id='outside_edge')])
    base=deepcopy(ROUTE);base['properties']['subway_selection']=deepcopy(SELECTION)
    count,characters=schema_identity_budget(base)
    schema=dataset_selection_schema(discovery,enum_budget=count,string_budget=characters)
    base['properties']['subway_selection']=schema
    assert min(schema_identity_budget(base))>=0
    v=dict(dataset_ids=['source_'+str(i) for i in range(4)],field_ids=[],relationship_ids=[],metadata_mode='datasets',filter_branches=[],percentage_basis='none',measure_basis='Only selected sources.',clarification='',business_resolution=dict(status='ready',question='',notes=''))
    validator=Draft202012Validator(schema)
    assert validator.is_valid(v)
    assert not validator.is_valid(dict(v,field_ids=['field_5']))
    assert not validator.is_valid(dict(v,relationship_ids=['outside_edge']))
    assert not validator.is_valid(dict(v,dataset_ids=v['dataset_ids']+['source_4']))
    assert not validator.is_valid(dict(v,dataset_ids=['foreign']))
    # Global field/edge cardinality cannot consume the routing identity allowance.
    discovery['sources'][0]['fields']*=2000
    discovery['relationships']=[dict(relationship_id='edge_'+str(i)) for i in range(2000)]
    assert Draft202012Validator(dataset_selection_schema(discovery)).is_valid(v)


def test_scoped_metadata_contains_only_selected_endpoints_and_required_keys(subway):
    f=subway;q=f.q
    chosen=selection(q,['finance.invoicedatas','finance.purchaseorders']);chosen['metadata_mode']='datasets'
    original=deepcopy(chosen);normalized=q.selection(f.auth,chosen)
    assert normalized['dataset_ids']==chosen['dataset_ids'] and chosen==original
    view=q.catalog(f.auth,'Compare invoices and linked order amounts',normalized)
    assert {d['dataset_id'] for d in view['sources']}==set(chosen['dataset_ids'])
    assert view['relationships']
    fields={x['field_id'] for d in view['sources'] for x in d['fields']}
    for edge in view['relationships']:
        assert {edge['source_dataset_id'],edge['target_dataset_id']}<=set(chosen['dataset_ids'])
        assert {edge['source_field_id'],edge['target_field_id']}<=fields
    assert len(normalized['dataset_ids'])==2


def test_legacy_overflow_and_contradictory_dataset_mode_remain_denied(subway):
    f=subway;catalog=f.q.catalog(f.auth)
    sources=[s for s in catalog['datasets'].values() if s['fields']][:5]
    old=dict(dataset_ids=[sources[0]['dataset_id']],field_ids=[s['fields'][0]['field_id'] for s in sources],relationship_ids=[],measure_basis='Controlled union reproduction.',clarification='')
    with pytest.raises(ApiFailure) as error:f.q.selection(f.auth,old)
    assert error.value.code=='SUBWAY_SELECTION_INVALID'
    old['metadata_mode']='datasets'
    with pytest.raises(ApiFailure):f.q.selection(f.auth,old)
    with pytest.raises(ApiFailure):f.q.catalog(f.auth,'Count records',old)
    minimal=selection(f.q,['finance.purchaseorders']);minimal['metadata_mode']='datasets'
    assert len(f.q.selection(f.auth,minimal)['dataset_ids'])==1


def test_dataset_routing_preserves_real_join_execution_and_unmatched_coverage(subway):
    from decimal import Decimal
    f=subway;q=f.q;catalog=q.catalog(f.auth)
    invoices=next(d['dataset_id'] for d in catalog['datasets'].values() if d['label']=='finance.invoicedatas')
    orders=next(d['dataset_id'] for d in catalog['datasets'].values() if d['label']=='finance.purchaseorders')
    edge=next(e for e in catalog['relationships'].values() if e['source_dataset_id']==invoices and e['target_dataset_id']==orders)
    f.rows['subway_finance']['invoicedatas']=[dict(_id=1,poId=1,invoiceAmount=Decimal('10')),dict(_id=2,poId=99999,invoiceAmount=Decimal('12.5')),dict(_id=3,poId=None,invoiceAmount=Decimal('8'))]
    invoice_id=field(q,'finance.invoicedatas','_id');invoice_amount=field(q,'finance.invoicedatas','invoiceAmount');order_amount=field(q,'finance.purchaseorders','totalAmount')
    f.query=plan(q,'finance.invoicedatas',joins=[edge['relationship_id']],fields=[invoice_id,invoice_amount,edge['source_field_id'],edge['target_field_id'],order_amount],metrics=[],limit=3)
    chosen=selection(q,['finance.invoicedatas','finance.purchaseorders']);chosen['metadata_mode']='datasets'
    chosen['business_resolution']=dict(status='ready',question='',notes='Preserve distinct named amounts and link coverage; no approved equivalence or policy finding.')
    result=overview(f,'Compare invoice records to their linked orders and disclose missing links and source limits.',chosen)
    _,_,run=execute(f,result)
    output=run['action_instances']['read']['output']
    assert output['coverage']['complete_scan'] and output['coverage']['matched_records']==3
    check=output['join_checks'][0]
    assert check['matched_rows']==check['missing_reference_rows']==check['unmatched_reference_rows']==1
    assert output['rows'][0][invoice_amount]=='10' and output['rows'][0][order_amount]=='1.01'
    assert all(r[edge['target_field_id']] is None for r in output['rows'][1:])
    assert run['action_instances']['report']['state']=='completed'
