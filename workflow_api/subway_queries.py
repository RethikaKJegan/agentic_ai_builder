"""Tenant-pinned structured queries over complete restored Subway collections.

No SQL/Mongo source text, hidden model calls, writes or sample-based aggregates.
Read results are bounded; predicates and aggregates examine the complete source.
"""
from copy import deepcopy
from datetime import date,datetime,timezone
from decimal import Decimal,localcontext
import hashlib,json,time
import re
from uuid import uuid4
from pathlib import Path
from jsonschema import Draft202012Validator
from registry.safety import reject_secrets
from .service import ApiFailure
from .business_graph import at
from .business_sources import fields_for
from .business_compiler import canonical
from .google_connections import now

SCOPE={'workspace_id':'client-subway','subject_id':'subway-client'}
def obj(properties):return dict(type='object',properties=properties,required=list(properties),additionalProperties=False)
def arr(items,n):return dict(type='array',items=items,maxItems=n)
STR={'type':'string','maxLength':200}
QUERY=obj(dict(base_dataset_id=STR,joins=arr({'type':'string','maxLength':100},3),fields=arr(STR,24),filters=arr(obj(dict(field_id=STR,op={'type':'string','enum':['eq','ne','gt','gte','lt','lte','is_null','not_null']},value={'anyOf':[{'type':'string','maxLength':500},{'type':'number'},{'type':'boolean'},{'type':'null'}]})),20),group_by=arr(STR,6),metrics=arr(obj(dict(label={'type':'string','pattern':'^[a-zA-Z][a-zA-Z0-9_]{0,50}$'},op={'type':'string','enum':['count','sum','avg','min','max']},field_id=STR)),12),order_by=arr(obj(dict(column=STR,direction={'type':'string','enum':['asc','desc']})),3),offset={'type':'integer','minimum':0,'maximum':1000000},limit={'type':'integer','minimum':1,'maximum':500}))
INPUT=obj(dict(query=QUERY))
OUTPUT=obj(dict(query_id={'type':'string'},columns={'type':'array','items':{'type':'object'}},rows={'type':'array','items':{'type':'object'}},coverage={'type':'object'},sources={'type':'array','items':{'type':'object'}},join_checks={'type':'array','items':{'type':'object'}}))
PLAN_OUTPUT=obj(dict(query=QUERY))

def fail(message,code='SUBWAY_QUERY_INVALID',status=422):raise ApiFailure(code,message,status)
def key(value):
 from bson import ObjectId
 if value is None:return None
 if isinstance(value,ObjectId):return ('objectid',str(value))
 if type(value) in (int,float,Decimal):return ('number',Decimal(str(value)))
 if isinstance(value,(str,bool,datetime,date)):return (type(value).__name__,value)
 fail('Query requires a scalar value; choose a scalar path.','SUBWAY_QUERY_TYPE')
def scalar(value):
 from bson.decimal128 import Decimal128
 if isinstance(value,Decimal128):value=value.to_decimal()
 if isinstance(value,Decimal) and not value.is_finite():fail('Nonfinite source values cannot be used.','SUBWAY_QUERY_TYPE')
 if isinstance(value,(dict,list,bytes)):fail('Selected values are not scalar. Choose a scalar field.','SUBWAY_QUERY_TYPE')
 if isinstance(value,float) and not __import__('math').isfinite(value):fail('Nonfinite source values cannot be used.','SUBWAY_QUERY_TYPE')
 return value

def reference_key(value,conversion):
 # Match Mongoose's declared Number reference only for exact, safe integer IDs.
 # Never coerce arbitrary text IDs or guess identities across applications.
 if conversion=='schema_integer_reference' and isinstance(value,str) and re.fullmatch(r'[+-]?\d+(?:\.0+)?',value.strip()):
  number=Decimal(value.strip())
  if abs(number)<=9007199254740991:return key(int(number))
 return key(value)

def wire(value):
 if isinstance(value,Decimal):return str(value)
 if isinstance(value,(datetime,date)):return value.isoformat()
 from bson import ObjectId
 if isinstance(value,ObjectId):return str(value)
 return value

