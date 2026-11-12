"""Persistent demonstration data through actual SQLite source reads and shared query tools."""
from copy import deepcopy
import json
import pytest
from tests.test_subway_full_queries import engine,installed,AUTH,plan
from workflow_api.subway_demonstration import install,DemoQueries,from_workflow
from workflow_api.subway_demo_data import generate,DATASET,LABEL
from workflow_api.subway_assessments import SubwayAssessments
from workflow_api.service import ApiFailure

@pytest.fixture
def demo(engine):
    real,_=engine;install(real.store,AUTH,real.version);return real,DemoQueries(real,AUTH)

def query(q,col='purchaseorders',metrics=None):
    c=q.catalog(AUTH);d=next(d for d in c['datasets'].values() if d['role']=='finance' and d['collection']==col)
    f=next(f['field_id'] for f in d['fields'] if f['name']=='_id')
    return dict(base_dataset_id=d['dataset_id'],fields=[f] if metrics is None else [],metrics=[] if metrics is None else metrics,joins=[],filters=[],group_by=[],order_by=[],offset=0,limit=20)

def test_persistent_dataset_is_idempotent_and_has_coherent_relationships(demo):
    real,q=demo;first=install(real.store,AUTH,real.version);assert first==q.demo_context
    with real.store.transaction(write=False) as db:
        count=db.execute('SELECT COUNT(*) FROM subway_demo_records').fetchone()[0]
    assert count==192
    fresh=DemoQueries(real,AUTH);assert fresh.catalog(AUTH)==q.catalog(AUTH)
    records=generate()['records'];po={r['_id']:r for r in records['finance.purchaseorders']};prs={r['_id']:r for r in records['finance.purchaserequests']}
    for p in po.values():assert p['_id'] in prs[p['purchaseRequestId']]['purchaseOrderIds']
    for inv in records['finance.invoicedatas']:
        assert sum(i['totalAmount'] for i in inv['items'])==inv['invoiceAmount']
        for item in inv['items']:
            assert item['quantity']*item['unitPrice']==item['amount']
            assert item['amount']*item['taxRate']//100==item['taxAmount']
            assert item['amount']+item['taxAmount']==item['totalAmount']
    for b in records['finance.budgets']:assert b['utilizedAmount']+b['reservedAmount']+b['availableBudgetCost']==b['modifiedBudgetCost']

def test_existing_query_executor_reads_persistent_data_and_rejects_mixing(demo):
    real,q=demo;r=q.execute(AUTH,query(q,metrics=[dict(label='records',op='count',field_id='')]))
    assert r['rows']==[dict(records=8)] and r['coverage']['demo_context']==q.demo_context
    assert all(s['freshness']['status']=='modeled_demonstration' for s in r['sources'])
    with pytest.raises(ApiFailure):real.execute(AUTH,query(q))
    with pytest.raises(ApiFailure):q.execute(AUTH,plan(real))
    foreign=deepcopy(AUTH);foreign['subject']['workspace_id']='client-simpsons'
    with pytest.raises(ApiFailure):q.catalog(foreign)

def test_modeled_rules_execute_with_item_reconciliation_and_provenance(demo):
    real,q=demo;r=SubwayAssessments(q).execute(AUTH,dict(assessment='purchase_order_reconciliation',query=query(q)))
    assert r['report']['provenance']['mode']=='modeled_demonstration'
    checks=r['report']['results'];assert any(c['rule_id']=='subway_demo_rule:invoice_tolerance' and c['outcome']=='FAIL' for c in checks)
    assert any(c['rule_id']=='subway_demo_rule:invoice_quantity' and c['outcome']=='FAIL' for c in checks)
    assert all(c['outcome']=='PASS' for c in checks if c['rule_id'] in ('subway_demo_rule:budget_balance','subway_demo_rule:store_mapping','subway_demo_rule:supplier_mapping','subway_demo_rule:requisition_link'))
    assert len(r['report']['invoice_reconciliation'])==8
    assert all(i['due_date'] and i['currency'] and i['items'] for i in r['report']['invoice_reconciliation'])
    assert r['report']['readiness']['outcome']=='PASS'

def test_source_and_ontology_pins_survive_recreation_and_detect_tampering(demo):
    real,q=demo;workflow=dict(metadata=dict(action_binding_context=dict(validated_context=dict(demo_context=q.demo_context))))
    assert from_workflow(real,workflow,AUTH).version['version_id']==q.version['version_id']
    workflow['metadata']['action_binding_context']['validated_context']['demo_context']['sha256']='0'*64
    with pytest.raises(ApiFailure):from_workflow(real,workflow,AUTH)
    with real.store.transaction() as db:db.execute("UPDATE subway_demo_records SET document=json_set(document,'$.totalAmount',1) WHERE collection='finance.purchaseorders'")
    with pytest.raises(ApiFailure):DemoQueries(real,AUTH)

def test_demo_knowledge_has_policy_rag_definitions_and_trusted_bindings(demo):
    _,q=demo;c,k=q.knowledge(AUTH,'Investigate purchase order invoice discrepancies and prepare a report')
    assert k['modeled_policy']['authority']=='modeled_demonstration_only'
    assert k['procurement_knowledge']['assessment_kinds']['purchase_order_reconciliation']=='purchase_order_reconciliation'
    assert any('demo_' in r['id'] for r in k['references'])
    assert q.version['revision']==0  # explicit demo cannot replace the historical default

def test_recurring_demo_assessment_pins_kind_dataset_policy_and_native_query(demo):
    from workflow_api.subway_automation import assessment_schema,validate_assessment_consent,check_assessment,ANNOTATION
    from workflow_api.business_knowledge_model import digest
    from workflow_api.subway_demo_data import POLICY
    _,q=demo;catalog=q.catalog(AUTH,'purchase order');scope=dict(catalog_sha256=digest(catalog),temporal=None,demo_context=q.demo_context)
    schema=assessment_schema(dict(assessment='purchase_order_reconciliation',query_scope=scope));validate_assessment_consent(schema,'Asia/Kolkata')
    workflow=dict(metadata=dict(overview_intent={},action_binding_context=dict(validated_context=dict(demo_context=q.demo_context,subway_query_catalog=catalog))))
    inputs=dict(assessment='purchase_order_reconciliation',query=query(q));check_assessment(schema,inputs,workflow,{},q.real,AUTH)
    inputs['assessment']='invoice_investigation'
    with pytest.raises(ApiFailure):check_assessment(schema,inputs,workflow,{},q.real,AUTH)
    tampered=deepcopy(schema);tampered['properties']['as_of']={'type':'string'}
    with pytest.raises(ApiFailure):validate_assessment_consent(tampered,'Asia/Kolkata')
