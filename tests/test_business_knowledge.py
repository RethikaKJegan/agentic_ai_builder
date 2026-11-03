"""Backend Phase 1 acceptance. Fixtures are synthetic, not company evidence."""
from copy import deepcopy
from pathlib import Path
from unittest.mock import patch
import json
import pytest
from tests.test_business_ontology import foundation,auth
from tests.test_business_generation import generation,submit
from tests.test_business_reference import reference
from workflow_api.business_knowledge import BusinessKnowledge,load_package,preserve_knowledge,apply_package
from workflow_api.business_knowledge_model import digest,convert,associate,state_check,evaluate_rule,validate_knowledge,MODEL_SCHEMA
from workflow_api.business_compiler import compile_snapshot,check_snapshot,build_graphs
from workflow_api.service import ApiFailure


@pytest.fixture
def knowledge(reference):
    f,jobs,ref,current=reference
    ref.apply(current,dict(expected_revision=1,request_key='knowledge_base_001'))
    service=BusinessKnowledge(f,lambda w,o:current if (w,o)==('one','alice') else None)
    old=f.get(current)['current_version_id']
    result=service.import_package(current,dict(expected_revision=2,request_key='knowledge_import_001'))
    return f,service,current,old,result


def test_connected_version_and_export(knowledge):
    f,s,a,old,result=knowledge;v=f.version(a,result['version_id']);k=v['knowledge']
    assert len(v['layers'])==5 and len(v['modules'])==12
    assert {c['id'] for c in f.version(a,old)['concepts']} <= {c['id'] for c in v['concepts']}
    assert f.version(a,old).get('knowledge') is None
    assert len(k['source_mappings'])>=36 and len(k['structured_rules'])==3
    assert next(c for c in v['concepts'] if c['id']=='engines:engine_instance')['parent_id']=='engines:physical_product'
    assert compile_snapshot(v)[0]['status']=='passed'
    assert all(x['status']=='collection_unavailable' for x in k['manifest']['source_status'])
    assert 'knowledge' not in f.version(a,old)


def test_saved_inspection_without_authoring_reads(knowledge):
    f,s,a,old,result=knowledge
    with patch('pathlib.Path.read_text',side_effect=AssertionError('No mutable authoring reads')):
        view=s.inspect(a,result['version_id'],'inspection:inspection_report')
        assert view['mappings'] and view['relationships'] and view['details']['attributes']
        assert s.inspect(a,old)['knowledge'] is None
        r=s.diagnose(a,result['version_id'],dict(operation='state',id='state:inspection_report',value='PUBLISHED'))
    assert r['result']['activity_completion_inferred'] is False


def test_import_idempotency_conflicts_and_scope(knowledge):
    f,s,a,old,result=knowledge
    again=s.import_package(a,dict(expected_revision=2,request_key='knowledge_import_001'))
    assert again['version_id']==result['version_id'] and again['idempotent']
    assert s.import_package(a,dict(expected_revision=3,request_key='knowledge_import_002'))['version_id']==result['version_id']
    for body in [dict(expected_revision=2,request_key='knowledge_import_002'),dict(expected_revision=3,request_key='knowledge_import_001')]:
        with pytest.raises(ApiFailure):s.import_package(a,body)
    for authority in [auth(owner='bob'),auth(workspace='other'),auth(write=False)]:
        with pytest.raises(ApiFailure):s.import_package(authority,dict(expected_revision=3,request_key='knowledge_foreign_001'))
    with pytest.raises(ApiFailure):s.inspect(auth(owner='bob'),result['version_id'])


@pytest.mark.parametrize('value,state,expected',[(None,'unknown',None),('0','value','0'),(0,'value','0'),('12.50','value','12.50'),('-1','conversion_issue',None),('nan','conversion_issue',None),(True,'conversion_issue',None),('12 hours','conversion_issue',None),({},'conversion_issue',None)])
def test_conversion_zero_missing_and_invalid(value,state,expected):
    assert convert(value,'parse_nonnegative_decimal','decimal')==dict(state=state,value=expected)


