"""Candidate evidence and fixed RDF competency queries, never company decisions."""
from copy import deepcopy
from hashlib import sha256
import json
from unittest.mock import patch

import pytest
from tests.test_business_ontology import foundation, auth, initialize
from tests.test_business_generation import generation, submit
from tests.test_business_compiler import compiled_draft
from workflow_api.business_compiler import COMPILER_VERSION, canonical, compile_snapshot
from workflow_api.business_rules import BusinessRules, QUERIES, catalogue, execute, question_reference
from workflow_api.service import ApiFailure


def request(query='rule_inputs',focus=None,limit=50,offset=0):
    return dict(query_id=query,focus_id=focus,limit=limit,offset=offset)


def compiled(snapshot):
    report,artifacts=compile_snapshot(snapshot)
    return dict(version_id=snapshot['version_id'],compiler_version=COMPILER_VERSION,input_sha256=sha256(canonical(snapshot).encode()).hexdigest(),report=report,artifacts=artifacts)


@pytest.fixture
def rules(compiled_draft):
    f,compiler,snapshot=compiled_draft
    return f,compiler,snapshot,BusinessRules(f,compiler)


def test_catalogue_is_version_bound_evidence_backed_and_read_only(rules):
    f,compiler,snapshot,service=rules;before=f.get(auth())
    view=service.view(auth(write=False),snapshot['version_id'])
    assert view['counts']==dict(policy_statement=0,descriptive_implementation=0,proposed_logic=1)
    rule=view['rules'][0]
    assert rule['executable'] is False and rule['business_policy_verified'] is False
    assert rule['basis_label']=='Proposed logic' and rule['input_definitions'][0]['data_availability']=='not_checked'
    assert rule['input_definitions'][0]['properties'][0]['required'] is True
    assert rule['evidence'][0]['quote'] in snapshot['sources'][0]['text']
    assert rule['evidence'][0]['sha256']==snapshot['sources'][0]['sha256']
    assert rule['module_questions'] and rule['unknowns']
    assert all(q['available'] is False for q in view['queries'])
    assert len(view['business_questions'])==22 and {q['status'] for q in view['business_questions']}=={'requires_instance_mapping'}
    assert f.get(auth())==before
    assert compiler.get(auth(),snapshot['version_id'])['compilation'] is None


def test_actual_six_queries_answer_definitions_with_provenance(rules):
    f,compiler,snapshot,service=rules;version=snapshot['version_id']
    compiler.compile(auth(),version,{})
    assert all(q['available'] for q in service.view(auth(),version)['queries'])
    before=f.get(auth())
    # A socket request or RDF update would fail this test. Values are read only
    # from the owned persisted compilation, with no source connector involved.
    with patch('socket.create_connection',side_effect=AssertionError('network forbidden')),patch('rdflib.Graph.update',side_effect=AssertionError('update forbidden')):
        results={qid:service.run(auth(write=False),version,request(qid)) for qid in QUERIES}
    inputs=results['rule_inputs'];assert len(inputs['rows'])==8
    assert {r['attribute_name']['value'] for r in inputs['rows']}=={'hours','sale date','readingTime','active','amount','serial','status','claim'}
    hours=next(r for r in inputs['rows'] if r['attribute_name']['value']=='hours')
    assert hours['required']['value']=='true' and hours['input']['entity_id']=='warranty:engine'
    assert hours['datatype']['value'].endswith('#integer')
    assert results['rule_evidence']['rows'][0]['source_hash']['value']==snapshot['sources'][0]['sha256']
    assert results['concept_relationships']['rows'][0]['target']['entity_id']=='warranty:engine'
    assert results['policy_candidates']['result_state']=='no_matching_definitions'
    assert results['implementation_candidates']['rows']==[]
    assert any('Exclusions' in r['information']['value'] for r in results['unresolved_information']['rows'])
    assert any('Which policy exclusions' in r['information']['value'] for r in results['unresolved_information']['rows'])
    for result in results.values():
        assert result['version_id']==version and result['revision']==snapshot['revision']
        assert result['scope']=='definitions_only' and result['business_policy_verified'] is False
        assert result['company_records_queried'] is False and result['rules_executed'] is False
        assert len(result['provenance']['query_sha256'])==64
        assert result['provenance']['input_sha256']==sha256(canonical(snapshot).encode()).hexdigest()
    assert f.get(auth())==before


