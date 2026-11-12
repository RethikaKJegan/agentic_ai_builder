"""Source semantics, exact arithmetic, evidence gaps and isolation; no live effects."""
from copy import deepcopy
import importlib.util
import json
from pathlib import Path
import pytest
from workflow_api.business_knowledge_model import evaluate_rule, digest
from workflow_api.subway_procurement import load, assess, reconcile, status, resolve_identity
from workflow_api.subway_assessments import SubwayAssessments, definition
from workflow_api.service import ApiFailure
from tests.test_subway_full_queries import engine, installed, plan, field, Collection, Cursor, AUTH

spec=importlib.util.spec_from_file_location('subway_scenarios',Path(__file__).parent/'fixtures/subway_procurement_scenarios.py')
scenarios=importlib.util.module_from_spec(spec);spec.loader.exec_module(scenarios)
V=json.loads((Path(__file__).parents[1]/'ontology/subway/business-ontology-v4.json').read_text())
B=load(('client-subway','subway-client'),V)


def result(name='standard',kind='purchase_order_reconciliation',ids=None,**kw):
    entities={'approval_assessment':[501],'invoice_investigation':[801],'goods_receipt_verification':[701],'requisition_assessment':[901]}
    return assess(B,scenarios.generate(name)['evidence'],kind,ids or entities.get(kind,[1001]),scenario=True,**kw)


def outcome(report,key):return next(r['outcome'] for r in report['results'] if r['rule_id']=='subway_rule:'+key)


def test_reproducible_hash_bound_extension_and_real_source_citations():
    from scripts.build_subway_procurement_knowledge import build
    assert build()==B
    assert len(B['identity_definitions'])==10 and len(B['structured_rules'])>=40 and len(B['readiness'])==8
    sources={s['source_id']:s for s in B['sources']}
    for rule in B['structured_rules']:
        for citation in rule['provenance']['evidence']:assert citation['quote'] in sources[citation['source_id']]['text']
        assert rule['handler']=='typed_conditions_v1' and rule['executable_effects'] is False
    assert load(('client-simpsons','simpsons-client'),V) is None
    changed=deepcopy(V);changed['revision']+=1
    with pytest.raises(ApiFailure,match='bind'):load(('client-subway','subway-client'),changed)


def test_source_scoped_identity_ambiguity_missing_and_native_type_handling():
    d=B['identity_definitions'][4]
    l=dict(connection_id='dbconn_subway_finance',collection='purchaseorders',native_type='integer',native_value='1001')
    assert resolve_identity(d,l,[l])['state']=='resolved'
    assert resolve_identity(d,l,[l,deepcopy(l)])['state']=='ambiguous'
    assert resolve_identity(d,l,[dict(l,connection_id='dbconn_subway_central')])['state']=='unresolved'
    assert resolve_identity(d,l,[dict(l,native_type='string')])['state']=='unresolved'


def test_status_values_are_source_specific_and_unknown_is_not_pending():
    assert status(B,'approvals','approval_in_progress')['recognized']
    for raw in ['PENDING','APPROVED','nonsense',None]:assert not status(B,'approvals',raw)['recognized']
    assert status(B,'purchaserequests','Draft')['recognized']
    assert not status(B,'purchaseorders','Draft')['recognized']
    assert all(not m['transitions'] for m in B['state_models'])


def test_previous_reporting_month_and_quarter_keep_timezone_and_boundaries():
    from datetime import datetime
    from workflow_api.temporal_queries import window
    due=datetime.fromisoformat(scenarios.AS_OF).timestamp()
    assert window('previous_month','Asia/Kolkata',due)==('2026-09-30T18:30:00+00:00','2026-10-31T18:30:00+00:00')
    assert window('previous_quarter','Asia/Kolkata',due)==('2026-06-30T18:30:00+00:00','2026-09-30T18:30:00+00:00')
    assert next(t for t in B['temporal_models'] if t['field']=='createdAt')['missing_behavior'].startswith('INSUFFICIENT')


