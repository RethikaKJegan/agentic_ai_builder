"""Cited policy drafts and comparisons never establish business authority."""
from copy import deepcopy
from hashlib import sha256
import json
from unittest.mock import patch
import pytest
from tests.test_business_graph import graph,build
from tests.test_business_compiler import compiled_draft
from tests.test_business_generation import generation
from tests.test_business_ontology import foundation,auth
from workflow_api.business_documents import BusinessDocuments
from workflow_api.business_policies import BusinessPolicies,CLAUSES,checked
from workflow_api.service import ApiFailure

TEXT='''Fixture policy version V1. Effective 2026-01-01 through 2026-12-31, inclusive, assessed on assessment date. OEM reference o1; engine model M. Sale coverage 12 months. Invoice coverage 18 months. Operating-hour limit 1000. Coverage limits include the boundary. Exclusions require evidence; missing exclusion inputs require review. Fixture calculation: sale and hours, assessment date, clamped calendar-month anniversary, inclusive period and hours. Required exclusion code misuse_check.'''

@pytest.fixture
def policies(graph):
    x=graph;x.reader.rows['tickets'][0]['engineModal']='M'
    service=BusinessPolicies(x.f,x.service,lambda *args:auth())
    source=BusinessDocuments(x.f).add(auth(),dict(title='Fixture policy',kind='policy',module_ids=['warranty'],text=TEXT))
    return x,service,source


def body(source,**changes):
    values=dict(source_version='V1',effective_from='2026-01-01',effective_to='2026-12-31',oem_references=['o1'],models=['M'],date_basis='assessment_date',effective_bounds='inclusive',sale_months=12,invoice_months=18,max_hours='1000',coverage_boundaries='inclusive',exclusions='Evidence required',coverage_mode='sale_and_hours',coverage_date_basis='assessment_date',period_method='calendar_month_anniversary_clamped',period_boundary='inclusive',hours_boundary='inclusive',exclusion_mode='checks_required',exclusion_checks=['misuse_check'])
    clauses={key:dict(value=value,quote=TEXT) for key,value in values.items()}
    return {**dict(request_key='policy_request_001',expected_revision=0,policy=dict(policy_key='fixture-policy',title='Fixture policy draft',source_id=source['source_id'],clauses=clauses)),**changes}


def request(policy,g,**changes):
    return {**dict(policy_id=policy['policy_id'],ticket_node_id=next(r['node_id'] for r in g['records'] if r['collection']=='tickets'),assessment_at='2026-06-01T12:00:00+05:30',invoice_node_id=None),**changes}


def test_cited_versions_preserve_ontology_graph_and_immutable_policy_history(policies):
    x,service,source=policies;g=build(x);before=x.f.get(auth());first=service.save(auth(),body(source));original=deepcopy(first)
    assert first['missing_clauses']==[] and first['business_policy_verified'] is first['executable'] is False
    assert service.save(auth(),body(source))==first
    next_body=body(source,expected_revision=1,request_key='policy_request_002');next_body['policy']['clauses']['max_hours']['value']=None;next_body['policy']['clauses']['max_hours']['quote']=None
    second=service.save(auth(),next_body)
    assert second['revision']==2 and second['missing_clauses']==['max_hours']
    assert service.get(auth(),first['policy_id'])==original and x.f.get(auth())==before
    assert x.service.get(auth(),x.snapshot['version_id'],g['graph_id'])==g
    assert [r['revision'] for r in service.list(auth())['items']]==[2,1]
    with pytest.raises(ApiFailure):service.save(auth(),{**body(source),'expected_revision':2})
    with pytest.raises(ApiFailure):service.save(auth(),body(source,request_key='policy_stale_001'))
    with x.f.store.transaction(write=False) as db:
        events=[json.loads(r[0]) for r in db.execute('SELECT document FROM business_ontology_events')]
        assert sum(e['action']=='save_policy_draft' for e in events)==2


def test_matching_checks_still_require_review_and_no_network(policies):
    x,service,source=policies;policy=service.save(auth(),body(source));g=build(x);calls=len(x.reader.calls)
    with patch('socket.create_connection',side_effect=AssertionError('No external calls')):
        report=service.compare(auth(write=False),x.snapshot['version_id'],g['graph_id'],request(policy,g))
    assert all(c['status']=='match' for c in report['checks']) and report['candidate_comparison']=='all_observed_checks_match'
    assert report['status']=='requires_review' and report['eligibility']=='not_evaluated'
    assert report['rules_executed'] is report['business_policy_verified'] is False
    assert report['model_calls']==report['company_queries']==0 and len(x.reader.calls)==calls
    assert report['provenance']['policy_sha256']==policy['sha256']
    assert service.compare(auth(),x.snapshot['version_id'],g['graph_id'],request(policy,g))['report_sha256']==report['report_sha256']


