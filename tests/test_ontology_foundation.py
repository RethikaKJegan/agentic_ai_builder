"""Ontology acceptance: no cloud calls or fabricated expert business validation."""
from copy import deepcopy
import json
from types import SimpleNamespace
import pytest
from workflow_api.data_sources import DataSources
from workflow_api.storage import WorkflowStore
from workflow_api.service import ApiFailure
from workflow_api.data_profiles import summarize, overlap, composite
from workflow_api.ontology_model import graph_errors
from tests.test_data_relationships import auth, sources


@pytest.fixture
def foundation(tmp_path):
    manager=DataSources(WorkflowStore(tmp_path/'ontology.sqlite'),{})
    with manager.store.transaction() as db:
        for source in sources():
            c=source['connection']
            db.execute('INSERT INTO data_source_connections VALUES (?,?,?,?,?)',(c['connection_id'],'one','alice','encrypted',json.dumps(c)))
            db.execute('INSERT INTO data_source_snapshots VALUES (?,?,?)',(c['connection_id'],1,json.dumps(source['snapshot'])))
    return manager.ontology_foundation


def concept(rid='customer',**changes):
    return dict(id=rid,kind='concept',layer='organization',label=rid,definition='Reviewed fixture definition',dependencies=[],source_refs=[],evidence_class='unverified_hypothesis',properties={},**changes)


def put(f,r,revision=0):
    return f.put(auth(),dict(record=r,expected_revision=revision))


def accept(f,rid,action='accept',**extra):
    r=next(r for r in f.get(auth())['records'] if r['id']==rid)
    return f.review(auth(),rid,dict(action=action,expected_revision=r['revision'],reason='Fixture review, not a Simpsons SME decision.',**extra))


def published(f):
    return f.publish(auth(),dict(revision=f.get(auth())['revision']))['version_id']


def test_migration_idempotent_and_tenant_isolation(foundation):
    f=foundation;put(f,concept());type(f)(f.manager)
    assert len(f.get(auth())['records'])==1
    assert f.get(auth(owner='other'))['records']==[]
    assert f.get(auth(workspace='two'))['records']==[]
    with pytest.raises(ApiFailure):f.put(auth(write=False),dict(record=concept(),expected_revision=0))


def test_strict_shapes_and_stale_edit(foundation):
    f=foundation;bad=concept();bad['confidence']=.99
    with pytest.raises(ApiFailure):put(f,bad)
    put(f,concept())
    with pytest.raises(ApiFailure) as error:put(f,concept())
    assert error.value.status==409
    with pytest.raises(ApiFailure):put(f,{**concept('mapping'),'kind':'mapping'})


def test_templates_and_imports_are_drafts(foundation):
    f=foundation;f.templates(auth());view=f.sync(auth())
    assert {'Sales','Procurement','Finance','Customer Service'}<={r.get('domain') for r in view['records']}
    assert all(r['status']=='draft' for r in view['records'])
    assert any(r['id']=='source:pg_orders' for r in view['records'])
    count=len(view['records']);assert len(f.sync(auth())['records'])==count
    with pytest.raises(ApiFailure):published(f)


def test_review_history_and_publication_idempotency(foundation):
    f=foundation;put(f,concept());accept(f,'customer')
    version=published(f);assert published(f)==version
    corrected={**concept(),'definition':'Corrected definition'}
    accept(f,'customer','correct',record=corrected)
    history=f.history(auth(),'customer')['events']
    event=next(e for e in history if e['action']=='correct')
    assert event['original']['definition']=='Reviewed fixture definition'
    assert event['record']['definition']=='Corrected definition'
    assert f.version(auth(),version)['records'][0]['definition']=='Reviewed fixture definition'
    assert published(f)!=version


def test_cycle_rules_are_predicate_specific(foundation):
    f=foundation
    for rid in ('a','b'):put(f,concept(rid))
    def edge(rid,a,b,acyclic=False):
        r=concept(rid);r.update(kind='relationship',properties=dict(source=a,target=b,predicate='references',acyclic=acyclic));return r
    put(f,edge('ab','a','b'));put(f,edge('ba','b','a'))
    assert not graph_errors(f.get(auth())['records'])
    with pytest.raises(ApiFailure):put(f,edge('ab','a','b',True),1)