class SubwayQueries:
 def __init__(self,app,auth):
  self.app,self.auth=app,deepcopy(auth);self.service=app.state.workflow_service;self.sources=app.state.business_sources;self.store=self.service.store
  self.version=app.state.business_ontology.version(auth,'bov_subway_dump_v4')
  self.collection_scope={(c['role'],c['collection']) for c in self.version['dump_grounding']['correspondence']}
  from .subway_onboarding import build_package
  self.binding_stamps={b['connection_id']:(b['metadata_revision'],b['generation']) for b in build_package(self.version,4)['resource_bindings'].values()}
 def catalog(self,auth,objective=None):
  self.authorize(auth);datasets={};fields={};stamps={}
  with self.store.transaction(write=False) as db:
   for role in ('central','finance'):
    cid='dbconn_subway_'+role
    _,secret,conn,metadata=self.sources.bound(db,auth,cid)
    if not secret or conn['connection_status']!='connected' or conn.get('profiling_status')!='ready' or not metadata:fail('Subway source metadata is not ready.','SUBWAY_QUERY_STALE',409)
    if (conn['metadata_revision'],conn['generation'])!=self.binding_stamps[cid]:fail('Source differs from the reviewed Subway ontology bindings; refresh and review its definition before querying.','SUBWAY_QUERY_STALE',409)
    stamps[cid]=dict(generation=conn['generation'],metadata_revision=conn['metadata_revision'],secret_sha256=hashlib.sha256(secret.encode()).hexdigest())
    for ds in metadata['datasets']:
     if (role,ds['name']) not in self.collection_scope:continue
     fs=fields_for(ds,allow_report_labels=True)
     if not fs and ds['name']=='blogprojects' and ds.get('sample_count')==0:fs=[dict(field_id=ds['dataset_id']+'_native_id',name='_id',types=['ObjectId'])]
     did=ds['dataset_id'];datasets[did]=dict(dataset_id=did,connection_id=cid,role=role,collection=ds['name'],label=role+'.'+ds['name'],generation=conn['generation'],metadata_revision=conn['metadata_revision'],fields=deepcopy(fs))
     for f in fs:
      if f['field_id'] in fields:fail('Source field identifiers conflict.','SUBWAY_QUERY_STALE',409)
      fields[f['field_id']]={**deepcopy(f),'dataset_id':did}
  by_collection={(d['role'],d['collection']):did for did,d in datasets.items()};concepts={c['id']:c for c in self.version['concepts']};rels={}
  for r in self.version['relationships']:
   source=concepts[r['source']]['dump_mapping'];target=concepts[r['target']]['dump_mapping'];path=r['source_field']
   if '[]' in path:continue # fanout requires explicit grain, not accidental double counting
   left=by_collection[(source['role'],source['collection'])];right=by_collection[(target['role'],target['collection'])]
   src=next((f['field_id'] for f in datasets[left]['fields'] if f['name']==path),None);dst=next((f['field_id'] for f in datasets[right]['fields'] if f['name']=='_id'),None)
   if src and dst:
    numeric_ref=any(f['name']==path and f['type']=='Number' for f in concepts[r['source']].get('declared_fields',[]))
    numeric_target=set(fields[dst]['types'])-{'null'} <= {'integer'}
    conversion='schema_integer_reference' if numeric_ref and numeric_target else 'native'
    rels[r['id']]=dict(relationship_id=r['id'],source_dataset_id=left,target_dataset_id=right,source_field_id=src,target_field_id=dst,join_kind='left',reference_conversion=conversion,label=r['label'],definition=r['definition'])
  result=dict(datasets=datasets,fields=fields,relationships=rels,stamps=stamps)
  if objective is None:return result
  from .kg_retrieval import terms
  tokens=terms(objective);scored=[]
  if 'po' in tokens or re.search(r'\bPOs\b',objective):tokens|=terms('purchase order')
  for did,d in datasets.items():
   c=next(c for c in self.version['concepts'] if c.get('dump_mapping',{}).get('role')==d['role'] and c.get('dump_mapping',{}).get('collection')==d['collection'])
   score=6*len(tokens & terms(c['label']+' '+d['collection']))+max((len(tokens & terms(f['name'])) for f in d['fields']),default=0)
   scored.append((-score,did))
  selected_ids=[did for score,did in sorted(scored)[:4] if score<0];selected=set(selected_ids)
  view=[]
  for did in selected_ids:
   d=datasets[did];ranked=sorted(d['fields'],key=lambda f:(-int(f['name']=='_id'),-len(tokens & terms(f['name'])),f['name']))[:45]
   view.append({**{k:d[k] for k in ['dataset_id','label']},'fields':[{k:f[k] for k in ['field_id','name','types']} for f in ranked]})
  return dict(sources=view,relationships=[r for r in rels.values() if {r['source_dataset_id'],r['target_dataset_id']}<=selected],query_schema=QUERY,semantics='Filters examine all source rows. Aggregates use every matched row, never a 25-row sample. Use count with empty field_id for row counts; sum/avg require a numeric field. No arithmetic expressions. Group by currency before monetary totals across currencies. Joins preserve all base rows and report unmatched references; no array/fanout joins. Result limit controls display only; totals and matched counts are complete. Do not invent missing dates, currency, fields or business definitions.')
 def authorize(self,auth):
  if auth.get('subject')!=SCOPE:fail('Query is outside the Subway client.','SUBWAY_QUERY_DENIED',403)
  self.sources.authorize(auth)
  if 'workflow.execute' not in auth.get('permissions',[]):fail('Current execution permission required.','SUBWAY_QUERY_DENIED',403)
 def validate(self,query,catalog):
  if list(Draft202012Validator(QUERY).iter_errors(query)):fail('Supply the structured query schema; database source text is not supported.')
  reject_secrets(query)
  datasets=catalog['datasets'];fields=catalog['fields'];base=query['base_dataset_id'];selected={base};edges=[]
  if base not in datasets:fail('Base dataset is outside the current owned Subway catalog.','SUBWAY_QUERY_DENIED',403)
  for rid in query['joins']:
   r=catalog['relationships'].get(rid)
   if not r or r['source_dataset_id'] not in selected or r['target_dataset_id'] in selected:fail('Join must add an exact allowlisted scalar target to the current query scope.')
   selected.add(r['target_dataset_id']);edges.append(r)
  used=set(query['fields']+query['group_by']+[f['field_id'] for f in query['filters']]+[m['field_id'] for m in query['metrics'] if m['field_id']])
  if any(fid not in fields or fields[fid]['dataset_id'] not in selected for fid in used):fail('Selected fields are outside the query datasets.','SUBWAY_QUERY_DENIED',403)
  if len(query['fields'])!=len(set(query['fields'])) or len(query['group_by'])!=len(set(query['group_by'])):fail('Select each field once.')
  if query['metrics'] and query['fields'] or query['group_by'] and not query['metrics'] or not query['metrics'] and not query['fields']:fail('Use projected fields for details or metrics/group_by for aggregates.')
  labels=[m['label'] for m in query['metrics']]
  if len(labels)!=len(set(labels)) or set(labels)&set(query['group_by']):fail('Metric labels must be distinct from each other and group field IDs.')
  for metric in query['metrics']:
   if metric['op']!='count' and not metric['field_id']:fail('This metric requires an explicit field.')
  columns=query['group_by']+labels if labels else query['fields']
  if any(o['column'] not in columns for o in query['order_by']):fail('Sort columns must be selected output columns.')
  if not labels and any(fields[o['column']]['dataset_id']!=base for o in query['order_by']):fail('Detail sorting currently requires a base collection field; aggregate/group to sort joined measures.')
  return selected,edges,used
 def execute(self,auth,query):
  self.authorize(auth);before=self.catalog(auth);selected,edges,used=self.validate(query,before);start=time.monotonic();deadline=start+100
  fields=before['fields'];datasets=before['datasets'];base=query['base_dataset_id'];needed={did:set() for did in selected}
  for fid in used:needed[fields[fid]['dataset_id']].add(fid)
  for edge in edges:
   needed[edge['source_dataset_id']].add(edge['source_field_id']);needed[edge['target_dataset_id']].add(edge['target_field_id'])
  currency_guards={}
  for metric in query['metrics']:
   if metric['op'] not in {'sum','avg'}:continue
   measure=fields[metric['field_id']]
   if measure['name'].split('.')[-1] not in {'amount','totalAmount','invoiceAmount','price','updatedPrice','unitPrice','advanceAmount','balanceAmount'}:continue
   currency=next((f for f in datasets[measure['dataset_id']]['fields'] if f['name']=='currency'),None)
   if currency and currency['field_id'] not in query['group_by']:
    needed[measure['dataset_id']].add(currency['field_id']);currency_guards[currency['field_id']]=set()
  join_checks=[];lookup={};source_counts={};source_bytes=0
  def checkpoint():
   from .data_query_control import checkpoint as control
   control()
   if time.monotonic()>deadline:fail('Full query timed out; no partial answer returned.','SUBWAY_QUERY_TIMEOUT',504)
  def read(did):
   nonlocal source_bytes
   d=datasets[did];cid=d['connection_id']
   with self.store.transaction(write=False) as db:_,secret,_,_=self.sources.bound(db,auth,cid)
   config=json.loads(self.sources.manager.cipher.decrypt(secret.encode()))
   names={fields[fid]['name'] for fid in needed[did]}|{'_id'}
   with self.sources.manager.adapter.connection(config) as client:
    collection=client[config['database']][d['collection']]
    cursor=collection.find({},dict.fromkeys(names,1)).batch_size(500).max_time_ms(95000)
    sort=[(fields[o['column']]['name'],1 if o['direction']=='asc' else -1) for o in query['order_by']] if did==base and not query['metrics'] else []
    if not any(name=='_id' for name,_ in sort):sort.append(('_id',1))
    cursor=cursor.sort(sort);count=0
    try:
     for row in cursor:
      checkpoint();count+=1
      if count>2000000:fail('Full query exceeds its two-million-row source budget; narrow the source operation. No partial result returned.','SUBWAY_QUERY_LIMIT')
      values={fid:scalar(at(row,fields[fid]['name'])) for fid in needed[did]}
      source_bytes+=len(json.dumps({k:wire(v) for k,v in values.items()},default=str).encode())
      if source_bytes>256000000:fail('Full query exceeds its projected-data budget; choose fewer fields. No partial result returned.','SUBWAY_QUERY_LIMIT')
      yield row.get('_id'),values
    finally:cursor.close()
    source_counts[did]=count
  for edge in edges:
   did=edge['target_dataset_id'];index={};kfid=edge['target_field_id']
   for _,row in read(did):
    k=key(row[kfid])
    if k is None or k in index:fail('Relationship target IDs are not unique/non-null.','SUBWAY_QUERY_JOIN_INVALID')
    index[k]=row
   lookup[edge['relationship_id']]=index;join_checks.append(dict(relationship_id=edge['relationship_id'],matched_rows=0,missing_reference_rows=0,unmatched_reference_rows=0,normalized_reference_rows=0,reference_conversion=edge['reference_conversion'],target_rows=source_counts[did],join_kind='left'))
  def native_filter(f,value):
   types=set(f['types'])-{'null'}
   if value is None:return None
   if types&{'date','datetime','timestamp'}:
    if not isinstance(value,str):fail('Date filters require ISO strings.')
    try:
     parsed=datetime.fromisoformat(value.replace('Z','+00:00'))
     if parsed.tzinfo:parsed=parsed.astimezone(timezone.utc).replace(tzinfo=None)
     return parsed
    except ValueError:fail('Date filter is invalid.')
   if types=={'ObjectId'}:
    from bson import ObjectId
    try:return ObjectId(value)
    except Exception:fail('Object identifier filter is invalid.')
   if types <= {'integer','number','decimal','Decimal128','numeric'}:
    if type(value) not in (int,float):fail('Numeric filters require numeric values.')
    return Decimal(str(value))
   return value
  filters=[(f['field_id'],f['op'],native_filter(fields[f['field_id']],f['value'])) for f in query['filters']]
  def matches(row):
   for fid,op,value in filters:
    actual=row.get(fid)
    if op=='is_null':ok=actual is None
    elif op=='not_null':ok=actual is not None
    elif op=='eq':ok=key(actual)==key(value)
    elif op=='ne':ok=key(actual)!=key(value)
    elif actual is None:ok=False
    else:
     a,b=key(actual),key(value)
     if a[0]!=b[0]:fail('A filter encountered an incompatible source type.','SUBWAY_QUERY_TYPE')
     ok={'gt':lambda:a[1]>b[1],'gte':lambda:a[1]>=b[1],'lt':lambda:a[1]<b[1],'lte':lambda:a[1]<=b[1]}[op]()
    if not ok:return False
   return True
  matched=0;results=[];groups={};aggregate=bool(query['metrics']);offset=query['offset'];limit=query['limit']
  with localcontext() as ctx:
   ctx.prec=38
   for identity,row in read(base):
    for i,edge in enumerate(edges):
     original=row.get(edge['source_field_id']);k=reference_key(original,edge['reference_conversion']);target=lookup[edge['relationship_id']].get(k);check=join_checks[i]
     if k!=key(original):check['normalized_reference_rows']+=1
     check['matched_rows' if target is not None else 'missing_reference_rows' if k is None else 'unmatched_reference_rows']+=1
     row.update(target or dict.fromkeys(needed[edge['target_dataset_id']],None))
    if not matches(row):continue
    matched+=1
    for fid,currencies in currency_guards.items():
     currencies.add(key(row.get(fid)))
     if len(currencies)>1:fail('Monetary totals span different or missing currencies. Group by currency or filter one currency; no mixed-currency total returned.','SUBWAY_QUERY_CURRENCY')
    if not aggregate:
     if offset<matched<=offset+limit:results.append({fid:wire(row.get(fid)) for fid in query['fields']})
     continue
    group=tuple(key(row.get(fid)) for fid in query['group_by'])
    if group not in groups:
     if len(groups)>=10000:fail('Query has over 10,000 groups; refine grouping. No partial aggregate returned.','SUBWAY_QUERY_LIMIT')
     groups[group]=dict(values={fid:row.get(fid) for fid in query['group_by']},metrics={m['label']:dict(count=0,sum=Decimal(0),min=None,max=None) for m in query['metrics']})
    g=groups[group]
    for m in query['metrics']:
     value=row.get(m['field_id']) if m['field_id'] else 1;state=g['metrics'][m['label']]
     if value is None:continue
     state['count']+=1
     if m['op']=='count':continue
     if m['op'] in {'min','max'}:
      k=key(value)
      if state['min'] is not None and key(state['min'])[0]!=k[0]:fail('Minimum/maximum encountered incompatible source types.','SUBWAY_QUERY_TYPE')
      state['min']=value if state['min'] is None or k[1]<key(state['min'])[1] else state['min']
      state['max']=value if state['max'] is None or k[1]>key(state['max'])[1] else state['max']
      continue
     if type(value) not in (int,float,Decimal):fail('Aggregate encountered nonnumeric values; select the correct numeric measure. No partial total returned.','SUBWAY_QUERY_TYPE')
     number=Decimal(str(value))
     if not number.is_finite() or len(number.as_tuple().digits)>30:fail('Numeric value exceeds exact arithmetic bounds.','SUBWAY_QUERY_TYPE')
     state['sum']+=number
     if len(state['sum'].as_tuple().digits)>36:fail('Aggregate precision exceeds supported bounds.','SUBWAY_QUERY_TYPE')
     state['min']=number if state['min'] is None else min(state['min'],number);state['max']=number if state['max'] is None else max(state['max'],number)
   if aggregate:
    if not groups and not query['group_by']:groups[()]=dict(values={},metrics={m['label']:dict(count=0,sum=Decimal(0),min=None,max=None) for m in query['metrics']})
    for group in groups.values():
     result=deepcopy(group['values'])
     for m in query['metrics']:
      state=group['metrics'][m['label']];op=m['op']
      result[m['label']]=state['count'] if op=='count' else None if state['count']==0 else state['sum']/state['count'] if op=='avg' else state[op]
     results.append(result)
    for o in reversed(query['order_by']):results.sort(key=lambda row:(row[o['column']] is not None,row[o['column']]),reverse=o['direction']=='desc')
    total_rows=len(results);results=[{k:wire(v) for k,v in row.items()} for row in results[offset:offset+limit]]
   else:total_rows=matched
  after=self.catalog(auth)
  if before['stamps']!=after['stamps']:fail('Source authority changed during query.','SUBWAY_QUERY_STALE',409)
  columns=query['group_by']+[m['label'] for m in query['metrics']] if aggregate else query['fields']
  query_id='subway_query_'+uuid4().hex
  result=dict(query_id=query_id,columns=[dict(id=fid,label=(datasets[fields[fid]['dataset_id']]['label']+'.'+fields[fid]['name']) if fid in fields else fid) for fid in columns],rows=results,coverage=dict(complete_scan=True,matched_records=matched,total_result_rows=total_rows,returned_rows=len(results),offset=offset,limit=limit,has_more=offset+len(results)<total_rows,aggregate_complete=aggregate,filtered_on_entire_source=True,qualification='Display pagination does not limit matching or aggregation. Left-join coverage is measured before query filters. Average values use 38-digit decimal arithmetic.'),sources=[dict(dataset_id=did,label=datasets[did]['label'],scanned_records=source_counts[did],metadata_revision=datasets[did]['metadata_revision'],generation=datasets[did]['generation'],read_at=now()) for did in sorted(selected)],join_checks=join_checks)
  reject_secrets(result)
  if len(canonical(result).encode())>100000:fail('Query result exceeds 100 KB; reduce displayed rows/fields or aggregate. No partial result returned.','SUBWAY_QUERY_LIMIT')
  with self.store.transaction() as db:
   db.execute('CREATE TABLE IF NOT EXISTS subway_query_receipts (workspace TEXT NOT NULL,owner TEXT NOT NULL,query_id TEXT NOT NULL,document TEXT NOT NULL,PRIMARY KEY(workspace,owner,query_id))')
   receipt=dict(query=deepcopy(query),query_sha256=hashlib.sha256(canonical(query).encode()).hexdigest(),source_authority_sha256=hashlib.sha256(canonical(before['stamps']).encode()).hexdigest(),ontology_version=self.version['version_id'],coverage=result['coverage'],sources=result['sources'],join_checks=result['join_checks'])
   db.execute('INSERT INTO subway_query_receipts VALUES (?,?,?,?)',('client-subway','subway-client',query_id,canonical(receipt)))
  return result