@pytest.mark.parametrize('change',[
 lambda b:b.update(expected_revision=True),lambda b:b.update(request_key='bad'),lambda b:b.update(extra=True),
 lambda b:b['policy'].update(policy_key='../path'),lambda b:b['policy'].update(title=''),
 lambda b:b['policy']['clauses']['max_hours'].update(value='NaN'),lambda b:b['policy']['clauses']['sale_months'].update(value=True),
 lambda b:b['policy']['clauses']['effective_from'].update(value='2027-01-01'),lambda b:b['policy']['clauses']['effective_to'].update(value='2026-02-30'),
 lambda b:b['policy']['clauses']['oem_references'].update(value=['*']),lambda b:b['policy']['clauses']['models'].update(value=['M','M']),
 lambda b:b['policy']['clauses']['date_basis'].update(value='today'),lambda b:b['policy']['clauses']['exclusions'].update(quote='Invented quotation'),lambda b:b['policy']['clauses']['exclusions'].update(quote='    '),lambda b:b['policy']['clauses']['exclusions'].update(quote=' V1 '),
 lambda b:b['policy']['clauses']['max_hours'].update(value=None),lambda b:b['policy']['clauses'].pop('max_hours'),
])
def test_bad_policy_never_advances_head_or_events(policies,change):
    x,service,source=policies;b=body(source);change(b)
    with pytest.raises(ApiFailure):service.save(auth(),b)
    assert service.list(auth())['items']==[]
    with x.f.store.transaction(write=False) as db:assert db.execute('SELECT COUNT(*) FROM business_policy_heads').fetchone()[0]==0


def test_sources_authority_scopes_and_integrity(policies):
    x,service,source=policies;b=body(source)
    for other in [auth(write=False),auth(owner='bob'),auth(workspace='two')]:
        with pytest.raises(ApiFailure):service.save(other,b)
    invalid=BusinessDocuments(x.f).add(auth(),dict(title='Code is not policy',kind='application_code',module_ids=['warranty'],text=TEXT))
    code_body=body(invalid,request_key='code_interpretation_001');code_body['policy']['policy_key']='code-reference'
    code_draft=service.save(auth(),code_body)
    assert code_draft['interpretation_basis']=='descriptive_implementation' and code_draft['business_policy_verified'] is False
    wrong=BusinessDocuments(x.f).add(auth(),dict(title='Other module',kind='policy',module_ids=['quality'],text=TEXT))
    with pytest.raises(ApiFailure):service.save(auth(),body(wrong))
    saved=service.save(auth(),b)
    for other in [auth(owner='bob'),auth(workspace='two')]:
        assert service.list(other)['items']==[]
        with pytest.raises(ApiFailure):service.get(other,saved['policy_id'])
    saved['clauses']['max_hours']['value']='9999'
    with pytest.raises(ApiFailure):checked(saved)
    service.resolve=lambda *args:{**auth(),'decision':'deny'}
    with pytest.raises(ApiFailure):service.save(auth(),body(source,expected_revision=1,request_key='revoked_request'))


@pytest.mark.parametrize('basis,selected,expected',[('invoice_date',False,'unavailable'),('invoice_date',True,'unavailable'),('sale_date',False,'unavailable')])
def test_missing_selected_date_has_no_fallback(policies,basis,selected,expected):
    x,service,source=policies;b=body(source);b['policy']['clauses']['date_basis']['value']=basis;policy=service.save(auth(),b);g=build(x)
    req=request(policy,g);req['invoice_node_id']=next(r['node_id'] for r in g['records'] if r['collection']=='enginedetails') if selected else None
    result=service.compare(auth(),x.snapshot['version_id'],g['graph_id'],req)
    assert result['checks'][2]['status']==expected and result['checks'][2]['observed'] is None


def test_invoice_selection_dates_boundaries_unknown_end_and_scope_differences(policies):
    x,service,source=policies;x.reader.rows['enginedetails'][0]['invoiceDate']='2026-01-01';x.reader.rows['tickets'][0]['oem']='other'
    b=body(source);b['policy']['clauses']['date_basis']['value']='invoice_date';b['policy']['clauses']['effective_bounds']['value']='exclusive';p1=service.save(auth(),b);g=build(x)
    req=request(p1,g);req['invoice_node_id']=next(r['node_id'] for r in g['records'] if r['collection']=='enginedetails')
    result=service.compare(auth(),x.snapshot['version_id'],g['graph_id'],req)
    assert result['checks'][0]['status']=='different' and result['checks'][2]['status']=='different'
    b2=body(source,expected_revision=1,request_key='policy_request_002');b2['policy']['clauses']['effective_to']=dict(value=None,quote=None);p2=service.save(auth(),b2)
    assert service.compare(auth(),x.snapshot['version_id'],g['graph_id'],{**req,'policy_id':p2['policy_id']})['checks'][2]['status']=='unavailable'


