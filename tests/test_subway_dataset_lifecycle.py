"""Automatic defaults, immutable source contracts, activation and safe cleanup."""
from copy import deepcopy
import json
import pytest
from tests.test_subway_full_queries import engine,installed,AUTH,plan,field
from workflow_api.subway_demonstration import install,DemoQueries,from_workflow
from workflow_api.subway_demo_data import DATASET,VERSION
from workflow_api.subway_dataset_lifecycle import SubwayDatasetLifecycle,read_dataset,document_from,state
from workflow_api.business_knowledge_model import digest
from workflow_api.service import ApiFailure

ADMIN=deepcopy(AUTH);ADMIN['permissions']=sorted(set(ADMIN['permissions'])|{'workflow.approve','workflow.view'})

@pytest.fixture
def configured(engine):
    real,_=engine;install(real.store,AUTH,real.version,automatic_default=True)
    return real,SubwayDatasetLifecycle(real.store)

def newer(real,revision=2):
    h,r=read_dataset(real.store,AUTH,DATASET);doc=document_from(h,r);doc.update(dataset_id='subway-demonstration-v'+str(revision),revision=revision)
    for rows in doc['records'].values():
        for row in rows:row['demo_dataset']=doc['dataset_id']
    doc['sha256']=digest({k:v for k,v in doc.items() if k!='sha256'});return doc

def workflow(q):return dict(metadata=dict(action_binding_context=dict(validated_context=dict(demo_context=q.demo_context,source_resolution=q.source_resolution))))

@pytest.mark.parametrize('objective',['Investigate purchase-order discrepancies and prepare an evidence-backed report.','Summarize purchase-order counts and values by status and currency.','Check purchase orders for approval issues, budget problems and invoice discrepancies.'])
def test_normal_requests_resolve_active_before_models(configured,objective):
    real,_=configured;q=real.for_objective(AUTH,objective)
    assert q.demo_context['dataset_id']==DATASET and q.source_resolution['selection']=='automatic'
    assert q.version['version_id']==VERSION
    assert q.execute(AUTH,plan(q))['rows']==[dict(records=8)]
    assert from_workflow(real,workflow(q),AUTH).demo_context==q.demo_context

@pytest.mark.parametrize('objective',['Use historical Subway records to count purchase orders.','Query restored Subway data.','Use actual Subway records.'])
def test_explicit_historical_preserves_restored_source(configured,objective):
    real,_=configured;q=real.for_objective(AUTH,objective)
    assert not getattr(q,'demo_context',None)
    assert q.source_resolution['kind']=='historical_snapshot'
    assert q.execute(AUTH,plan(q))['rows']==[dict(records=100)]

@pytest.mark.parametrize('objective',['Investigate real current Subway operations.','Summarize current Subway operations.','Analyze live Subway business data.','Show actual current purchase orders.','Show current invoices.'])
def test_real_current_is_not_substituted(configured,objective):
    real,_=configured
    with pytest.raises(ApiFailure,match='current operations'):real.for_objective(AUTH,objective)

def test_existing_data_and_ontology_are_reused_without_authoring(configured,monkeypatch):
    real,_=configured
    def forbidden(*a,**k):raise AssertionError('Existing demonstration data must not be regenerated')
    monkeypatch.setattr('workflow_api.subway_demonstration.generate',forbidden);monkeypatch.setattr('workflow_api.subway_demonstration.build_ontology',forbidden)
    before=read_dataset(real.store,AUTH,DATASET)
    install(real.store,AUTH,real.version,automatic_default=True)
    assert read_dataset(real.store,AUTH,DATASET)==before

def test_higher_numeric_activation_and_existing_workflow_contracts(configured):
    real,manager=configured;old=real.for_objective(AUTH,'Investigate purchase orders.');saved=workflow(old)
    # Existing historical workflow with no new source contract never follows default.
    assert from_workflow(real,dict(metadata={}),AUTH) is real
    second=manager.register(ADMIN,newer(real,2));assert second['status']=='ACTIVE'
    assert real.for_objective(AUTH,'Investigate purchase orders.').demo_context['revision']==2
    assert from_workflow(real,saved,AUTH).demo_context==old.demo_context
    assert real.for_objective(AUTH,'Use Subway demonstration dataset v1. Investigate orders.').demo_context==old.demo_context
    manager.register(ADMIN,newer(real,10));assert real.for_objective(AUTH,'Investigate orders.').demo_context['revision']==10
    with pytest.raises(ApiFailure):manager.activate(ADMIN,DATASET)
    assert from_workflow(real,saved,AUTH).demo_context['revision']==1

