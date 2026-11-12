"""Subway-only source lifecycle in the existing application store.

Immutable manifests/records remain in their original tables. Workspace settings
hold the active pointer; audit and recovery archives are never cleaned up.
"""
from copy import deepcopy
from datetime import datetime, timezone
from decimal import Decimal
import json
import re
from uuid import uuid4

from .business_knowledge_model import digest
from .service import ApiFailure
from runtime.service import RuntimeFailure
from .subway_demo_data import DATASET, VERSION, SCOPE, POLICY

KEY='subway.demo.lifecycle:subway-client'
RULE_VERSION='subway-demo-procurement-v1'
PREFIX=re.compile(r'^\s*use\s+subway\s+(?:demonstration|demo)\s+dataset\s+v(\d+)\s*(?:[.!:;\n]|$)',re.I)
NAMED=re.compile(r'^\s*use\s+subway\s+dataset\s+([A-Za-z0-9_-]+)\s*(?:[.!:;\n]|$)',re.I)
CURRENT=re.compile(r'\b(?:real|actual)\s+(?:current|live|latest)\b|\bcurrent\s+(?:subway\s+)?(?:purchase[- ]orders|invoices|payments|budgets|records)\b|\b(?:real\s+current|real[- ]time|live|current)\s+(?:subway\s+)?(?:operational\s+)?(?:operations|production\s+data|business\s+data|subway\s+records)\b',re.I)
HISTORICAL=re.compile(r'\bhistorical\b|\brestored\b|\b(?:real|actual|production)\s+(?:subway\s+)?(?:records|data|transactions|purchase\s+orders)\b',re.I)


def now():return datetime.now(timezone.utc).isoformat()
def fail(message,code='SUBWAY_DATASET_INVALID',status=422):raise ApiFailure(code,message,status)
def authorize(auth,write=False):
    from .subway_demonstration import authorize as tenant
    tenant(auth)
    if auth.get('decision')!='allow' or 'workspace:read' not in auth.get('scopes',[]):fail('Subway dataset access is not authorized.','OPERATION_NOT_AUTHORIZED',403)
    if write:
        from runtime.service import RuntimeService
        RuntimeService.authorize(auth,'workflow.approve',{'admin','approver'})
        if 'workspace:write' not in auth.get('scopes',[]):fail('Subway dataset management requires workspace write access.','OPERATION_NOT_AUTHORIZED',403)


def state(db):
    row=db.execute('SELECT value FROM workspace_settings WHERE workspace=? AND key=?',(SCOPE[0],KEY)).fetchone()
    return json.loads(row[0]) if row else None

def save(db,value):
    db.execute('INSERT INTO workspace_settings VALUES (?,?,?,?) ON CONFLICT(workspace,key) DO UPDATE SET value=excluded.value,updated_at=excluded.updated_at',(SCOPE[0],KEY,json.dumps(value),now()))

def audit(db,event,dataset_id,details=None):
    db.execute('INSERT INTO subway_demo_lifecycle_audit VALUES (?,?,?,?,?,?)',(*SCOPE,'demo_event_'+uuid4().hex,event,dataset_id,json.dumps(dict(at=now(),details=details or {}))))

def initialize(db):
    db.execute('CREATE TABLE IF NOT EXISTS subway_demo_lifecycle_audit (workspace TEXT,owner TEXT,event_id TEXT,event TEXT,dataset_id TEXT,document TEXT,PRIMARY KEY(workspace,owner,event_id))')
    db.execute('CREATE TABLE IF NOT EXISTS subway_demo_archives (workspace TEXT,owner TEXT,dataset_id TEXT,sha256 TEXT,document TEXT,PRIMARY KEY(workspace,owner,dataset_id))')