@pytest.mark.parametrize('mutation',[
 lambda v:v['concepts'][0].update(parent_id=v['concepts'][0]['id']),
 lambda v:v['knowledge']['relationship_details'][0].update(min_count=2,max_count=1),
 lambda v:v['knowledge']['relationship_details'][0].update(binding_id='identity:invoice_qa_serial'),
 lambda v:v['knowledge']['source_mappings'][0].update(attribute='absent'),
 lambda v:v['knowledge']['source_mappings'][0].update(conversion='eval_python'),
 lambda v:v['knowledge']['concept_details'][0]['attributes'][0].update(reference_target='absent:concept'),
 lambda v:v['knowledge']['dependencies'][0]['concepts'].append('missing:concept'),
 lambda v:v['knowledge']['structured_rules'][0]['conditions']['all'][0].update(operator='execute'),
 lambda v:v['knowledge']['structured_rules'][0]['conditions']['all'][0].update(fact='absent'),
 lambda v:v['knowledge']['state_models'][0]['transitions'].append(dict(source='OPENED',target='FABRICATED',required_facts=[])),
 lambda v:v['knowledge']['temporal_models'][0].update(fallback_mapping_id='mapping:complaint_created'),
 lambda v:v['knowledge']['temporal_models'][0].update(mapping_id='mapping:invoice_date'),
])
def test_semantic_corruption_is_rejected(knowledge,mutation):
    f,s,a,old,result=knowledge;v=f.version(a,result['version_id']);mutation(v);v['knowledge_sha256']=digest(v['knowledge'])
    with pytest.raises(ApiFailure):check_snapshot(v)


def test_rule_results_preserve_origin_and_no_effects(knowledge):
    f,s,a,old,result=knowledge;vid=result['version_id']
    r=s.diagnose(a,vid,dict(operation='rule',id='warranty:assessment_readiness',facts={}))['result']
    assert r['state']=='missing' and r['outcome']=='insufficient_information'
    complete=dict(operating_hours=0,assessment_date='2026-11-03',identity_resolved=True,policy_applicable=True)
    r=s.diagnose(a,vid,dict(operation='rule',id='warranty:assessment_readiness',facts=complete))['result']
    assert r['state']=='satisfied' and r['provenance']['origin']=='configured_logic'
    assert r['official_policy_result'] is False and r['operational_effects'] is False
    complete['identity_resolved']=False
    assert s.diagnose(a,vid,dict(operation='rule',id='warranty:assessment_readiness',facts=complete))['result']['state']=='unsatisfied'
    for unknown in ({'python':'print(1)'},{'operating_hours':True}):
        if 'python' in unknown:
            with pytest.raises(ApiFailure):s.diagnose(a,vid,dict(operation='rule',id='warranty:assessment_readiness',facts=unknown))
        else:assert s.diagnose(a,vid,dict(operation='rule',id='warranty:assessment_readiness',facts=unknown))['result']['state']=='missing'


def test_lifecycle_dates_and_no_publication_completion(knowledge):
    f,s,a,old,result=knowledge;vid=result['version_id']
    assert s.diagnose(a,vid,dict(operation='state',id='state:inspection_report',value='PUBLISHED'))['result']['activity_completion_inferred'] is False
    assert s.diagnose(a,vid,dict(operation='state',id='state:inspection_report',value='DRAFTED',target='PUBLISHED'))['result']['transition']=='undefined'
    assert s.diagnose(a,vid,dict(operation='state',id='state:inspection_activity',value='COMPLETED'))['result']['state']=='unknown'
    assert s.diagnose(a,vid,dict(operation='convert',id='mapping:sale_date',value=None))['result']['state']=='unknown'
    assert s.diagnose(a,vid,dict(operation='convert',id='mapping:sale_date',value='not-a-date'))['result']['state']=='conversion_issue'


def test_identity_namespace_and_candidates(knowledge):
    f,s,a,old,result=knowledge;k=f.version(a,result['version_id'])['knowledge'];definition=next(i for i in k['identity_rules'] if i['id']=='identity:invoice_qa_serial')
    left=dict(connection_id='one',collection='enginedetails',native_type='string',native_value='42',serial='S1')
    right=dict(connection_id='two',collection='failedengineanalyses',native_type='string',native_value='42',serial='S1')
    assert associate(definition,left,right)['association']=='ambiguous_candidate'
    assert associate(definition,{**left,'company':'A','model':'M'},{**right,'company':'A','model':'M'})['association']=='scope_supported_candidate'
    r=associate(definition,{**left,'company':'A'},{**right,'company':'B'})
    assert r['association']=='conflicting_candidate' and r['merge_permitted'] is False
    assert associate(definition,left,left)['association']=='identical_source_record'


