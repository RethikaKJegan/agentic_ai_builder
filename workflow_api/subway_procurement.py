"""Pure Subway procurement semantics using the existing typed-condition engine.

No model calls, connectors, writes, inferred corporate policy or generated records.
The Registry adapter supplies authorized evidence; tests may supply isolated scenarios.
"""
from copy import deepcopy
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation, localcontext
from functools import wraps
import json
from pathlib import Path

from .business_knowledge_model import digest, evaluate_rule, associate
from .service import ApiFailure

ARTIFACT = Path(__file__).resolve().parents[1]/'ontology/subway/procurement-knowledge-v1.json'
SCOPE = ('client-subway','subway-client')


def load(scope, snapshot):
    if tuple(scope) != SCOPE or snapshot.get('version_id') != 'bov_subway_dump_v4':
        return None
    bundle=json.loads(ARTIFACT.read_text()); stamp=bundle.pop('sha256')
    if digest(bundle)!=stamp or bundle['scope']!=dict(workspace_id=SCOPE[0],subject_id=SCOPE[1]):
        raise ApiFailure('SUBWAY_KNOWLEDGE_INTEGRITY','Subway knowledge integrity check failed.',409)
    if bundle['definition_sha256']!=digest(snapshot):
        raise ApiFailure('SUBWAY_KNOWLEDGE_STALE','Procurement definitions do not bind this ontology.',409)
    for source in bundle['sources']:
        if __import__('hashlib').sha256(source['text'].encode()).hexdigest()!=source['sha256']:
            raise ApiFailure('SUBWAY_KNOWLEDGE_INTEGRITY','Procurement source citation changed.',409)
    from jsonschema import Draft202012Validator
    from .business_knowledge_model import RULE
    for rule in bundle['structured_rules']:
        Draft202012Validator(RULE).validate({k:rule[k] for k in RULE['properties']})
    ids={r['id'] for r in bundle['structured_rules']}
    if len(ids)!=len(bundle['structured_rules']) or any(set(d['required_rules']+d['optional_rules'])-ids for d in bundle['readiness']):
        raise ApiFailure('SUBWAY_KNOWLEDGE_INTEGRITY','Invalid procurement rule dependencies.',409)
    bundle['sha256']=stamp
    return bundle


def context(bundle, labels=None):
    """Bounded relevant semantics, never the complete code corpus in a model prompt."""
    include_all=labels is None
    labels=set(labels or [])
    def relevant(item):
        return include_all or item.get('collection',item.get('source_dataset','')) in labels or 'finance.'+item.get('entity','') in labels
    return dict(extension_version=bundle['extension_version'],sha256=bundle['sha256'],ontology_version=bundle['ontology_version'],
        identity_definitions=[deepcopy(x) for x in bundle['identity_definitions'] if relevant(x)],
        state_models=[deepcopy(x) for x in bundle['state_models'] if relevant(x)],temporal_models=[deepcopy(x) for x in bundle['temporal_models'] if relevant(x)],
        structured_rules=[{k:deepcopy(v) for k,v in x.items() if k!='provenance'} for x in bundle['structured_rules'] if relevant(x)],
        assessment_kinds={r['id'].split(':',1)[1]:r['id'].split(':',1)[1] for r in bundle['readiness']},
        readiness=deepcopy(bundle['readiness']),unresolved=deepcopy(bundle['unresolved']),
        execution='For tool.subway_assess bind assessment from context business_knowledge path [procurement_knowledge, assessment_kinds, chosen assessment name]. Use subway.plan_query to generate an ID-only detail query without joins/metrics, limit <=20; bind output path [query] to the assessment query. Use tool.subway_assess for deterministic checks and bounded receipt-line reconciliation; use subway.plan_query and tool.subway_query for ordinary data queries. Assessment findings are analytical, never business approvals. Missing evidence is not a granted decision. Model text must not replace deterministic checks.')


def resolve_identity(definition, left, candidates):
    """Reuse native identity diagnostics, adding explicit cardinality handling."""
    source=definition['source']
    if left.get('collection')!=source['collection'] or left.get('connection_id')!='dbconn_subway_'+source['source_role']:
        return dict(state='unresolved',matches=[],merge_permitted=False)
    matches=[]
    for right in candidates:
        result=associate(definition,left,right)
        if result['association'] in ('identical_source_record','direct_reference'):matches.append(right)
    return dict(state='resolved' if len(matches)==1 else 'ambiguous' if matches else 'unresolved',matches=matches,merge_permitted=False)


