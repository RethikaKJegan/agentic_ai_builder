"""Authorized bounded procurement investigations through the existing Registry.

Caller data is a structured source query, never records, policies or join code.
"""
from copy import deepcopy
from datetime import datetime, timezone
from decimal import Decimal
import json
import time
from uuid import uuid4
from jsonschema import Draft202012Validator

from .business_knowledge_model import digest
from .service import ApiFailure
from .subway_queries import QUERY, SubwayQueryConnector, definition as query_definition
from .subway_procurement import load, assess, token, record_digest

ASSESSMENTS={'purchase_order_validation':'purchaseorders','purchase_order_reconciliation':'purchaseorders','budget_comparison':'purchaseorders','supplier_spending':'purchaseorders',
    'approval_assessment':'approvals','invoice_investigation':'invoicedatas','goods_receipt_verification':'grns','requisition_assessment':'purchaserequests'}
INPUT=dict(type='object',additionalProperties=False,required=['assessment','query'],properties=dict(
    assessment=dict(type='string',enum=list(ASSESSMENTS)),query=deepcopy(QUERY),
    as_of=dict(type='string',format='date-time',maxLength=60),delay_days=dict(type='number',minimum=0,maximum=36500)))
OUTPUT=dict(type='object',additionalProperties=False,required=['assessment_id','scope','ontology_version','input_sha256','report','coverage','sources'],properties=dict(
    assessment_id=dict(type='string'),scope=dict(type='object'),ontology_version=dict(type='string'),input_sha256=dict(type='string'),report=dict(type='object'),coverage=dict(type='object'),sources=dict(type='array',items=dict(type='object'))))


def definition():
    d=query_definition()
    d.update(tool_id='subway_assess',capability='subway.assess',input_schema=INPUT,output_schema=OUTPUT,timeout_seconds=120,
        description='Read-only deterministic Subway procurement assessment using versioned typed rules and source evidence. '
        'Bind assessment from context business_knowledge path [procurement_knowledge,assessment_kinds,chosen name]. '
        'Choose assessment and a typed detail query returning ONLY the base native _id, no joins or metrics, limit <= 20. '
        'Supported base collections: PO validation/reconciliation/budgets/supplier spending → purchaseorders; approval_assessment → approvals; '
        'invoice_investigation → invoicedatas; goods_receipt_verification → grns. Requisition source is unavailable unless explicitly connected. '
        'Authorized related evidence is retrieved automatically within bounds. Pagination is explicit; no population claim from a page. '
        'Use ordinary subway_query for population aggregates. Optional as_of and delay_days are requested analytical parameters, never official policy. '
        'Returns PASS/FAIL/INSUFFICIENT_EVIDENCE/NOT_APPLICABLE and line reconciliation; cannot approve, mutate records or use simulated data.')
    return d


def normalized(row):
    """BSON dates are UTC instants; text timestamps are preserved verbatim."""
    if isinstance(row,dict):return {k:normalized(v) for k,v in row.items()}
    if isinstance(row,list):return [normalized(v) for v in row]
    if isinstance(row,datetime):return (row.replace(tzinfo=timezone.utc) if row.tzinfo is None else row).isoformat()
    if hasattr(row,'to_decimal'):return row.to_decimal()
    return row


def public(value):
    if isinstance(value,dict):return {k:public(v) for k,v in value.items()}
    if isinstance(value,list):return [public(v) for v in value]
    if isinstance(value,Decimal):return str(value)
    if isinstance(value,(str,int,float,bool)) or value is None:return value
    return str(value)