def test_deterministic_rules_preserve_invalid_amount_and_independent_results():
    r=result('invalid_amount');assert outcome(r,'po_amounts')=='FAIL'
    assert outcome(r,'po_supplier')=='PASS'
    assert r['provenance']['official_policy_result'] is False


def test_budget_shortfall_requires_mapping_period_and_currency():
    r=result('budget_overrun','budget_comparison');assert outcome(r,'budget_shortfall')=='FAIL'
    e=scenarios.generate()['evidence'];e['budgets'][0].pop('site')
    r=assess(B,e,'budget_comparison',[1001],scenario=True)
    assert outcome(r,'budget_shortfall')=='INSUFFICIENT_EVIDENCE'
    assert outcome(result('missing_evidence','budget_comparison'),'budget_reservation')=='INSUFFICIENT_EVIDENCE'
    e=scenarios.generate()['evidence'];e['locations']=[]
    assert outcome(assess(B,e,'budget_comparison',[1001],scenario=True),'budget_location')=='INSUFFICIENT_EVIDENCE'
    e=scenarios.generate()['evidence'];e['purchaseorders'][0]['budget']=999
    assert outcome(assess(B,e,'budget_comparison',[1001],scenario=True),'budget_exists')=='FAIL'


def test_receipt_lines_sum_once_without_header_fanout():
    r=result();rec=r['reconciliations'][0]
    assert rec['header_total']==1180 and rec['lines'][0]['received_quantity']=='10'
    assert rec['lines'][0]['result']=='MATCH'
    assert result('partial')['reconciliations'][0]['lines'][0]['result']=='PARTIAL'
    assert result('over_received')['reconciliations'][0]['lines'][0]['result']=='OVER_RECEIVED'
    assert result('duplicate_line')['reconciliations'][0]['issues']==['Missing or duplicate PO line identity']


def test_invoice_discrepancy_currency_and_missing_items_are_distinct():
    r=result(kind='invoice_investigation');assert outcome(r,'invoice_amount')=='PASS'
    assert outcome(r,'invoice_items')=='INSUFFICIENT_EVIDENCE'
    assert outcome(result('duplicate_invoice','invoice_investigation'),'invoice_unique')=='FAIL'
    assert outcome(result('currency_mismatch','invoice_investigation'),'invoice_currency')=='FAIL'
    assert outcome(result('missing_evidence','invoice_investigation'),'invoice_amount')=='INSUFFICIENT_EVIDENCE'


def test_approval_delay_requires_explicit_asof_and_requested_threshold():
    r=result('in_progress','approval_assessment',as_of=scenarios.AS_OF,delay_days=10)
    assert outcome(r,'approval_delay')=='FAIL'
    assert outcome(result('in_progress','approval_assessment'),'approval_delay')=='INSUFFICIENT_EVIDENCE'
    assert outcome(result(kind='approval_assessment',as_of=scenarios.AS_OF,delay_days=10),'approval_delay')=='NOT_APPLICABLE'
    assert outcome(result('inconsistent_history','approval_assessment'),'approval_history')=='FAIL'
    for name in ['rejected','cancelled','reconsider']:
        assert outcome(result(name,'approval_assessment'),'approval_status')=='PASS'  # known state, not a granted decision
        assert outcome(result(name),'po_approval')=='FAIL'


def test_missing_pr_approval_budget_reservations_keep_supported_results():
    r=result('missing_evidence')
    assert outcome(r,'po_requisition')==outcome(r,'po_approval')==outcome(r,'budget_reservation')=='INSUFFICIENT_EVIDENCE'
    assert outcome(r,'po_required')=='PASS'
    assert outcome(r,'stage_parent')=='INSUFFICIENT_EVIDENCE'
    assert 'subway_rule:invoice_items' in r['readiness']['optional_missing_rules']
    assert r['readiness']['outcome']=='PASS'  # optional gaps preserve required receipt checks


