"""Offline compiler semantics, SHACL failures and scoped version-bound exports."""
from copy import deepcopy
from hashlib import sha256
import json
from unittest.mock import patch

import pytest
from rdflib import Graph, Literal, Namespace, URIRef
from rdflib.namespace import OWL, RDF, RDFS, SH, XSD
from pyshacl import validate

from tests.test_business_generation import generation, submit
from tests.test_business_ontology import foundation, auth, initialize
from workflow_api.business_compiler import BusinessCompiler, COMPILER_VERSION, VOCAB_IRI, build_graphs, compile_snapshot
from workflow_api.service import ApiFailure


@pytest.fixture
def compiled_draft(generation):
    f,_,_,source,provider,jobs=generation
    def enrich(result):
        engine=result['concepts'][0]
        engine['properties']=[dict(name=name,datatype=datatype,required=required,description='Observed '+name) for name,datatype,required in [
            ('hours','integer',True),('sale date','date',False),('readingTime','datetime',False),('active','boolean',False),('amount','decimal',False),('serial','string',False),('status','enumeration',False),('claim','reference',False)]]
        engine['unknowns']=['Exclusions are not supplied.']
        child={**deepcopy(engine),'id':'warranty:replacement_engine','label':'Replacement engine','parent_id':engine['id'],'properties':[],'unknowns':[]}
        result['concepts'].append(child)
        base={k:deepcopy(engine[k]) for k in ('definition','layer','evidence','confidence','unknowns')}
        result['relationships']=[dict(**base,id='warranty:replaces',label='Replaces engine',source=child['id'],target=engine['id'],predicate='replaces')]
        result['rules']=[dict(**base,id='warranty:review',label='Requires review',inputs=[engine['id']],conditions=['Policy is missing'],outcome='Requires Review',basis='proposed_logic')]
    provider.modify=enrich;job=submit(generation);jobs.tick()
    result=jobs.get(auth(),job['job_id']);assert result['state']=='succeeded'
    version=f.version(auth(),result['version_id'])
    return f,BusinessCompiler(f),version


def test_compiler_semantics_roundtrip_and_no_rule_execution(compiled_draft):
    f,compiler,snapshot=compiled_draft
    before=f.get(auth());result=compiler.compile(auth(),snapshot['version_id'],{})['compilation']
    report=result['report'];assert report['status']=='passed' and report['definition_conforms'] is True
    assert report['checks']==dict(snapshot='passed',rdf_syntax='passed',shapes_meta_shacl='passed',definition_shacl='passed')
    assert report['instance_validation']=='not_run' and report['owl_reasoning']=='not_run' and report['business_policy_verified'] is False
    assert {w['code'] for w in report['warnings']}=={'ENUMERATION_VALUES_UNSPECIFIED','REFERENCE_TARGET_UNSPECIFIED','UNRESOLVED_INFORMATION','UNRESOLVED_QUESTION'}
    assert f.get(auth())==before and f.version(auth(),snapshot['version_id'])==snapshot
    artifacts={a['name']:a for a in result['artifacts']}
    for artifact in artifacts.values():assert sha256(artifact['content'].encode()).hexdigest()==artifact['sha256']
    ontology=Graph().parse(data=artifacts['ontology.ttl']['content'],format='turtle')
    xml=Graph().parse(data=artifacts['ontology.rdf']['content'],format='xml')
    assert set(ontology)==set(xml)
    ns=snapshot['workspace']['namespace'];v=Namespace(VOCAB_IRI)
    engine=URIRef(ns+'concept:warranty%3Aengine');child=URIRef(ns+'concept:warranty%3Areplacement_engine')
    assert (child,RDFS.subClassOf,engine) in ontology
    edge=URIRef(ns+'relationship:warranty%3Areplaces')
    assert (edge,RDF.type,OWL.ObjectProperty) in ontology and (edge,RDFS.domain,child) in ontology and (edge,RDFS.range,engine) in ontology
    hours=URIRef(ns+'attribute:warranty%3Aengine:hours')
    assert (hours,RDFS.range,XSD.integer) in ontology
    rule=URIRef(ns+'rule:warranty%3Areview')
    assert (rule,v.executable,Literal(False)) in ontology and (rule,RDF.type,v.RuleCandidate) in ontology
    assert not list(ontology.triples((None,OWL.imports,None)))
    shapes=Graph().parse(data=artifacts['instance-shapes.ttl']['content'],format='turtle')
    assert not list(shapes.triples((None,SH.rule,None))) and not list(shapes.triples((None,SH.sparql,None)))
    assert json.loads(artifacts['validation-report.json']['content'])==report