def test_regeneration_cannot_erase_or_modify_enrichment(knowledge):
    f,s,a,old,result=knowledge;previous=f.version(a,result['version_id']);generated=deepcopy(previous);generated.pop('knowledge');generated.pop('knowledge_sha256')
    preserve_knowledge(previous,generated);assert generated['knowledge']==previous['knowledge']
    generated['concepts']=[c for c in generated['concepts'] if c['id']!='engines:physical_product']
    with pytest.raises(ApiFailure) as exc:preserve_knowledge(previous,generated)
    assert exc.value.code=='BUSINESS_KNOWLEDGE_REGENERATION_CONFLICT'


def test_package_changes_create_new_version_and_history(knowledge):
    f,s,a,old,result=knowledge;pack=load_package();pack['revision']+=1;pack['knowledge']['concept_details'][0]['aliases'].append('additional term')
    new=s.import_package(a,dict(expected_revision=3,request_key='knowledge_revision_002'),package=pack)
    assert new['revision']==4 and new['version_id']!=result['version_id']
    assert f.version(a,result['version_id'])['knowledge']['manifest']['package_revision']==pack['revision']-1


def test_unsafe_mapping_package_rolls_back(knowledge):
    f,s,a,old,result=knowledge;before=f.get(a);pack=load_package();pack['knowledge']['source_mappings'][0]['field_path']='inventedField'
    with pytest.raises(ApiFailure):s.import_package(a,dict(expected_revision=3,request_key='knowledge_invalid_001'),package=pack)
    assert f.get(a)==before


def test_schema_artifact_matches_runtime():
    path=Path(__file__).resolve().parents[1]/'workflow_api/schemas/business-knowledge-v1.json'
    assert json.loads(path.read_text())==MODEL_SCHEMA


def test_real_regeneration_preserves_enrichment_and_conflict_is_atomic(knowledge,generation):
    from workflow_api.business_extraction import OUTPUT_SCHEMA
    f,s,a,old,result=knowledge;provider=generation[4];jobs=generation[5];previous=f.version(a,result['version_id'])
    def output(target):
        target.clear()
        for group in ('concepts','relationships','rules'):
            fields=OUTPUT_SCHEMA['properties'][group]['items']['properties']
            target[group]=[{key:deepcopy(v[key]) for key in fields} for v in previous[group] if v['module_id']=='engines']
        target['questions']=[]
    provider.modify=output
    job=submit(generation,module='engines',key='knowledge_regeneration_001');jobs.tick()
    assert jobs.get(a,job['job_id'])['state']=='succeeded'
    saved=f.version(a,jobs.get(a,job['job_id'])['version_id'])
    assert saved['knowledge']==previous['knowledge']
    check_snapshot(saved)
    assert provider.calls[-1]['protected_definitions']['relationships']
    def conflict(target):
        output(target);target['relationships']=[]
    provider.modify=conflict
    job=submit(generation,module='engines',key='knowledge_regeneration_002');jobs.tick()
    assert jobs.get(a,job['job_id'])['state']=='failed'
    assert f.get(a)['current_version_id']==saved['version_id']


def test_existing_reference_rule_handlers_unchanged(knowledge):
    from workflow_api.business_rule_execution import availability,SPECS
    f,s,a,old,result=knowledge;v=f.version(a,result['version_id'])
    selected=[r for r in v['rules'] if r['id'] in SPECS]
    assert len(selected)==3 and all(availability(r)['available'] for r in selected)


def test_relationship_direction_and_typed_operands(knowledge):
    f,s,a,old,result=knowledge
    for modify in [
      lambda v:next(r for r in v['relationships'] if r['id']=='inspection:report_complaint').update(source='complaints:warranty_ticket'),
      lambda v:v['knowledge']['structured_rules'][0]['conditions']['all'][2].update(value='true'),
      lambda v:v['knowledge']['concept_details'][0]['attributes'][0].update(allowed_values=['x','x']),
    ]:
        v=f.version(a,result['version_id']);modify(v);v['knowledge_sha256']=digest(v['knowledge'])
        with pytest.raises(ApiFailure):check_snapshot(v)


def test_mapping_metadata_coverage_and_missing_fields(knowledge):
    from workflow_api.business_knowledge import metadata_coverage
    f,s,a,old,result=knowledge;k=f.version(a,result['version_id'])['knowledge']
    with f.store.transaction() as db:
        doc=dict(datasets=[dict(name='tickets',fields=[dict(name='engineNo',types=['string']),dict(name='complaintRecord.hmr',types=['number'])])])
        db.execute('INSERT INTO data_source_snapshots VALUES (?,?,?)',('service',1,json.dumps(doc)))
        report=metadata_coverage(db,('one','alice'),f.document(db,('one','alice')),k['source_mappings'],k['identity_rules'])
    states={r['id']:r['status'] for r in report}
    assert states['mapping:ticket_serial']=='observed_in_metadata'
    assert states['mapping:complaint_hours']=='type_mismatch'
    assert states['mapping:sale_date']=='field_unavailable'
    assert states['mapping:qa_serial']=='collection_unavailable'