@pytest.mark.parametrize('name',scenarios.SCENARIOS)
def test_scenario_generation_is_deterministic_provenance_marked_and_schema_coherent(name):
    s=scenarios.generate(name);assert s==scenarios.generate(name)
    assert s['authoritative'] is False and s['origin']=='modeled_test_fixture'
    e=s['evidence'];po=e['purchaseorders'][0]
    assert type(po['_id']) is int and isinstance(po['items'],list)
    assert e['invoicedatas'][0]['poId']==po['_id']
    assert all(g['purchaseOrderId']==po['_id'] for g in e['grns']) if name!='missing_relationship' else e['grns'][0]['purchaseOrderId']==9999
    assert all(r['scenario'] for r in result(name)['results'])


@pytest.fixture
def assessment_engine(engine,monkeypatch):
    q,rows=engine
    def find(self,query,projection):
        assert query=={} or all(isinstance(v,dict) and set(v)=={'$in'} for v in query.values())
        return Cursor([r for r in self.rows if all(r.get(k) in v['$in'] for k,v in query.items())])
    monkeypatch.setattr(Collection,'find',find)
    e=scenarios.generate('missing_evidence')['evidence']
    rows['subway_finance'].update(deepcopy(e))
    return q,rows


def request(q,kind='purchase_order_validation'):
    labels={'approval_assessment':'finance.approvals','invoice_investigation':'finance.invoicedatas','goods_receipt_verification':'finance.grns'}
    label=labels.get(kind,'finance.purchaseorders');fid=field(q,label,'_id')
    return dict(assessment=kind,query=plan(q,label,fields=[fid],metrics=[],limit=20))


def test_registered_assessment_reads_real_adapter_path_and_persists_receipt(assessment_engine):
    q,rows=assessment_engine;r=SubwayAssessments(q).execute(AUTH,request(q,'purchase_order_reconciliation'))
    assert r['scope']==dict(workspace_id='client-subway',owner_id='subway-client')
    assert r['report']['provenance']['mode']=='source_records'
    assert outcome(r['report'],'po_required')=='PASS'
    assert outcome(r['report'],'budget_currency')=='INSUFFICIENT_EVIDENCE'
    assert all(s['freshness']['status']=='unverified' for s in r['sources'])
    with q.store.transaction(write=False) as db:
        receipt=json.loads(db.execute('SELECT document FROM subway_assessment_receipts').fetchone()[0])
    assert receipt['output_sha256']==digest(r)
    assert all('currency' not in row for row in r['report'].get('invoicedatas',[]))


def test_connector_rejects_cross_tenant_injected_records_and_invalid_grain(assessment_engine):
    q,_=assessment_engine;c=SubwayAssessments(q);inputs=request(q)
    foreign=deepcopy(AUTH);foreign['subject']['workspace_id']='client-simpsons'
    with pytest.raises(ApiFailure):c.execute(foreign,inputs)
    with pytest.raises(ApiFailure):c.execute(AUTH,dict(inputs,scenario='standard'))
    with pytest.raises(ApiFailure):c.execute(AUTH,dict(inputs,records=[]))
    inputs['query']['limit']=21
    with pytest.raises(ApiFailure):c.execute(AUTH,inputs)


def test_knowledge_and_discovery_expose_source_status_and_rules(assessment_engine):
    q,_=assessment_engine;d=q.discovery(AUTH,'Find Subway purchase orders with approvals currently in progress.')
    assert 'approval_in_progress' in d['procurement_knowledge']['status_semantics']['finance.approvals']
    cat,k=q.knowledge(AUTH,'Check purchase orders for missing supplier information, invalid amounts, and supported approval exceptions.')
    assert k['procurement_knowledge']['structured_rules']
    assert k['procurement_knowledge']['sha256']==B['sha256']
    assert any(r.get('procurement_semantics') for r in k['references'] if r['kind']=='concept')
    assert len(json.dumps(d))<200000