def test_endpoint_and_attribute_type_validation(foundation):
    f=foundation;put(f,concept('a'))
    attr={**concept('name'),'kind':'attribute','label':'Name','properties':dict(source='a',datatype='string')}
    put(f,attr)
    with pytest.raises(ApiFailure):put(f,{**attr,'id':'name2','properties':dict(source='a',datatype='integer')})
    with pytest.raises(ApiFailure):put(f,{**concept('edge'),'kind':'relationship','properties':dict(source='name',target='a',predicate='references')})


def test_select_dependency_closure_excludes_unrelated_and_records_impact(foundation):
    f=foundation
    for rid in ('party','customer','unrelated'):
        r=concept(rid)
        if rid=='customer':r['dependencies']=['party']
        put(f,r);accept(f,rid)
    version=published(f);selected=f.select(auth(),dict(version_id=version,concept_ids=['customer']))
    assert {r['id'] for r in selected['records']}=={'party','customer'}
    with f.store.transaction() as db:
        binding=f.bind(db,auth(),selected['manifest']['selection_id'],'wf',1,'run1')
    accept(f,'party','correct',record={**concept('party'),'definition':'Changed meaning'})
    impacts=f.get(auth())['impacts']
    assert any(i['workflow_id']=='wf' and i['run_id']=='run1' for i in impacts)
    with f.store.transaction() as db:
        with pytest.raises(ApiFailure):f.bind(db,auth(),selected['manifest']['selection_id'],'wf',1)
    with pytest.raises(ApiFailure):f.select(auth(),dict(version_id=version,concept_ids=['customer']))
    assert binding['record_ids']==['customer','party']


def test_revoked_source_blocks_historical_access_and_dependents(foundation):
    f=foundation;r=concept();r['source_refs']=['pg_orders'];put(f,r);accept(f,'customer');version=published(f)
    put(f,{**concept('dependent'),'dependencies':['customer']})
    with f.store.transaction() as db:
        row=db.execute("SELECT document FROM data_source_connections WHERE connection_id='pg'").fetchone();c=json.loads(row[0]);c['connection_status']='disconnected'
        db.execute("UPDATE data_source_connections SET document=? WHERE connection_id='pg'",(json.dumps(c),))
    assert f.get(auth())['records']==[]
    with pytest.raises(ApiFailure):f.version(auth(),version)
    with pytest.raises(ApiFailure):f.history(auth(),'customer')


def test_source_drift_only_invalidates_dependent_definitions(foundation):
    f=foundation;r=concept();r['source_refs']=['pg_orders'];put(f,r);accept(f,'customer');put(f,concept('unrelated'));accept(f,'unrelated')
    with f.store.transaction() as db:
        row=db.execute("SELECT document FROM data_source_snapshots WHERE connection_id='pg'").fetchone();snapshot=json.loads(row[0]);snapshot['datasets'][0]['fields'][0]['types']=['boolean']
        db.execute("UPDATE data_source_snapshots SET document=? WHERE connection_id='pg'",(json.dumps(snapshot),))
    by_id={r['id']:r for r in f.get(auth())['records']}
    assert by_id['customer']['stale'] and not by_id['unrelated']['stale']
    with pytest.raises(ApiFailure):accept(f,'customer')
    with pytest.raises(ApiFailure):published(f)


def test_profiles_have_honest_denominators_and_typed_hashes():
    fields=[dict(field_id='id',name='id')]
    profile=summarize([{},dict(id=None),dict(id=1),dict(id=1),dict(id='1'),dict(id=True)],fields)['id']
    assert (profile['sample_size'],profile['missing'],profile['nulls'],profile['null_rate'])==(6,1,1,.2)
    assert profile['distinct']==3 and profile['uniqueness']==.75
    assert summarize([],fields)['id']['null_rate'] is None
    assert overlap(profile,profile)['referential_consistency']==1
    assert not overlap(profile,profile)['population_verified']
    keys=composite([dict(a=1,b='2'),dict(a='1',b=2),dict(a=1)],['a','b'])
    assert keys['comparable']==2 and len(keys['key_hashes'])==2
    assert '1' not in profile['key_hashes']


def test_uncalibrated_never_auto_accepts(foundation):
    f=foundation;put(f,concept());r=f.get(auth())['records'][0]
    assert r['assessment']['calibrated_score'] is None
    calibration=f.calibrate(auth(),dict(minimum_precision=.95,minimum_examples=20))
    assert calibration['precision'] is None and not calibration['eligible']
    with pytest.raises(ApiFailure):f.apply_calibration(auth(),dict(record_id=r['id'],expected_revision=r['revision'],calibration_id=calibration['calibration_id'],auto_accept=True))


