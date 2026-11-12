"""Persistent Subway modeled data via the existing full-data query executor.

The adapter is a real SQLite source, not a fixture or a model-output substitute.
It implements only the read cursor contract used by the existing query tools.
"""
from contextlib import contextmanager
from copy import deepcopy
from datetime import datetime
from hashlib import sha256
import json,re
from types import SimpleNamespace

from .business_knowledge_model import digest
from .service import ApiFailure
from .subway_queries import SubwayQueries, key
from .subway_demo_data import DATASET,VERSION,SCOPE,LABEL,POLICY,generate

PREFIX=re.compile(r'^\s*use\s+subway\s+(?:demonstration|demo)\s+dataset\s+v1\s*(?:[.!:;\n]|$)',re.I)

def selected(objective):return bool(PREFIX.match(objective or ''))
def deny(message):raise ApiFailure('SUBWAY_DEMO_DENIED',message,403)
def authorize(auth):
    if (auth.get('subject',{}).get('workspace_id'),auth.get('subject',{}).get('subject_id'))!=SCOPE:deny('Demonstration data belongs only to Subway.')

def descriptor(document):return {k:deepcopy(document[k]) for k in ('dataset_id','revision','sha256','mode','label','as_of')}

def install(store,auth,base_version):
    authorize(auth);document=generate();ontology=build_ontology(base_version,document)
    from .business_compiler import check_snapshot
    check_snapshot(ontology)
    with store.transaction() as db:
        db.execute('CREATE TABLE IF NOT EXISTS subway_demo_datasets (workspace TEXT,owner TEXT,dataset_id TEXT,document TEXT,PRIMARY KEY(workspace,owner,dataset_id))')
        db.execute('CREATE TABLE IF NOT EXISTS subway_demo_records (workspace TEXT,owner TEXT,dataset_id TEXT,collection TEXT,native_id TEXT,document TEXT,PRIMARY KEY(workspace,owner,dataset_id,collection,native_id))')
        existing=db.execute('SELECT document FROM subway_demo_datasets WHERE workspace=? AND owner=? AND dataset_id=?',(*SCOPE,DATASET)).fetchone()
        if existing:
            old=json.loads(existing[0])
            if old['sha256']!=document['sha256']:raise ApiFailure('SUBWAY_DEMO_CONFLICT','A published demonstration version is immutable.',409)
        else:
            for collection,rows in document['records'].items():
                for row in rows:db.execute('INSERT INTO subway_demo_records VALUES (?,?,?,?,?,?)',(*SCOPE,DATASET,collection,str(row['_id']),json.dumps(row)))
            header={k:v for k,v in document.items() if k!='records'}
            header['record_hashes']={c:[digest(r) for r in rows] for c,rows in document['records'].items()}
            db.execute('INSERT INTO subway_demo_datasets VALUES (?,?,?,?)',(*SCOPE,DATASET,json.dumps(header)))
        old=db.execute('SELECT document FROM business_ontology_versions WHERE workspace=? AND owner=? AND version_id=?',(*SCOPE,VERSION)).fetchone()
        if old and digest(json.loads(old[0]))!=digest(ontology):raise ApiFailure('SUBWAY_DEMO_CONFLICT','Demonstration ontology version changed.',409)
        if not old:db.execute('INSERT INTO business_ontology_versions VALUES (?,?,?,?)',(*SCOPE,VERSION,json.dumps(ontology)))
    return descriptor(document)

def read(store,auth):
    authorize(auth)
    with store.transaction(write=False) as db:
        if not db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='subway_demo_datasets'").fetchone():raise ApiFailure('SUBWAY_DEMO_UNAVAILABLE','Demonstration data is not provisioned.',409)
        row=db.execute('SELECT document FROM subway_demo_datasets WHERE workspace=? AND owner=? AND dataset_id=?',(*SCOPE,DATASET)).fetchone()
        if not row:raise ApiFailure('SUBWAY_DEMO_UNAVAILABLE','Provision Subway demonstration dataset v1 before selecting it.',409)
        header=json.loads(row[0]);records={}
        for collection,raw in db.execute('SELECT collection,document FROM subway_demo_records WHERE workspace=? AND owner=? AND dataset_id=? ORDER BY collection,native_id',(*SCOPE,DATASET)):
            records.setdefault(collection,[]).append(json.loads(raw))
    hashes={c:sorted(digest(r) for r in rows) for c,rows in records.items()}
    if hashes!={c:sorted(rows) for c,rows in header['record_hashes'].items()}:raise ApiFailure('SUBWAY_DEMO_INTEGRITY','Persisted demo records differ from their immutable manifest.',409)
    document={k:v for k,v in header.items() if k not in ('record_hashes','sha256')};document['records']=records
    # The manifest also binds record order; normalize back to deterministic native ID order.
    for rows in records.values():rows.sort(key=lambda r:r['_id'])
    expected=generate()
    if header['sha256']!=expected['sha256'] or any(sorted(digest(r) for r in records[c])!=sorted(digest(r) for r in expected['records'][c]) for c in records):
        raise ApiFailure('SUBWAY_DEMO_INTEGRITY','Demo version/policy manifest mismatch.',409)
    return header,records