def test_native_direct_reference_does_not_join_equal_unrelated_primary_ids():
    d=next(r for r in B['reference_definitions'] if r['source']['collection']=='purchaseorders' and r['target']['collection']=='approvals')
    left=dict(connection_id='dbconn_subway_finance',collection='purchaseorders',native_type='integer',native_value='1001',reference_type='integer',reference_value='501')
    right=dict(connection_id='dbconn_subway_finance',collection='approvals',native_type='integer',native_value='501')
    assert resolve_identity(d,left,[right])['state']=='resolved'
    assert resolve_identity(d,left,[dict(right,native_value='1001')])['state']=='unresolved'
    assert resolve_identity(d,left,[dict(right,connection_id='dbconn_subway_central')])['state']=='unresolved'


def test_received_duplicate_or_rejected_quantities_never_hide_uncertainty():
    e=scenarios.generate()['evidence'];po=e['purchaseorders'][0]
    e['grns'][0]['receivedItems']*=2
    rec=reconcile(po,e['grns'],e['invoicedatas'])
    assert rec['lines'][0]['result']=='INSUFFICIENT_EVIDENCE'
    e=scenarios.generate()['evidence'];e['grns'][1]['status']='rejected'
    rec=reconcile(e['purchaseorders'][0],e['grns'],e['invoicedatas'])
    assert rec['lines'][0]['received_quantity']=='4' and rec['lines'][0]['result']=='PARTIAL'


def test_catalog_registers_assessment_for_subway_only():
    from workflow_api.live_providers import registry_configuration
    env=dict(BUILDER_CLIENT_ID='subway',BUILDER_SUBWAY_DATA_ENABLED='1',BUILDER_SUBWAY_QUERY_ENABLED='1')
    tools=registry_configuration(env)['tools']
    assert any(t['definition']['tool_id']=='subway_assess' for t in tools)
    assert all(t['definition']['tool_id']!='subway_assess' for t in registry_configuration(dict(BUILDER_CLIENT_ID='simpsons'))['tools'])


def test_production_modules_never_import_scenario_generator():
    root=Path(__file__).parents[1]/'workflow_api'
    for p in root.glob('*.py'):assert 'subway_procurement_scenarios' not in p.read_text()


def test_real_snapshot_status_observations_and_data_gaps_are_retained():
    observed=B['source_observations']
    assert observed['writes']==0 and observed['model_calls']==0
    assert observed['collections']['purchaseorders']['field_presence']['purchaseRequestId']==0
    assert observed['collections']['lineitems']['field_presence']['reservedAmount']==0
    assert observed['pr_approval_records']==0
    assert next(s['records'] for s in observed['collections']['approvals']['status_counts'] if s['_id']=='approval_in_progress')==390


def test_quantity_reconciliation_keeps_exact_large_decimal_precision():
    from decimal import Decimal
    e=scenarios.generate()['evidence'];po=e['purchaseorders'][0]
    po['items'][0]['quantity']=Decimal('123456789012345678901234567890')
    e['grns'][0]['receivedItems'][0]['receivedQuantity']=Decimal('123456789012345678901234567889')
    e['grns'][1]['receivedItems'][0]['receivedQuantity']=1
    r=reconcile(po,e['grns'],[])
    assert r['lines'][0]['result']=='MATCH'
    assert r['lines'][0]['received_quantity']=='123456789012345678901234567890'


def test_modeled_cross_source_correspondences_are_explicit_and_coherent():
    e=scenarios.generate('modeled_cross_source_mapping')['evidence']
    store,vendor=e['scenario_correspondences']
    assert store['source_id']==e['central_stores'][0]['_id'] and store['target_id']==e['locations'][0]['_id']
    assert vendor['source_id']==e['central_vendors'][0]['_id'] and vendor['target_id']==e['purchaseorders'][0]['vendorCode']
    assert all(m['authoritative'] is False for m in e['scenario_correspondences'])
    assert 'central store to finance location mapping not verified' in B['unresolved']