def read_dataset(store,auth,dataset_id,db=None):
    """Verify the original manifest without recreating its authoring records."""
    authorize(auth)
    if db is None:
        with store.transaction(write=False) as conn:return read_dataset(store,auth,dataset_id,conn)
    if not db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='subway_demo_datasets'").fetchone():fail('Subway demonstration data is not provisioned.','SUBWAY_DEMO_UNAVAILABLE',409)
    row=db.execute('SELECT document FROM subway_demo_datasets WHERE workspace=? AND owner=? AND dataset_id=?',(*SCOPE,dataset_id)).fetchone()
    if not row:fail('The selected Subway demonstration version is unavailable.','SUBWAY_DEMO_UNAVAILABLE',409)
    header=json.loads(row[0]);records={}
    for col,raw in db.execute('SELECT collection,document FROM subway_demo_records WHERE workspace=? AND owner=? AND dataset_id=?',(*SCOPE,dataset_id)):
        records.setdefault(col,[]).append(json.loads(raw))
    if set(records)!=set(header.get('record_hashes',{})):fail('Demo collections differ from their manifest.','SUBWAY_DEMO_INTEGRITY',409)
    ordered={}
    for col,rows in records.items():
        indexed={digest(r):r for r in rows};hashes=header['record_hashes'][col]
        if len(indexed)!=len(rows) or len(hashes)!=len(rows) or set(indexed)!=set(hashes):fail('Persisted demonstration records failed integrity verification.','SUBWAY_DEMO_INTEGRITY',409)
        ordered[col]=[indexed[h] for h in hashes]
    document={k:v for k,v in header.items() if k not in ('record_hashes','sha256')};document['records']=ordered
    if header.get('dataset_id')!=dataset_id or header.get('scope')!={'workspace_id':SCOPE[0],'owner_id':SCOPE[1]} or digest(document)!=header.get('sha256'):fail('Dataset scope or manifest hash changed.','SUBWAY_DEMO_INTEGRITY',409)
    # Retain the original reader's stable native ordering for legacy workflows.
    for rows in records.values():rows.sort(key=lambda r:r['_id'])
    return header,records