def test_merge_preserves_old_identity_and_requires_compatible_target(foundation):
    f=foundation
    for rid in ('a','b'):put(f,concept(rid));accept(f,rid)
    accept(f,'a','merge',target_id='b');assert next(r for r in f.get(auth())['records'] if r['id']=='a')['redirect']=='b'
    with pytest.raises(ApiFailure):accept(f,'b','merge',target_id='a')


def test_replay_is_eligibility_only_without_bound_workflow(foundation):
    f=foundation;put(f,concept());accept(f,'customer');v=published(f);f.select(auth(),dict(version_id=v,concept_ids=['customer']))
    accept(f,'customer','correct',record={**concept(),'definition':'New meaning'})
    iid=f.get(auth())['impacts'][0]['impact_id'];result=f.replay(auth(),iid,dict(action='assess'))
    assert result['eligibility']=='requires_reconciliation_or_workflow_binding'
    with pytest.raises(ApiFailure):f.replay(auth(),iid,dict(action='submit',inputs={},idempotency_key='test'))


def test_version_lookups_return_provenance(foundation):
    f=foundation;r=concept();r['source_refs']=['pg_orders_customerID'];put(f,r);accept(f,'customer');v=published(f)
    result=f.lookup(auth(),v,'source_field','pg_orders_customerID')
    assert result['records'][0]['source_signatures']
    assert result['version_id']==v


def test_readonly_replay_uses_existing_service_with_stable_idempotency(foundation):
    f=foundation;put(f,concept());accept(f,'customer');v=published(f);s=f.select(auth(),dict(version_id=v,concept_ids=['customer']))
    workflow=dict(workflow_id='wf',version=1,status='approved',execution_policy=dict(allow_external_writes=False),tools=[])
    with f.store.transaction() as db:
        f.store.put(db,'one',workflow);f.bind(db,auth(),s['manifest']['selection_id'],'wf',1,'run1')
    accept(f,'customer','correct',record={**concept(),'definition':'Changed'})
    requests=[]
    f.workflow_service=SimpleNamespace(store=f.store,handle=lambda req,auth:requests.append(req) or dict(status=409,error='Canonical service rejected stale selection'))
    impact=next(i for i in f.get(auth())['impacts'] if i.get('run_id'))
    body=dict(action='submit',inputs={},idempotency_key='same')
    assert f.replay(auth(),impact['impact_id'],body)['status']==409
    f.replay(auth(),impact['impact_id'],body)
    assert requests[0]['operation']=='execute_workflow' and requests[0]['idempotency_key']==requests[1]['idempotency_key']


def test_http_api_compatibility_and_rejected_mutations(foundation):
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from unittest.mock import patch
    from workflow_api.data_source_routes import install
    class Service:
        store=foundation.store
        def envelope(self,ref,status,data):return dict(request_id=ref,status=status,data=data)
        def failure(self,ref,exc):return dict(error=dict(error_code=exc.code,message=str(exc)))
    app=FastAPI()
    with patch('workflow_api.data_source_routes.DataSources',return_value=foundation.manager):install(app,Service(),auth(),{},lambda:'req_test')
    client=TestClient(app)
    assert client.get('/ontology/v1').status_code==410
    assert client.get('/ontology/v1/metrics').status_code==410
    assert client.get('/data-ontology').status_code==200
    assert client.get('/knowledge-graph').status_code==200
    assert client.post('/ontology/v1/templates',json={}).status_code==410
    assert client.post('/ontology/v1/record',json={'invalid':'shape'}).status_code==410
    assert client.post('/ontology/v1/select',json={'version_id':'other','concept_ids':['customer']}).status_code==410
    app.state.workflow_auth=auth(write=False)
    assert client.post('/ontology/v1/templates',json={}).status_code==410


def test_profiles_stay_outside_legacy_metadata_contract(foundation):
    from jsonschema import Draft202012Validator
    from pathlib import Path
    f=foundation
    with f.store.transaction() as db:
        f.store_profiles(db,'pg',1,1,{'pg_orders':dict(fields={'pg_orders_customerID':dict(sample_size=2,missing=0,nulls=0,key_hashes=['abc'])},basis='bounded_sample')})
    view=f.get(auth());dataset=next(d for c in view['catalogue'] for d in c['datasets'] if d['dataset_id']=='pg_orders')
    assert dataset['value_profiles']['pg_orders_customerID']['sample_size']==2
    assert 'value_profiles' not in f.manager.metadata(auth(),'pg')['snapshot']['datasets'][0]


