from copy import deepcopy
from concurrent.futures import ThreadPoolExecutor
import json
from unittest.mock import patch
import pytest
from tests.test_business_graph import graph,build
from tests.test_business_compiler import compiled_draft
from tests.test_business_generation import generation
from tests.test_business_ontology import foundation,auth
from workflow_api.business_reference import BusinessReference,load_kit
from workflow_api.business_documents import BusinessDocuments
from workflow_api.business_rule_execution import BusinessRuleExecution,SPECS,evaluate,availability,digest
from workflow_api.service import ApiFailure

ROOT_RULE='failure:unconfirmed_similarity';RECURRENCE='effectivity:recurrence_needs_evidence';RATE='monitoring:rate_requires_exposure'
VALUES={ROOT_RULE:dict(suspected_cause='Gasket leak',finding_basis='inspection',diagnosis='confirmed',finding_details='Inspection and pressure test identify a gasket leak.'),
 RECURRENCE:dict(physical_identity='same_engine',applicability='applies',incorporation='installed',mechanism='same',root_cause='same',inspection_conclusion='comparable_failure',incorporation_date='2026-01-01',failure_date='2026-06-01',post_change_hours='100',required_hours='100'),
 RATE:dict(cohort='Synthetic MODEL-A cohort',period_start='2026-01-01',period_end='2026-12-31',coverage='complete',counting_basis='distinct_first_failures',confirmed_failures=5,population_engines=100,exposure_hours='10000')}

@pytest.fixture
def execution(graph,monkeypatch):
    x=graph;kit,bundle=load_kit();bundle=deepcopy(bundle);bundle['required_sources']={'service':'service','quality':'quality'}
    monkeypatch.setattr('workflow_api.business_reference.load_kit',lambda:(deepcopy(kit),deepcopy(bundle)))
    ref=BusinessReference(x.f,lambda *args:auth());version=ref.apply(auth(),dict(expected_revision=x.f.get(auth())['workspace']['revision'],request_key='execution_reference_001'))
    x.snapshot=x.f.version(auth(),version['version_id']);x.service.compiler.compile(auth(),x.snapshot['version_id'],{});g=build(x)
    return x,g,BusinessRuleExecution(x.f,x.service,lambda *args:auth())

def request(g,rid,eid=None):return dict(rule_id=rid,subject_node_id=None if rid==RATE else next(r['node_id'] for r in g['records'] if r['collection']=='tickets'),change_node_id=next(r['node_id'] for r in g['records'] if r['collection']=='internalcutins') if rid==RECURRENCE else None,evidence_id=eid)
def save(execution,rid=RATE,values=None,key='execution_evidence_001',revision=0):
    x,g,service=execution;values=deepcopy(VALUES[rid] if values is None else values);text='Synthetic source-cited test report: '+json.dumps(values,sort_keys=True)
    source=BusinessDocuments(x.f).add(auth(),dict(title='Synthetic rule evidence',kind='evidence',module_ids=[SPECS[rid]['module']],text=text))
    req=request(g,rid);req.pop('evidence_id')
    body=dict(**req,request_key=key,expected_revision=revision,source_id=source['source_id'],facts={k:dict(value=values.get(k),quote=text if values.get(k) is not None else None) for k in SPECS[rid]['facts']})
    return service.save(auth(),x.snapshot['version_id'],g['graph_id'],body),body

@pytest.mark.parametrize('rid,change,outcome',[
 (ROOT_RULE,{},'documented_root_cause'),(ROOT_RULE,{'finding_basis':'similarity_only'},'hypothesis_only'),(ROOT_RULE,{'diagnosis':'inconclusive'},'hypothesis_only'),(ROOT_RULE,{'diagnosis':'ruled_out'},'cause_ruled_out'),(ROOT_RULE,{'finding_details':None},'insufficient_evidence'),
 (RECURRENCE,{},'recurrence_supported'),(RECURRENCE,{'applicability':'does_not_apply'},'recurrence_not_established'),(RECURRENCE,{'incorporation':'not_installed'},'recurrence_not_established'),(RECURRENCE,{'mechanism':'different'},'recurrence_not_established'),(RECURRENCE,{'root_cause':'different'},'recurrence_not_established'),(RECURRENCE,{'failure_date':'2025-01-01'},'recurrence_not_established'),(RECURRENCE,{'post_change_hours':'99.999'},'recurrence_not_established'),(RECURRENCE,{'applicability':'does_not_apply','mechanism':None},'insufficient_evidence'),
 (RATE,{},'rate_calculated'),(RATE,{'confirmed_failures':0},'rate_calculated'),(RATE,{'exposure_hours':'0'},'rate_not_calculable'),(RATE,{'population_engines':0},'rate_not_calculable'),(RATE,{'confirmed_failures':101},'rate_not_calculable'),(RATE,{'coverage':'incomplete'},'rate_not_calculable'),(RATE,{'counting_basis':'other_or_unconfirmed'},'rate_not_calculable'),(RATE,{'period_start':'2027-01-01'},'rate_not_calculable'),(RATE,{'confirmed_failures':None,'coverage':'incomplete'},'insufficient_evidence'),
])
def test_all_outcome_branches(rid,change,outcome):assert evaluate(rid,{**VALUES[rid],**change})['outcome']==outcome

