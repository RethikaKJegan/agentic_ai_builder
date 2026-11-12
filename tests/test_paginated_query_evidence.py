"""Native receipt validation and recurring execution with incomplete detail pages."""
from copy import deepcopy
import json
import pytest
from runtime.service import digest
from tests.test_subway_autonomy import subway,engine,installed,start,decision,drain,load
from tests.test_subway_full_queries import plan,field
from tests.test_subway_automations import schedule,dispatch
from workflow_api.workflow_adaptive import evidence


def evaluator(ctx,**_):
    result=decision(ctx)
    valid=[key for key,item in ctx['evidence'].items() if item['valid']]
    if valid:
        assert any(l['code']=='QUERY_DETAIL_PAGINATED' for l in ctx['deterministic_limitations'])
        assert 'requirements needing unreturned detail remain unsatisfied' in ctx['evidence_projection']
        result['assessment']['requirements'][0].update(status='verified',evidence_ids=valid)
        result['assessment'].update(completion_eligible=True,gaps=[],source_limitations=['Only returned records were reviewed; the detail response is paginated.'])
    return result


def detail(f,byte_limit,monkeypatch):
    if byte_limit:
        import workflow_api.subway_query_pages as pages
        original=pages.bounded_page
        monkeypatch.setattr(pages,'bounded_page',lambda output:original(output,max_bytes=12000))
        for row in f.rows['subway_finance']['purchaseorders']:row['poNumber']='synthetic '+str(row['_id'])+'x'*500
    f.query=plan(f.q,fields=[field(f.q,'finance.purchaseorders','poNumber')],metrics=[],limit=100 if byte_limit else 2)


def check(f,run):
    assert run['status']=='completed',run.get('error_code')
    output=run['action_instances']['read']['output'];coverage=output['coverage']
    assert coverage['complete_scan'] and coverage['has_more'] and not coverage['aggregate_complete']
    assert coverage['returned_rows']<coverage['matched_records']==100
    assert any(l['code']=='QUERY_DETAIL_PAGINATED' for l in run['adaptive']['deterministic_limitations'])
    report=[i for i in f.model_inputs if 'data' in i][-1]
    assert report['data']['query_detail_pages']['read']==dict(query_id=output['query_id'],coverage=coverage)
    assert 'Do not infer population totals' in report['instructions']
    assert 'query_detail_pages' not in output
    return output


@pytest.mark.parametrize('byte_limit',[False,True])
def test_reviewed_detail_page_is_valid_scoped_evidence(subway,monkeypatch,byte_limit):
    f=subway;rid,_,_=start(f,evaluator);detail(f,byte_limit,monkeypatch)
    output=check(f,drain(f,rid))
    if byte_limit:assert output['coverage']['display_limited_by']=='response_bytes'


def test_two_daily_occurrences_accept_detail_and_do_not_duplicate(subway,monkeypatch):
    f=subway;auto,record,_=schedule(f,monkeypatch,evaluator);detail(f,True,monkeypatch)
    f.now=record['due'];first=dispatch(f,auto)
    assert len(first)==1 and first[0]['state']=='completed'
    check(f,load(f,first[0]['run_id']))
    auto.tick(f.service.worker_authenticate)
    assert len(auto.listing(f.auth,'occurrence')['items'])==1
    f.now=auto.get(f.auth,record['id'])['due'];second=dispatch(f,auto)
    assert len(second)==2 and all(o['state']=='completed' for o in second)
    check(f,load(f,second[-1]['run_id']))


@pytest.mark.parametrize('mutation',['fingerprint','scope','incomplete_scan','warnings','truncated','authority'])
def test_pagination_never_overrides_invalid_receipts(subway,monkeypatch,mutation):
    f=subway;rid,_,workflow=start(f,evaluator);detail(f,False,monkeypatch);run=deepcopy(drain(f,rid))
    item=run['action_instances']['read'];output=item['output']
    if mutation=='fingerprint':output['rows'][0]['forged']='changed'
    if mutation=='scope':output['scope']['owner_id']='another-owner'
    if mutation in ('incomplete_scan','warnings','truncated'):
        if mutation=='incomplete_scan':output['coverage']['complete_scan']=False
        if mutation=='warnings':output['coverage']['warnings']=['partial source']
        if mutation=='truncated':output['coverage']['truncated']=True
        item['output_fingerprint']=digest(output)
        # Match persisted receipt too, isolating scan-quality checks from integrity.
        with f.service.store.transaction() as db:
            receipt=json.loads(db.execute('SELECT document FROM subway_query_receipts WHERE query_id=?',(output['query_id'],)).fetchone()[0])
            receipt['coverage']=deepcopy(output['coverage'])
            db.execute('UPDATE subway_query_receipts SET document=? WHERE query_id=?',(json.dumps(receipt),output['query_id']))
    if mutation=='authority':
        original=f.q.catalog
        def revoked(auth):
            catalog=deepcopy(original(auth));catalog['stamps']={'revoked':True};return catalog
        monkeypatch.setattr(f.q,'catalog',revoked)
    with f.service.store.transaction(write=False) as db:
        ev,limits=evidence(f.service.runtime_runner.runtime,db,run,workflow,f.auth)
    assert ev and not any(e['valid'] for e in ev.values())
    assert any(l['code']=='EVIDENCE_INCOMPLETE_OR_UNVERIFIED' for l in limits)