def test_nested_fields_are_not_misreported_missing():
    fields=[dict(field_id='nested',name='a.b'),dict(field_id='array',name='items[].id')]
    profiles=summarize([{'a':{'b':None},'items':[{'id':1},{'id':2}]},{'a':{'b':'x'}}],fields)
    assert profiles['nested']['missing']==0 and profiles['nested']['nulls']==1
    assert profiles['array']['missing']==1 and profiles['array']['unsupported_values']==1


def test_changed_dependency_requires_explicit_revalidation(foundation):
    f=foundation;put(f,concept('common'));accept(f,'common')
    put(f,{**concept('org'),'dependencies':['common']});accept(f,'org');published(f)
    accept(f,'common','correct',record={**concept('common'),'definition':'Changed shared definition'})
    assert next(r for r in f.get(auth())['records'] if r['id']=='org')['stale']
    with pytest.raises(ApiFailure):published(f)
    accept(f,'org','correct',record={**concept('org'),'dependencies':['common']});published(f)


def test_typed_constraints_and_mapping_conflicts(foundation):
    f=foundation
    for rid in ('a','b'):put(f,concept(rid))
    put(f,{**concept('amount'),'kind':'attribute','label':'Amount','properties':dict(source='a',datatype='number')})
    constraint={**concept('limit'),'kind':'constraint','properties':dict(source='a',attribute='amount',rule='range',minimum=0,maximum=10)}
    put(f,constraint)
    with pytest.raises(ApiFailure):put(f,{**constraint,'id':'bad_limit','properties':dict(source='a',attribute='amount',rule='range',minimum=11,maximum=10)})
    put(f,{**concept('other_amount'),'kind':'attribute','label':'Amount','properties':dict(source='b',datatype='string')})
    with pytest.raises(ApiFailure):put(f,{**concept('mapping'),'kind':'mapping','properties':dict(source='a',target='b')})


def test_removed_field_retains_authorized_history_but_invalidates_current_use(foundation):
    f=foundation;r=concept();r['source_refs']=['pg_orders_customerID'];put(f,r);accept(f,'customer');version=published(f)
    with f.store.transaction() as db:
        snapshot=json.loads(db.execute("SELECT document FROM data_source_snapshots WHERE connection_id='pg'").fetchone()[0]);snapshot['datasets'][0]['fields']=[x for x in snapshot['datasets'][0]['fields'] if x['field_id']!='pg_orders_customerID']
        db.execute("UPDATE data_source_snapshots SET document=? WHERE connection_id='pg'",(json.dumps(snapshot),))
        f.source_changed(db,('one','alice'))
    assert f.version(auth(),version)['stale']
    assert f.get(auth())['records'][0]['stale']
    assert f.history(auth(),'customer')['events']
    with pytest.raises(ApiFailure):f.select(auth(),dict(version_id=version,concept_ids=['customer']))


from tests.test_runtime import RuntimeFixture
from runtime.service import RuntimeFailure

class OntologyRuntimeTests(RuntimeFixture):
    def setUp(self):
        super().setUp()
        manager=DataSources(self.store,{})
        self.workflows.database_workflows=SimpleNamespace(manager=manager)
        self.ontology=manager.ontology_foundation
        r=concept()
        self.ontology.put(self.auth,dict(record=r,expected_revision=0))
        self.ontology.review(self.auth,'customer',dict(action='accept',expected_revision=1,reason='Fixture business validation'))
        version=self.ontology.publish(self.auth,dict(revision=self.ontology.get(self.auth)['revision']))['version_id']
        self.selection=self.ontology.select(self.auth,dict(version_id=version,concept_ids=['customer']))['manifest']['selection_id']
        self.workflow['metadata']['ontology_selection_id']=self.selection;self.put()

    def test_run_creation_atomically_records_actual_ontology_consumption(self):
        run=self.runtime.create_run(self.request(),self.auth)
        with self.store.transaction(write=False) as db:
            bindings=self.ontology.rows(db,'selections',('local-workspace','operator'))
        self.assertTrue(any(b.get('run_id')==run['run_id'] and b['record_ids']==['customer'] for b in bindings))

    def test_changed_ontology_prevents_run_submission_and_worker_revision_use(self):
        self.ontology.review(self.auth,'customer',dict(action='correct',expected_revision=2,reason='Fixture correction',record={**concept(),'definition':'Changed definition'}))
        with self.assertRaises(RuntimeFailure) as error:self.runtime.create_run(self.request(),self.auth)
        self.assertEqual(error.exception.code,'ONTOLOGY_STALE')
        with self.store.transaction(write=False) as db:
            self.assertEqual(db.execute('SELECT COUNT(*) FROM runtime_runs').fetchone()[0],0)