def test_invalid_or_inactive_versions_never_become_default(configured):
    real,manager=configured;doc=newer(real);doc['records']['finance.purchaseorders'][0]['purchaseRequestId']=99999;doc['sha256']=digest({k:v for k,v in doc.items() if k!='sha256'})
    with pytest.raises(ApiFailure,match='reference'):manager.register(ADMIN,doc)
    assert real.for_objective(AUTH,'Investigate orders.').demo_context['revision']==1
    manager.register(ADMIN,newer(real),activate=False)
    assert real.for_objective(AUTH,'Investigate orders.').demo_context['revision']==1
    manager.activate(ADMIN,'subway-demonstration-v2');assert real.for_objective(AUTH,'Investigate orders.').demo_context['revision']==2
    manager.retire(ADMIN,'subway-demonstration-v2')
    with pytest.raises(ApiFailure,match='No eligible active'):real.for_objective(AUTH,'Investigate orders.')
    assert real.for_objective(AUTH,'Use historical records.').source_resolution['kind']=='historical_snapshot'

@pytest.mark.parametrize('mutation',[lambda d:d.update(policy={}),lambda d:d['records']['finance.invoicedatas'][0].update(invoiceAmount=1),lambda d:d['records']['finance.purchaseorders'][0].update(demo_origin='production'),lambda d:d['records']['finance.purchaseorders'].append(deepcopy(d['records']['finance.purchaseorders'][0])),lambda d:d.update(scope=dict(workspace_id='client-simpsons',owner_id='simpsons-client'))])
def test_registration_rejects_incompatible_policy_arithmetic_identity_scope(configured,mutation):
    real,manager=configured;doc=newer(real);mutation(doc);doc['sha256']=digest({k:v for k,v in doc.items() if k!='sha256'})
    with pytest.raises(ApiFailure):manager.register(ADMIN,doc)
    assert manager.inventory(AUTH)['active_dataset_id']==DATASET

def test_cleanup_archives_only_retired_unreferenced_versions_and_retains_ontology(configured):
    real,manager=configured;manager.register(ADMIN,newer(real),activate=False);manager.retire(ADMIN,'subway-demonstration-v2')
    result=manager.cleanup(ADMIN,'subway-demonstration-v2');assert result['status']=='DELETED'
    with pytest.raises(ApiFailure):DemoQueries(real,AUTH,'subway-demonstration-v2')
    with real.store.transaction(write=False) as db:
        assert db.execute('SELECT COUNT(*) FROM subway_demo_records').fetchone()[0]==192
        assert db.execute('SELECT COUNT(*) FROM subway_demo_archives').fetchone()[0]==1
        assert db.execute('SELECT COUNT(*) FROM business_ontology_versions WHERE version_id=?',(VERSION,)).fetchone()[0]==1
    manager.restore(ADMIN,'subway-demonstration-v2');assert DemoQueries(real,AUTH,'subway-demonstration-v2').demo_context['revision']==2
    manager.cleanup(ADMIN,'subway-demonstration-v2')
    with pytest.raises(ApiFailure):manager.cleanup(ADMIN,DATASET)

def test_cleanup_protects_saved_and_inflight_source_references(configured):
    real,manager=configured;manager.register(ADMIN,newer(real));q=real.for_objective(AUTH,'Investigate orders.');manager.register(ADMIN,newer(real,3))
    with pytest.raises(ApiFailure,match='protected'):manager.cleanup(ADMIN,'subway-demonstration-v2')
    inventory=manager.inventory(AUTH);assert inventory['versions']['subway-demonstration-v2']['inventory_classification']=='REFERENCED'
    # A receipt or saved history alone also protects versions never resolved.
    manager.register(ADMIN,newer(real,4),activate=False);manager.retire(ADMIN,'subway-demonstration-v4')
    with real.store.transaction() as db:
        db.execute('CREATE TABLE saved_evidence(workspace TEXT,document TEXT)');db.execute('INSERT INTO saved_evidence VALUES (?,?)',('client-subway',json.dumps(dict(dataset_id='subway-demonstration-v4'))))
    with pytest.raises(ApiFailure):manager.cleanup(ADMIN,'subway-demonstration-v4')

