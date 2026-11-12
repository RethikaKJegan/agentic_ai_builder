"""Real query/assessment execution; no live models or external actions."""
from copy import deepcopy
import json
import pytest
from tests.test_subway_persistent_demo import demo,engine,installed,AUTH,query
from workflow_api.subway_assessments import SubwayAssessments,ASSESSMENTS
from workflow_api.business_knowledge_model import digest
from workflow_api.service import ApiFailure
from runtime.service import RuntimeFailure
from runtime.recovery import classify


def fields(q,col):
    c=q.catalog(AUTH);d=next(d for d in c['datasets'].values() if d['role']=='finance' and d['collection']==col)
    return {f['name']:f['field_id'] for f in d['fields']}


@pytest.mark.parametrize('kind',list(ASSESSMENTS))
def test_all_assessments_accept_valid_extra_base_fields_and_audit_effective_selection(demo,kind):
    _,q=demo;col=ASSESSMENTS[kind];fs=fields(q,col);selection=query(q,col);selection['fields']=list(fs.values())[:10]
    if fs['_id'] not in selection['fields']:selection['fields'].append(fs['_id'])
    inputs=dict(assessment=kind,query=selection);saved=deepcopy(inputs)
    output=SubwayAssessments(q).execute(AUTH,inputs)
    assert inputs==saved and output['input_sha256']==digest(saved)
    audit=output['coverage']['assessment_selection'];assert audit['requested_fields']==selection['fields'] and audit['effective_fields']==[fs['_id']]
    with q.store.transaction(write=False) as db:
        receipt=json.loads(db.execute('select document from subway_query_receipts where query_id=?',(audit['query_id'],)).fetchone()[0])
    assert receipt['query']==dict(selection,fields=[fs['_id']])
    assert output['report']['provenance']['mode']=='modeled_demonstration'


@pytest.mark.parametrize('projection',['missing_id','empty','extra'])
def test_projection_changes_preserve_filters_hidden_sort_and_page(demo,projection):
    _,q=demo;fs=fields(q,'purchaseorders');selection=query(q)
    selection.update(fields=[] if projection=='empty' else [fs['vendorName']] if projection=='missing_id' else [fs['_id'],fs['vendorName'],fs['totalAmount']],filters=[dict(field_id=fs['totalAmount'],op='gte',value=3000)],order_by=[dict(column=fs['totalAmount'],direction='desc')],offset=1,limit=2)
    expected=q.execute(AUTH,dict(selection,fields=[fs['_id']]))
    output=SubwayAssessments(q).execute(AUTH,dict(assessment='purchase_order_reconciliation',query=selection))
    assert output['coverage']['matched_records']==expected['coverage']['matched_records']
    assert output['coverage']['offset']==1 and output['coverage']['returned_rows']==2
    selection_audit=output['coverage']['assessment_selection']
    with q.store.transaction(write=False) as db:
        receipt=json.loads(db.execute('select document from subway_query_receipts where query_id=?',(selection_audit['query_id'],)).fetchone()[0])
    assert receipt['query']==dict(selection,fields=[fs['_id']])
    expected_ids=[row[fs['_id']] for row in expected['rows']]
    assert {item['po_id'] for item in output['report']['reconciliations']}==set(expected_ids)


@pytest.mark.parametrize('invalid',['foreign_field','duplicate_field','wrong_base','join','metric','group','limit'])
def test_unsupported_queries_are_rejected_before_source_read(demo,monkeypatch,invalid):
    _,q=demo;selection=query(q);fs=fields(q,'purchaseorders')
    if invalid=='foreign_field':selection['fields'].append('another_tenant_secret')
    elif invalid=='duplicate_field':selection['fields']*=2
    elif invalid=='wrong_base':selection=query(q,'invoicedatas')
    elif invalid=='join':selection['joins']=['invented_join']
    elif invalid=='metric':selection.update(fields=[],metrics=[dict(label='total',op='count',field_id=None)])
    elif invalid=='group':selection['group_by']=[fs['status']]
    else:selection['limit']=21
    def forbidden(*args):pytest.fail('Invalid query reached source execution')
    monkeypatch.setattr(q,'execute',forbidden)
    with pytest.raises(ApiFailure) as caught:SubwayAssessments(q).execute(AUTH,dict(assessment='purchase_order_reconciliation',query=selection))
    assert caught.value.code in ('SUBWAY_ASSESSMENT_INVALID','SUBWAY_QUERY_DENIED','SUBWAY_QUERY_INVALID')


def test_connector_exposes_validation_code_and_closed_retry_policy(demo):
    _,q=demo;c=SubwayAssessments(q)
    with pytest.raises(RuntimeFailure) as caught:c.invoke(dict(tool_id='subway_assess'),{},'test')
    assert caught.value.code=='SUBWAY_ASSESSMENT_DENIED' and caught.value.status==403
    with pytest.raises(RuntimeFailure) as caught:c.bind_context(dict(metadata={}),{},AUTH,{})
    assert caught.value.code=='SUBWAY_QUERY_DENIED'
    failure=classify('SUBWAY_ASSESSMENT_INVALID',task='assess',source='subway_assess')
    assert failure['category']=='incorrect_source_mapping' and not failure['retry_eligible']
    assert classify('SUBWAY_KNOWLEDGE_STALE')['category']=='stale_metadata'
    assert classify('SUBWAY_QUERY_TIMEOUT',external_write=True)['category']=='uncertain_external_write'
    assert classify('INVOCATION_FAILED')['category']=='internal_execution_failure'
