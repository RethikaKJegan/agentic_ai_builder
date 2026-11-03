"""Explicit bounded source-record graph. No identity merge or policy execution."""
from copy import deepcopy
from contextlib import ExitStack, nullcontext
from datetime import date, datetime
from decimal import Decimal
from hashlib import sha256
import json
from pathlib import Path
import re
import secrets
from threading import Lock
import time
from urllib.parse import quote

from registry.safety import reject_secrets
from .business_compiler import canonical, dependencies, turtle, VOCAB_IRI
from .business_ontology import identity
from .business_rules import compilation_problem
from .data_write_adapter import pack, public_record, value_for
from .google_connections import now
from .service import ApiFailure

MAPPING_VERSION='simpson-source-graph-v2'
INVENTORY=Path(__file__).resolve().parents[1]/'ontology/business-reference/source-mappings.json'
SERIAL={'enginedetails':'engineSerialNumber','tickets':'engineNo','claims':'engineSerialNumber','claimsftps':'engineSerialNumber','failedengineanalyses':'engineSerialNumber'}
CHILDREN={'jointinspectionreports':'ticketId','enginereplacements':'ticket','partreplacements':'ticket','floatengines':'ticketId','focs':'ticket'}
MODULES={'oemnames':['organization'],'oems':['organization'],'enginedetails':['engines','warranty'],'tickets':['complaints','warranty'],
 'jointinspectionreports':['inspection'],'enginereplacements':['replacement'],'partreplacements':['replacement'],'floatengines':['replacement'],
 'focs':['replacement','warranty'],'workorders':['replacement','quality'],'internalcutins':['effectivity'],'servicebulletins':['effectivity'],
 'serviceinformations':['effectivity'],'claims':['warranty'],'claimsftps':['warranty'],'failedengineanalyses':['quality','failure'],
 'failedpartanalyses':['quality','failure'],'icacapas':['capa'],'products':['engines'],'floatengineftps':['engines','replacement'],'jirlogs':['inspection','evidence']}
EXCLUDED={'photos','documents','attachments','serviceMaintenanceRecord','listData','plantDetails','cutInDetails'}
STAGES={'engine':['enginedetails'],'complaint':['tickets'],'inspection':['jointinspectionreports'],'replacement':['enginereplacements','partreplacements','floatengines','focs'],'claims':['claims','claimsftps'],'quality':['failedengineanalyses'],'engineering_change':['internalcutins'],'capa':['icacapas']}


def fail(message,code='BUSINESS_GRAPH_INVALID',status=422):raise ApiFailure(code,message,status)
def digest(value):return sha256(canonical(value).encode()).hexdigest()
def safe_name(name):return bool(re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z_][A-Za-z0-9_]*)*',name)) and not re.search('password|secret|token|credential|private.?key|api.?key',name,re.I)
def scalar_field(field):
    return safe_name(field['name']) and len(set(field.get('types',[]))-{'null'})==1 and next(iter(set(field['types'])-{'null'}),'') in {'string','ObjectId','integer','number','boolean','date','datetime','Decimal128','decimal','numeric'}
_MISSING=object()
def at(row,path,missing=None):
    if path in row:return row[path]
    current=row
    for part in path.split('.'):
        if not isinstance(current,dict) or part not in current:return missing
        current=current[part]
    return current

def specs():
    inventory=json.loads(INVENTORY.read_text())
    return [dict(mapping_id=m['collection'],label=m['label'],role=m['role'],collection=m['collection'],modules=MODULES[m['collection']],fields=[f for f in m['fields'] if f not in EXCLUDED and safe_name(f)]) for m in inventory['items']]


class GraphReader:
    def __init__(self,manager):self.manager=manager
    def read(self,config,collection,fields,query,deadline):
        if time.monotonic()>=deadline:fail('Source graph deadline exceeded.','BUSINESS_GRAPH_TIMEOUT',504)
        from pymongo import timeout
        with (nullcontext(config['_graph_client']) if '_graph_client' in config else self.manager.adapter.connection(config)) as client,timeout(max(.001,min(8,deadline-time.monotonic()))):
            cursor=client[config['database']][collection].find(query,{f:1 for f in fields}).sort([('_id',1)]).limit(21).batch_size(21).max_time_ms(3000)
            try:rows=[{f:at(row,f) for f in fields if at(row,f,_MISSING) is not _MISSING} for row in cursor]
            finally:cursor.close()
        if time.monotonic()>=deadline:fail('Source graph deadline exceeded.','BUSINESS_GRAPH_TIMEOUT',504)
        return rows


