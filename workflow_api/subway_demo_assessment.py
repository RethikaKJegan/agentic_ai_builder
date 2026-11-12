"""Modeled demonstration policy, evaluated by the existing typed-condition engine."""
from copy import deepcopy
from decimal import Decimal
from .business_knowledge_model import evaluate_rule,digest
from .subway_procurement import number,token,instant,record_digest,assess,exact_arithmetic
from .subway_demo_data import POLICY,LABEL,generate

DEMO_FIELDS={label if label.startswith('central.') else label.split('.')[1]:sorted({k for r in rows for k in r}) for label,rows in generate()['records'].items()}
SPECS={
 'invoice_tolerance':('invoicedatas',['within_tolerance'],'Invoice total difference is within the modeled absolute tolerance'),
 'invoice_quantity':('invoicedatas',['quantities_match'],'Invoice PO-line quantities agree with ordered quantities'),
 'invoice_payment':('invoicedatas',['payment_consistent'],'Recorded payments reconcile to invoice payment details without overpayment'),
 'invoice_not_overdue':('invoicedatas',['not_overdue'],'Outstanding modeled invoice is not past its due date at the demo as-of instant'),
 'approval_conditions':('approvals',['approval_granted','required_stages_present'],'Modeled purchase approval status and stage prerequisites'),
 'budget_balance':('lineitems',['balance_consistent'],'Modeled allocation equals available plus reservations plus recorded expenditure'),
 'store_mapping':('purchaseorders',['mapping_verified'],'Explicit modeled central-store to finance-location correspondence'),
 'supplier_mapping':('purchaseorders',['mapping_verified'],'Explicit modeled central-vendor to procurement-code correspondence'),
 'requisition_link':('purchaserequests',['po_reference_consistent'],'Requisition and order references agree in both directions'),
}

def rules():
    return [dict(id='subway_demo_rule:'+rid,label=purpose,entity=entity,business_purpose=purpose,version=1,scope='modeled_demonstration',
        fact_types={f:'boolean' for f in facts},required_facts=facts,conditions=dict(all=[dict(fact=f,operator='equals',value=True) for f in facts]),parameters={},applicability=dict(oems=[],models=[]),
        outcomes=dict(satisfied='PASS',unsatisfied='FAIL',missing='INSUFFICIENT_EVIDENCE'),handler='typed_conditions_v1',executable_effects=False,
        provenance=dict(origin='configured_logic',evidence=[dict(source_id='subway_demo_model_v1',quote=LABEL)]),input_fields=facts,required_evidence=facts,related_concepts=[],missing_evidence_behavior='INSUFFICIENT_EVIDENCE',source_classification='modeled demonstration policy only; not company authority') for rid,(entity,facts,purpose) in SPECS.items()]