def validate(store,auth,document,ontology_id,db):
    from .business_compiler import check_snapshot
    from .business_knowledge_model import RULE
    from .subway_demo_assessment import rules
    from jsonschema import Draft202012Validator
    from .subway_procurement import token
    authorize(auth)
    manifest_schema=dict(type='object',required=['dataset_id','revision','scope','label','mode','as_of','policy','records','sha256'],properties=dict(dataset_id=dict(type='string',maxLength=101),revision=dict(type='integer',minimum=1),scope=dict(type='object'),label=dict(type='string',minLength=1),mode=dict(type='string'),as_of=dict(type='string'),policy=dict(type='object'),records=dict(type='object'),sha256=dict(type='string',pattern='^[a-f0-9]{64}$')))
    if list(Draft202012Validator(manifest_schema).iter_errors(document)):fail('Dataset manifest schema is invalid.')
    try:size=len(json.dumps(document,allow_nan=False).encode())
    except (ValueError,TypeError):fail('Dataset values must be finite JSON data.')
    if size>8000000:fail('Dataset exceeds the reviewed 8 MB version limit.')
    required={'dataset_id','revision','scope','label','mode','as_of','policy','records','sha256'}
    if not isinstance(document,dict) or set(document)-required-{'created_at','schema_version'} or not required<=set(document):fail('Use a complete versioned demonstration manifest.')
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]{0,100}',document['dataset_id']) or type(document['revision']) is not int or document['revision']<1:fail('Dataset identity and positive numeric revision are required.')
    if document['scope']!={'workspace_id':SCOPE[0],'owner_id':SCOPE[1]} or document['mode']!='modeled_demonstration':fail('Only Subway modeled records can be registered.','SUBWAY_DATASET_SCOPE',403)
    if document.get('schema_version',1)!=1 or document['policy']!=POLICY or document['as_of']!=POLICY['as_of']:fail('This runtime supports only the reviewed schema and modeled policy; incompatible policies require a reviewed runtime change.')
    if 'MODELED' not in document['label'].upper() or digest({k:v for k,v in document.items() if k!='sha256'})!=document['sha256']:fail('Modeled provenance and exact manifest integrity are required.')
    row=db.execute('SELECT document FROM business_ontology_versions WHERE workspace=? AND owner=? AND version_id=?',(*SCOPE,ontology_id)).fetchone()
    if not row:fail('The associated Subway ontology does not exist.')
    ontology=json.loads(row[0]);check_snapshot(ontology)
    if ontology.get('demo_context',{}).get('mode')!='modeled_demonstration' or ontology.get('base_version_id')!='bov_subway_dump_v4':fail('A compatible modeled Subway ontology is required.')
    records=document['records'];baseline_row=db.execute('SELECT document FROM subway_demo_datasets WHERE workspace=? AND owner=? AND dataset_id=?',(*SCOPE,DATASET)).fetchone()
    # Bootstrap validates the existing source itself; future versions use its
    # persisted schema rather than generating another authoring fixture.
    if not baseline_row:fail('The validated base dataset must exist first.')
    _,baseline=read_dataset(store,auth,DATASET,db)
    if set(records)!=set(baseline):fail('A compatible version must retain the supported collections.')
    def shape(samples):
        variants=[]
        for kind in ('object','array','string','number','boolean','null'):
            chosen=[v for v in samples if ('null' if v is None else 'boolean' if type(v) is bool else 'number' if type(v) in (int,float) else 'object' if isinstance(v,dict) else 'array' if isinstance(v,list) else 'string' if isinstance(v,str) else 'unsupported')==kind]
            if not chosen:continue
            schema=dict(type=kind)
            if kind=='object':
                keys=set().union(*(v.keys() for v in chosen));schema.update(properties={k:shape([v[k] for v in chosen if k in v]) for k in keys},required=sorted(set.intersection(*(set(v) for v in chosen))),additionalProperties=False)
            if kind=='array':
                items=[i for v in chosen for i in v];schema['items']=shape(items) if items else {}
            variants.append(schema)
        return variants[0] if len(variants)==1 else dict(anyOf=variants)
    indexes={}
    for col,rows in records.items():
        allowed={k for r in baseline[col] for k in r}
        if not isinstance(rows,list) or not rows:fail('Compatible collections cannot be empty.')
        if list(Draft202012Validator(dict(type='array',items=shape(baseline[col]))).iter_errors(rows)):fail('Nested record schema is incompatible: '+col)
        indexes[col]={}
        for row in rows:
            if not isinstance(row,dict) or set(row)-allowed or not set(baseline[col][0])<=set(row):fail('Record schema is incompatible: '+col)
            if type(row.get('_id')) is not type(baseline[col][0]['_id']):fail('Native identity type changed: '+col)
            ident=token(row.get('_id'))
            if ident is None or ident in indexes[col] or row.get('demo_origin')!='modeled_demonstration' or row.get('demo_dataset')!=document['dataset_id']:fail('Record identity or modeled provenance is invalid: '+col)
            indexes[col][ident]=row
    links=[('finance.purchaseorders','site','finance.locations'),('finance.purchaseorders','vendorId','central.vendors'),('finance.purchaseorders','budget','finance.budgets'),('finance.purchaseorders','approvalId','finance.approvals'),('finance.purchaseorders','purchaseRequestId','finance.purchaserequests'),('finance.locations','storeId','central.stores'),('finance.storemappings','centralStoreId','central.stores'),('finance.storemappings','financeLocationId','finance.locations'),('finance.suppliermappings','centralVendorId','central.vendors'),('finance.lineitems','budgetId','finance.budgets'),('finance.budgets','site','finance.locations'),('finance.stages','approvalId','finance.approvals'),('finance.invoicedatas','poId','finance.purchaseorders'),('finance.invoicedatas','grnId','finance.grns'),('finance.invoicedatas','approvalId','finance.approvals'),('finance.invoiceitems','invoiceId','finance.invoicedatas'),('finance.invoiceitems','poId','finance.purchaseorders'),('finance.payments','invoiceId','finance.invoicedatas'),('finance.grns','purchaseOrderId','finance.purchaseorders'),('finance.purchaserequests','approvalId','finance.approvals'),('finance.reservations','purchaseRequestId','finance.purchaserequests'),('finance.reservations','purchaseOrderId','finance.purchaseorders'),('finance.reservations','lineItemId','finance.lineitems'),('finance.allocations','budgetId','finance.budgets'),('finance.allocations','lineItemId','finance.lineitems')]
    for col,field,target in links:
        if any(token(r.get(field)) not in indexes[target] for r in records[col]):fail('Unresolved modeled reference: '+col+'.'+field)
    def decimal(v):
        if type(v) not in (int,float):fail('Financial values must be finite numbers.')
        x=Decimal(str(v))
        if not x.is_finite() or x<0:fail('Financial values must be nonnegative finite numbers.')
        return x
    for po in records['finance.purchaseorders']:
        pr=indexes['finance.purchaserequests'][token(po['purchaseRequestId'])]
        if po['_id'] not in pr['purchaseOrderIds']:fail('Requisition/order references must be bidirectional.')
        for item in po['items']:
            if token(item['lineItem']) not in indexes['finance.lineitems'] or token(item['item']) not in indexes['finance.items']:fail('PO line references are unresolved.')
        if sum(decimal(i['totalAmount']) for i in po['items'])!=decimal(po['totalAmount']):fail('PO header and line totals differ.')
    for inv in records['finance.invoicedatas']:
        po=indexes['finance.purchaseorders'][token(inv['poId'])];lines={i['_id'] for i in po['items']}
        if inv['currency']!=po['currency'] or any(i['poLineId'] not in lines for i in inv['items']):fail('Invoice currency or PO-line references are incompatible.')
        if sum(decimal(i['totalAmount']) for i in inv['items'])!=decimal(inv['invoiceAmount']):fail('Invoice header and line totals differ.')
        for item in inv['items']:
            if decimal(item['quantity'])*decimal(item['unitPrice'])!=decimal(item['amount']) or decimal(item['amount'])+decimal(item['taxAmount'])!=decimal(item['totalAmount']):fail('Invoice line arithmetic is inconsistent.')
        children=[{k:v for k,v in row.items() if k not in ('demo_origin','demo_dataset','invoiceId','poId')} for row in records['finance.invoiceitems'] if row['invoiceId']==inv['_id']]
        if sorted(children,key=lambda i:i['_id'])!=sorted(inv['items'],key=lambda i:i['_id']):fail('Embedded and queryable invoice items differ.')
        if any(p['currency']!=inv['currency'] for p in records['finance.payments'] if p['invoiceId']==inv['_id']):fail('Payment currency differs from the invoice.')
        paid=sum(decimal(p['amount']) for p in records['finance.payments'] if p['invoiceId']==inv['_id'])
        if paid!=decimal(inv['paymentAmount']) or paid>decimal(inv['invoiceAmount']):fail('Invoice payment balances are inconsistent.')
        try:
            if datetime.fromisoformat(inv['dueDate'].replace('Z','+00:00')).tzinfo is None:raise ValueError()
        except (ValueError,TypeError,AttributeError):fail('Invoice due dates require explicit timezones.')
    for b in records['finance.budgets']:
        if sum(decimal(b[f]) for f in ('utilizedAmount','reservedAmount','availableBudgetCost'))!=decimal(b['modifiedBudgetCost']):fail('Budget balance identity failed.')
    for line in records['finance.lineitems']:
        if sum(decimal(line[f]) for f in ('availableAmount','reservedAmount','recordedExpenditure'))!=decimal(line['currentAmount']):fail('Budget line balance identity failed.')
    for rule in rules():Draft202012Validator(RULE).validate({k:rule[k] for k in RULE['properties']})
    return dict(schema='passed',relationships='passed',arithmetic='passed',ontology_sha256=digest(ontology),policy_sha256=digest(POLICY),business_rule_version=RULE_VERSION,tool_contract='subway-native-query-and-assessment-v1')