def infer(value):
    if value is None:return 'null'
    if type(value) is bool:return 'boolean'
    if type(value) is int:return 'integer'
    if type(value) is float:return 'number'
    if isinstance(value,str) and re.match(r'^\d{4}-\d{2}-\d{2}T',value):return 'datetime'
    return 'string' if isinstance(value,str) else 'array' if isinstance(value,list) else 'object'

def fields(rows):
    names={k for r in rows for k,v in r.items() if not isinstance(v,(list,dict))}
    return [dict(name=n,types=sorted({infer(r.get(n)) for r in rows}),field_id='') for n in sorted(names)]

def build_ontology(base,document):
    v=deepcopy(base);v.update(version_id=VERSION,revision=0,created_at='2026-11-12T00:00:00+00:00',demo_context=descriptor(document),base_version_id=base['version_id'])
    v['workspace']['sources']={'central':'demo_central','finance':'demo_finance'}
    for c in v['concepts']:
        if c.get('dump_mapping'):c['dump_mapping']['connection_id']='demo_'+c['dump_mapping']['role']
    text=LABEL+'\nModeled procurement schema includes persistent requisitions, approvals and histories, reservations and allocations, invoice items/currency/due dates/payment details, explicit store/location and supplier mappings.\nModeled policy: absolute invoice tolerance 5 currency units; second approval stage for amounts above 5000; approval delay review after 7 days. These are illustrative policies, not company authority.'
    src=dict(source_id='subway_demo_model_v1',kind='evidence',origin='modeled_demonstration',title=LABEL,module_ids=['procurement','receipts','budgets','organization','approvals'],text=text,sha256=sha256(text.encode()).hexdigest())
    v['sources'].append(src);by={(c.get('dump_mapping',{}).get('role'),c.get('dump_mapping',{}).get('collection')):c for c in v['concepts']}
    for label,rows in document['records'].items():
        role,col=label.split('.');c=by.get((role,col))
        if not c:
            mid='procurement' if col=='purchaserequests' else 'budgets' if col in ('reservations','allocations') else 'receipts' if col in ('invoiceitems','payments') else 'organization'
            c=deepcopy(next(c for c in v['concepts'] if c['id']=='procurement:finance_purchaseorders'))
            c.update(id=mid+':demo_'+col,module_id=mid,label='Demonstration '+col,parent_id='evidence:business_record',code_provenance=[],dump_mapping=dict(role=role,collection=col,connection_id='demo_'+role),declared_fields=[])
            v['concepts'].append(c);by[(role,col)]=c
        c.update(definition=LABEL+' Dataset '+label+'.',evidence=[dict(source_id=src['source_id'],quote=LABEL)],unknowns=['Modeled demonstration data, never operational evidence.'])
        c['properties']=[dict(name=f['name'],datatype='datetime' if 'datetime' in f['types'] else 'integer' if 'integer' in f['types'] else 'boolean' if 'boolean' in f['types'] else 'string',required=f['name']=='_id',description='Generated demonstration field; not a production schema assertion.') for f in fields(rows)][:20]
        c['declared_fields']=[dict(name=f['name'],type='Number' if 'integer' in f['types'] else 'Date' if 'datetime' in f['types'] else 'String') for f in fields(rows)]
    edges=[('finance.purchaseorders','purchaseRequestId','finance.purchaserequests'),('finance.purchaseorders','vendorId','central.vendors'),('finance.locations','storeId','central.stores'),('finance.budgets','site','finance.locations'),('finance.storemappings','centralStoreId','central.stores'),('finance.storemappings','financeLocationId','finance.locations'),('finance.suppliermappings','centralVendorId','central.vendors'),('finance.invoiceitems','invoiceId','finance.invoicedatas'),('finance.invoiceitems','poId','finance.purchaseorders'),('finance.payments','invoiceId','finance.invoicedatas'),('finance.reservations','purchaseRequestId','finance.purchaserequests'),('finance.reservations','lineItemId','finance.lineitems'),('finance.allocations','budgetId','finance.budgets'),('finance.purchaserequests','approvalId','finance.approvals')]
    for i,(a,field,b) in enumerate(edges):
        source=by[tuple(a.split('.'))];target=by[tuple(b.split('.'))];mid=source['module_id']
        v['relationships'].append(dict(id=mid+':demo_reference_'+str(i),module_id=mid,label='Demo '+a+' '+field+' '+b,definition='Explicit modeled reference '+a+'.'+field+' → '+b+'._id. '+LABEL,layer='domain',source=source['id'],target=target['id'],predicate='demo_ref_'+field.lower(),source_field=field,evidence=[dict(source_id=src['source_id'],quote=LABEL)],confidence=1,status='draft',unknowns=['Applicable only to the selected demonstration dataset.']))
    from .subway_demo_assessment import rules
    for rule in rules():
        entity=by[('finance',rule['entity'])];mid=entity['module_id']
        v['rules'].append(dict(id=mid+':demo_'+rule['id'].split(':')[1],label=rule['label'],definition=LABEL+' Deterministic rule '+rule['id']+'.',module_id=mid,layer='business',inputs=[entity['id']],conditions=[rule['business_purpose']],outcome='Analytical PASS/FAIL/INSUFFICIENT_EVIDENCE under modeled policy only.',basis='proposed_logic',evidence=[dict(source_id=src['source_id'],quote=LABEL)],confidence=1,unknowns=['Not an official company policy.'],status='draft',executable=False))
    return v