def test_actual_reference_value_required_and_native_types_preserved(knowledge):
    f,s,a,old,result=knowledge;definition=next(i for i in f.version(a,result['version_id'])['knowledge']['identity_rules'] if i['id']=='identity:inspection_ticket')
    left=dict(connection_id='one',collection='jointinspectionreports',native_type='string',native_value='report1',reference_type='string',reference_value='ticket1')
    right=dict(connection_id='one',collection='tickets',native_type='string',native_value='ticket1')
    assert associate(definition,left,right)['association']=='direct_reference'
    assert associate(definition,{**left,'reference_type':'ObjectId'},right)['association']=='unresolved_reference'
    assert associate(definition,left,{**right,'connection_id':'other'})['association']=='unresolved_reference'
    assert associate(definition,{k:v for k,v in left.items() if not k.startswith('reference')},right)['association']=='unresolved_reference'


def test_policy_revision_pinned_even_after_heads_change(knowledge):
    from workflow_api.business_policies import BusinessPolicies,CLAUSES,digest as policy_digest
    from hashlib import sha256
    f,s,a,old,result=knowledge;BusinessPolicies(f,None,None)
    text='Configuration of assessment date basis for a synthetic policy-version fixture.'
    source=dict(source_id='fixture_policy',kind='policy',title='Fixture',text=text,sha256=sha256(text.encode()).hexdigest())
    policy=dict(policy_id='policy_fixture1',policy_key='fixture_policy',revision=1,source=source,clauses={k:dict(value=None,quote=None) for k in CLAUSES})
    policy['sha256']=policy_digest(policy)
    with f.store.transaction() as db:
        db.execute('INSERT INTO business_policy_heads VALUES (?,?,?,?)',('one','alice','fixture_policy',1))
        db.execute('INSERT INTO business_policy_versions VALUES (?,?,?,?,?,?,?,?)',('one','alice','policy_fixture1','fixture_policy',1,'policy_key_001','fixture',json.dumps(policy)))
    new=s.import_package(a,dict(expected_revision=3,request_key='knowledge_policy_001'))
    v=f.version(a,new['version_id']);assert v['knowledge']['manifest']['policy_refs'][0]['revision']==1
    with f.store.transaction() as db:db.execute('DELETE FROM business_policy_heads WHERE workspace=? AND owner=?',('one','alice'))
    check_snapshot(f.version(a,new['version_id']))
    assert s.inspect(a,new['version_id'])['knowledge']['manifest']['policy_snapshots'][0]==policy


def test_cli_reads_saved_version_without_writes(knowledge,tmp_path):
    import subprocess,sys,sqlite3,hashlib
    f,s,a,old,result=knowledge
    # SQLite WAL content is observed through a logical snapshot, not main-file bytes.
    def rows():
        with sqlite3.connect(f.store.path) as db:return db.execute('SELECT * FROM business_ontology_versions').fetchall(),db.execute('SELECT * FROM business_ontology_events').fetchall()
    before=rows()
    cmd=[sys.executable,str(Path(__file__).resolve().parents[1]/'scripts/inspect_business_knowledge.py'),'--database',f.store.path,'--workspace','one','--owner','alice','--concept','inspection:inspection_report']
    run=subprocess.run(cmd,capture_output=True,text=True,timeout=30)
    assert run.returncode==0,run.stdout+run.stderr
    assert json.loads(run.stdout)['concept']['id']=='inspection:inspection_report'
    assert rows()==before