@pytest.mark.parametrize('change',[{'assessment_at':'2026-01-01'},{'assessment_at':'2026-01-01T00:00:00'},{'assessment_at':'bad'}, {'invoice_node_id':'foreign'},{'ticket_node_id':'foreign'},{'policy':{}},{'policy_id':False}])
def test_invalid_comparison_requests(policies,change):
    x,service,source=policies;p=service.save(auth(),body(source));g=build(x)
    with pytest.raises(ApiFailure):service.compare(auth(),x.snapshot['version_id'],g['graph_id'],{**request(p,g),**change})


def test_concurrent_identical_requests_commit_one_revision(policies):
    from concurrent.futures import ThreadPoolExecutor
    x,service,source=policies;other=BusinessPolicies(x.f,x.service,lambda *args:auth());b=body(source)
    with ThreadPoolExecutor(max_workers=2) as pool:
        results=list(pool.map(lambda instance:instance.save(auth(),b),[service,other]))
    assert results[0]==results[1] and len(service.list(auth())['items'])==1
    with x.f.store.transaction(write=False) as db:assert db.execute('SELECT revision FROM business_policy_heads').fetchone()[0]==1


def test_historical_policy_comparison_after_disconnect_is_read_only(policies):
    x,service,source=policies;p=service.save(auth(),body(source));g=build(x)
    with x.f.store.transaction() as db:
        db.execute("UPDATE data_source_connections SET document=? WHERE connection_id='quality'",(json.dumps(dict(connection_status='disconnected',metadata_revision=10)),))
    with x.f.store.transaction(write=False) as db:
        before={name:db.execute('SELECT * FROM '+name).fetchall() for name in ['business_policy_heads','business_policy_versions','business_ontology_events','business_ontology_versions','business_ontology_graphs','data_source_connections']}
    assert service.compare(auth(write=False),x.snapshot['version_id'],g['graph_id'],request(p,g))['status']=='requires_review'
    for other in [auth(owner='bob'),auth(workspace='two')]:
        with pytest.raises(ApiFailure):service.compare(other,x.snapshot['version_id'],g['graph_id'],request(p,g))
    with x.f.store.transaction(write=False) as db:assert all(db.execute('SELECT * FROM '+name).fetchall()==rows for name,rows in before.items())


def test_policy_http_scope_origin_payloads_and_comparison(tmp_path,policies):
    from fastapi.testclient import TestClient
    from workflow_api.main import create_app
    x,_,_=policies;app=create_app(database=tmp_path/'policies.sqlite',dev_auth=True,start_workers=False,planning_worker_enabled=False)
    client=TestClient(app);root='/business-ontology/v1'
    assert client.get(root+'/warranty-policies').status_code==401
    client.get('/session');client.cookies.set('builder_dev_session',client.cookies.get('builder_dev_session'),path='/')
    with app.state.workflow_service.store.transaction() as db:
        for cid in ('service','quality'):
            doc=dict(connection_id=cid,name=cid,engine='mongodb',connection_status='connected',metadata_revision=1)
            db.execute('INSERT INTO data_source_connections VALUES (?,?,?,?,?)',(cid,'local-workspace','local-builder',None,json.dumps(doc)))
    state=client.post(root+'/initialize',json={'sources':{'service':'service','quality':'quality'}}).json()['data'];version=state['current_version_id']
    source=client.post(root+'/documents',json=dict(title='HTTP fixture policy',kind='policy',module_ids=['warranty'],text=TEXT)).json()['data'];b=body(source)
    assert client.post(root+'/warranty-policies',json=b,headers={'origin':'https://untrusted.example'}).status_code==403
    assert client.post(root+'/warranty-policies',content='bad-json').status_code==422
    saved=client.post(root+'/warranty-policies',json=b);assert saved.status_code==200 and saved.headers['cache-control']=='no-store'
    p=saved.json()['data'];assert client.post(root+'/warranty-policies',json=b).json()['data']['policy_id']==p['policy_id']
    loaded=client.get(root+'/warranty-policies/'+p['policy_id']).json()['data']
    assert all(loaded[key]==p[key] for key in ('policy_id','sha256','clauses','source','revision'))
    assert len(client.get(root+'/warranty-policies').json()['data']['items'])==1
    from pathlib import Path
    bundle=json.loads(Path('ontology/business-reference/simpson-evidence.json').read_text());code=next(d for d in bundle['documents'] if d['source_id']=='ref_621995136ad5360339474d92')
    assert client.post(root+'/documents',json={k:code[k] for k in ('title','kind','module_ids','text')}).status_code==200
    imported=client.post(root+'/warranty-policies/import-implementation',json={})
    assert imported.status_code==200 and len(imported.json()['data']['items'])==5
    assert client.post(root+'/warranty-policies/import-implementation',json={'verified':True}).status_code==422
    assert client.post(root+'/warranty-policies/import-implementation',json={},headers={'origin':'https://untrusted.example'}).status_code==403
    g=deepcopy(build(x));g['version_id']=version
    with app.state.workflow_service.store.transaction() as db:db.execute('INSERT INTO business_ontology_graphs VALUES (?,?,?,?,?,?,?)',('local-workspace','local-builder',version,g['graph_id'],'http_policy_graph','fixture',json.dumps(g)))
    endpoint=root+'/versions/'+version+'/graphs/'+g['graph_id']+'/policy-comparison'
    with patch('socket.create_connection',side_effect=AssertionError('No external calls')):response=client.post(endpoint,json=request(p,g))
    assert response.status_code==200 and response.headers['cache-control']=='no-store' and response.json()['data']['eligibility']=='not_evaluated'
    assert client.post(endpoint,json={**request(p,g),'policy':{}}).status_code==422
    app.state.workflow_auth['subject']['subject_id']='other'
    assert client.get(root+'/warranty-policies/'+p['policy_id']).status_code==404
    assert client.post(endpoint,json=request(p,g)).status_code==404