class Cursor:
    def __init__(self,rows):self.rows=rows
    def batch_size(self,n):return self
    def max_time_ms(self,n):return self
    def sort(self,columns):
        for name,direction in reversed(columns):self.rows.sort(key=lambda r:(r.get(name) is not None,key(r.get(name))),reverse=direction<0)
        return self
    def __iter__(self):return iter(self.rows)
    def close(self):pass
class Collection:
    def __init__(self,rows):self.rows=rows
    def find(self,query,projection):
        if query and any(not isinstance(v,dict) or set(v)!={'$in'} for v in query.values()):deny('Unsupported demonstration source predicate.')
        selected=[deepcopy(r) for r in self.rows if all(r.get(k) in v['$in'] for k,v in query.items())]
        def date_value(v):return datetime.fromisoformat(v.replace('Z','+00:00')) if isinstance(v,str) and re.match(r'^\d{4}-\d{2}-\d{2}T',v) else v
        return Cursor([{k:date_value(v) for k,v in r.items() if k in projection} for r in selected])
class Database:
    def __init__(self,rows):self.rows=rows
    def __getitem__(self,col):return Collection(self.rows.get(col,[]))
class DemoAdapter:
    def __init__(self,queries):self.queries=queries
    @contextmanager
    def connection(self,config):
        header,records=read(self.queries.store,self.queries.auth)
        yield {role:Database({c.split('.')[1]:rows for c,rows in records.items() if c.startswith(role+'.')}) for role in ('central','finance')}
    def business_freshness(self,config):return dict(status='modeled_demonstration',source_version=self.queries.demo_context['sha256'],refresh_available=False)
class Cipher:
    def decrypt(self,value):return value
class DemoSources:
    def __init__(self,queries):self.queries=queries;self.manager=SimpleNamespace(cipher=Cipher(),adapter=DemoAdapter(queries))
    def bound(self,db,auth,cid):
        authorize(auth)
        if cid not in ('demo_central','demo_finance'):deny('Historical source bindings are unavailable in demo context.')
        return None,json.dumps(dict(database=cid.removeprefix('demo_'),demo_dataset=DATASET)),None,None