def test_secret_rejected_before_ontology_persistence(foundation):
    r=concept();r['definition']='password=never_store_this'
    with pytest.raises(ApiFailure) as error:put(foundation,r)
    assert error.value.code=='SENSITIVE_DATA_DETECTED'
    assert foundation.get(auth())['records']==[]


def test_rename_candidates_never_transfer_identity_or_approval():
    from workflow_api.data_drift import rename_candidates
    previous=dict(datasets=[dict(dataset_id='d',discovery_method='sampled',fields=[dict(field_id='old',name='customer_code',types=['string'])])])
    current=dict(datasets=[dict(dataset_id='d',fields=[dict(field_id='new',name='customerCode',types=['string'])])])
    candidate=rename_candidates(previous,current)[0]
    assert candidate['classification']=='unverified_hypothesis' and candidate['validation_status']=='needs_review'
    assert candidate['sampled_omission_is_not_deletion'] and candidate['previous_field_id']!=candidate['current_field_id']


def test_calibration_precision_gate_has_positive_and_negative_cases():
    from workflow_api.ontology_foundation import calibration_statistics
    # Synthetic labels verify the calculation only; not production calibration evidence.
    labels={str(i):(.99,True,i>=200) for i in range(300)}
    good=calibration_statistics(labels,.95,20)
    assert good['eligible'] and good['precision']==1 and good['precision_lower_bound']>.95
    for i in range(200,250):labels[str(i)]=(.99,False,True)
    bad=calibration_statistics(labels,.95,20)
    assert not bad['eligible'] and bad['precision']==.5 and bad['false_positive_rate']==1


def test_legacy_review_is_preserved_as_evidence_without_bulk_approval(foundation):
    from unittest.mock import patch
    f=foundation;f.manager.relationships.request(auth());f.manager.relationships.tick()
    edge=f.manager.relationships.get(auth())['graph']['relationships'][0]
    legacy=dict(source_dataset_id=edge['source_dataset_id'],target_dataset_id=edge['target_dataset_id'],relationship_id='old_review',reversed=True,predicate='places',rationale='Previously reviewed fixture meaning',status='confirmed',inference_method='user_review',technical_relationship_id=edge['relationship_id'],field_pairs=edge['field_pairs'])
    with patch.object(f.manager.semantic,'project',return_value=dict(relationships=[legacy])):view=f.sync(auth())
    imported=next(r for r in view['records'] if r['id']=='legacy:old_review')
    assert imported['status']=='draft' and imported['evidence_class']=='model_inference'
    assert imported['properties']['source']=='source:'+edge['target_dataset_id']
    with f.store.transaction(write=False) as db:events=f.rows_events(db,('one','alice'))
    assert any(e.get('legacy',{}).get('status')=='confirmed' for e in events)


def test_definition_candidates_and_value_observations_remain_unverified(foundation):
    from workflow_api.data_profiles import token
    f=foundation;f.templates(auth())
    with f.store.transaction() as db:
        profile=dict(sample_size=15,comparable=15,uniqueness=1,key_hashes=[token(str(i)) for i in range(15)])
        f.store_profiles(db,'pg',1,1,{'pg_orders':dict(fields={'pg_orders_customerID':profile},basis='bounded_sample'),'pg_customers':dict(fields={'pg_customers_customerID':profile},basis='bounded_sample')})
    view=f.sync(auth())
    assert any(r['kind']=='mapping' and r['properties']['method']=='ontology_definition_similarity_v1' for r in view['records'])
    observations=[r for r in view['records'] if r['evidence_class']=='statistical_finding']
    assert observations and all(r['status']=='draft' and r['properties']['predicate']=='sample_overlap' for r in observations)