def metadata(document,ontology_id,validation):
    did=document['dataset_id'];rev=document['revision']
    return dict(dataset_id=did,workspace=SCOPE[0],owner=SCOPE[1],version=rev,created_at=document.get('created_at',now()),status='VALIDATED',classification='modeled_demonstration',ontology_version=ontology_id,business_rule_version=RULE_VERSION,schema_version=1,validation_status='passed',validation=validation,sha256=document['sha256'],query_namespace='demo_v1' if did==DATASET else 'demo_'+digest([did,rev])[:12],provenance=dict(label=document['label'],as_of=document['as_of'],policy_id=POLICY['id']),dependencies=dict(ontology=ontology_id,base_ontology='bov_subway_dump_v4',rules=RULE_VERSION))


def document_from(header,records):
    indexes={col:{digest(r):r for r in rows} for col,rows in records.items()}
    return {**{k:deepcopy(v) for k,v in header.items() if k!='record_hashes'},'records':{col:[indexes[col][h] for h in hashes] for col,hashes in header['record_hashes'].items()}}


def bootstrap(store,auth,automatic_default=False):
    authorize(auth)
    with store.transaction() as db:
        initialize(db);s=state(db)
        if s is None:
            h,r=read_dataset(store,auth,DATASET,db);doc=document_from(h,r);v=validate(store,auth,doc,VERSION,db);entry=metadata(doc,VERSION,v);entry['status']='ACTIVE'
            s=dict(schema_version=1,scope=dict(workspace=SCOPE[0],owner=SCOPE[1]),automatic_default_enabled=bool(automatic_default),active_dataset_id=DATASET,generation=1,versions={DATASET:entry});audit(db,'bootstrap',DATASET,dict(sha256=h['sha256'],records_reused=True))
        s['automatic_default_enabled']=bool(automatic_default);save(db,s)
    return deepcopy(s)