def implementation_source(x):
    from pathlib import Path
    bundle=json.loads(Path('ontology/business-reference/simpson-evidence.json').read_text())
    source=next(d for d in bundle['documents'] if d['source_id']=='ref_621995136ad5360339474d92')
    return BusinessDocuments(x.f).add(auth(),{k:source[k] for k in ('title','kind','module_ids','text')})


def test_known_implementation_import_is_atomic_idempotent_and_not_policy(policies,tmp_path):
    from workflow_api.business_release import run
    x,service,_=policies;source=implementation_source(x);g=build(x)
    with patch('socket.create_connection',side_effect=AssertionError('No network')):
        library=service.import_implementation(auth(),{});again=service.import_implementation(auth(),{})
    assert library==again and len(library['items'])==4
    expected={'tafe':(27,24,'2000'),'cnh':(24,21,'2000'),'terex':(24,18,'2000'),'other':(15,12,'1500')}
    for row in library['items']:
        draft=service.get(auth(),row['policy_id']);branch=draft['implementation_reference']['branch']
        assert tuple(draft['clauses'][k]['value'] for k in ('invoice_months','sale_months','max_hours'))==expected[branch]
        assert draft['source_id']==source['source_id'] and draft['interpretation_basis']=='descriptive_implementation'
        assert draft['executable'] is draft['business_policy_verified'] is False
        for key in ['exclusions','effective_from','effective_to','oem_references','models']:
            assert draft['clauses'][key]==dict(value=None,quote=None)
        for cell in draft['clauses'].values():
            if cell['value'] is not None:assert ' '.join(cell['quote'].split()) in ' '.join(draft['source']['text'].split())
        report=service.assess(auth(),x.snapshot['version_id'],g['graph_id'],request(draft,g))
        assert report['classification']=='Requires Review' and report['eligibility_final'] is False
    audit=run(x.f.store.path,tmp_path/'recovery','one','alice','2026-01-01','2026-12-31')
    assert audit['artifact_checks']['policy_revisions']==4 and audit['recovery']['status']=='passed'


def test_implementation_import_scope_integrity_and_transaction_rollback(policies,monkeypatch):
    x,service,_=policies
    with pytest.raises(ApiFailure):service.import_implementation(auth(),{})
    implementation_source(x)
    for who in [auth(write=False),auth(owner='bob'),auth(workspace='two')]:
        with pytest.raises(ApiFailure):service.import_implementation(who,{})
    with pytest.raises(ApiFailure):service.import_implementation(auth(),{'verified':True})
    original=service._save;calls=[]
    def partial(*args,**kwargs):
        calls.append(True)
        if len(calls)==2:raise ApiFailure('TEST_ROLLBACK','Rollback',409)
        return original(*args,**kwargs)
    monkeypatch.setattr(service,'_save',partial)
    with pytest.raises(ApiFailure):service.import_implementation(auth(),{})
    assert service.list(auth())['items']==[]
    with x.f.store.transaction(write=False) as db:
        assert db.execute('SELECT COUNT(*) FROM business_policy_heads').fetchone()[0]==0
    monkeypatch.setattr(service,'_save',original)
    assert len(service.import_implementation(auth(),{})['items'])==4