class SubwayAssessments:
    external_write=False
    retry_safe=True
    timeout=120

    def __init__(self,queries,auth=None,pin=None):self.queries,self.auth,self.pin=queries,auth,pin
    def reservation(self,grant):return dict(tool_calls=1,llm_calls=0,tokens=0,estimated_cost_usd=0)
    def bind_context(self,workflow,run,auth,node):
        try:return self._bind_context(workflow,run,auth,node)
        except ApiFailure as exc:
            from runtime.service import RuntimeFailure
            raise RuntimeFailure(exc.code,str(exc),exc.status) from None

    def _bind_context(self,workflow,run,auth,node):
        bound=SubwayQueryConnector(self.queries).bind_context(workflow,run,auth,node)
        knowledge=workflow.get('metadata',{}).get('action_binding_context',{}).get('validated_context',{}).get('business_knowledge',{}).get('procurement_knowledge',{})
        bundle=bound.queries.procurement_bundle()
        if knowledge.get('sha256')!=bundle['sha256']:
            raise ApiFailure('SUBWAY_KNOWLEDGE_STALE','Review the current procurement knowledge before execution.',409)
        pin=deepcopy(bound.pin);pin['procurement_sha256']=bundle['sha256']
        pin['required_date_filters']=deepcopy(workflow.get('metadata',{}).get('action_binding_context',{}).get('validated_context',{}).get('subway_date_filters',[]))
        if run.get('automation_reference') and workflow.get('metadata',{}).get('overview_intent',{}).get('subway_temporal'):
            from .subway_automation import date_filters
            pin['required_date_filters']=date_filters(workflow['metadata']['overview_intent'],run)
        return SubwayAssessments(bound.queries,bound.auth,pin)

    def invoke(self,grant,inputs,effect_id):
        try:return self._invoke(grant,inputs,effect_id)
        except ApiFailure as exc:
            from runtime.service import RuntimeFailure
            raise RuntimeFailure(exc.code,str(exc),exc.status) from None

    def _invoke(self,grant,inputs,effect_id):
        from jsonschema import FormatChecker
        from registry.safety import reject_secrets
        if not self.auth or grant.get('tool_id')!='subway_assess' or list(Draft202012Validator(INPUT,format_checker=FormatChecker()).iter_errors(inputs)):
            raise ApiFailure('SUBWAY_ASSESSMENT_DENIED','Use a bound structured assessment.',403)
        self.queries.authorize(self.auth)
        packages=self.queries.app.state.client_packages
        if packages.get(self.auth,self.pin['package_id'],self.pin['revision'])['sha256']!=self.pin['package_sha256']:
            raise ApiFailure('SUBWAY_QUERY_STALE','Pinned Subway package changed.',409)
        bundle=self.queries.procurement_bundle()
        if self.pin.get('procurement_sha256')!=bundle['sha256']:
            raise ApiFailure('SUBWAY_KNOWLEDGE_STALE','The reviewed procurement rules changed.',409)
        if any(inputs['query']['filters'].count(f)!=1 for f in self.pin.get('required_date_filters',[])):
            raise ApiFailure('SUBWAY_ASSESSMENT_INVALID','Preserve the reviewed reporting period.',422)
        return self.execute(self.auth,inputs)

    def execute(self,auth,inputs):
        """Internal service entry; still checks current tenant and source authority."""
        from jsonschema import FormatChecker
        from registry.safety import reject_secrets
        if list(Draft202012Validator(INPUT,format_checker=FormatChecker()).iter_errors(inputs)):
            raise ApiFailure('SUBWAY_ASSESSMENT_INVALID','Invalid assessment input.',422)
        deadline=time.monotonic()+100
        q=self.queries;q.authorize(auth);before=q.catalog(auth);query=inputs['query'];col=ASSESSMENTS[inputs['assessment']]
        source=before['datasets'].get(query['base_dataset_id'],{})
        idfield=next((f['field_id'] for f in source.get('fields',[]) if f['name']=='_id'),None)
        if source.get('role')!='finance' or source.get('collection')!=col or query['joins'] or query['metrics'] or query['group_by'] or not idfield or query['limit']>20:
            raise ApiFailure('SUBWAY_ASSESSMENT_INVALID','Use a detail query on the assessment base collection with no joins/metrics/groups and limit <= 20.',422)
        # Validate every requested field before discarding projection-only columns.
        # Hidden base sort/filter fields retain their normal query-engine semantics.
        selection=deepcopy(query)
        if not selection['fields']:selection['fields']=[idfield]
        q.validate(selection,before)
        selection['fields']=[idfield]
        bundle=q.procurement_bundle()
        page=q.execute(auth,selection);ids=[r[idfield] for r in page['rows']]
        datasets={d['collection']:d for d in before['datasets'].values() if d['role']=='finance'}
        if getattr(q,'demo_context',None):datasets.update({d['label']:d for d in before['datasets'].values() if d['role']=='central'})
        evidence={};read_sources={};seen={};count=0;bytecount=0
        def fetch(collection,field,values):
            nonlocal count,bytecount
            values=[v for v in values if token(v) is not None]
            if not values or collection not in datasets:return
            d=datasets[collection];cid=d['connection_id']
            # Every traversal has a fixed source-code mapping; no caller field/path.
            from .data_query_control import checkpoint
            checkpoint()
            with q.store.transaction(write=False) as db:_,secret,_,_=q.sources.bound(db,auth,cid)
            config=json.loads(q.sources.manager.cipher.decrypt(secret.encode()))
            # Fixed safe fields only; never fetch arbitrary private/user documents.
            fields=FIELDS.get(collection,[])
            if getattr(q,'demo_context',None):
                from .subway_demo_assessment import DEMO_FIELDS
                fields=DEMO_FIELDS[collection]
            from .source_freshness import describe
            read_sources[collection]=dict(dataset_id=d['dataset_id'],label=d['label'],generation=d['generation'],metadata_revision=d['metadata_revision'],freshness=describe(q.sources.manager.adapter,config,d['metadata_revision']))
            with q.sources.manager.adapter.connection(config) as client:
                cursor=client[config['database']][d['collection']].find({field:{'$in':values}},dict.fromkeys(fields,1)).batch_size(100).max_time_ms(15000)
                try:
                    for raw in cursor:
                        checkpoint()
                        if time.monotonic()>deadline:raise ApiFailure('SUBWAY_QUERY_TIMEOUT','Assessment evidence deadline exceeded.',504)
                        row=normalized({k:v for k,v in raw.items() if k in fields});key=token(row.get('_id'))
                        if key in seen.setdefault(collection,set()):continue
                        seen[collection].add(key);count+=1;bytecount+=len(json.dumps(public(row)).encode())
                        if count>5000 or bytecount>8000000:raise ApiFailure('SUBWAY_ASSESSMENT_LIMIT','Narrow the assessment scope; evidence exceeds 5000 records or 8 MB. No partial assessment returned.',422)
                        evidence.setdefault(collection,[]).append(row)
                finally:cursor.close()
        fetch(col,'_id',ids)
        root=evidence.get(col,[])
        if col in ('grns','invoicedatas'):
            fetch('purchaseorders','_id',[r.get('purchaseOrderId' if col=='grns' else 'poId') for r in root])
        pos=evidence.get('purchaseorders',[])
        fetch('purchaseorders','poNumber',[p.get('poNumber') for p in pos])
        # Keep actual duplicate reference rows for uniqueness checks, but traverse
        # only selected POs and the unique exact parents of selected invoices/GRNs.
        pids=[p['_id'] for p in pos]
        fetch('grns','purchaseOrderId',pids);fetch('invoicedatas','poId',pids)
        invoices=evidence.get('invoicedatas',[])
        fetch('invoicedatas','invoiceNumber',[r.get('invoiceNumber') for r in invoices])
        fetch('grns','_id',[r.get('grnId') for r in invoices])
        records=pos+invoices+evidence.get('grns',[])
        fetch('approvals','_id',[r.get('approvalId') for r in records])
        aps=evidence.get('approvals',[])
        fetch('stages','approvalId',[r['_id'] for r in aps]+[r.get('approvalId') for r in records])
        fetch('lineitems','_id',[i.get('lineItem') for p in pos for i in p.get('items',[])])
        fetch('budgets','_id',[l.get('budgetId') for l in evidence.get('lineitems',[])])
        fetch('locations','_id',[r.get('site') for r in pos+evidence.get('budgets',[])])
        if getattr(q,'demo_context',None):
            fetch('central.stores','_id',[r.get('storeId') for r in pos])
            fetch('central.vendors','_id',[r.get('vendorId') for r in pos])
            fetch('storemappings','financeLocationId',[r.get('site') for r in pos])
            fetch('suppliermappings','vendorCode',[r.get('vendorCode') for r in pos])
            fetch('purchaserequests','_id',[r.get('purchaseRequestId') for r in pos])
            fetch('approvals','_id',[r.get('approvalId') for r in evidence.get('purchaserequests',[])])
            fetch('stages','approvalId',[r['_id'] for r in evidence.get('approvals',[])])
            fetch('invoiceitems','invoiceId',[r['_id'] for r in invoices])
            fetch('payments','invoiceId',[r['_id'] for r in invoices])
            fetch('reservations','purchaseOrderId',pids)
            fetch('allocations','lineItemId',[r['_id'] for r in evidence.get('lineitems',[])])
        # No PR/store/vendor cross-source traversal without an authorized mapping.
        assessment_inputs=inputs
        if getattr(q,'demo_context',None):
            from .subway_demo_data import POLICY
            assessment_inputs={**dict(as_of=POLICY['as_of'],delay_days=POLICY['approval_delay_days']),**inputs}
        report=assess(bundle,evidence,inputs['assessment'],ids,as_of=assessment_inputs.get('as_of'),delay_days=assessment_inputs.get('delay_days'))
        if getattr(q,'demo_context',None):
            from .subway_demo_assessment import augment
            report=augment(bundle,evidence,report,assessment_inputs,q.demo_context)
        after=q.catalog(auth)
        if before['stamps']!=after['stamps']:raise ApiFailure('SUBWAY_QUERY_STALE','Source authority changed during assessment.',409)
        coverage=deepcopy(page['coverage']);coverage.update(assessment_scope='selected base page plus bounded authorized related evidence',related_records=count,population_assessment_complete=not coverage['has_more'] and query['offset']==0,
            historical_source_warning='Source read time is not current business coverage; preserve each source freshness attestation.')
        coverage['assessment_selection']=dict(requested_fields=deepcopy(query['fields']),effective_fields=[idfield],query_id=page['query_id'])
        output=public(dict(assessment_id='subway_assessment_'+uuid4().hex,scope=dict(workspace_id='client-subway',owner_id='subway-client'),ontology_version=q.version['version_id'],input_sha256=digest(inputs),report=report,coverage=coverage,sources=list(read_sources.values())))
        reject_secrets(output)
        if len(json.dumps(output).encode())>800000:raise ApiFailure('SUBWAY_ASSESSMENT_LIMIT','Assessment output exceeds 800 KB; narrow the query.',422)
        with q.store.transaction() as db:
            db.execute('CREATE TABLE IF NOT EXISTS subway_assessment_receipts (workspace TEXT,owner TEXT,assessment_id TEXT,document TEXT,PRIMARY KEY(workspace,owner,assessment_id))')
            receipt=dict(output_sha256=digest(output),input_sha256=digest(inputs),source_authority_sha256=digest(before['stamps']),knowledge_sha256=bundle['sha256'])
            db.execute('INSERT INTO subway_assessment_receipts VALUES (?,?,?,?)',('client-subway','subway-client',output['assessment_id'],json.dumps(receipt)))
        return output