def references(db,entry):
    """Conservative tenant-scoped dependency inventory; never returns payloads."""
    needles=(entry['dataset_id'],entry['sha256'],entry['query_namespace']+'_');found=[]
    tables=db.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
    excluded={'subway_demo_datasets','subway_demo_records','subway_demo_archives','subway_demo_lifecycle_audit'}
    def contains(value):
        if isinstance(value,str):return any(n in value for n in needles)
        if isinstance(value,dict):return any(contains(v) for v in value.values())
        if isinstance(value,list):return any(contains(v) for v in value)
        return False
    for (table,) in tables:
        if table in excluded:continue
        quoted='"'+table.replace('"','""')+'"';info=db.execute('PRAGMA table_info('+quoted+')').fetchall();cols={r[1] for r in info};jsoncols=sorted(r[1] for r in info if (r[2].upper()=='TEXT' or r[1] in {'document','response','value','payload'}) and not any(secret in r[1].lower() for secret in ('secret','password','credential','token')))
        if not jsoncols:continue
        where=' WHERE workspace=?' if 'workspace' in cols else ' WHERE workspace_id=?' if 'workspace_id' in cols else ''
        params=(SCOPE[0],) if where else ()
        if table=='workspace_settings':where+=' AND key!=?';params+= (KEY,)
        for row in db.execute('SELECT '+','.join('"'+c+'"' for c in jsoncols)+' FROM '+quoted+where,params):
            if any(isinstance(raw,str) and contains(raw) for raw in row):found.append(dict(table=table,reference_sha256=digest(list(row))));break
    if db.execute("SELECT 1 FROM subway_demo_lifecycle_audit WHERE workspace=? AND owner=? AND dataset_id=? AND event='resolved' LIMIT 1",(*SCOPE,entry['dataset_id'])).fetchone():found.append(dict(table='subway_demo_lifecycle_audit',reason='durable source-resolution pin'))
    return found


