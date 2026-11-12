"""Reproduce the additive, source-cited Subway procurement extension; no source I/O."""
import json, re, sys, zipfile
from pathlib import Path
from hashlib import sha256
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from workflow_api.business_knowledge_model import digest


def build():
    base = json.loads((ROOT/'ontology/subway/business-ontology-v4.json').read_text())
    sources = []
    archive = ROOT/'subway-finance-api-v2-gowtham-finance-v2-pr.zip'
    with zipfile.ZipFile(archive) as z:
        for member in z.namelist():
            if member.endswith(tuple('/'+s for s in ['config/statusEnums.js','models/purchase-order.model.js','models/purchase-request.model.js','models/grn.model.js','models/invoicedata.model.js','models/approval.model.js','models/stage.model.js','models/line-item.model.js','models/budget.model.js'])):
                text=z.read(member).decode()
                sources.append(dict(source_id='subway_procurement_'+Path(member).stem.replace('.','_'),kind='application_code',title=member,text=text,sha256=sha256(text.encode()).hexdigest()))
    def provenance(file, quote=None, origin='application_behavior'):
        s=next(s for s in sources if s['title'].endswith('/'+file))
        return dict(origin=origin,evidence=[dict(source_id=s['source_id'],quote=quote or s['text'][:250])])
    concepts={c['dump_mapping']['collection']:c for c in base['concepts'] if c.get('dump_mapping',{}).get('role')=='finance'}
    identities=[]
    for entity,role,collection,alternatives in [
        ('store','central','stores',['restaurantName']),('finance_location','finance','locations',['code','siteId','storeId']),
        ('supplier','central','vendors',['manufacturerNumber','splCode','name']),('requisition','finance','purchaserequests',['prNumber']),
        ('purchase_order','finance','purchaseorders',['poNumber']),('goods_receipt','finance','grns',['grnNo']),
        ('invoice','finance','invoicedatas',['invoiceNumber','invoiceDocumentNumber']),('budget','finance','budgets',['name']),
        ('approval','finance','approvals',['documentId']),('item','finance','items',['itemCode'])]:
        concept=next((c['id'] for c in base['concepts'] if c.get('dump_mapping',{}).get('role')==role and c['dump_mapping']['collection']==collection),None)
        identities.append(dict(id='subway_identity:'+entity,entity_type=entity,concept_id=concept,source_dataset=role+'.'+collection,
            authoritative_source='native record identity only; company-wide authority not established',primary_identifier='_id',alternative_identifiers=alternatives,
            identifier_scope=['connection_id','collection','native_type','native_value'],kind='source_identity',comparison='source_scoped_native_id',permits_physical_merge=False,
            source=dict(source_role=role,collection=collection,field_path='_id'),target=None,
            valid_relationship_paths=[r['id'] for r in base['relationships'] if r['source']==concept or r['target']==concept],
            ambiguity_behavior='preserve all candidates; never choose the first duplicate',missing_behavior='INSUFFICIENT_EVIDENCE',
            alternative_identifier_behavior='candidate only; numeric overlap and names never establish cross-source identity',
            source_basis='existing dump ontology' if concept else 'code-defined only; no restored dataset binding',
            provenance=dict(origin='source_definition',evidence=[dict(source_id='subway_schema_'+('organization' if entity in ('supplier','finance_location') else 'stores' if entity=='store' else 'procurement' if entity in ('requisition','purchase_order','item') else 'receipts' if entity in ('invoice','goods_receipt') else entity+'s'),quote=collection)])))
    for identity in identities:
        c=next((c for c in base['concepts'] if c['id']==identity['concept_id']),None)
        identity['provenance']=dict(origin='source_definition',evidence=c['evidence']) if c else provenance('purchase-request.model.js')
    meanings={'created':'Created record; submission not established','draft':'Draft record','approval_in_progress':'Approval currently in progress; not a granted decision','approved':'Recorded approval state; not proof of delivery or payment','rejected':'Rejected in this approval cycle','reconsider':'Returned for reconsideration','reconsider_by_user':'Reconsideration requested by user','cancelled':'Cancelled record','short_close':'PO contract short closed; not necessarily fully received','hold':'On hold','inactive':'Inactive','not_initiated':'Not initiated','created_by_vendor':'Created by vendor','converted':'PR converted to PO','partially_rejected':'Some child PRs rejected','replaced':'Approval cycle superseded'}
    observed=json.loads((ROOT/'ontology/subway/procurement-source-observations-v1.json').read_text())
    state_models=[]
    for collection,file in [('purchaseorders','purchase-order.model.js'),('purchaserequests','purchase-request.model.js'),('approvals','approval.model.js'),('stages','stage.model.js'),('grns','grn.model.js'),('invoicedatas','invoicedata.model.js'),('budgets','budget.model.js'),('lineitems','line-item.model.js')]:
        state_models.append(dict(id='subway_state:'+collection,concept_id=concepts.get(collection,{}).get('id'),collection='finance.'+collection,field='status',
            values=[dict(raw=k,meaning=v,terminal=(k in ['rejected','cancelled','replaced','short_close','converted']) if collection in ('approvals','stages','purchaseorders','purchaserequests') else None) for k,v in meanings.items()]+([dict(raw='Draft',meaning='PR reverted to draft by edit',terminal=False)] if collection=='purchaserequests' else []),
            observed_status_counts=observed['collections'].get(collection,{}).get('status_counts',[]),
            transitions=[],unknown_behavior='unknown',provenance=provenance(file),vocabulary_provenance=provenance('statusEnums.js'),
            qualification='Shared enum declares possible vocabulary, not observed use or verified transitions for every entity. Approved is not a universal closed/completed state.'))
    temporal=[]
    for col,field,meaning,file in [
        ('purchaseorders','createdAt','PO creation instant','purchase-order.model.js'),('purchaseorders','poDate','Recorded order date','purchase-order.model.js'),
        ('purchaserequests','prDate','Requisition date','purchase-request.model.js'),('approvals','createdAt','Approval-cycle creation instant','approval.model.js'),
        ('stages','createdAt','Stage creation instant, not last action','stage.model.js'),('stages','stageDate','Stage action date; not approval completion date','stage.model.js'),
        ('invoicedatas','invoiceDate','Recorded invoice date','invoicedata.model.js'),('invoicedatas','dateOfPayment','Recorded payment date','invoicedata.model.js'),
        ('grns','inwardDate','Recorded receipt inward date','grn.model.js'),('budgets','financialYear','Source reporting label; boundaries not established','budget.model.js'),
        ('lineitems','financialYear','Source reporting label; boundaries not established','line-item.model.js')]:
        temporal.append(dict(id='subway_time:'+col+'_'+field.lower(),collection='finance.'+col,concept_id=concepts.get(col,{}).get('id'),field=field,meaning=meaning,
            precision='reporting_label' if field=='financialYear' else 'instant',filter_semantics='explicit label only; no inferred fiscal boundaries' if field=='financialYear' else 'half-open [start,end); existing temporal_queries.window using configured IANA reporting timezone',
            timezone_behavior='preserve offset; BSON dates are UTC; naive text timestamps remain unverified',missing_behavior='INSUFFICIENT_EVIDENCE; no fallback date',provenance=provenance(file)))
    rules=[]
    def rule(key,entity,purpose,facts,file,mode='source_integrity',applicable=True):
        # Boolean facts are deterministically derived from cited source fields by the registered tool.
        r=dict(id='subway_rule:'+key,label=purpose,entity=entity,business_purpose=purpose,version=1,scope=mode,
            fact_types={f:'boolean' for f in facts},required_facts=facts,conditions={'all':[dict(fact=f,operator='equals',value=True) for f in facts]},parameters={},
            applicability=dict(oems=[],models=[]),outcomes=dict(satisfied='PASS',unsatisfied='FAIL',missing='INSUFFICIENT_EVIDENCE'),handler='typed_conditions_v1',executable_effects=False,
            provenance=provenance(file,origin='configured_logic'),source_classification='source-backed structural check; analytical result, not official company policy',
            input_fields=facts,required_evidence=facts,related_concepts=[concepts[entity]['id']] if entity in concepts else [],missing_evidence_behavior='INSUFFICIENT_EVIDENCE; preserve other rule results')
        rules.append(r)
    groups={
      'purchaseorders':('purchase-order.model.js',{'po_required':['header_complete'],'po_supplier':['supplier_present'],'po_amounts':['amounts_valid'],'po_items':['items_valid'],'po_currency':['currency_present'],'po_unique':['reference_unique'],'po_approval':['approval_supported'],'po_requisition':['requisition_linked']}),
      'purchaserequests':('purchase-request.model.js',{'pr_required':['header_complete'],'pr_requester':['requester_present'],'pr_items':['items_valid'],'pr_approval':['approval_supported'],'pr_conversion':['conversion_ready']}),
      'invoicedatas':('invoicedata.model.js',{'invoice_required':['header_complete'],'invoice_unique':['reference_unique'],'invoice_supplier':['supplier_consistent'],'invoice_po':['po_linked'],'invoice_amount':['amount_comparable','amount_matches'],'invoice_currency':['currency_compatible'],'invoice_receipt':['receipt_linked'],'invoice_approval':['approval_supported'],'invoice_items':['item_evidence_available'],'invoice_due':['due_date_available']}),
      'lineitems':('line-item.model.js',{'budget_exists':['budget_linked'],'budget_location':['location_verified'],'budget_period':['period_verified'],'budget_currency':['currency_compatible'],'budget_available':['available_valid'],'budget_reservation':['reservation_present'],'budget_shortfall':['within_available'],'budget_spend':['expenditure_available']}),
      'approvals':('approval.model.js',{'approval_status':['status_supported'],'approval_stages':['stages_available'],'approval_history':['history_consistent'],'approval_delay':['within_requested_delay']}),
      'stages':('stage.model.js',{'stage_parent':['parent_available']}),
      'grns':('grn.model.js',{'receipt_required':['header_complete'],'receipt_po':['po_linked'],'receipt_items':['items_valid'],'receipt_unique_lines':['lines_unique'],'receipt_quantity':['quantity_within_order']}),
      'vendors':('purchase-order.model.js',{'supplier_identity':['identity_resolved'],'supplier_unique':['reference_unique'],'supplier_source':['cross_source_supported']})}
    for entity,(file,checks) in groups.items():
        for key,facts in checks.items():rule(key,entity,key.replace('_',' ').capitalize(),facts,file)
    readiness=[]
    for name,required,optional in [
      ('requisition_assessment',['pr_required','pr_requester','pr_items'],['pr_approval']),('purchase_order_validation',['po_required','po_amounts','po_items'],['po_supplier','po_approval','po_requisition']),
      ('budget_comparison',['budget_exists','budget_location','budget_period','budget_currency','budget_available'],['budget_reservation','budget_spend']),
      ('approval_assessment',['approval_status','approval_stages'],['approval_delay','approval_history']),
      ('invoice_investigation',['invoice_po','invoice_currency','invoice_amount'],['invoice_receipt','invoice_items','invoice_approval']),
      ('goods_receipt_verification',['receipt_po','receipt_items','receipt_unique_lines'],['receipt_quantity']),
      ('purchase_order_reconciliation',['po_items','receipt_po','receipt_items'],['invoice_items','invoice_amount']),
      ('supplier_spending',['po_supplier','po_currency'],['supplier_identity','supplier_source'])]:
        readiness.append(dict(id='subway_readiness:'+name,required_rules=['subway_rule:'+r for r in required],optional_rules=['subway_rule:'+r for r in optional],missing_behavior='retrieve authorized recoverable evidence; retain supported independent findings',official_policy_result=False))
    bundle=dict(schema_version='subway-procurement-knowledge-v1',extension_version='subway-procurement-v1',revision=1,
        scope=dict(workspace_id='client-subway',subject_id='subway-client'),ontology_version=base['version_id'],definition_sha256=digest(base),
        source_archive_sha256=sha256(archive.read_bytes()).hexdigest(),sources=sources,identity_definitions=identities,state_models=state_models,temporal_models=temporal,
        structured_rules=rules,readiness=readiness,relationships=[dict(r,authority='source-defined mapping' if 'dump_ref_' in r['id'] else 'bounded candidate observation; do not infer identity') for r in base['relationships']],
        source_observations=observed,
        reference_definitions=[dict(id='subway_reference:'+str(n),kind='direct_reference',source=dict(source_role=next(c['dump_mapping']['role'] for c in base['concepts'] if c['id']==r['source']),collection=next(c['dump_mapping']['collection'] for c in base['concepts'] if c['id']==r['source']),field_path=r['source_field']),target=dict(source_role=next(c['dump_mapping']['role'] for c in base['concepts'] if c['id']==r['target']),collection=next(c['dump_mapping']['collection'] for c in base['concepts'] if c['id']==r['target']),field_path='_id'),comparison='native_type_and_value',permits_physical_merge=False,provenance=dict(origin='source_definition',evidence=r['evidence']),relationship_id=r['id']) for n,r in enumerate(base['relationships']) if 'dump_ref_' in r['id'] and '[]' not in r['source_field'] and next(c['dump_mapping']['role'] for c in base['concepts'] if c['id']==r['source'])==next(c['dump_mapping']['role'] for c in base['concepts'] if c['id']==r['target'])],
        unresolved=['central store to finance location mapping not verified','PO vendorCode to central vendor identity not verified','restored requisition dataset unavailable','invoice currency and item quantities not established','invoice due date not established','approval completion timestamp not established','fiscal-calendar boundaries not established','historical snapshot has no current synchronization'],
        scenario_policy=dict(mode='test_only',authority='modeled_scenario_only',production_record_injection=False))
    bundle['sha256']=digest(bundle)
    return bundle

if __name__=='__main__':
    target=ROOT/'ontology/subway/procurement-knowledge-v1.json'
    target.write_text(json.dumps(build(),indent=2,ensure_ascii=False)+'\n')
    print(target)