class DemoQueries(SubwayQueries):
    def __init__(self,real,auth):
        real.authorize(auth);self.real=real;self.app=real.app;self.service=real.service;self.store=real.store;self.auth=deepcopy(auth)
        self.header,self.records=read(self.store,auth);self.demo_context=descriptor(self.header)
        self.version=self.app.state.business_ontology.version(auth,VERSION)
        self.sources=DemoSources(self)
    def authorize(self,auth):self.real.authorize(auth);authorize(auth)
    def for_workflow(self,workflow,auth):return from_workflow(self.real,workflow,auth)
    def procurement_bundle(self):
        b=deepcopy(self.real.procurement_bundle())
        from .subway_demo_assessment import rules
        b['structured_rules']+=rules()
        for state in b['state_models']:state['values']=[v for v in state['values'] if v['raw'] in ('created','draft','approval_in_progress','approved','rejected','reconsider','cancelled')]
        b.update(extension_version='subway-demo-procurement-v1',demo_policy=deepcopy(POLICY),unresolved=[],definition_sha256=digest(self.version));b['sha256']=digest({k:v for k,v in b.items() if k!='sha256'});return b
    def source_catalog(self,auth):
        self.authorize(auth);header,records=read(self.store,auth);datasets={};fs={};by={}
        for label,rows in records.items():
            role,col=label.split('.');did='demo_v1_'+role+'_'+col;by[(role,col)]=did
            fields_=[]
            for f in fields(rows):
                f['field_id']=did+'_'+f['name'];fields_.append(f);fs[f['field_id']]={**f,'dataset_id':did}
            datasets[did]=dict(dataset_id=did,connection_id='demo_'+role,role=role,collection=col,label=label,generation=1,metadata_revision=1,fields=fields_)
        concepts={c['id']:c for c in self.version['concepts']};rels={}
        for r in self.version['relationships']:
            a=concepts[r['source']].get('dump_mapping',{});b=concepts[r['target']].get('dump_mapping',{});left=by.get((a.get('role'),a.get('collection')));right=by.get((b.get('role'),b.get('collection')));path=r.get('source_field','')
            if not left or not right or '[]' in path:continue
            src=next((f['field_id'] for f in datasets[left]['fields'] if f['name']==path),None);dst=next((f['field_id'] for f in datasets[right]['fields'] if f['name']=='_id'),None)
            if src and dst:rels[r['id']]=dict(relationship_id=r['id'],source_dataset_id=left,target_dataset_id=right,source_field_id=src,target_field_id=dst,join_kind='left',reference_conversion='native',label=r['label'],definition=r['definition'])
        return dict(datasets=datasets,fields=fs,relationships=rels,stamps=dict(demonstration=dict(generation=1,metadata_revision=1,dataset_sha256=header['sha256'])))
    def discovery(self,auth,objective='',*,max_bytes=180000):
        d=super().discovery(auth,objective,max_bytes=max_bytes);d['demo_context']=deepcopy(self.demo_context);d['modeled_policy']=deepcopy(POLICY);d['guidance']+=' '+LABEL+' All requested comparisons are analytical under the explicit modeled policy. Use subway_assess for deterministic investigations; do not request unavailable real-company policies.';return d
    def planning_view(self,*args,**kwargs):
        d=super().planning_view(*args,**kwargs);d['demo_context']=deepcopy(self.demo_context);return d
    def knowledge(self,auth,objective,selection=None):
        c,k=super().knowledge(auth,objective,selection);k['demo_context']=deepcopy(self.demo_context);k['modeled_policy']=deepcopy(POLICY)
        k['procurement_knowledge']['unresolved']=[]
        k['procurement_knowledge']['execution']+=' '+LABEL+' The selected persistent data includes requisitions, invoice items, currencies, due dates, payments and modeled mappings. Use tool.subway_assess for deterministic investigations and explicitly cite the modeled policy; no additional company policy is required for a demo.'
        while len(json.dumps(k,separators=(',',':'),ensure_ascii=True).encode())>69800 and len(k.get('references',[]))>1:
            k['references'].pop();k['truncated']=True
        k['retrieval_sha256']=digest({a:b for a,b in k.items() if a!='retrieval_sha256'});return c,k
    def validate(self,query,catalog):
        result=super().validate(query,catalog)
        for metric in query['metrics']:
            if metric['field_id'] and metric['op'] in ('sum','avg') and catalog['fields'][metric['field_id']]['dataset_id']!=query['base_dataset_id']:
                raise ApiFailure('SUBWAY_DEMO_GRAIN','Aggregate header measures from their native base dataset, not repeated joined child rows.',422)
        return result
    def execute(self,auth,query):
        # Reuse the complete existing filter/join/aggregation/receipt executor.
        output=super().execute(auth,query)
        # Context is carried inside persisted coverage so adaptive verification
        # binds the demonstration label as part of the original receipt.
        return output

def from_workflow(real,workflow,auth):
    pin=workflow.get('metadata',{}).get('action_binding_context',{}).get('validated_context',{}).get('demo_context')
    if not pin:return real
    q=DemoQueries(real,auth)
    if pin!=q.demo_context:raise ApiFailure('SUBWAY_DEMO_STALE','The reviewed demo dataset pin changed.',409)
    return q