def test_policy_and_implementation_remain_separate_unverified_candidates(rules):
    _,_,snapshot,_=rules;snapshot=deepcopy(snapshot)
    for basis,kind in [('policy_statement','policy'),('descriptive_implementation','application_code')]:
        source={**snapshot['sources'][0],'source_id':basis+'_source','kind':kind};snapshot['sources'].append(source)
        rule={**deepcopy(snapshot['rules'][0]),'id':'warranty:'+basis,'label':basis,'basis':basis}
        rule['evidence'][0]['source_id']=source['source_id'];snapshot['rules'].append(rule)
    artifact=compiled(snapshot)
    policy=execute(snapshot,artifact,request('policy_candidates'));code=execute(snapshot,artifact,request('implementation_candidates'))
    assert {r['rule']['entity_id'] for r in policy['rows']}=={'warranty:policy_statement'}
    assert {r['rule']['entity_id'] for r in code['rows']}=={'warranty:descriptive_implementation'}
    assert all(r['business_policy_verified'] is False and r['executable'] is False for r in catalogue(snapshot))


def test_query_pagination_and_focus_are_stable(rules):
    _,_,snapshot,_=rules;artifact=compiled(snapshot)
    first=execute(snapshot,artifact,request(limit=3));second=execute(snapshot,artifact,request(limit=3,offset=first['next_offset']))
    final=execute(snapshot,artifact,request(limit=3,offset=second['next_offset']))
    whole=execute(snapshot,artifact,request())
    assert first['has_more'] and second['has_more'] and not final['has_more'] and final['next_offset'] is None
    assert first['rows']+second['rows']+final['rows']==whole['rows']
    assert execute(snapshot,artifact,request('rule_inputs','warranty:review'))['rows']==whole['rows']
    assert len(execute(snapshot,artifact,request('concept_relationships','warranty:replacement_engine'))['rows'])==1
    focused=execute(snapshot,artifact,request('unresolved_information','warranty:engine'))
    assert len(focused['rows'])==1 and focused['rows'][0]['item']['entity_id']=='warranty:engine'


@pytest.mark.parametrize('body',[
 None,{},dict(query_id='rule_inputs'),{**request(),'sparql':'SERVICE <https://attacker.invalid> {}'},
 request('DELETE WHERE {?s ?p ?o}'),request(focus='warranty:review> SERVICE <https://attacker.invalid> {}'),
 request(focus='warranty:engine'),request(limit=True),request(limit=0),request(limit=51),request(offset=-1),request(offset=20001),request(offset='1'),
])
def test_query_rejects_arbitrary_text_wrong_focus_and_invalid_bounds(rules,body):
    _,_,snapshot,_=rules
    with pytest.raises(ApiFailure) as exc:execute(snapshot,None,body)
    assert exc.value.status==422


@pytest.mark.parametrize('mutate',[
 lambda c:c.update(input_sha256='wrong'),lambda c:c.update(version_id='foreign'),
 lambda c:c.update(compiler_version='future'),lambda c:c['report'].update(status='failed'),
 lambda c:c['report'].update(definition_conforms=False),lambda c:c['report']['checks'].update(shapes_meta_shacl='failed'),
 lambda c:c['artifacts'][0].update(content='@prefix evil: <https://attacker.invalid/> .'),
 lambda c:c.update(artifacts=[]),
])
def test_missing_or_corrupt_compilation_is_never_an_empty_success(rules,mutate):
    _,_,snapshot,_=rules;artifact=compiled(snapshot);mutate(artifact)
    with pytest.raises(ApiFailure) as exc:execute(snapshot,artifact,request())
    assert exc.value.status==409 and exc.value.code=='BUSINESS_QUERY_UNAVAILABLE'