class SubwayDatasetLifecycle:
    def __init__(self,store):self.store=store
    def inventory(self,auth):
        authorize(auth)
        with self.store.transaction(write=False) as db:
            s=state(db)
            if not s:fail('Subway dataset lifecycle is not configured.','SUBWAY_DATASET_UNAVAILABLE',409)
            result=deepcopy(s)
            for e in result['versions'].values():
                e['references']=references(db,e);e['inventory_classification']='ACTIVE' if e['dataset_id']==s['active_dataset_id'] else 'REFERENCED' if e['references'] else e['status'] if e['status'] in ('RETIRED','INVALID','DELETED') else 'UNUSED'
            result['protected_resources']=['historical source registrations and records','shared/referenced ontology and packages','workflow/run history','evidence receipts and Knowledge Map history','all recovery backups and lifecycle audit']
            return result
    def register(self,auth,document,ontology_version=VERSION,activate=True):
        authorize(auth,True)
        with self.store.transaction() as db:
            s=state(db)
            if not s:fail('Initialize Subway lifecycle before registering versions.')
            v=validate(self.store,auth,document,ontology_version,db);entry=metadata(document,ontology_version,v);did=entry['dataset_id']
            if did in s['versions']:fail('Dataset versions are immutable; use a new identity.','SUBWAY_DATASET_CONFLICT',409)
            if any(e['version']==entry['version'] for e in s['versions'].values()):fail('Numeric dataset revisions must be unique.','SUBWAY_DATASET_CONFLICT',409)
            header={k:deepcopy(x) for k,x in document.items() if k!='records'};header['record_hashes']={col:[digest(r) for r in rows] for col,rows in document['records'].items()}
            db.execute('INSERT INTO subway_demo_datasets VALUES (?,?,?,?)',(*SCOPE,did,json.dumps(header)))
            for col,rows in document['records'].items():
                for row in rows:db.execute('INSERT INTO subway_demo_records VALUES (?,?,?,?,?,?)',(*SCOPE,did,col,str(row['_id']),json.dumps(row)))
            s['versions'][did]=entry;audit(db,'registered',did,dict(sha256=entry['sha256'],validation=v))
            if activate:self._activate(db,s,did,auth)
            save(db,s);return deepcopy(s['versions'][did])
    def _activate(self,db,s,did,auth):
        if did not in s['versions']:fail('Unknown Subway dataset.')
        entry=s['versions'][did]
        if entry['status'] not in ('VALIDATED','RETIRED','ACTIVE') or entry['validation_status']!='passed':fail('Only validated retained versions can be activated.')
        if any(e['status']=='ACTIVE' and e['version']>entry['version'] for e in s['versions'].values()):fail('A newer active version already exists.')
        current=s['versions'].get(s['active_dataset_id'])
        if current and current['version']>entry['version']:fail('An older version cannot replace the latest active default.')
        header,records=read_dataset(self.store,auth,did,db);proof=validate(self.store,auth,document_from(header,records),entry['ontology_version'],db)
        if proof!=entry['validation']:fail('Dataset compatibility changed; revalidation is required.')
        if current and current['dataset_id']!=did:current['status']='RETIRED'
        entry['status']='ACTIVE';s['active_dataset_id']=did;s['generation']+=1;audit(db,'activated',did,dict(previous=current['dataset_id'] if current else None,generation=s['generation']))
    def activate(self,auth,dataset_id):
        authorize(auth,True)
        with self.store.transaction() as db:
            s=state(db);self._activate(db,s,dataset_id,auth);save(db,s);return deepcopy(s['versions'][dataset_id])
    def retire(self,auth,dataset_id):
        authorize(auth,True)
        with self.store.transaction() as db:
            s=state(db);entry=s['versions'].get(dataset_id)
            if not entry or entry['status']=='DELETED':fail('Dataset is unavailable.')
            entry['status']='RETIRED'
            if s['active_dataset_id']==dataset_id:s['active_dataset_id']=None
            s['generation']+=1;save(db,s);audit(db,'retired',dataset_id);return deepcopy(entry)
    def cleanup(self,auth,dataset_id):
        authorize(auth,True)
        with self.store.transaction() as db:
            s=state(db);entry=s['versions'].get(dataset_id)
            if not entry or dataset_id==DATASET or s['active_dataset_id']==dataset_id or entry['status']!='RETIRED':fail('Only retired non-base, inactive demonstration versions can be cleaned up.','SUBWAY_DATASET_PROTECTED',409)
            refs=references(db,entry)
            if refs:fail('Dataset is required by protected history or a saved source pin.','SUBWAY_DATASET_REFERENCED',409)
            h,r=read_dataset(self.store,auth,dataset_id,db);archive=dict(header=h,records=r);stamp=digest(archive)
            db.execute('INSERT INTO subway_demo_archives VALUES (?,?,?,?,?) ON CONFLICT(workspace,owner,dataset_id) DO NOTHING',(*SCOPE,dataset_id,stamp,json.dumps(archive)))
            check=db.execute('SELECT sha256,document FROM subway_demo_archives WHERE workspace=? AND owner=? AND dataset_id=?',(*SCOPE,dataset_id)).fetchone()
            if check[0]!=digest(json.loads(check[1])) or check[0]!=stamp:fail('Recovery archive verification failed.')
            db.execute('DELETE FROM subway_demo_records WHERE workspace=? AND owner=? AND dataset_id=?',(*SCOPE,dataset_id));db.execute('DELETE FROM subway_demo_datasets WHERE workspace=? AND owner=? AND dataset_id=?',(*SCOPE,dataset_id))
            entry['status']='DELETED';entry['recovery_archive_sha256']=stamp;save(db,s);audit(db,'operational_data_archived',dataset_id,dict(archive_sha256=stamp));return deepcopy(entry)
    def restore(self,auth,dataset_id):
        authorize(auth,True)
        with self.store.transaction() as db:
            s=state(db);entry=s['versions'].get(dataset_id);row=db.execute('SELECT sha256,document FROM subway_demo_archives WHERE workspace=? AND owner=? AND dataset_id=?',(*SCOPE,dataset_id)).fetchone()
            if not entry or entry['status']!='DELETED' or not row:fail('A retained recovery archive is required.')
            archive=json.loads(row[1])
            if digest(archive)!=row[0]:fail('Recovery archive integrity failed.')
            h=archive['header'];r=archive['records'];validate(self.store,auth,document_from(h,r),entry['ontology_version'],db)
            db.execute('INSERT INTO subway_demo_datasets VALUES (?,?,?,?)',(*SCOPE,dataset_id,json.dumps(h)))
            for col,rows in r.items():
                for rec in rows:db.execute('INSERT INTO subway_demo_records VALUES (?,?,?,?,?,?)',(*SCOPE,dataset_id,col,str(rec['_id']),json.dumps(rec)))
            entry['status']='RETIRED';save(db,s);audit(db,'restored',dataset_id);return deepcopy(entry)