@exact_arithmetic
def augment(bundle,evidence,report,inputs,context):
    report=deepcopy(report);catalog={r['id']:r for r in bundle['structured_rules']};get=lambda c:evidence.get(c,[])
    def find(col,id):
        rows=[r for r in get(col) if token(r.get('_id'))==token(id)]
        return rows[0] if len(rows)==1 else None
    def emit(rid,record,col,**facts):
        rule=catalog[rid];r=evaluate_rule(rule,facts);r.update(entity_collection=col,entity_id=record['_id'],record_sha256=record_digest(record),rule_version=1,scenario=True,source_classification='modeled demonstration policy only')
        report['results']=[x for x in report['results'] if (x['rule_id'],x['entity_collection'],x['entity_id'])!=(rid,col,record['_id'])]+[r]
    asof=instant(inputs.get('as_of') or POLICY['as_of']);reconciliations=[]
    for inv in get('invoicedatas'):
        po=find('purchaseorders',inv.get('poId'));pa=number(po.get('totalAmount')) if po else None;ia=number(inv.get('invoiceAmount'));cur=inv.get('currency')
        compatible=po and token(cur)==token(po.get('currency')) and cur is not None
        difference=ia-pa if compatible and ia is not None and pa is not None else None
        emit('subway_demo_rule:invoice_tolerance',inv,'invoicedatas',within_tolerance=None if difference is None else abs(difference)<=Decimal(POLICY['invoice_absolute_tolerance']))
        lines=inv.get('items');polines={token(l['_id']):l for l in po.get('items',[])} if po else {};seen=set();details=[];matches=[]
        for item in lines or []:
            key=token(item.get('poLineId'));ordered=polines.get(key);q=number(item.get('quantity'));expected=number(ordered.get('quantity')) if ordered else None
            valid=None if q is None or expected is None else key not in seen and q==expected and item.get('uom')==ordered.get('uom') and token(item.get('item'))==token(ordered.get('item'))
            matches.append(valid);seen.add(key);details.append(dict(invoice_line_id=item.get('_id'),po_line_id=item.get('poLineId'),invoice_quantity=str(q),ordered_quantity=str(expected),matches=valid))
        emit('subway_demo_rule:invoice_quantity',inv,'invoicedatas',quantities_match=None if not lines or any(m is None for m in matches) else all(matches) and seen==set(polines))
        emit('subway_rule:invoice_items',inv,'invoicedatas',item_evidence_available=True if lines and polines else None)
        emit('subway_rule:invoice_due',inv,'invoicedatas',due_date_available=True if instant(inv.get('dueDate')) else None)
        payments=[p for p in get('payments') if token(p.get('invoiceId'))==token(inv['_id'])];amounts=[number(p.get('amount')) for p in payments]
        paid=sum(amounts,Decimal(0)) if payments and all(a is not None and a>=0 for a in amounts) and all(token(p.get('currency'))==token(cur) for p in payments) else None
        emit('subway_demo_rule:invoice_payment',inv,'invoicedatas',payment_consistent=None if paid is None or ia is None else paid<=ia and paid==number(inv.get('paymentAmount')))
        due=instant(inv.get('dueDate'));outstanding=ia-paid if ia is not None and paid is not None else None
        overdue=None if not due or not asof or outstanding is None else outstanding>0 and due<asof
        emit('subway_demo_rule:invoice_not_overdue',inv,'invoicedatas',not_overdue=None if overdue is None else not overdue)
        reconciliations.append(dict(invoice_id=inv['_id'],po_id=po['_id'] if po else None,currency=cur,invoice_total=str(ia),po_total=str(pa),difference=str(difference) if difference is not None else None,tolerance=POLICY['invoice_absolute_tolerance'],paid=str(paid),outstanding=str(outstanding),due_date=inv.get('dueDate'),overdue=overdue,as_of=inputs.get('as_of') or POLICY['as_of'],items=details))
    for po in get('purchaseorders'):
        ap=find('approvals',po.get('approvalId'));amount=number(po.get('totalAmount'));required=2 if amount is not None and amount>Decimal(POLICY['approval_second_stage_above']) else 1
        if ap:emit('subway_demo_rule:approval_conditions',ap,'approvals',approval_granted=ap.get('status')=='approved',required_stages_present=len([s for s in get('stages') if token(s.get('approvalId'))==token(ap['_id'])])>=required)
        locations=[r for r in get('locations') if token(r['_id'])==token(po.get('site'))];maps=[m for m in get('storemappings') if token(m.get('financeLocationId'))==token(po.get('site')) and token(m.get('centralStoreId'))==token(po.get('storeId'))]
        emit('subway_demo_rule:store_mapping',po,'purchaseorders',mapping_verified=bool(locations and maps and find('central.stores',po.get('storeId'))))
        maps=[m for m in get('suppliermappings') if m.get('vendorCode')==po.get('vendorCode') and token(m.get('centralVendorId'))==token(po.get('vendorId'))]
        supplier_supported=bool(len(maps)==1 and find('central.vendors',po.get('vendorId')))
        emit('subway_demo_rule:supplier_mapping',po,'purchaseorders',mapping_verified=supplier_supported)
        emit('subway_rule:supplier_identity',po,'purchaseorders',identity_resolved=supplier_supported)
        emit('subway_rule:supplier_unique',po,'purchaseorders',reference_unique=len(maps)==1)
        emit('subway_rule:supplier_source',po,'purchaseorders',cross_source_supported=supplier_supported)
    for line in get('lineitems'):
        values=[number(line.get(k)) for k in ('currentAmount','availableAmount','reservedAmount','recordedExpenditure')]
        emit('subway_demo_rule:budget_balance',line,'lineitems',balance_consistent=None if any(v is None for v in values) else values[0]==sum(values[1:],Decimal(0)))
    for pr in get('purchaserequests'):
        children=[p for p in get('purchaseorders') if token(p.get('purchaseRequestId'))==token(pr['_id'])]
        emit('subway_demo_rule:requisition_link',pr,'purchaserequests',po_reference_consistent=bool(children) and {token(p['_id']) for p in children}=={token(v) for v in pr.get('purchaseOrderIds',[])})
        child=assess(bundle,evidence,'requisition_assessment',[pr['_id']],scenario=True)
        keys={(r['rule_id'],r['entity_id']) for r in report['results']};report['results'].extend(r for r in child['results'] if (r['rule_id'],r['entity_id']) not in keys)
    for rec in report.get('reconciliations',[]):
        related=[i for i in reconciliations if token(i['po_id'])==token(rec.get('po_id'))]
        values=[d['matches'] for i in related for d in i['items']]
        rec['invoice_item_comparison']='INSUFFICIENT_EVIDENCE' if not values or any(v is None for v in values) else 'PASS' if all(values) else 'FAIL'
        rec['qualification']='Explicit modeled invoice-to-PO line references and quantities; generated receipt records are not independent proof of delivery.'
    for result in report['results']:result.update(scenario=True,official_policy_result=False)
    report.update(invoice_reconciliation=reconciliations,demo_context=deepcopy(context),modeled_policy=deepcopy(POLICY),limitations=['All records and policies in this assessment are explicitly modeled demonstration evidence.'],provenance=dict(mode='modeled_demonstration',official_policy_result=False,operational_effects=False,label=LABEL))
    # Recompute required and optional evidence gaps after modeled prerequisites
    # have been supplied, retaining actual rule failures as analytical findings.
    outcomes={}
    for r in report['results']:outcomes.setdefault(r['rule_id'],[]).append(r['outcome'])
    ready=report['readiness'];ready['missing_rules']=[r for r in ready['required_rules'] if not outcomes.get(r) or 'INSUFFICIENT_EVIDENCE' in outcomes[r]]
    ready['optional_missing_rules']=[r for r in ready['optional_rules'] if not outcomes.get(r) or 'INSUFFICIENT_EVIDENCE' in outcomes[r]]
    ready['failed_rules']=[r for r in ready['required_rules'] if 'FAIL' in outcomes.get(r,[])]
    ready['outcome']='INSUFFICIENT_EVIDENCE' if ready['missing_rules'] else 'FAIL' if ready['failed_rules'] else 'PASS'
    report['modeled_rule_summary']={s:sum(r['outcome']==s for r in report['results']) for s in ('PASS','FAIL','INSUFFICIENT_EVIDENCE','NOT_APPLICABLE')}
    report['modeled_policy_results']=[dict(rule_id=r['id'],outcomes={s:sum(v['rule_id']==r['id'] and v['outcome']==s for v in report['results']) for s in ('PASS','FAIL','INSUFFICIENT_EVIDENCE','NOT_APPLICABLE')}) for r in rules()]
    return report