def render_graph(snapshot,compilation,bindings,records,edges,outcomes,unresolved):
    Graph,Literal,Namespace,URIRef,_,_,RDF,_,SH,XSD,validate=dependencies()
    graph=Graph();v=Namespace(VOCAB_IRI);ns=snapshot['workspace']['namespace'];concepts={c['id']:c for c in snapshot['concepts']}
    conversion_issues=[];mapped=0
    for record in records:
        node=URIRef(ns+'record:'+record['node_id'])
        graph.add((node,RDF.type,v.SourceRecord));graph.add((node,v.sourceCollection,Literal(record['collection'])))
        graph.add((node,v.sourceRole,Literal(record['role'])));graph.add((node,v.sourceRecordHash,Literal(record['record_sha256'])))
        binding=bindings.get(record['collection'])
        if not binding:continue
        mapped+=1;cid=binding['concept_id'];graph.add((node,RDF.type,URIRef(ns+'concept:'+quote(cid,safe=''))))
        props={p['name']:p for p in concepts[cid]['properties']}
        for name,field in binding['attributes'].items():
            cell=next((c for c in record['fields'] if c['name']==field),None)
            if not cell or cell['state']!='value':continue
            value=cell['value'];kind=props[name]['datatype']
            try:
                if kind in ('string','enumeration'):
                    if not isinstance(value,str):raise ValueError()
                    lit=Literal(value,datatype=XSD.string)
                elif kind=='integer':
                    if isinstance(value,bool) or not re.fullmatch(r'-?\d{1,16}',str(value)) or abs(int(value))>9007199254740991:raise ValueError()
                    lit=Literal(int(value),datatype=XSD.integer)
                elif kind=='decimal':
                    number=Decimal(str(value))
                    if isinstance(value,bool) or not number.is_finite():raise ValueError()
                    lit=Literal(number,datatype=XSD.decimal)
                elif kind=='boolean':
                    if type(value) is not bool:raise ValueError()
                    lit=Literal(value,datatype=XSD.boolean)
                elif kind=='date':lit=Literal(date.fromisoformat(str(value)),datatype=XSD.date)
                elif kind=='datetime':
                    parsed=datetime.fromisoformat(str(value).replace('Z','+00:00'))
                    if parsed.tzinfo is None:raise ValueError()
                    lit=Literal(parsed,datatype=XSD.dateTime)
                else:raise ValueError('Reference target not bound')
                graph.add((node,URIRef(ns+'attribute:'+quote(cid,safe='')+':'+quote(name,safe='')),lit))
            except Exception:conversion_issues.append(dict(node_id=record['node_id'],attribute=name,field=field,reason='Value cannot be converted to the declared datatype or reference target.'))
    for edge in edges:
        graph.add((URIRef(ns+'record:'+edge['source']),v[edge['predicate']],URIRef(ns+'record:'+edge['target'])))
    artifacts={a['name']:a for a in compilation['artifacts']}
    shape_artifact=artifacts['instance-shapes.ttl']
    if sha256(shape_artifact['content'].encode()).hexdigest()!=shape_artifact['sha256']:fail('Saved instance shapes failed integrity checks.','BUSINESS_GRAPH_STALE',409)
    shapes=Graph().parse(data=shape_artifact['content'],format='turtle')
    ontology=Graph().parse(data=artifacts['ontology.ttl']['content'],format='turtle')
    conforms,report,_=validate(graph,shacl_graph=shapes,ont_graph=ontology,inference='none',advanced=False,js=False,do_owl_imports=False)
    issues=[dict(focus=str(report.value(n,SH.focusNode) or ''),path=str(report.value(n,SH.resultPath) or ''),message=str(report.value(n,SH.resultMessage) or 'Mapped instance constraint failed.')) for n in report.subjects(RDF.type,SH.ValidationResult)]
    validation=dict(status='passed' if mapped and conforms and not conversion_issues else 'failed' if mapped else 'not_run',mapped_records=mapped,conforms=bool(conforms) if mapped else None,issues=issues,conversion_issues=conversion_issues,business_policy_verified=False,mapping_meaning_verified=False)
    coverage=[dict(stage=stage,records=sum(r['collection'] in collections for r in records),collections=collections) for stage,collections in STAGES.items()]
    return dict(records=records,edges=edges,outcomes=outcomes,unresolved=unresolved,coverage=coverage,validation=validation,
        monitoring=dict(status='unavailable',missing=['Verified change applicability and incorporation','Comparable confirmed failures','Operating exposure and population denominators']),
        warranty_evaluation='not_run',physical_engine_identity='unresolved',rdf=turtle(graph),shacl_report=turtle(report),
        warnings=['Bounded exact-serial search, not a complete engine history or population.','Sources were read independently; no shared cross-database or historical snapshot.','Candidate serial/scope matches do not prove physical-engine identity, change incorporation or recurrence.'])