def historical(real):
    return dict(schema_version=1,kind='historical_snapshot',selection='explicit_or_legacy',scope=dict(workspace_id=SCOPE[0],owner_id=SCOPE[1]),ontology_version=real.version['version_id'],qualification='Restored historical Subway records; current operational coverage is unverified.')


def resolve(real,auth,objective,resolution=None):
    """The only source selector for new Subway planning. Models cannot choose it."""
    real.authorize(auth);authorize(auth)
    if resolution is not None:
        if resolution.get('scope')!={'workspace_id':SCOPE[0],'owner_id':SCOPE[1]}:fail('Source pin belongs to another tenant.','SUBWAY_DATASET_SCOPE',403)
        if resolution.get('kind')=='historical_snapshot':return real,deepcopy(resolution)
        if resolution.get('kind')!='modeled_demonstration':fail('Unsupported saved source resolution.')
        from .subway_demonstration import DemoQueries
        q=DemoQueries(real,auth,resolution['dataset']['dataset_id'])
        if q.demo_context!=resolution['dataset'] or q.version['version_id']!=resolution['ontology_version'] or q.entry['query_namespace']!=resolution['query_namespace'] or q.entry['business_rule_version']!=resolution['business_rule_version']:fail('Saved dataset authority changed.','SUBWAY_DEMO_STALE',409)
        return q,deepcopy(resolution)
    explicit=PREFIX.match(objective or '');named=NAMED.match(objective or '')
    if CURRENT.search(objective or ''):fail('Restored Subway sources do not establish real current operations. Choose historical records or a clearly modeled demonstration.','SUBWAY_CURRENT_SOURCE_UNVERIFIED',409)
    if HISTORICAL.search(objective or ''):
        if explicit or named:fail('Choose one source: historical records or a demonstration version.','SUBWAY_SOURCE_SELECTION_CONFLICT',422)
        return real,historical(real)
    with real.store.transaction() as db:
        s=state(db)
        if not s:
            if explicit or named:fail('Demonstration lifecycle is not provisioned.','SUBWAY_DATASET_UNAVAILABLE',409)
            return real,historical(real)
        if explicit:
            entries=[e for e in s['versions'].values() if e['version']==int(explicit.group(1))]
            entry=entries[0] if len(entries)==1 else None
        elif named:entry=s['versions'].get(named.group(1))
        elif not s['automatic_default_enabled']:return real,historical(real)
        else:entry=s['versions'].get(s['active_dataset_id'])
        allowed={'ACTIVE','VALIDATED','RETIRED'} if explicit or named else {'ACTIVE'}
        if not entry or entry['status'] not in allowed or entry['validation_status']!='passed':fail('No eligible active validated Subway demonstration dataset is available. Select historical records or configure an active dataset.','SUBWAY_DATASET_UNAVAILABLE',409)
        h,_=read_dataset(real.store,auth,entry['dataset_id'],db)
        if h['sha256']!=entry['sha256']:fail('Validated source manifest changed.','SUBWAY_DEMO_STALE',409)
        from .subway_demonstration import descriptor
        pin=dict(schema_version=1,kind='modeled_demonstration',selection='explicit' if explicit or named else 'automatic',scope=dict(workspace_id=SCOPE[0],owner_id=SCOPE[1]),dataset=descriptor(h),ontology_version=entry['ontology_version'],business_rule_version=entry['business_rule_version'],query_namespace=entry['query_namespace'],registry_generation=s['generation'])
        # Durable before model routing: cleanup cannot race an in-flight plan.
        audit(db,'resolved',entry['dataset_id'],dict(resolution_sha256=digest(pin),generation=s['generation']))
    q,pin=resolve(real,auth,objective,pin);return q,pin