def record_digest(value):
    return digest(json.loads(json.dumps(value,default=lambda v: {"native_type":type(v).__name__,"value":str(v)},sort_keys=True)))


def number(value):
    if isinstance(value,bool) or value is None:return None
    if hasattr(value,'to_decimal'):value=value.to_decimal()
    if not isinstance(value,(int,float,Decimal)):return None
    try:
        d=Decimal(str(value))
        return d if d.is_finite() and len(d.as_tuple().digits)<=30 else None
    except (InvalidOperation,ValueError):return None


def token(value):
    # Type-preserving identity; string "12" is never native integer 12.
    if value is None or isinstance(value,(dict,list,bool)):return None
    return (type(value).__name__,str(value))


def present(value):return value is not None and (not isinstance(value,str) or bool(value.strip()))


def unique(rows, field, value):
    if not present(value):return None
    return sum(token(r.get(field))==token(value) for r in rows)==1


def linked(rows, field, value):
    if token(value) is None:return None
    matches=[r for r in rows if token(r.get(field))==token(value)]
    return matches[0] if len(matches)==1 else None


def instant(value):
    if isinstance(value,datetime):return value if value.tzinfo else None
    if isinstance(value,str):
        try:
            v=datetime.fromisoformat(value.replace('Z','+00:00'))
            return v if v.tzinfo else None
        except ValueError:pass
    return None


def status(bundle, collection, raw):
    model=next((s for s in bundle['state_models'] if s['collection']=='finance.'+collection),None)
    value=next((s for s in model['values'] if s['raw']==raw),None) if model else None
    return dict(raw=raw,meaning=value['meaning'] if value else None,recognized=value is not None,transition='unverified')


def exact_arithmetic(function):
    @wraps(function)
    def run(*args,**kwargs):
        with localcontext() as ctx:
            ctx.prec=38
            return function(*args,**kwargs)
    return run


@exact_arithmetic
def reconcile(po, receipts, invoices):
    """PO line _id → GRN poItemId. Header amounts never enter line fanout."""
    lines=po.get('items'); output=[]; issues=[]
    if not isinstance(lines,list) or not lines:return dict(lines=[],issues=['PO item evidence unavailable'],header_total=po.get('totalAmount'),invoice_item_comparison='INSUFFICIENT_EVIDENCE')
    index={}
    for line in lines:
        key=token(line.get('_id'))
        if key is None or key in index:issues.append('Missing or duplicate PO line identity');continue
        index[key]=line
    if len(index)!=len(lines):return dict(lines=[],issues=issues,header_total=po.get('totalAmount'),invoice_item_comparison='INSUFFICIENT_EVIDENCE')
    quantities={k:Decimal(0) for k in index};seen=set();usable=set();unknown=set()
    for receipt in receipts:
        if token(receipt.get('purchaseOrderId'))!=token(po.get('_id')):continue
        # Source services book quantities only on submission; rejected/reconsidered
        # receipts reverse them. Report these as excluded observations, not delivery.
        if receipt.get('status') not in ('approved','approval_in_progress'):
            issues.append('Receipt '+str(receipt.get('_id'))+' excluded from booked quantities: '+str(receipt.get('status')));continue
        rows=receipt.get('receivedItems')
        if not isinstance(rows,list) or not rows:issues.append('Receipt item evidence unavailable');unknown.update(index);continue
        for row in rows:
            key=token(row.get('poItemId'));rid=(token(receipt.get('_id')),key)
            if key not in index:issues.append('Unmatched receipt PO line reference');unknown.update(index);continue
            if rid in seen:issues.append('Duplicate receipt line reference');unknown.add(key);continue
            seen.add(rid);qty=number(row.get('receivedQuantity'))
            if qty is None or qty<0:issues.append('Invalid received quantity');unknown.add(key);continue
            quantities[key]+=qty;usable.add(key)
    for key,line in index.items():
        ordered=number(line.get('quantity')); received=quantities[key] if key in usable and key not in unknown else None
        state='INSUFFICIENT_EVIDENCE' if ordered is None or ordered<0 or received is None else 'OVER_RECEIVED' if received>ordered else 'PARTIAL' if received<ordered else 'MATCH'
        output.append(dict(po_line_id=line['_id'],item_id=line.get('item'),uom=line.get('uom'),ordered_quantity=str(ordered) if ordered is not None else None,
            received_quantity=str(received) if received is not None else None,result=state))
    return dict(lines=output,issues=issues,header_total=po.get('totalAmount'),header_grain='one source PO header, never summed across lines/receipts',invoice_item_comparison='INSUFFICIENT_EVIDENCE',
        invoice_count=len(invoices),qualification='Booked source quantities, not independent proof of physical delivery. Invoice schema has no verified comparable item quantities.')