def test_foundation_historical_and_foreign_access(rules):
    f,compiler,snapshot,service=rules
    foundation_version=f.get(auth())['versions'][0]['version_id']
    view=service.view(auth(),foundation_version)
    assert view['rules']==[] and all(n==0 for n in view['counts'].values())
    with pytest.raises(ApiFailure) as exc:service.run(auth(),foundation_version,request())
    assert exc.value.status==409
    compiler.compile(auth(),snapshot['version_id'],{})
    with f.store.transaction() as db:
        workspace=f.document(db,('one','alice'));workspace['revision']=99
        db.execute('UPDATE business_ontology_workspaces SET document=?',(json.dumps(workspace),))
        db.execute("UPDATE data_source_connections SET document=? WHERE connection_id='quality'",(json.dumps(dict(connection_status='disconnected')),))
    assert service.run(auth(),snapshot['version_id'],request())['revision']==2
    for foreign in (auth(owner='bob'),auth(workspace='two')):
        for method,args in [(service.view,()),(service.run,(request(),))]:
            with pytest.raises(ApiFailure) as exc:method(foreign,snapshot['version_id'],*args)
            assert exc.value.status==404
    with pytest.raises(ApiFailure):service.view({**auth(),'permissions':[]},snapshot['version_id'])


def test_blueprint_business_questions_keep_specific_prerequisites():
    reference=question_reference()
    assert len(reference['source']['sha256'])==64
    assert [q['id'] for q in reference['items']]==[f'business_{n:02}' for n in range(1,23)]
    assert all(q['prerequisites'] and q['status']=='requires_instance_mapping' for q in reference['items'])
    assert 'failure date' in reference['items'][0]['question']
    assert any('denominator' in p for p in reference['items'][18]['prerequisites'])


def test_rule_query_http_is_read_only_and_authorized(tmp_path):
    from fastapi.testclient import TestClient
    from workflow_api.main import create_app
    from tests.test_business_generation import Provider,TEXT
    app=create_app(database=tmp_path/'rules.sqlite',dev_auth=True,start_workers=False,planning_worker_enabled=False)
    provider=Provider()
    def rule(result):
        c=result['concepts'][0]
        result['rules']=[{k:v for k,v in c.items() if k not in ('parent_id','properties')}|dict(id='warranty:review',label='Missing information',inputs=[c['id']],conditions=['Policy is missing'],outcome='Requires Review',basis='proposed_logic')]
    provider.modify=rule;app.state.business_generation.provider=provider
    client=TestClient(app);client.get('/session');client.cookies.set('builder_dev_session',client.cookies.get('builder_dev_session'),path='/')
    with app.state.workflow_service.store.transaction() as db:
        for cid in ('service','quality'):
            doc=dict(connection_id=cid,name=cid,engine='mongodb',connection_status='connected',metadata_revision=1)
            db.execute('INSERT INTO data_source_connections VALUES (?,?,?,?,?)',(cid,'local-workspace','local-builder',None,json.dumps(doc)))
    root='/business-ontology/v1'
    client.post(root+'/initialize',json={'sources':{'service':'service','quality':'quality'}})
    client.post(root+'/documents',json=dict(title='Process',kind='process',module_ids=['warranty'],text=TEXT))
    job=client.post(root+'/jobs',json=dict(module_id='warranty',expected_revision=1,request_key='http_rules_001')).json()['data']
    app.state.business_generation.tick()
    version=client.get(root+'/jobs/'+job['job_id']).json()['data']['version_id'];path=root+'/versions/'+version
    assert client.get(path+'/rule-catalogue').json()['data']['rules'][0]['executable'] is False
    assert client.post(path+'/competency-queries/run',json=request()).status_code==409
    assert client.post(path+'/compilation',json={}).status_code==200
    with app.state.workflow_service.store.transaction(write=False) as db:
        before={table:db.execute('SELECT COUNT(*) FROM '+table).fetchone()[0] for table in ('business_ontology_events','business_ontology_versions','business_ontology_jobs','business_ontology_compilations')}
    app.state.workflow_auth['scopes']=['workspace:read']
    app.state.workflow_auth['permissions']=['tools.read']
    result=client.post(path+'/competency-queries/run',json=request())
    assert result.status_code==200 and result.headers['cache-control']=='no-store'
    assert result.json()['data']['rows'][0]['input']['entity_id']=='warranty:engine'
    assert client.get(path+'/rule-catalogue').status_code==200
    assert client.post(path+'/competency-queries/run',json={'sparql':'SELECT * {}'}).status_code==422
    with app.state.workflow_service.store.transaction(write=False) as db:
        assert {table:db.execute('SELECT COUNT(*) FROM '+table).fetchone()[0] for table in before}==before
    assert len(provider.calls)==1 # only the preceding fixture generation
    app.state.workflow_auth['subject']['subject_id']='other'
    assert client.get(path+'/rule-catalogue').status_code==404
    assert client.post(path+'/competency-queries/run',json=request()).status_code==404