class SubwayQueryConnector:
 external_write=False;retry_safe=True;timeout=120
 def __init__(self,queries,auth=None,pin=None):self.queries,self.auth,self.pin=queries,auth,pin
 def reservation(self,grant):return dict(tool_calls=1,tokens=0,llm_calls=0,estimated_cost_usd=0)
 def bind_context(self,workflow,run,auth,node):
  pin=workflow.get('metadata',{}).get('client_package_pin')
  if not pin or pin.get('ontology_version')!='bov_subway_dump_v4':fail('Use the reviewed Subway ontology pin.','SUBWAY_QUERY_DENIED',403)
  self.queries.authorize(auth)
  return SubwayQueryConnector(self.queries,deepcopy(auth),deepcopy(pin))
 def invoke(self,grant,inputs,effect_id):
  if not self.auth or grant.get('tool_id')!='subway_query':fail('Use a workflow-bound Subway query.','SUBWAY_QUERY_DENIED',403)
  p=self.queries.app.state.client_packages.get(self.auth,self.pin['package_id'],self.pin['revision'])
  if p['sha256']!=self.pin['package_sha256']:fail('Pinned Subway package changed.','SUBWAY_QUERY_STALE',409)
  if list(Draft202012Validator(INPUT).iter_errors(inputs)):fail('Use the structured query contract.')
  return self.queries.execute(self.auth,inputs['query'])

def definition():
 from .client_packages import package_tool_definition
 tool=package_tool_definition();tool.update(tool_id='subway_query',capability='subway.query',description='Run an allowlisted read-only Subway query over ALL relevant source records. Filters and count/sum/avg/min/max/grouping are complete. Detail limit is display pagination only. Scalar left joins retain unmatched source rows and return exact match coverage. Never use package inspection samples to answer totals or filtered questions.',input_schema=INPUT,output_schema=OUTPUT,timeout_seconds=120)
 return tool

def planning_contract():
 from .capability_contracts import contract,INPUT_SCHEMA
 return contract('subway.plan_query','prepare_validated_query_content','Translate the actual goal into a typed Subway query using only exact catalog dataset/field/relationship IDs. Query content is validated by the executor; never SQL, pipelines or new authority. Preserve requested date/currency/filter semantics.','model',inputs=INPUT_SCHEMA,outputs=PLAN_OUTPUT,domain='restaurant_operations')

def install(app,auth):
 queries=SubwayQueries(app,auth);service=app.state.workflow_service;service.subway_queries=queries
 service.runtime_runner.connectors['subway_query']=SubwayQueryConnector(queries)