class BusinessGraph:
    def __init__(self,ontology,compiler,manager,resolve,reader=None):
        self.ontology=ontology;self.compiler=compiler;self.manager=manager;self.store=ontology.store;self.resolve=resolve
        self.reader=reader or GraphReader(manager);self.lock=Lock();self.active=set()
        with self.store.transaction() as db:
            db.execute('CREATE TABLE IF NOT EXISTS business_ontology_graphs (workspace TEXT NOT NULL, owner TEXT NOT NULL, version_id TEXT NOT NULL, graph_id TEXT NOT NULL, request_key TEXT NOT NULL, fingerprint TEXT NOT NULL, document TEXT NOT NULL, PRIMARY KEY(workspace,owner,graph_id), UNIQUE(workspace,owner,request_key))')

    def authority(self,auth,write=False):
        scope=identity(auth,write);current=self.resolve(*scope) if self.resolve else auth
        if not current or current.get('subject')!=auth['subject']:fail('Current graph access is unavailable.','OPERATION_NOT_AUTHORIZED',403)
        identity(current,write);return scope

    def context(self,auth,version_id,decrypt=False):
        scope=self.authority(auth,decrypt);snapshot=self.ontology.version(auth,version_id)
        with self.store.transaction(write=False) as db:
            workspace=self.ontology.document(db,scope)
            if not workspace or workspace['sources']!=snapshot['workspace']['sources']:fail('Source bindings changed.','BUSINESS_GRAPH_STALE',409)
            sources={};stamps={}
            for role,cid in workspace['sources'].items():
                secret,connection=self.manager.owned(db,auth,cid)
                row=db.execute('SELECT document FROM data_source_snapshots WHERE connection_id=? AND revision=?',(cid,connection['metadata_revision'])).fetchone()
                metadata=json.loads(row[0]) if row else {'datasets':[]}
                stamps[role]=digest([connection,secret,metadata])
                source=dict(connection_id=cid,name=connection.get('name',''),revision=connection['metadata_revision'],generation=connection.get('generation'),connected=connection.get('connection_status')=='connected',datasets=metadata['datasets'])
                if decrypt:
                    self.manager.configured()
                    if not secret or not source['connected']:fail('Both mapped sources must remain connected.','BUSINESS_SOURCE_UNAVAILABLE',409)
                    try:source['config']=json.loads(self.manager.cipher.decrypt(secret.encode()))
                    except Exception:fail('Source credentials are unavailable.','BUSINESS_SOURCE_UNAVAILABLE',409)
                    if source['config'].get('engine')!='mongodb':fail('MongoDB sources required.')
                sources[role]=source
        mappings=[]
        for spec in specs():
            source=sources[spec['role']];dataset=next((d for d in source['datasets'] if d.get('name')==spec['collection']),None)
            fields=[dict(name=f['name'],types=f['types']) for f in (dataset or {}).get('fields',[]) if f['name'] in spec['fields'] and scalar_field(f)]
            ready=source['connected'] and any(f['name']=='_id' for f in fields)
            mappings.append({**spec,'fields':fields,'available':ready,'reason':None if ready else 'Connected source, current collection metadata and scalar native _id are required.'})
        compilation=self.compiler.get(auth,version_id)['compilation'];problem=compilation_problem(snapshot,compilation)
        if not problem and not all(s['connected'] for s in sources.values()):problem='Both bound sources must remain connected.'
        if not problem and not any(m['available'] for m in mappings):problem='Refresh source metadata before configuring graph mappings.'
        plan_hash=digest([MAPPING_VERSION,snapshot,stamps,mappings])
        return snapshot,compilation,sources,stamps,dict(version_id=version_id,mapping_version=MAPPING_VERSION,plan_hash=plan_hash,mappings=mappings,available=problem is None,unavailable_reason=problem,configured=bool(self.manager.cipher))

    def plan(self,auth,version_id):
        _,_,_,_,plan=self.context(auth,version_id)
        scope=identity(auth)
        with self.store.transaction(write=False) as db:rows=db.execute('SELECT graph_id,document FROM business_ontology_graphs WHERE workspace=? AND owner=? AND version_id=?',(*scope,version_id)).fetchall()
        plan['snapshots']=sorted([dict(graph_id=gid,created_at=d['created_at'],serial=d['serial'],records=len(d['records']),version_id=version_id) for gid,raw in rows for d in [json.loads(raw)]],key=lambda d:d['created_at'],reverse=True)
        return plan

    def get(self,auth,version_id,graph_id):
        scope=self.authority(auth);self.ontology.version(auth,version_id)
        with self.store.transaction(write=False) as db:row=db.execute('SELECT document FROM business_ontology_graphs WHERE workspace=? AND owner=? AND version_id=? AND graph_id=?',(*scope,version_id,graph_id)).fetchone()
        if not row:fail('Graph snapshot not found.','BUSINESS_GRAPH_NOT_FOUND',404)
        return json.loads(row[0])

    def build(self,auth,version_id,body):
        scope=self.authority(auth,True)
        if (not isinstance(body,dict) or set(body)!={'plan_hash','serial','bindings','request_key'} or not isinstance(body['plan_hash'],str)
            or not isinstance(body['serial'],str) or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9 /_.-]{0,79}',body['serial'])
            or body['serial']!=body['serial'].strip() or not isinstance(body['request_key'],str) or not re.fullmatch(r'[A-Za-z0-9_-]{8,100}',body['request_key'])
            or not isinstance(body['bindings'],dict) or not body['bindings']):fail('Choose a serial, current mapping plan, explicit concept/field bindings and request key.')
        fingerprint=digest([version_id,{k:body[k] for k in ('plan_hash','serial','bindings')}])
        with self.store.transaction(write=False) as db:old=db.execute('SELECT graph_id,fingerprint,version_id FROM business_ontology_graphs WHERE workspace=? AND owner=? AND request_key=?',(*scope,body['request_key'])).fetchone()
        if old:
            if old[1]!=fingerprint:fail('This request key belongs to a different graph.','IDEMPOTENCY_KEY_REUSED',409)
            return self.get(auth,version_id,old[0])
        with self.lock:
            if scope in self.active or len(self.active)>=2:fail('A graph build is already running.','BUSINESS_GRAPH_BUSY',429)
            self.active.add(scope)
        try:return self._build(auth,version_id,body,fingerprint)
        finally:
            with self.lock:self.active.discard(scope)

    def _build(self,auth,version_id,body,fingerprint):
        scope=self.authority(auth,True);snapshot,compilation,sources,stamps,plan=self.context(auth,version_id,True)
        if body['plan_hash']!=plan['plan_hash']:fail('Source metadata or mapping plan changed. Refresh first.','BUSINESS_GRAPH_STALE',409)
        if not plan['available']:fail(plan['unavailable_reason'],'BUSINESS_GRAPH_UNAVAILABLE',409)
        maps={m['mapping_id']:m for m in plan['mappings']};concepts={c['id']:c for c in snapshot['concepts']}
        for mid,binding in body['bindings'].items():
            if mid not in maps or not maps[mid]['available'] or not isinstance(binding,dict) or set(binding)!={'concept_id','attributes'} or not isinstance(binding['concept_id'],str) or not isinstance(binding['attributes'],dict):fail('Unsupported mapping binding.')
            concept=concepts.get(binding['concept_id']);fields={f['name'] for f in maps[mid]['fields']}
            if not concept or concept['module_id'] not in maps[mid]['modules'] or not set(binding['attributes'])<={p['name'] for p in concept['properties']} or any(not isinstance(f,str) or f not in fields for f in binding['attributes'].values()):fail('Select permitted concepts and scalar fields from this version.')
        with ExitStack() as stack:
            deadline=time.monotonic()+25;raw={};outcomes=[];records=[];unresolved=[];native_nodes={};read_started=now()
            def fetch(collection,field,values):
                spec=maps[collection];by_name={f['name']:f for f in spec['fields']}
                if not spec['available'] or field not in by_name:
                    outcomes.append(dict(collection=collection,role=spec['role'],status='unavailable',records=0,truncated=False));return
                native=[];seen=set()
                for value in values:
                    try:
                        converted=value_for(by_name[field],public_record(pack({'v':value},'mongodb'))['v']);token=digest(pack({'v':converted},'mongodb'))
                        if token not in seen:seen.add(token);native.append(converted)
                    except ApiFailure:continue
                domain_truncated=len(native)>20;native=native[:20]
                if not native:
                    outcomes.append(dict(collection=collection,role=spec['role'],status='no_usable_search_values',records=0,truncated=False));return
                self.authority(auth,True)
                try:
                    rows=self.reader.read(sources[spec['role']]['config'],collection,list(by_name),{field:{'$in':native}},deadline)
                except ApiFailure:raise
                except Exception:fail('A source read failed. No graph was saved.','BUSINESS_GRAPH_SOURCE_FAILED',502)
                if len(rows)>21:fail('Source exceeded the bounded read limit.')
                raw[collection]=rows[:20];outcomes.append(dict(collection=collection,role=spec['role'],status='matched' if rows else 'no_matches',records=min(len(rows),20),truncated=len(rows)>20 or domain_truncated))
            if isinstance(self.reader,GraphReader):
                for source in sources.values():source['config']['_graph_client']=stack.enter_context(self.manager.adapter.connection(source['config']))
            for collection,field in SERIAL.items():fetch(collection,field,[body['serial']])
            tickets=raw.get('tickets',[]);ticket_keys=[r['_id'] for r in tickets if r.get('_id') is not None]
            for collection,field in CHILDREN.items():fetch(collection,field,ticket_keys)
            fetch('oems','_id',[r['oem'] for r in tickets if r.get('oem') is not None])
            company_values=[r['oemOrg'] for r in tickets if r.get('oemOrg') is not None]
            company_values += [r['oem'] for r in raw.get('enginedetails',[]) if r.get('oem') is not None]
            company_values += [r['oemNameId'] for r in raw.get('oems',[]) if r.get('oemNameId') is not None]
            fetch('oemnames','_id',company_values)
            # Engineering scope evidence is only a candidate. OEM/model equality is
            # retained per edge; no serial-boundary or incorporation inference.
            invoice_rows=raw.get('enginedetails',[])+raw.get('failedengineanalyses',[])
            for collection in ('internalcutins','icacapas'):fetch(collection,'listNo',[r['listNo'] for r in invoice_rows if r.get('listNo') is not None])
            for collection,spec in maps.items():
                if collection not in {o['collection'] for o in outcomes}:outcomes.append(dict(collection=collection,role=spec['role'],status='not_in_serial_path',records=0,truncated=False))
            for collection,rows in raw.items():
                spec=maps[collection];cid=sources[spec['role']]['connection_id']
                for row in rows:
                    if row.get('_id') is None:fail('Source returned a missing native identity.','BUSINESS_GRAPH_IDENTITY',409)
                    key=pack({'_id':row['_id']},'mongodb');node_id=digest([cid,collection,key])
                    if node_id in native_nodes.values():fail('Source returned duplicate native identity.','BUSINESS_GRAPH_IDENTITY',409)
                    native_nodes[(collection,canonical(key))]=node_id
                    fields=[]
                    for field in spec['fields']:
                        name=field['name'];value=at(row,name);state='not_returned' if name not in row else 'not_recorded' if value is None else 'value'
                        try:value=public_record(pack({'v':value},'mongodb'))['v']
                        except ApiFailure:value=None;state='unsupported'
                        if isinstance(value,str) and len(value)>4096:value=None;state='over_limit'
                        item=dict(name=name,value=value,state=state)
                        if state=='value' and name in {'_id','oem','oemOrg','oemNameId','engineNo','engineSerialNumber','engineModal','engineModel','replacementEngineNumber','ticket','ticketId'}:
                            item['native_token']=digest(pack({'v':at(row,name)},'mongodb'))
                        fields.append(item)
                    reject_secrets(fields)
                    records.append(dict(node_id=node_id,role=spec['role'],connection_id=cid,collection=collection,key=public_record(key),fields=fields,record_sha256=digest(fields)))
            edges=[]
            def node(collection,row):return native_nodes[(collection,canonical(pack({'_id':row['_id']},'mongodb')))]
            def edge(a,b,predicate,classification,source_field=None):
                item=dict(source=a,target=b,predicate=predicate,classification=classification)
                if source_field is not None:item['source_field']=source_field
                edges.append(item)
            def resolve(collection,field,target):
                for row in raw.get(collection,[]):
                    value=row.get(field);matches=[r for r in raw.get(target,[]) if value is not None and pack({'v':value},'mongodb')==pack({'v':r['_id']},'mongodb')]
                    if len(matches)==1:edge(node(collection,row),node(target,matches[0]),'source_reference','source_reference',field)
                    else:unresolved.append(dict(node_id=node(collection,row),field=field,target_collection=target,state='not_recorded' if value is None else 'not_resolved_in_bounded_graph'))
            for collection,field in CHILDREN.items():resolve(collection,field,'tickets')
            resolve('tickets','oem','oems');resolve('tickets','oemOrg','oemnames')
            resolve('oems','oemNameId','oemnames');resolve('enginedetails','oem','oemnames')
            serial_records=[(c,r) for c,f in SERIAL.items() for r in raw.get(c,[]) if r.get(f)==body['serial']]
            # A star anchored to each invoice preserves ambiguity without quadratic
            # cross-source joins or collapsing independent record identities.
            anchors=[(c,r) for c,r in serial_records if c=='enginedetails'] or serial_records[:1]
            for ac,anchor in anchors:
                for bc,other in serial_records:
                    if (ac,anchor['_id'])!=(bc,other['_id']):edge(node(ac,anchor),node(bc,other),'candidate_serial_match','candidate')
            for collection in ('internalcutins','icacapas'):
                for row in raw.get(collection,[]):
                    for invoice in raw.get('enginedetails',[]):
                        if all(row.get(f) is not None and pack({'v':row[f]},'mongodb')==pack({'v':invoice.get(f)},'mongodb') for f in ('listNo','oem','engineModel')):
                            edge(node('enginedetails',invoice),node(collection,row),'candidate_scope_match','candidate')
                        else:unresolved.append(dict(node_id=node(collection,row),field='listNo/oem/engineModel',target_collection='enginedetails',state='scope_not_established'))
            result=render_graph(snapshot,compilation,body['bindings'],records,edges,outcomes,unresolved)
            self.authority(auth,True)
            _,_,_,after,after_plan=self.context(auth,version_id,True)
            if after!=stamps or after_plan['plan_hash']!=body['plan_hash']:fail('Source state changed during graph retrieval.','BUSINESS_GRAPH_STALE',409)
            if time.monotonic()>deadline:fail('Graph deadline exceeded.','BUSINESS_GRAPH_TIMEOUT',504)
            graph_id='bog_'+secrets.token_hex(16)
            document=dict(graph_id=graph_id,version_id=version_id,mapping_version=MAPPING_VERSION,created_at=now(),read_started_at=read_started,serial=body['serial'],bindings=body['bindings'],plan_hash=body['plan_hash'],source_stamps=stamps,source_revisions={role:source['revision'] for role,source in sources.items()},**result)
            if len(json.dumps(document).encode())>2_000_000:fail('Graph exceeds the 2 MB snapshot limit.')
            reject_secrets(document)
            with self.store.transaction() as db:
                self.authority(auth,True)
                version_row=db.execute('SELECT document FROM business_ontology_versions WHERE workspace=? AND owner=? AND version_id=?',(*scope,version_id)).fetchone()
                if not version_row or digest(json.loads(version_row[0]))!=digest(snapshot):fail('Definition version changed before graph save.','BUSINESS_GRAPH_STALE',409)
                for role,source in sources.items():
                    secret,current=self.manager.owned(db,auth,source['connection_id'])
                    row=db.execute('SELECT document FROM data_source_snapshots WHERE connection_id=? AND revision=?',(source['connection_id'],current['metadata_revision'])).fetchone()
                    metadata=json.loads(row[0]) if row else {'datasets':[]}
                    if digest([current,secret,metadata])!=stamps[role]:fail('Source state changed before graph save.','BUSINESS_GRAPH_STALE',409)
                inserted=db.execute('INSERT INTO business_ontology_graphs VALUES (?,?,?,?,?,?,?) ON CONFLICT DO NOTHING RETURNING graph_id',(*scope,version_id,graph_id,body['request_key'],fingerprint,json.dumps(document))).fetchone()
                if not inserted:
                    existing=db.execute('SELECT document,fingerprint FROM business_ontology_graphs WHERE workspace=? AND owner=? AND request_key=?',(*scope,body['request_key'])).fetchone()
                    if not existing or existing[1]!=fingerprint:fail('This request key belongs to a different graph.','IDEMPOTENCY_KEY_REUSED',409)
                    return json.loads(existing[0])
                db.execute('INSERT INTO business_ontology_events VALUES (?,?,?,?)',(*scope,'boe_'+secrets.token_hex(16),json.dumps(dict(action='build_source_graph',at=document['created_at'],version_id=version_id,graph_id=graph_id))))
            return document