def test_backend_http_inspection_import_and_access(tmp_path):
    from fastapi.testclient import TestClient
    from workflow_api.main import create_app
    from workflow_api.business_reference import load_kit
    app=create_app(database=tmp_path/'http.sqlite',dev_auth=True,start_workers=False,planning_worker_enabled=False)
    client=TestClient(app);root='/business-ontology/v1'
    assert client.get(root+'/versions/missing/knowledge').status_code==401
    client.get('/session');client.cookies.set('builder_dev_session',client.cookies.get('builder_dev_session'),path='/')
    kit,bundle=load_kit()
    with app.state.workflow_service.store.transaction() as db:
        for cid in bundle['required_sources'].values():
            doc=dict(connection_id=cid,name=cid,engine='mongodb',connection_status='connected',metadata_revision=1)
            db.execute('INSERT INTO data_source_connections VALUES (?,?,?,?,?)',(cid,'local-workspace','local-builder',None,json.dumps(doc)))
    client.post(root+'/initialize',json={'sources':bundle['required_sources']})
    client.post(root+'/reference-modules',json=dict(expected_revision=1,request_key='knowledge_http_base'))
    body=dict(expected_revision=2,request_key='knowledge_http_import')
    assert client.post(root+'/knowledge/import',json=body,headers={'origin':'https://foreign.example'}).status_code==403
    assert client.post(root+'/knowledge/import',json={}).status_code==422
    r=client.post(root+'/knowledge/import',json=body)
    assert r.status_code==200,r.text
    vid=r.json()['data']['version_id']
    assert client.get(root+'/versions/'+vid+'/knowledge').json()['data']['knowledge']['schema_version']=='simpson-knowledge-v1'
    assert client.get(root+'/versions/'+vid+'/knowledge/concepts/inspection:inspection_report').status_code==200
    assert client.get(root+'/versions/'+vid+'/knowledge/concepts/missing:concept').status_code==404
    endpoint=root+'/versions/'+vid+'/knowledge/diagnose'
    assert client.post(endpoint,json=dict(operation='convert',id='mapping:complaint_hours',value='0')).json()['data']['result']['value']=='0'
    assert client.post(endpoint,json=dict(operation='state',id='state:inspection_report',value={})).status_code==422
    assert client.post(endpoint,json=dict(operation='execute_python',id='x')).status_code==422
    app.state.workflow_auth['subject']['subject_id']='foreign'
    assert client.get(root+'/versions/'+vid+'/knowledge').status_code==404


def test_enriched_version_works_with_existing_query_and_graph_services(knowledge):
    from workflow_api.business_compiler import BusinessCompiler
    from workflow_api.business_rules import BusinessRules,compilation_problem
    from workflow_api.business_graph import BusinessGraph
    from workflow_api.data_sources import DataSources
    f,s,a,old,result=knowledge;vid=result['version_id'];snapshot=f.version(a,vid)
    compiler=BusinessCompiler(f);compilation=compiler.compile(a,vid,{})['compilation']
    assert compilation_problem(snapshot,compilation) is None
    assert BusinessRules(f,compiler).view(a,vid)['version_id']==vid
    manager=DataSources(f.store,{})
    plan=BusinessGraph(f,compiler,manager,lambda w,o:a).plan(a,vid)
    assert plan['version_id']==vid and len(plan['mappings'])==21


def test_source_change_during_import_rolls_back(knowledge):
    from workflow_api.business_documents import source_stamp
    f,s,a,old,result=knowledge;pack=load_package();pack['revision']+=1
    with f.store.transaction(write=False) as db:stamp=source_stamp(f,db,('one','alice'),f.document(db,('one','alice')))
    changed=deepcopy(stamp);changed['service']['revision']=99
    before=f.get(a)
    with patch('workflow_api.business_knowledge.source_stamp',side_effect=[stamp,changed]):
        with pytest.raises(ApiFailure) as exc:s.import_package(a,dict(expected_revision=3,request_key='knowledge_drift_001'),package=pack)
    assert exc.value.code=='BUSINESS_SOURCE_CHANGED'
    assert f.get(a)==before


def test_arbitrary_conversion_and_diagnostic_payloads_rejected(knowledge):
    f,s,a,old,result=knowledge
    for body in [dict(operation='rule',id='warranty:assessment_readiness',facts={},parameters={'max_hours':999}),dict(operation='convert',id='mapping:complaint_hours',value='0',code='anything')]:
        with pytest.raises(ApiFailure):s.diagnose(a,result['version_id'],body)
    with pytest.raises(ApiFailure):convert('0','eval','decimal')
    r=s.diagnose(a,result['version_id'],dict(operation='convert',id='mapping:inspection_status',value='COMPLETED'))
    assert r['result']['state']=='unsupported_value'


def test_association_does_not_coerce_boolean_or_numeric_serials(knowledge):
    f,s,a,old,result=knowledge;definition=next(i for i in f.version(a,result['version_id'])['knowledge']['identity_rules'] if i['id']=='identity:invoice_qa_serial')
    left=dict(connection_id='one',collection='enginedetails',native_type='string',native_value='1',serial=1)
    right=dict(connection_id='two',collection='failedengineanalyses',native_type='string',native_value='2',serial=True)
    with pytest.raises(ApiFailure):associate(definition,left,right)