def test_scope_permissions_integrity_and_saved_pin_tampering(configured):
    real,manager=configured
    with pytest.raises(Exception):manager.register(AUTH,newer(real))
    foreign=deepcopy(ADMIN);foreign['subject']=dict(workspace_id='client-simpsons',subject_id='simpsons-client')
    with pytest.raises(ApiFailure):manager.inventory(foreign)
    with pytest.raises(ApiFailure):real.for_objective(foreign,'Investigate orders.')
    q=real.for_objective(AUTH,'Investigate orders.');saved=workflow(q);saved['metadata']['action_binding_context']['validated_context']['source_resolution']['dataset']['sha256']='0'*64
    with pytest.raises(ApiFailure):from_workflow(real,saved,AUTH)
    with real.store.transaction() as db:db.execute("UPDATE subway_demo_records SET document=json_set(document,'$.totalAmount',0) WHERE collection='finance.purchaseorders'")
    with pytest.raises(ApiFailure):real.for_objective(AUTH,'Investigate orders.')

def test_grouped_counts_and_values_match_exact_currency_separated_math(configured):
    from decimal import Decimal
    real,_=configured;q=real.for_objective(AUTH,'Summarize purchase-order counts and values by status and currency.')
    status=field(q,'finance.purchaseorders','status');currency=field(q,'finance.purchaseorders','currency');amount=field(q,'finance.purchaseorders','totalAmount')
    out=q.execute(AUTH,plan(q,group_by=[status,currency],metrics=[dict(label='count',op='count',field_id=''),dict(label='value',op='sum',field_id=amount)]));expected={}
    for p in q.records['finance.purchaseorders']:
        row=expected.setdefault((p['status'],p['currency']),[0,Decimal(0)]);row[0]+=1;row[1]+=Decimal(str(p['totalAmount']))
    assert {(r[status],r[currency]):[r['count'],Decimal(r['value'])] for r in out['rows']}==expected


def test_prepare_source_pin_survives_activation_between_routing_and_compilation(configured):
    real,manager=configured;first=real.for_objective(AUTH,'Investigate orders.');pin=deepcopy(first.source_resolution)
    manager.register(ADMIN,newer(real))
    compiled=real.for_objective(AUTH,'Investigate orders.',pin)
    assert compiled.demo_context['revision']==1
    assert real.for_objective(AUTH,'Investigate orders.').demo_context['revision']==2
    old_historical=real.for_objective(AUTH,'Use historical Subway records.')
    assert old_historical.source_resolution['kind']=='historical_snapshot'
    assert not hasattr(real,'source_resolution')


def test_lifecycle_management_api_uses_tenant_and_review_permissions(configured):
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from workflow_api.subway_dataset_lifecycle import install_routes
    real,_=configured;app=FastAPI();app.state.workflow_auth=deepcopy(ADMIN)
    install_routes(app,real.store,ADMIN,lambda:'dataset_test_request');client=TestClient(app)
    response=client.get('/business-ontology/v1/subway/datasets');assert response.status_code==200
    assert response.json()['data']['active_dataset_id']==DATASET
    response=client.post('/business-ontology/v1/subway/datasets',json=dict(document=newer(real),activate=False));assert response.status_code==200,response.text
    assert client.post('/business-ontology/v1/subway/datasets/subway-demonstration-v2/activate').status_code==200
    app.state.workflow_auth=deepcopy(AUTH)
    assert client.post('/business-ontology/v1/subway/datasets/subway-demonstration-v2/retire').status_code==403
    app.state.workflow_auth['subject']=dict(workspace_id='client-simpsons',subject_id='simpsons-client')
    assert client.get('/business-ontology/v1/subway/datasets').status_code==403

@pytest.mark.parametrize('change',[lambda d:d['records']['finance.invoicedatas'][0]['items'][0].pop('poLineId'),lambda d:d['records']['finance.invoiceitems'][0].update(quantity=99),lambda d:d['records']['finance.payments'][0].update(currency=999)])
def test_deep_schema_and_redundant_invoice_evidence_must_be_consistent(configured,change):
    real,manager=configured;doc=newer(real);change(doc);doc['sha256']=digest({k:v for k,v in doc.items() if k!='sha256'})
    with pytest.raises(ApiFailure):manager.register(ADMIN,doc)