def test_exact_decimal_calculations_and_small_exposure():
    result=evaluate(RATE,VALUES[RATE]);assert result['calculations']['failed_engine_percentage']=='5.000000' and result['calculations']['first_failures_per_1000_engine_hours']=='0.500000'
    assert evaluate(RATE,{**VALUES[RATE],'confirmed_failures':0})['calculations']['first_failures_per_1000_engine_hours']=='0.000000'
    assert evaluate(RATE,{**VALUES[RATE],'exposure_hours':'0.'+'0'*60+'1'})['outcome']=='rate_calculated'

@pytest.mark.parametrize('rid,expected',[(ROOT_RULE,'documented_root_cause'),(RECURRENCE,'recurrence_supported'),(RATE,'rate_calculated')])
def test_public_service_complete_evidence_and_missing_paths(execution,rid,expected):
    x,g,service=execution;evidence,_=save(execution,rid);calls=len(x.reader.calls)
    with patch('socket.create_connection',side_effect=AssertionError('No network')):result=service.run(auth(write=False),x.snapshot['version_id'],g['graph_id'],request(g,rid,evidence['evidence_id']))
    assert result['outcome']==expected and result['rules_executed'] is True and result['independently_verified'] is False
    assert result['company_queries']==result['model_calls']==result['source_writes']==0 and len(x.reader.calls)==calls
    assert result['provenance']['evidence_sha256']==evidence['sha256']
    assert service.run(auth(),x.snapshot['version_id'],g['graph_id'],request(g,rid))['outcome']=='insufficient_evidence'
    assert service.run(auth(),x.snapshot['version_id'],g['graph_id'],request(g,rid,evidence['evidence_id']))==result

def test_exact_rule_definition_dispatch_rejects_modified_rule(execution):
    x,g,service=execution;rule=next(r for r in x.snapshot['rules'] if r['id']==RATE);assert availability(rule)['available']
    altered={**rule,'outcome':'Approve all claims'};assert not availability(altered)['available']
    snap=deepcopy(x.snapshot);next(r for r in snap['rules'] if r['id']==RATE)['outcome']='Changed'
    with x.f.store.transaction() as db:db.execute('UPDATE business_ontology_versions SET document=? WHERE version_id=?',(json.dumps(snap),snap['version_id']))
    with pytest.raises(ApiFailure):service.run(auth(),snap['version_id'],g['graph_id'],request(g,RATE))

def test_revision_idempotency_concurrency_and_immutable_history(execution):
    x,g,service=execution;first,body=save(execution)
    with ThreadPoolExecutor(max_workers=2) as pool:results=list(pool.map(lambda _:service.save(auth(),x.snapshot['version_id'],g['graph_id'],body),range(2)))
    assert results==[first,first]
    second,_=save(execution,key='execution_evidence_002',revision=1);assert second['revision']==2 and service.get(auth(),first['evidence_id'])==first
    with pytest.raises(ApiFailure):service.save(auth(),x.snapshot['version_id'],g['graph_id'],{**body,'facts':{}})
    with pytest.raises(ApiFailure):save(execution,key='execution_stale_001',revision=0)