def install_routes(app,store,auth,reference):
    """Mounted only by the dedicated Subway configured launcher."""
    from fastapi import Request
    from fastapi.responses import JSONResponse
    from starlette.concurrency import run_in_threadpool
    manager=SubwayDatasetLifecycle(store)
    async def call(request,operation,dataset_id=None):
        actor=getattr(app.state,'workflow_auth',auth)
        try:
            if operation=='inventory':result=await run_in_threadpool(manager.inventory,actor)
            elif operation=='register':
                body=await request.json()
                if not isinstance(body,dict) or 'document' not in body or set(body)-{'document','ontology_version','activate'} or type(body.get('activate',True)) is not bool:fail('Use a version manifest, ontology version and activation flag.')
                result=await run_in_threadpool(manager.register,actor,body['document'],body.get('ontology_version',VERSION),body.get('activate',True))
            else:result=await run_in_threadpool(getattr(manager,operation),actor,dataset_id)
            return JSONResponse(dict(request_id=reference(),status=200,data=result),headers={'Cache-Control':'no-store'})
        except (ApiFailure,RuntimeFailure) as exc:return JSONResponse(dict(request_id=reference(),status=exc.status,data=dict(error=dict(error_code=exc.code,message=str(exc)))),status_code=exc.status)
    @app.get('/business-ontology/v1/subway/datasets')
    async def inventory(request:Request):return await call(request,'inventory')
    @app.post('/business-ontology/v1/subway/datasets')
    async def register(request:Request):return await call(request,'register')
    @app.post('/business-ontology/v1/subway/datasets/{dataset_id}/activate')
    async def activate(dataset_id:str,request:Request):return await call(request,'activate',dataset_id)
    @app.post('/business-ontology/v1/subway/datasets/{dataset_id}/retire')
    async def retire(dataset_id:str,request:Request):return await call(request,'retire',dataset_id)
    @app.post('/business-ontology/v1/subway/datasets/{dataset_id}/cleanup')
    async def cleanup(dataset_id:str,request:Request):return await call(request,'cleanup',dataset_id)
    @app.post('/business-ontology/v1/subway/datasets/{dataset_id}/restore')
    async def restore(dataset_id:str,request:Request):return await call(request,'restore',dataset_id)