def test_shapes_detect_real_missing_required_and_invalid_values(compiled_draft):
    _,_,snapshot=compiled_draft
    ontology,shapes,_,_=build_graphs(snapshot);ns=snapshot['workspace']['namespace']
    engine=URIRef(ns+'concept:warranty%3Aengine');hours=URIRef(ns+'attribute:warranty%3Aengine:hours')
    instance=URIRef('urn:test:instance');data=Graph();data.add((instance,RDF.type,engine))
    good,report,_=validate(data,shacl_graph=shapes,ont_graph=ontology,inference='none')
    assert not good and hours in set(report.objects(None,SH.resultPath))
    data.add((instance,hours,Literal('bad',datatype=XSD.string)))
    assert validate(data,shacl_graph=shapes,ont_graph=ontology,inference='none')[0] is False
    data.remove((instance,hours,None));data.add((instance,hours,Literal(42)))
    assert validate(data,shacl_graph=shapes,ont_graph=ontology,inference='none')[0] is True
    # A relationship value must have the declared target class, with IRI identity.
    other=URIRef('urn:test:other');edge=URIRef(ns+'relationship:warranty%3Areplaces')
    data.add((instance,RDF.type,URIRef(ns+'concept:warranty%3Areplacement_engine')))
    data.add((instance,edge,other))
    assert validate(data,shacl_graph=shapes,ont_graph=ontology,inference='none')[0] is False
    data.add((other,RDF.type,engine));data.add((other,hours,Literal(1)))
    assert validate(data,shacl_graph=shapes,ont_graph=ontology,inference='none')[0] is True


def test_idempotent_persistent_historical_and_read_only_access(compiled_draft):
    f,compiler,snapshot=compiled_draft;version=snapshot['version_id']
    assert compiler.get(auth(),version)=={'compilation':None}
    first=compiler.compile(auth(),version,{})
    assert compiler.compile(auth(),version,{})==first
    assert BusinessCompiler(f).get(auth(write=False),version)==first
    with f.store.transaction(write=False) as db:
        assert db.execute('SELECT COUNT(*) FROM business_ontology_compilations').fetchone()[0]==1
        assert db.execute("SELECT COUNT(*) FROM business_ontology_events WHERE event_id LIKE 'boe_compile_%'").fetchone()[0]==1
    # A newer workspace, or disconnected current source, does not invalidate a
    # historical immutable schema export.
    with f.store.transaction() as db:
        workspace=f.document(db,('one','alice'));workspace['revision']=99
        db.execute('UPDATE business_ontology_workspaces SET document=?',(json.dumps(workspace),))
        db.execute("UPDATE data_source_connections SET document=? WHERE connection_id='service'",(json.dumps(dict(engine='mongodb',connection_status='disconnected',metadata_revision=999)),))
    assert compiler.get(auth(),version)==first
    for foreign in [auth(owner='bob'),auth(workspace='two')]:
        with pytest.raises(ApiFailure) as exc:compiler.get(foreign,version)
        assert exc.value.status==404
        with pytest.raises(ApiFailure):compiler.compile(foreign,version,{})
    with pytest.raises(ApiFailure) as exc:compiler.compile(auth(write=False),version,{})
    assert exc.value.status==403


@pytest.mark.parametrize('body',[None,[],{'input':'external'},'{}'])
def test_invalid_payloads_fail_before_compilation(compiled_draft,body):
    _,compiler,snapshot=compiled_draft
    with pytest.raises(ApiFailure) as exc:compiler.compile(auth(),snapshot['version_id'],body)
    assert exc.value.status==422
    assert compiler.get(auth(),snapshot['version_id'])['compilation'] is None


@pytest.mark.parametrize('mutate',[
    lambda s:s['concepts'][0].update(parent_id='warranty:missing'),
    lambda s:s['concepts'][0].update(parent_id='warranty:replacement_engine'),
    lambda s:s['concepts'][0]['evidence'][0].update(quote='invented policy'),
    lambda s:s['sources'][0].update(sha256='wrong'),
    lambda s:s['rules'][0].update(executable=True),
    lambda s:s['relationships'][0].update(target='missing:target'),
    lambda s:s['concepts'][0]['properties'][0].update(datatype='malformed'),
    lambda s:s['workspace'].update(namespace='https://attacker.invalid/'),
])
def test_corrupt_snapshot_fails_without_artifact(compiled_draft,mutate):
    _,_,snapshot=compiled_draft;mutate(snapshot)
    with pytest.raises(ApiFailure) as exc:compile_snapshot(snapshot)
    assert exc.value.status==422