def test_scope_citation_types_and_tampering(execution):
    x,g,service=execution;evidence,body=save(execution)
    for who in [auth(owner='bob'),auth(workspace='two')]:
        with pytest.raises(ApiFailure):service.get(who,evidence['evidence_id'])
        with pytest.raises(ApiFailure):service.run(who,x.snapshot['version_id'],g['graph_id'],request(g,RATE,evidence['evidence_id']))
    with pytest.raises(ApiFailure):service.save(auth(write=False),x.snapshot['version_id'],g['graph_id'],body)
    for field,value in [('confirmed_failures',True),('exposure_hours','1e3'),('period_start','bad')]:
        bad=deepcopy(body);bad['request_key']='bad_input_'+field;bad['expected_revision']=1;bad['facts'][field]['value']=value
        with pytest.raises(ApiFailure):service.save(auth(),x.snapshot['version_id'],g['graph_id'],bad)
    bad=deepcopy(body);bad['request_key']='unmatched_quote';bad['facts']['cohort']['quote']='not in source'
    with pytest.raises(ApiFailure):service.save(auth(),x.snapshot['version_id'],g['graph_id'],bad)
    req=request(g,RATE,evidence['evidence_id'])
    for changes in [{'subject_node_id':next(r['node_id'] for r in g['records'] if r['collection']=='tickets')},{'verified':True},{'facts':{}},{'rule_id':ROOT_RULE}]:
        with pytest.raises(ApiFailure):service.run(auth(),x.snapshot['version_id'],g['graph_id'],{**req,**changes})
    with x.f.store.transaction() as db:
        doc=deepcopy(evidence);doc['facts']['confirmed_failures']['value']=99
        db.execute('UPDATE business_rule_evidence_versions SET document=? WHERE evidence_id=?',(json.dumps(doc),evidence['evidence_id']))
    with pytest.raises(ApiFailure):service.get(auth(),evidence['evidence_id'])

def test_http_saved_evidence_and_execution(tmp_path,execution):
    from fastapi.testclient import TestClient
    from workflow_api.main import create_app
    x,g,service=execution;evidence,body=save(execution)
    app=create_app(database=tmp_path/'http.sqlite',dev_auth=True,start_workers=False,planning_worker_enabled=False);client=TestClient(app);root='/business-ontology/v1';base=root+'/versions/'+x.snapshot['version_id']+'/graphs/'+g['graph_id']
    assert client.get(base+'/rule-execution').status_code==401
    with app.state.workflow_service.store.transaction() as db:
        with x.f.store.transaction(write=False) as original:
            for table in ['business_ontology_workspaces','business_ontology_versions','business_ontology_graphs','business_ontology_documents']:
                rows=original.execute('SELECT * FROM '+table).fetchall()
                for row in rows:db.execute('INSERT INTO '+table+' VALUES ('+','.join('?' for _ in row)+')',('local-workspace','local-builder',*row[2:]))
    client.get('/session');client.cookies.set('builder_dev_session',client.cookies.get('builder_dev_session'),path='/')
    assert client.get(base+'/rule-execution').status_code==200
    response=client.post(base+'/rule-evidence',json=body);assert response.status_code==200 and response.headers['cache-control']=='no-store';saved=response.json()['data']
    req=request(g,RATE,saved['evidence_id']);response=client.post(base+'/rules/execute',json=req)
    assert response.status_code==200 and response.json()['data']['outcome']=='rate_calculated'
    assert client.post(base+'/rules/execute',json={**req,'verified':True}).status_code==422
    assert client.post(base+'/rules/execute',json=req,headers={'origin':'https://untrusted.example'}).status_code==403
    assert client.post(base+'/rules/execute',content='bad-json').status_code==422
    app.state.workflow_auth['subject']['subject_id']='foreign';assert client.get(root+'/rule-evidence/'+saved['evidence_id']).status_code==404


def test_cited_evidence_recovery_and_head_graph_integrity(execution,tmp_path):
    from workflow_api.business_release import run,read_owned,inspect
    x,g,service=execution
    saved=[save(execution,rid,key='recovery_evidence_'+str(i))[0] for i,rid in enumerate(SPECS)]
    with patch('socket.create_connection',side_effect=AssertionError('No network')):
        result=run(x.f.store.path,tmp_path/'recovery','one','alice','2026-01-01','2026-12-31')
    assert result['recovery']['status']=='passed' and result['artifact_checks']['rule_evidence_revisions']==3
    restored=read_owned(tmp_path/'recovery/ontology-artifacts.sqlite3','one','alice')
    assert {json.loads(r['document'])['sha256'] for r in restored['business_rule_evidence_versions']}=={d['sha256'] for d in saved}
    damaged=deepcopy(restored);damaged['business_rule_evidence_heads'][0]['revision']+=1
    with pytest.raises(ValueError,match='history/head mismatch'):inspect(damaged,'2026-01-01','2026-12-31')
    damaged=deepcopy(restored);damaged['business_rule_evidence_versions'][0]['series_key']='wrong'
    with pytest.raises(ValueError,match='series mismatch'):inspect(damaged,'2026-01-01','2026-12-31')
    damaged=deepcopy(restored);damaged['business_ontology_graphs']=[]
    with pytest.raises(ValueError,match='graph missing'):inspect(damaged,'2026-01-01','2026-12-31')