FIELDS={
 'purchaseorders':['_id','poNumber','poDate','createdAt','status','vendorCode','vendorName','amount','totalAmount','taxAmount','currency','site','budget','approvalId','purchaseRequestId','financialYear','items'],
 'grns':['_id','grnNo','purchaseOrderId','status','inwardDate','invoiceNumber','invoiceDate','invoiceAmount','vendorCode','approvalId','receivedItems','invoiceDataId'],
 'invoicedatas':['_id','invoiceNumber','invoiceDocumentNumber','invoiceDate','invoiceAmount','poId','grnId','approvalId','vendorCode','financialYear','status','dateOfPayment','paymentStatus'],
 'approvals':['_id','status','approvalType','currentStageNumber','createdAt','updatedAt','stages','approved','rejected','previousApprovalId','cycleNumber'],
 'stages':['_id','approvalId','status','StageNumber','stageDate','createdAt','approved'],
 'lineitems':['_id','budgetId','availableAmount','reservedAmount','currentAmount','initialAmount','financialYear','status'],
 'budgets':['_id','site','financialYear','utilizedAmount','availableBudgetCost','reservedAmount','status'],
 'locations':['_id','code','name'],
 'purchaserequests':['_id','prNumber','prDate','site','createdBy','items','status','approvalId','isParentPR','legacyAllocationUnresolved']}