def test_replay_targets_only_existing_reviewed_replacement_revision(foundation):
    f=foundation;put(f,concept());accept(f,'customer');v=published(f);s=f.select(auth(),dict(version_id=v,concept_ids=['customer']))
    with f.store.transaction() as db:
        f.store.put(db,'one',dict(workflow_id='wf',version=1,status='approved',metadata=dict(ontology_selection_id=s['manifest']['selection_id']),execution_policy={},tools=[]))
        f.bind(db,auth(),s['manifest']['selection_id'],'wf',1,'run_old')
    accept(f,'customer','correct',record={**concept(),'definition':'Corrected meaning'})
    version=published(f);replacement=f.select(auth(),dict(version_id=version,concept_ids=['customer']))
    with f.store.transaction() as db:
        f.store.put(db,'one',dict(workflow_id='wf',version=2,status='approved',metadata=dict(ontology_selection_id=replacement['manifest']['selection_id']),execution_policy={},tools=[]))
    requests=[];f.workflow_service=SimpleNamespace(store=f.store,handle=lambda request,auth:requests.append(request) or dict(status=200,data=dict(run=dict(run_id='run_replay'))))
    impact=next(i for i in f.get(auth())['impacts'] if i.get('run_id'))
    assert f.replay(auth(),impact['impact_id'],dict(action='assess'))['revalidation']=='required'
    result=f.replay(auth(),impact['impact_id'],dict(action='submit',workflow_version=2,inputs={},idempotency_key='replace'))
    assert result['status']==200 and requests[0]['payload']['workflow_version']==2
    saved=next(i for i in f.get(auth())['impacts'] if i['impact_id']==impact['impact_id'])
    assert saved['workflow_version']==1 and saved['target_workflow_version']==2 and saved['submitted_run_id']=='run_replay'


def test_low_risk_policy_uses_validated_dependencies(foundation):
    f=foundation
    for rid in ('organization','shared'):put(f,concept(rid));accept(f,rid)
    r={**concept('match'),'kind':'mapping','definition':'customerID','source_refs':['pg_orders_customerID'],'properties':dict(source='organization',target='shared',risk='low')}
    put(f,r)
    # The fixture artifact exercises policy mechanics only; not production calibration.
    calibration=dict(calibration_id='fixture_calibration',created_at='2026-10-30',kind='mapping',domain=None,eligible=True,minimum_examples=20,minimum_precision=.95,bins=[dict(n=200,probability=1) for _ in range(5)],precision=1,false_positive_rate=0,held_out_examples=100)
    with f.store.transaction() as db:f.save(db,'calibrations','calibration_id',('one','alice'),'fixture_calibration',calibration)
    view=f.apply_calibration(auth(),dict(record_id='match',expected_revision=1,calibration_id='fixture_calibration',auto_accept=True))
    result=next(r for r in view['records'] if r['id']=='match')
    assert result['status']=='approved' and not result['stale'] and result['assessment']['calibrated_score']==1
    version=published(f);assert f.metrics(auth(),version,'fixture_calibration')['calibration']['held_out_examples']==100


def test_selecting_domain_concept_includes_organization_mapping_and_common_dependency(foundation):
    f=foundation
    definitions=[{**concept('party'),'layer':'common'},
        {**concept('customer'),'layer':'domain','domain':'Sales','dependencies':['party']},
        concept('organization_customer'),
        {**concept('customer_mapping'),'kind':'mapping','properties':dict(source='organization_customer',target='customer')}]
    for r in definitions:put(f,r);accept(f,r['id'])
    version=published(f);selected=f.select(auth(),dict(version_id=version,concept_ids=['customer']))
    assert set(selected['manifest']['record_ids'])=={'party','customer','organization_customer','customer_mapping'}


def test_import_provenance_is_visible_in_authorized_history(foundation):
    f=foundation
    with f.store.transaction() as db:
        f.import_record(db,('one','alice'),concept('reviewed_import'),{},'documented_application_draft',
            evidence=dict(review_hash='fixture_hash',business_policy_approved=False))
    history=f.history(auth(),'reviewed_import')['events']
    assert len(history)==1 and history[0]['action']=='import'
    assert history[0]['record']['id']=='reviewed_import'
    assert history[0]['evidence']['review_hash']=='fixture_hash'
    with pytest.raises(ApiFailure):f.history(auth(owner='other'),'reviewed_import')