@exact_arithmetic
def assess(bundle, evidence, assessment, entity_ids, *, as_of=None, delay_days=None, scenario=False):
    """Evaluate a coherent bounded evidence set; facts retain source-record hashes."""
    entities={'purchase_order_validation':'purchaseorders','purchase_order_reconciliation':'purchaseorders','budget_comparison':'purchaseorders','supplier_spending':'purchaseorders',
        'approval_assessment':'approvals','invoice_investigation':'invoicedatas','goods_receipt_verification':'grns','requisition_assessment':'purchaserequests'}
    if assessment not in entities:raise ValueError('Unknown assessment')
    base=entities[assessment];rules={r['id'].split(':',1)[1]:r for r in bundle['structured_rules']};results=[]
    get=lambda col:evidence.get(col,[])
    def lookup(col,value):return linked(get(col),'_id',value)
    def check(rule_id,facts,record,col,applies=True):
        r=rules[rule_id]
        result=evaluate_rule(r,{k:facts.get(k) for k in r['fact_types']})
        if not applies:result.update(state='not_applicable',outcome='NOT_APPLICABLE',missing_facts=[])
        result.update(entity_collection=col,entity_id=record.get('_id'),record_sha256=record_digest(record),rule_version=r['version'],
            source_classification=r['source_classification'],scenario=scenario)
        results.append(result)
    selected=[r for r in get(base) if token(r.get('_id')) in {token(v) for v in entity_ids}]
    reconciliations=[];states=[];temporal=[];comparisons=[]
    for record in selected:
        col=base;po=record if base=='purchaseorders' else lookup('purchaseorders',record.get('poId') if base=='invoicedatas' else record.get('purchaseOrderId'))
        if po:
            approval=lookup('approvals',po.get('approvalId'))
            items=po.get('items')
            iv=None if not isinstance(items,list) or not items else all(present(i.get('_id')) and present(i.get('item')) and number(i.get('quantity')) is not None and number(i['quantity'])>0 for i in items)
            amount,total=number(po.get('amount')),number(po.get('totalAmount'))
            # Separate source measures; no tax/extra-charge equation is assumed.
            checks={'po_required':dict(header_complete=all(present(po.get(f)) for f in ['_id','poNumber','poDate'])),
                'po_supplier':dict(supplier_present=present(po.get('vendorCode')) and present(po.get('vendorName'))),
                'po_amounts':dict(amounts_valid=None if po.get('amount') is None or po.get('totalAmount') is None else amount is not None and total is not None and amount>=0 and total>=0),
                'po_items':dict(items_valid=iv),'po_currency':dict(currency_present=present(po.get('currency'))),
                'po_unique':dict(reference_unique=unique(get('purchaseorders'),'poNumber',po.get('poNumber'))),
                'po_approval':dict(approval_supported=None if approval is None else approval.get('status')=='approved'),
                'po_requisition':dict(requisition_linked=True if lookup('purchaserequests',po.get('purchaseRequestId')) else None)}
            for rid,facts in checks.items():check(rid,facts,po,'purchaseorders')
            for rid,facts in {'supplier_identity':dict(identity_resolved=None),'supplier_unique':dict(reference_unique=None),
                    'supplier_source':dict(cross_source_supported=None)}.items():check(rid,facts,po,'purchaseorders')
            receipts=[r for r in get('grns') if token(r.get('purchaseOrderId'))==token(po.get('_id'))]
            invoices=[r for r in get('invoicedatas') if token(r.get('poId'))==token(po.get('_id'))]
            rec=reconcile(po,receipts,invoices);rec['po_id']=po['_id'];reconciliations.append(rec)
            # Per-line allocation, never compare the entire PO to every budget line.
            allocations={}
            for line in items or []:
                key=token(line.get('lineItem'));a=number(line.get('totalAmount'))
                allocations.setdefault(key,[]).append((line,a))
            for key,group in allocations.items():
                line=group[0][0];budgetline=lookup('lineitems',line.get('lineItem'));budget=lookup('budgets',budgetline.get('budgetId')) if budgetline else None
                available=number(budgetline.get('availableAmount')) if budgetline else None
                cost=sum((a for _,a in group),Decimal(0)) if all(a is not None and a>=0 for _,a in group) else None
                samecurrency=None if not budgetline or not present(budgetline.get('currency')) or not present(po.get('currency')) else token(budgetline['currency'])==token(po['currency'])
                sameperiod=None if not budgetline or not present(budgetline.get('financialYear')) or not present(po.get('financialYear')) else budgetline['financialYear']==po['financialYear']
                location=None if not budget or not present(budget.get('site')) or not present(po.get('site')) or not lookup('locations',po.get('site')) else token(budget['site'])==token(po['site'])
                header_budget=None if not budget or not present(po.get('budget')) else token(po['budget'])==token(budget['_id'])
                facts={'budget_exists':dict(budget_linked=header_budget),'budget_location':dict(location_verified=location),
                    'budget_period':dict(period_verified=sameperiod),'budget_currency':dict(currency_compatible=samecurrency),
                    'budget_available':dict(available_valid=None if available is None else available>=0),
                    'budget_reservation':dict(reservation_present=True if budgetline and number(budgetline.get('reservedAmount')) is not None else None),
                    'budget_shortfall':dict(within_available=None if cost is None or available is None or samecurrency is not True or sameperiod is not True or location is not True or header_budget is not True else cost<=available),
                    'budget_spend':dict(expenditure_available=True if budget and number(budget.get('utilizedAmount')) is not None else None)}
                for rid,f in facts.items():check(rid,f,budgetline or {'_id':line.get('lineItem')},'lineitems')
                comparisons.append(dict(kind='po_line_allocation_vs_available_snapshot',po_id=po['_id'],line_item_id=line.get('lineItem'),
                    allocated_po_amount=str(cost) if cost is not None else None,available_amount=str(available) if available is not None else None,
                    headroom=str(available-cost) if cost is not None and available is not None and samecurrency is True and sameperiod is True and location is True and header_budget is True else None,
                    qualification='Snapshot comparison only; no historical balance, inferred reservations or official approval decision.'))
            if not allocations:
                for rid in [r for r in rules if r.startswith('budget_')]:check(rid,{},po,'purchaseorders')
            if base=='purchaseorders' and not lookup('approvals',po.get('approvalId')):
                for stage in get('stages'):
                    if token(stage.get('approvalId'))==token(po.get('approvalId')):
                        check('stage_parent',dict(parent_available=None),stage,'stages')
        if base=='invoicedatas':
            inv=record
            observed=instant(inv.get('invoiceDate'));observed_now=instant(as_of)
            temporal.append(dict(collection='invoicedatas',id=inv['_id'],age_days=None if not observed or not observed_now or observed_now<observed else (observed_now-observed).total_seconds()/86400,
                basis='invoiceDate to explicit as_of; overdue cannot be established without a due date'))
            currency=inv.get('currency');ic=number(inv.get('invoiceAmount'));pc=number(po.get('totalAmount')) if po else None
            compatible=None if not po or not present(currency) or not present(po.get('currency')) else token(currency)==token(po['currency'])
            # A single invoice need not cover the full PO. Header equality is only
            # comparable when explicit full-order scope evidence was supplied.
            comparable=True if po and compatible and inv.get('coversFullOrder') is True else None
            comparisons.append(dict(kind='invoice_vs_full_order',invoice_id=inv['_id'],po_id=po['_id'] if po else None,
                difference=str(ic-pc) if comparable is True and ic is not None and pc is not None else None,
                percentage_difference=str((ic-pc)/pc*100) if comparable is True and ic is not None and pc is not None and pc!=0 else None,
                qualification='Exact analytical difference only when currency and full-order scope are established; no tolerance or overbilling inference.'))
            approval=lookup('approvals',inv.get('approvalId'))
            receipt=lookup('grns',inv.get('grnId'))
            receipt_link=True if receipt and po and token(receipt.get('purchaseOrderId'))==token(po.get('_id')) else False if receipt and po else None
            supplier=None if not po or not present(inv.get('vendorCode')) or not present(po.get('vendorCode')) else inv['vendorCode']==po['vendorCode']
            invoice_key=(inv.get('invoiceNumber'),inv.get('vendorCode'),inv.get('financialYear'))
            unique_invoice=None if not all(present(x) for x in invoice_key) else sum(tuple(i.get(f) for f in ['invoiceNumber','vendorCode','financialYear'])==invoice_key for i in get('invoicedatas'))==1
            for rid,f in {'invoice_required':dict(header_complete=all(present(inv.get(f)) for f in ['_id','invoiceNumber','invoiceDate','invoiceAmount'])),
                'invoice_unique':dict(reference_unique=unique_invoice),'invoice_supplier':dict(supplier_consistent=supplier),'invoice_po':dict(po_linked=True if po else None),
                'invoice_amount':dict(amount_comparable=comparable,amount_matches=None if comparable is not True or ic is None or pc is None else ic==pc),
                'invoice_currency':dict(currency_compatible=compatible),'invoice_receipt':dict(receipt_linked=receipt_link),
                'invoice_approval':dict(approval_supported=None if not approval else approval.get('status')=='approved'),
                'invoice_items':dict(item_evidence_available=None),'invoice_due':dict(due_date_available=None)}.items():check(rid,f,inv,col)
        if base=='grns':
            grn=record;items=grn.get('receivedItems');valid=None if not items else all(present(i.get('poItemId')) and number(i.get('receivedQuantity')) is not None and number(i['receivedQuantity'])>=0 for i in items)
            rec=reconciliations[-1] if po else None
            for rid,f in {'receipt_required':dict(header_complete=all(present(grn.get(f)) for f in ['_id','grnNo','purchaseOrderId','inwardDate','invoiceNumber'])),
                'receipt_po':dict(po_linked=True if po else None),'receipt_items':dict(items_valid=valid),
                'receipt_unique_lines':dict(lines_unique=None if not items else len({token(i.get('poItemId')) for i in items})==len(items)),
                'receipt_quantity':dict(quantity_within_order=None if not rec or any(l['result']=='INSUFFICIENT_EVIDENCE' for l in rec['lines']) else all(l['result']!='OVER_RECEIVED' for l in rec['lines']))}.items():check(rid,f,grn,col)
        if base=='approvals' or po:
            ap=record if base=='approvals' else lookup('approvals',po.get('approvalId'))
            if ap:
                stages=[s for s in get('stages') if token(s.get('approvalId'))==token(ap['_id'])]
                declared=ap.get('stages'); complete=bool(stages) and isinstance(declared,list) and len(declared)==len(stages) and {token(x) for x in declared}=={token(s['_id']) for s in stages}
                coherent=None
                if type(ap.get('approved')) is bool:
                    coherent=(ap['approved']==(ap.get('status')=='approved'))
                current=[s for s in stages if s.get('StageNumber')==ap.get('currentStageNumber') and ap.get('currentStageNumber') is not None]
                if len(current)==1 and ap.get('status')=='approved' and current[0].get('status')!='approved':coherent=False
                start=instant(ap.get('createdAt'));now=instant(as_of)
                duration=None if not start or not now or now<start else Decimal(str((now-start).total_seconds()/86400))
                for rid,f in {'approval_status':dict(status_supported=None if ap.get('status') is None else status(bundle,'approvals',ap['status'])['recognized']),'approval_stages':dict(stages_available=True if complete else None),
                    'approval_history':dict(history_consistent=coherent),'approval_delay':dict(within_requested_delay=None if duration is None or delay_days is None else duration<=Decimal(str(delay_days)))}.items():
                    check(rid,f,ap,'approvals',applies=rid!='approval_delay' or ap.get('status')=='approval_in_progress')
                temporal.append(dict(collection='approvals',id=ap['_id'],age_days=str(duration) if duration is not None else None,basis='createdAt to explicit as_of; not stage waiting duration',threshold_days=delay_days))
                for s in stages:
                    check('stage_parent',dict(parent_available=True),s,'stages')
                    created=instant(s.get('createdAt'))
                    age=None if not now or not created or now<created else (now-created).total_seconds()/86400
                    temporal.append(dict(collection='stages',id=s['_id'],age_days=age if s.get('status')=='approval_in_progress' else None,
                        basis='stage createdAt to explicit as_of; stageDate is an action date, never a waiting start'))
        if base=='purchaserequests':
            pr=record;items=pr.get('items');ap=lookup('approvals',pr.get('approvalId'))
            for rid,f in {'pr_required':dict(header_complete=all(present(pr.get(f)) for f in ['_id','prNumber','prDate','site'])),
                'pr_requester':dict(requester_present=present(pr.get('createdBy'))),'pr_items':dict(items_valid=None if not items else all(number(i.get('quantity')) is not None and number(i['quantity'])>0 and present(i.get('item')) for i in items)),
                'pr_approval':dict(approval_supported=None if not ap else ap.get('status')=='approved'),
                'pr_conversion':dict(conversion_ready=None if not ap or type(pr.get('isParentPR')) is not bool or type(pr.get('legacyAllocationUnresolved')) is not bool else ap.get('status')=='approved' and pr['isParentPR'] is False and pr['legacyAllocationUnresolved'] is False)}.items():check(rid,f,pr,col)
        states.append(dict(collection=base,id=record['_id'],**status(bundle,base,record.get('status'))))
    if base=='purchaseorders' and assessment=='purchase_order_reconciliation':
        pids={token(r['_id']) for r in selected}
        for child_assessment,col,reference in [('goods_receipt_verification','grns','purchaseOrderId'),('invoice_investigation','invoicedatas','poId')]:
            children=[r['_id'] for r in get(col) if token(r.get(reference)) in pids]
            if children:
                child=assess(bundle,evidence,child_assessment,children,as_of=as_of,delay_days=delay_days,scenario=scenario)
                keys={(r['rule_id'],r['entity_collection'],token(r['entity_id'])) for r in results}
                results.extend(r for r in child['results'] if (r['rule_id'],r['entity_collection'],token(r['entity_id'])) not in keys)
    spending={}
    for po in selected if base=='purchaseorders' else []:
        code=po.get('vendorCode');currency=po.get('currency');amount=number(po.get('totalAmount'))
        if present(code) and present(currency) and amount is not None:
            k=(token(code),token(currency));g=spending.setdefault(k,dict(vendor_code=code,currency=currency,total=Decimal(0),po_count=0))
            g['total']+=amount;g['po_count']+=1
    supplier_spending=[dict(vendor_code=g['vendor_code'],currency=g['currency'],recorded_po_value=str(g['total']),po_count=g['po_count'],
        scope='selected PO page only; raw vendor code is not a verified central supplier identity') for g in spending.values()]
    evaluated={r['rule_id']:[] for r in results}
    for r in results:evaluated[r['rule_id']].append(r['outcome'])
    definition=next(d for d in bundle['readiness'] if d['id']=='subway_readiness:'+assessment)
    missing=[rid for rid in definition['required_rules'] if rid not in evaluated or 'INSUFFICIENT_EVIDENCE' in evaluated[rid]]
    failed=[rid for rid in definition['required_rules'] if 'FAIL' in evaluated.get(rid,[])]
    return dict(assessment=assessment,knowledge_version=bundle['extension_version'],knowledge_sha256=bundle['sha256'],
        results=results,reconciliations=reconciliations,states=states,temporal=temporal,comparisons=comparisons,supplier_spending=supplier_spending,
        readiness=dict(optional_missing_rules=[rid for rid in definition['optional_rules'] if rid not in evaluated or 'INSUFFICIENT_EVIDENCE' in evaluated[rid]],outcome='INSUFFICIENT_EVIDENCE' if missing else 'FAIL' if failed else 'PASS',missing_rules=missing,failed_rules=failed,required_rules=definition['required_rules'],optional_rules=definition['optional_rules']),
        provenance=dict(mode='modeled_scenario' if scenario else 'source_records',official_policy_result=False,operational_effects=False),
        limitations=deepcopy(bundle['unresolved']),evidence_hashes={col:[dict(id=r.get('_id'),sha256=record_digest(r)) for r in rows] for col,rows in evidence.items()})