def test_foundation_is_not_a_generated_ontology(foundation):
    f,_=foundation;version=initialize(f)['versions'][0]['version_id'];compiler=BusinessCompiler(f)
    with pytest.raises(ApiFailure) as exc:compiler.compile(auth(),version,{})
    assert exc.value.code=='BUSINESS_DRAFT_REQUIRED'
    assert compiler.get(auth(),version)['compilation'] is None


def test_definition_shacl_failure_is_reported_not_passed(compiled_draft):
    _,_,snapshot=compiled_draft;graphs=build_graphs(snapshot)
    engine=URIRef(snapshot['workspace']['namespace']+'concept:warranty%3Aengine')
    graphs[0].remove((engine,RDFS.label,None))
    with patch('workflow_api.business_compiler.build_graphs',return_value=graphs):
        report,_=compile_snapshot(snapshot)
    assert report['status']=='failed' and report['definition_conforms'] is False
    assert any(i['path']==str(RDFS.label) for i in report['issues'])


def test_serialization_is_deterministic_and_strings_are_literal(compiled_draft):
    _,_,snapshot=compiled_draft
    snapshot['concepts'][0]['label']='Engine </rdf:Description> " @prefix evil: <https://attacker.invalid/> .'
    first=compile_snapshot(snapshot);second=compile_snapshot(deepcopy(snapshot))
    assert first==second
    assert first[0]['status']=='passed'


def test_mid_compile_snapshot_change_is_rejected(compiled_draft):
    f,compiler,snapshot=compiled_draft;original=compile_snapshot
    def changed(s):
        result=original(s)
        with f.store.transaction() as db:
            other=deepcopy(s);other['revision']=44
            db.execute('UPDATE business_ontology_versions SET document=? WHERE version_id=?',(json.dumps(other),s['version_id']))
        return result
    with patch('workflow_api.business_compiler.compile_snapshot',side_effect=changed):
        with pytest.raises(ApiFailure) as exc:compiler.compile(auth(),snapshot['version_id'],{})
    assert exc.value.status==409
    assert compiler.get(auth(),snapshot['version_id'])['compilation'] is None


def test_compilation_http_scope_payloads_and_no_company_access(tmp_path):
    from fastapi.testclient import TestClient
    from workflow_api.main import create_app
    from tests.test_business_generation import Provider, TEXT
    app=create_app(database=tmp_path/'http.sqlite',dev_auth=True,start_workers=False,planning_worker_enabled=False)
    app.state.business_generation.provider=Provider()
    client=TestClient(app);client.get('/session');client.cookies.set('builder_dev_session',client.cookies.get('builder_dev_session'),path='/')
    with app.state.workflow_service.store.transaction() as db:
        for cid in ('service','quality'):
            doc=dict(connection_id=cid,name=cid,engine='mongodb',connection_status='connected',metadata_revision=1)
            db.execute('INSERT INTO data_source_connections VALUES (?,?,?,?,?)',(cid,'local-workspace','local-builder',None,json.dumps(doc)))
    base='/business-ontology/v1'
    client.post(base+'/initialize',json={'sources':{'service':'service','quality':'quality'}})
    client.post(base+'/documents',json=dict(title='Process evidence',kind='process',module_ids=['warranty'],text=TEXT))
    job=client.post(base+'/jobs',json=dict(module_id='warranty',expected_revision=1,request_key='compile_http_001')).json()['data']
    assert app.state.business_generation.tick()
    version=client.get(base+'/jobs/'+job['job_id']).json()['data']['version_id']
    path=base+'/versions/'+version+'/compilation'
    assert client.get(path).json()['data']['compilation'] is None
    assert client.post(path,json={'text':'untrusted'}).status_code==422
    compiled=client.post(path,json={})
    assert compiled.status_code==200 and compiled.headers['cache-control']=='no-store'
    result=compiled.json()['data']['compilation'];assert result['report']['status']=='passed'
    assert client.post(path,json={}).json()['data']['compilation']==result
    assert client.get(path).json()['data']['compilation']==result
    app.state.workflow_auth['scopes']=['workspace:read']
    assert client.get(path).status_code==200 and client.post(path,json={}).status_code==403
    app.state.workflow_auth['scopes']=['workspace:read','workspace:write']
    app.state.workflow_auth['subject']['subject_id']='other'
    assert client.get(path).status_code==404 and client.post(path,json={}).status_code==404
