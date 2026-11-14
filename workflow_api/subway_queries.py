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
MONETARY_FIELDS={'amount','totalAmount','invoiceAmount','price','updatedPrice','unitPrice','advanceAmount','balanceAmount'}
def obj(properties):return dict(type='object',properties=properties,required=list(properties),additionalProperties=False)
def arr(items,n):return dict(type='array',items=items,maxItems=n)
STR={'type':'string','maxLength':200}
QUERY=obj(dict(base_dataset_id=STR,joins=arr({'type':'string','maxLength':100},3),fields=arr(STR,24),filters=arr(obj(dict(field_id=STR,op={'type':'string','enum':['eq','ne','gt','gte','lt','lte','is_null','not_null']},value={'anyOf':[{'type':'string','maxLength':500},{'type':'number'},{'type':'boolean'},{'type':'null'}]})),20),group_by=arr(STR,6),metrics=arr(obj(dict(label={'type':'string','pattern':'^[a-zA-Z][a-zA-Z0-9_]{0,50}$'},op={'type':'string','enum':['count','sum','avg','min','max']},field_id=STR)),12),order_by=arr(obj(dict(column=STR,direction={'type':'string','enum':['asc','desc']})),3),offset={'type':'integer','minimum':0,'maximum':1000000},limit={'type':'integer','minimum':1,'maximum':500}))
INPUT=obj(dict(query=QUERY))
OUTPUT=obj(dict(query_id={'type':'string'},columns={'type':'array','items':{'type':'object'}},rows={'type':'array','items':{'type':'object'}},coverage={'type':'object'},sources={'type':'array','items':{'type':'object'}},join_checks={'type':'array','items':{'type':'object'}}))
OUTPUT['properties'].update(ontology_version=STR,scope=obj(dict(workspace_id=STR,owner_id=STR)),query_sha256=STR,
 field_ids=arr(STR,200),relationship_ids=arr(STR,3))
PLAN_OUTPUT=obj(dict(query=QUERY))
# Selection is model interpretation of authorized metadata, never a query grant.
SELECTION=obj(dict(dataset_ids=arr(STR,4),field_ids=arr(STR,96),relationship_ids=arr(STR,3),
 measure_basis={'type':'string','maxLength':1500},clarification={'type':'string','maxLength':1500}))


# Optional for saved selections; new provider transport requires this decision.
BUSINESS_RESOLUTION={'anyOf':[
 obj(dict(status={'type':'string','enum':['ready']},question={'type':'string','enum':['']},notes={'type':'string','maxLength':1500})),
 obj(dict(status={'type':'string','enum':['needs_definition']},question={'type':'string','minLength':1,'maxLength':1500},notes={'type':'string','maxLength':1500}))]}
DESCRIPTIVE_RESOLUTION=obj(dict(status={'type':'string','enum':['descriptive_measures']},question={'type':'string','enum':['']},notes={'type':'string','maxLength':1500},base_dataset_id=deepcopy(STR),group_by=deepcopy(QUERY['properties']['group_by']),metrics=arr(obj(dict(op=deepcopy(QUERY['properties']['metrics']['items']['properties']['op']),field_id=deepcopy(STR))),12)))
DESCRIPTIVE_RESOLUTION['properties']['metrics']['minItems']=1
BUSINESS_RESOLUTION['anyOf'].append(DESCRIPTIVE_RESOLUTION)
SELECTION['properties']['business_resolution']=BUSINESS_RESOLUTION
SELECTION['properties']['metadata_mode']={'type':'string','enum':['datasets']}
SELECTION['properties']['percentage_basis']={'type':'string','enum':['none','overall_population','within_group']}
SELECTION['properties']['filter_branches']=arr(obj(dict(base_dataset_id=deepcopy(STR),filters=deepcopy(QUERY['properties']['filters']))),4)

def business_question(selection):
 """Use a structured decision, never classify untrusted explanatory prose."""
 resolution=selection.get('business_resolution')
 if resolution is None:return selection['clarification']
 if selection['clarification']:
  fail('Structured business resolution must keep legacy clarification empty.','SUBWAY_SELECTION_INVALID')
 return resolution['question'] if resolution['status']=='needs_definition' else ''

def schema_identity_budget(schema):
 """Remaining Structured Outputs enum/string capacity for identifier choices.

 Limits: developers.openai.com/api/docs/guides/structured-outputs
 """
 count=0;characters=0
 def visit(value):
  nonlocal count,characters
  if isinstance(value,dict):
   for key,item in value.items():
    if key=='enum':count+=len(item);characters+=sum(len(v) for v in item if isinstance(v,str))
    elif key=='const' and isinstance(item,str):characters+=len(item)
    elif key in ('properties','$defs','definitions'):characters+=sum(len(v) for v in item)
    visit(item)
  elif isinstance(value,list):
   for item in value:visit(item)
 visit(schema)
 return 1000-count,120000-characters

def selection_schema(discovery,objective='',*,enum_budget=1000,string_budget=120000):
 """Constrain generation to advertised identities; execution still revalidates."""
 schema=deepcopy(SELECTION)
 schema['required'].append('business_resolution')
 schema['properties']['clarification']={'type':'string','enum':[''],'description':'Legacy field: always empty. Use business_resolution for readiness, blocking question and nonblocking notes.'}
 # The added empty-string enum consumes one provider enum choice.
 enum_budget-=1
 choices=dict(dataset_ids=[d['dataset_id'] for d in discovery['sources']],
  field_ids=[f['field_id'] for d in discovery['sources'] for f in d['fields']],
  relationship_ids=[r['relationship_id'] for r in discovery['relationships']])
 # Preserve all source/relationship choices. If necessary, omit optional field
 # hints rather than send an unsupported schema; query planning expands metadata.
 anchors=choices['dataset_ids']+choices['relationship_ids']
 enum_budget-=len(anchors);string_budget-=sum(len(v) for v in anchors)
 if enum_budget<0 or string_budget<0:fail('Source identifier schema exceeds its provider allowance.','SUBWAY_CONTEXT_LIMIT')
 from .kg_retrieval import terms
 tokens=terms(objective)
 ranked=sorted([f for d in discovery['sources'] for f in d['fields']],key=lambda f:(-len(tokens & terms(f['name'])),f['field_id']))
 fields=[]
 for f in ranked:
  fid=f['field_id']
  if fid in fields or enum_budget<=0 or len(fid)>string_budget:continue
  fields.append(fid);enum_budget-=1;string_budget-=len(fid)
 choices['field_ids']=fields
 for name,values in choices.items():
  values=list(dict.fromkeys(values));target=schema['properties'][name]
  if len(values)>200:
   # Avoid the per-enum string-size restriction above 250 values.
   target['items']={'anyOf':[dict(type='string',enum=values[i:i+200]) for i in range(0,len(values),200)]}
  elif values:target['items']={'type':'string','maxLength':200,'enum':values}
  else:target['maxItems']=0
 schema['properties']['field_ids']['description']='Optional exact field IDs from the allowed choices. Use [] to retrieve dataset metadata if a required field is not among these suggestions.'
 return schema


def dataset_selection_schema(discovery,objective='',*,enum_budget=None,string_budget=None):
 """Routing chooses bounded sources; the existing query model chooses fields."""
 schema=deepcopy(SELECTION)
 schema['required'].extend(['business_resolution','metadata_mode','filter_branches','percentage_basis'])
 schema['properties']['filter_branches']['description']='For alternative requested filter categories over the same base source, enumerate every category using exact advertised field IDs and typed predicates. Repeat all common constraints in each branch. Use [] when there are no alternative categories. Never conjoin mutually exclusive alternatives or omit missing/null categories.'
 schema['properties']['clarification']={'type':'string','enum':[''],'description':'Legacy field: always empty. Use business_resolution for readiness, blocking question and nonblocking notes.'}
 own_count,own_characters=schema_identity_budget(schema)
 available_count=own_count if enum_budget is None else enum_budget-1
 available_characters=own_characters if string_budget is None else string_budget
 ids=list(dict.fromkeys(d['dataset_id'] for d in discovery['sources']))
 if len(ids)>available_count or sum(len(did) for did in ids)>available_characters:
  fail('Source identifier schema exceeds its provider allowance.','SUBWAY_CONTEXT_LIMIT')
 target=schema['properties']['dataset_ids']
 if ids:target['items']={'anyOf':[{'type':'string','enum':ids[i:i+200]} for i in range(0,len(ids),200)]}
 else:target['maxItems']=0
 for name in ('field_ids','relationship_ids'):
  schema['properties'][name]={'type':'array','items':{'type':'string'},'maxItems':0,
   'description':'Always empty during routing. The server supplies metadata scoped to dataset_ids to the existing query planner.'}
 return schema

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
 if isinstance(value,datetime) and value.tzinfo:value=value.astimezone(timezone.utc).replace(tzinfo=None)
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

def bounded_discovery(result,objective,max_bytes=180000):
 """Keep every source/relationship; bound field suggestions, never source rows."""
 from .kg_retrieval import terms
 result=deepcopy(result);tokens=terms(objective);candidates=[]
 for source in result['sources']:
  fields=source['fields'];source['field_count']=len(fields);source['fields']=[];source['returned_field_count']=0
  for f in fields:
   name=f['name'];leaf=name.split('.')[-1]
   score=(len(tokens & terms(name)),int(leaf=='_id'),int(leaf in {'currency','status'}),int(bool(set(f['types']) & {'integer','number','float','decimal','datetime','date','timestamp'})))
   candidates.append((score,source['dataset_id'],name,source,f))
 result['metadata_coverage']='All authorized source descriptors and supported relationships are present. Field suggestions are bounded and ranked for this objective; field_count and returned_field_count describe metadata only, not record coverage. If necessary fields are omitted, select the relevant datasets with empty field_ids to retrieve their objective-ranked planning metadata. Omitted metadata does not prove absent source data.'
 remaining=max_bytes-len(canonical(result).encode())-1024
 if remaining<0:fail('Authorized discovery source descriptors exceed their bound.','SUBWAY_CONTEXT_LIMIT')
 for score,did,name,source,f in sorted(candidates,key=lambda row:(tuple(-n for n in row[0]),row[1],row[2])):
  cost=len(canonical(f).encode())+1
  if cost>remaining:continue
  source['fields'].append(f);source['returned_field_count']+=1;remaining-=cost
 if len(canonical(result).encode())>max_bytes:fail('Authorized discovery metadata exceeds its bound.','SUBWAY_CONTEXT_LIMIT')
 return result

class SubwayQueries:
 def __init__(self,app,auth):
  self.app,self.auth=app,deepcopy(auth);self.service=app.state.workflow_service;self.sources=app.state.business_sources;self.store=self.service.store
  self.version=app.state.business_ontology.version(auth,'bov_subway_dump_v4')
  self.collection_scope={(c['role'],c['collection']) for c in self.version['dump_grounding']['correspondence']}
  from .subway_onboarding import build_package
  self.binding_stamps={b['connection_id']:(b['metadata_revision'],b['generation']) for b in build_package(self.version,4)['resource_bindings'].values()}
 def for_objective(self,auth,objective,resolution=None):
  from .subway_dataset_lifecycle import resolve
  queries,pin=resolve(getattr(self,'real',self),auth,objective,resolution)
  # Historical service instances are shared: never mutate their source contract.
  if queries is getattr(self,'real',self):
   from copy import copy
   queries=copy(queries)
  queries.source_resolution=pin
  return queries
 def for_workflow(self,workflow,auth):
  from .subway_demonstration import from_workflow
  return from_workflow(self,workflow,auth)
 def procurement_bundle(self):
  from .subway_procurement import load
  return load(('client-subway','subway-client'),self.version)
 def discovery(self,auth,objective='',*,max_bytes=180000):
  """Compact source-backed index for the existing intent model; no source rows."""
  catalog=self.catalog(auth);concepts={(c.get('dump_mapping',{}).get('role'),c.get('dump_mapping',{}).get('collection')):c for c in self.version['concepts']}
  details={d['concept_id']:d for d in self.version.get('knowledge',{}).get('concept_details',[])}
  sources=[]
  for d in catalog['datasets'].values():
   c=concepts[(d['role'],d['collection'])]
   sources.append(dict(dataset_id=d['dataset_id'],concept_id=c['id'],label=c['label'],source=d['label'],
    definition=c['definition'][:700],aliases=deepcopy(details.get(c['id'],{}).get('aliases',c.get('aliases',[]))),
    fields=[{k:f[k] for k in ('field_id','name','types')} for f in d['fields']]))
  result=dict(ontology_version=self.version['version_id'],sources=sources,relationships=list(catalog['relationships'].values()),
   guidance='Resolve business vocabulary using these definitions, aliases and field meanings, not exact names alone. During routing select at most four relevant datasets, set metadata_mode to datasets, and leave field_ids and relationship_ids empty. The existing query planner selects exact measures, dimensions, filters and joins from server-built metadata scoped to those datasets. Only listed directed scalar relationships support joins. Similar identifiers, store/site names or currencies never establish equivalence. Spending may mean purchase orders, invoices, payments or budget use: require clarification unless the supplied definitions or explicit goal establish the measure. Status names alone do not prove approval semantics. An absent relationship is a limitation, never permission to invent a join.')
  from .subway_procurement import load as procurement_load
  procurement=self.procurement_bundle()
  if procurement:
   result['procurement_knowledge']=dict(extension_version=procurement['extension_version'],sha256=procurement['sha256'],
    status_semantics={m['collection']:{v['raw']:v['meaning'] for v in m['values']} for m in procurement['state_models']},
    guidance='Approval in progress means exact approval_in_progress in the corresponding finance approval record. Awaiting approval requires parent approval evidence. Never use the demo PENDING definition for normal requests. Use tool.subway_assess for deterministic procurement checks; no corporate tolerance or fiscal calendar is established.')
  from .subway_demo_definitions import selected as demo_definitions
  example=demo_definitions((auth['subject']['workspace_id'],auth['subject']['subject_id']),self.version,objective)
  if example:result['analytical_assumptions']=example
  return bounded_discovery(result,objective,max_bytes=min(max_bytes,180000))
 def source_catalog(self,auth):
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
   if (source['role'],source['collection']) not in by_collection or (target['role'],target['collection']) not in by_collection:continue
   left=by_collection[(source['role'],source['collection'])];right=by_collection[(target['role'],target['collection'])]
   src=next((f['field_id'] for f in datasets[left]['fields'] if f['name']==path),None);dst=next((f['field_id'] for f in datasets[right]['fields'] if f['name']=='_id'),None)
   if src and dst:
    numeric_ref=any(f['name']==path and f['type']=='Number' for f in concepts[r['source']].get('declared_fields',[]))
    numeric_target=set(fields[dst]['types'])-{'null'} <= {'integer'}
    conversion='schema_integer_reference' if numeric_ref and numeric_target else 'native'
    rels[r['id']]=dict(relationship_id=r['id'],source_dataset_id=left,target_dataset_id=right,source_field_id=src,target_field_id=dst,join_kind='left',reference_conversion=conversion,label=r['label'],definition=r['definition'])
  result=dict(datasets=datasets,fields=fields,relationships=rels,stamps=stamps)
  return result
 def catalog(self,auth,objective=None,selection=None):
  result=self.source_catalog(auth)
  datasets=result['datasets'];fields=result['fields'];rels=result['relationships'];stamps=result['stamps']
  if objective is None and selection is None:return result
  if selection is not None:
   if list(Draft202012Validator(SELECTION).iter_errors(selection)):fail('Use a bounded metadata selection.','SUBWAY_SELECTION_INVALID')
   dataset_mode=selection.get('metadata_mode')=='datasets'
   if dataset_mode and (selection['field_ids'] or selection['relationship_ids']):fail('Dataset routing must leave field and relationship choices to query planning.','SUBWAY_SELECTION_INVALID')
   selected_ids=selection['dataset_ids'];selected=set(selected_ids)
   if len(selected)!=len(selected_ids) or not selected<=set(datasets):fail('Selected datasets are outside the owned Subway metadata.','SUBWAY_QUERY_DENIED',403)
   if any(fid not in fields or fields[fid]['dataset_id'] not in selected for fid in selection['field_ids']):fail('Selected fields are outside the chosen datasets.','SUBWAY_QUERY_DENIED',403)
   if any(rid not in rels or not {rels[rid]['source_dataset_id'],rels[rid]['target_dataset_id']}<=selected for rid in selection['relationship_ids']):fail('The requested relationship has no supported source mapping.','SUBWAY_RELATIONSHIP_UNAVAILABLE')
   scoped_edges=[r for r in rels.values() if {r['source_dataset_id'],r['target_dataset_id']}<=selected] if dataset_mode else [rels[rid] for rid in selection['relationship_ids']]
   from .query_branches import validate_branches
   validate_branches(selection.get('filter_branches',[]),result,selected)
   required=set(selection['field_ids'])|{p['field_id'] for b in selection.get('filter_branches',[]) for p in b['filters']}
   from .descriptive_measures import validate_intent
   required.update(validate_intent(selection.get('business_resolution',{}),result,selected))
   for edge in scoped_edges:required.update([edge['source_field_id'],edge['target_field_id']])
   view=[]
   for did in selected_ids:
    d=datasets[did];chosen=[f for f in d['fields'] if f['field_id'] in required or f['name']=='_id']
    if not selection['field_ids']:
     from .kg_retrieval import terms
     tokens=terms(objective or '')
     ranked=sorted(d['fields'],key=lambda f:(-len(tokens & terms(f['name'])),-int(f['name']=='_id'),f['name']))
     if dataset_mode:
      keys=[f for f in d['fields'] if f['field_id'] in required or f['name']=='_id']
      key_ids={f['field_id'] for f in keys}
      chosen=keys+[f for f in ranked if f['field_id'] not in key_ids][:max(0,45-len(keys))]
     else:chosen=ranked[:45]
    view.append({**{k:d[k] for k in ('dataset_id','label')},'fields':[{k:f[k] for k in ('field_id','name','types')} for f in chosen]})
   return self.planning_view(view,scoped_edges,selection)
  from .kg_retrieval import terms
  tokens=terms(objective);scored=[]
  if 'po' in tokens or re.search(r'\bPOs\b',objective):tokens|=terms('purchase order')
  for did,d in datasets.items():
   c=next(c for c in self.version['concepts'] if c.get('dump_mapping',{}).get('role')==d['role'] and c.get('dump_mapping',{}).get('collection')==d['collection'])
   score=6*len(tokens & terms(c['label']+' '+d['collection']))+len(tokens & terms(c['definition']+' '+' '.join(c.get('aliases',[]))))+max((len(tokens & terms(f['name'])) for f in d['fields']),default=0)
   scored.append((-score,did))
  selected_ids=[did for score,did in sorted(scored)[:4] if score<0];selected=set(selected_ids)
  view=[]
  for did in selected_ids:
   d=datasets[did];ranked=sorted(d['fields'],key=lambda f:(-int(f['name']=='_id'),-len(tokens & terms(f['name'])),f['name']))[:45]
   view.append({**{k:d[k] for k in ['dataset_id','label']},'fields':[{k:f[k] for k in ['field_id','name','types']} for f in ranked]})
  return self.planning_view(view,[r for r in rels.values() if {r['source_dataset_id'],r['target_dataset_id']}<=selected])
 def planning_view(self,sources,relationships,selection=None):
  return dict(sources=sources,relationships=relationships,ontology_version=self.version['version_id'],query_schema=QUERY,
   context_hash=hashlib.sha256(canonical([self.version['version_id'],sources,relationships]).encode()).hexdigest(),
   interpretation=deepcopy(selection),semantics='Filters examine all source rows and are combined with AND. Alternative conditions require separate query branches; contradictory conjunctions are rejected. Aggregates use every matched row, never a 25-row sample. Use count with empty field_id for row counts; sum/avg require a numeric field. No arithmetic expressions. Group by currency before monetary aggregates across currencies. Joins preserve all base rows and report unmatched references; no array/fanout joins. Result limit controls display only; totals and matched counts are complete. Do not invent missing dates, currency, fields or business definitions. Null measures are excluded from aggregate values; row counts include them. Independent collection reads are not an atomic cross-database snapshot.')
 def knowledge(self,auth,objective,selection=None):
  from .business_planning import retrieve
  catalog=self.catalog(auth,objective,selection)
  # Labels expand retrieval only after exact, authorized dataset resolution.
  labels={d['label'] for d in catalog['sources']}
  concepts=[c for c in self.version['concepts'] if c.get('dump_mapping',{}).get('role','')+'.'+c.get('dump_mapping',{}).get('collection','') in labels]
  evidence=retrieve(self.store,auth,objective+' '+' '.join(c['label'] for c in concepts),self.version['version_id'],
   concept_ids={c['id'] for c in concepts},relationship_ids={r['relationship_id'] for r in catalog['relationships']})
  names={f['name'] for d in catalog['sources'] for f in d['fields']}
  for ref in evidence.get('references',[]):
   if ref['kind']!='concept':continue
   for section in ('properties','declared_fields'):
    if section in ref:ref[section]=[p for p in ref[section] if p['name'] in names]
  evidence.setdefault('source_coverage',{}).update(record_read_basis='Complete read-only queries; displayed rows are paginated. Descriptive rules remain non-executable.')
  from .subway_procurement import load as procurement_load, context as procurement_context
  procurement=self.procurement_bundle()
  if procurement:
   evidence['procurement_knowledge']=procurement_context(procurement,labels)
   # The shared retrieval already annotates concept references. Keep one complete
   # set of typed definitions rather than repeating it in every concept.
   for ref in evidence.get('references',[]):
    if 'procurement_semantics' in ref:
     ref['procurement_semantics']={k:ref['procurement_semantics'][k] for k in ('extension_version','sha256')}
   while len(canonical(evidence).encode())>70000 and evidence.get('supporting_documents'):
    evidence['supporting_documents'].pop();evidence['truncated']=True
   while len(canonical(evidence).encode())>70000 and len(evidence.get('references',[]))>1:
    evidence['references'].pop();evidence['truncated']=True
   if len(canonical(evidence).encode())>70000:fail('Procurement context exceeds its bounded planning allowance.','SUBWAY_CONTEXT_LIMIT')
   evidence['source_coverage']['procurement_rules']='Versioned analytical typed checks execute through tool.subway_assess. Existing descriptive code guards remain non-executable.'
  from .business_knowledge_model import digest
  evidence.pop('retrieval_sha256',None);evidence['retrieval_sha256']=digest(evidence)
  return catalog,evidence
 def authorize(self,auth):
  if auth.get('subject')!=SCOPE:fail('Query is outside the Subway client.','SUBWAY_QUERY_DENIED',403)
  self.sources.authorize(auth)
  if 'workflow.execute' not in auth.get('permissions',[]):fail('Current execution permission required.','SUBWAY_QUERY_DENIED',403)
 def selection(self,auth,value):
  """Canonical metadata ownership closure, not a query or an execution grant."""
  if list(Draft202012Validator(SELECTION).iter_errors(value)):fail('Use a bounded metadata selection.','SUBWAY_SELECTION_INVALID')
  if value.get('metadata_mode')=='datasets' and (value['field_ids'] or value['relationship_ids']):fail('Dataset routing must leave field and relationship choices to query planning.','SUBWAY_SELECTION_INVALID')
  catalog=self.catalog(auth);result=deepcopy(value);datasets=catalog['datasets'];fields=catalog['fields'];relationships=catalog['relationships']
  ids=result['dataset_ids']
  if len(ids)!=len(set(ids)) or any(did not in datasets for did in ids):fail('Selected datasets are outside the owned Subway metadata.','SUBWAY_QUERY_DENIED',403)
  if any(fid not in fields for fid in result['field_ids']):fail('Selected fields are outside the owned Subway metadata.','SUBWAY_QUERY_DENIED',403)
  if any(rid not in relationships for rid in result['relationship_ids']):fail('The requested relationship has no supported source mapping.','SUBWAY_RELATIONSHIP_UNAVAILABLE')
  required={fields[fid]['dataset_id'] for fid in result['field_ids']}
  for rid in result['relationship_ids']:
   edge=relationships[rid];required.update((edge['source_dataset_id'],edge['target_dataset_id']))
  ids.extend(sorted(required-set(ids)))
  if len(ids)>SELECTION['properties']['dataset_ids']['maxItems']:fail('Selected fields and relationships require too many source datasets.','SUBWAY_SELECTION_INVALID')
  from .query_branches import validate_branches
  validate_branches(result.get('filter_branches',[]),catalog,set(ids))
  from .descriptive_measures import validate_intent
  validate_intent(result.get('business_resolution',{}),catalog,set(ids))
  return result
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
  # A detail sort may use an authorized base field without displaying it.
  # Include it in the same scope/type/provenance checks and source projection.
  if not query['metrics']:used.update(o['column'] for o in query['order_by'])
  if any(fid not in fields or fields[fid]['dataset_id'] not in selected for fid in used):fail('Selected fields are outside the query datasets.','SUBWAY_QUERY_DENIED',403)
  if len(query['fields'])!=len(set(query['fields'])) or len(query['group_by'])!=len(set(query['group_by'])):fail('Select each field once.')
  if query['metrics'] and query['fields'] or query['group_by'] and not query['metrics'] or not query['metrics'] and not query['fields']:fail('Use projected fields for details or metrics/group_by for aggregates.')
  from .query_predicates import validate_conjunction
  validate_conjunction(query['filters'],fields)
  labels=[m['label'] for m in query['metrics']]
  if len(labels)!=len(set(labels)) or set(labels)&set(query['group_by']):fail('Metric labels must be distinct from each other and group field IDs.')
  for metric in query['metrics']:
   if metric['op']!='count' and not metric['field_id']:fail('This metric requires an explicit field.')
  columns=query['group_by']+labels if labels else query['fields']
  if labels and any(o['column'] not in columns for o in query['order_by']):fail('Aggregate sort columns must be selected output columns.')
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
   if metric['op'] not in {'sum','avg','min','max'}:continue
   measure=fields[metric['field_id']]
   if measure['name'].split('.')[-1] not in MONETARY_FIELDS:continue
   currency=next((f for f in datasets[measure['dataset_id']]['fields'] if f['name']=='currency'),None)
   if currency and currency['field_id'] not in query['group_by']:
    needed[measure['dataset_id']].add(currency['field_id']);currency_guards[currency['field_id']]=set()
  join_checks=[];lookup={};source_counts={};source_freshness={};source_bytes=0
  def checkpoint():
   from .data_query_control import checkpoint as control
   control()
   if time.monotonic()>deadline:fail('Full query timed out; no partial answer returned.','SUBWAY_QUERY_TIMEOUT',504)
  def read(did):
   nonlocal source_bytes
   d=datasets[did];cid=d['connection_id']
   with self.store.transaction(write=False) as db:_,secret,_,_=self.sources.bound(db,auth,cid)
   config=json.loads(self.sources.manager.cipher.decrypt(secret.encode()))
   from .source_freshness import describe
   source_freshness[did]=describe(self.sources.manager.adapter,config,d['metadata_revision'])
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
  matched=0;results=[];aggregate=bool(query['metrics']);offset=query['offset'];limit=query['limit']
  from .subway_query_pages import GroupStore,bounded_page
  with localcontext() as ctx, GroupStore(checkpoint) as groups:
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
    g=groups.get(group)
    if g is None:
     g=dict(values={fid:row.get(fid) for fid in query['group_by']},metrics={m['label']:dict(count=0,sum=Decimal(0),min=None,max=None) for m in query['metrics']})
    for m in query['metrics']:
     value=row.get(m['field_id']) if m['field_id'] else 1;state=g['metrics'][m['label']]
     if value is None:continue
     state['count']+=1
     if m['op']=='count':continue
     if m['op'] in {'min','max'}:
      if fields[m['field_id']]['name'].split('.')[-1] in MONETARY_FIELDS and type(value) not in (int,float,Decimal):fail('Monetary minimum/maximum requires numeric source values; text amounts were not converted.','SUBWAY_QUERY_TYPE')
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
    groups.put(group,g)
   if aggregate:
    if not groups and not query['group_by']:groups.put((),dict(values={},metrics={m['label']:dict(count=0,sum=Decimal(0),min=None,max=None) for m in query['metrics']}))
    def finalize(group):
     result=deepcopy(group['values'])
     for m in query['metrics']:
      state=group['metrics'][m['label']];op=m['op']
      result[m['label']]=state['count'] if op=='count' else None if state['count']==0 else state['sum']/state['count'] if op=='avg' else state[op]
     return result
    total_rows=len(groups)
    results=[{k:wire(v) for k,v in row.items()} for row in groups.page(finalize,query['order_by'],offset,limit,key)]
   else:total_rows=matched
  after=self.catalog(auth)
  if before['stamps']!=after['stamps']:fail('Source authority changed during query.','SUBWAY_QUERY_STALE',409)
  columns=query['group_by']+[m['label'] for m in query['metrics']] if aggregate else query['fields']
  query_id='subway_query_'+uuid4().hex
  reporting_filters=[deepcopy(f) for f in query['filters'] if set(fields[f['field_id']]['types'])&{'date','datetime','timestamp'}]
  result=dict(query_id=query_id,columns=[dict(id=fid,label=(datasets[fields[fid]['dataset_id']]['label']+'.'+fields[fid]['name']) if fid in fields else fid) for fid in columns],rows=results,coverage=dict(complete_scan=True,matched_records=matched,total_result_rows=total_rows,returned_rows=len(results),offset=offset,limit=limit,has_more=offset+len(results)<total_rows,aggregate_complete=aggregate,filtered_on_entire_source=True,qualification='Display pagination does not limit matching or aggregation. Left-join coverage is measured before query filters. Average values use 38-digit decimal arithmetic.'),sources=[dict(dataset_id=did,label=datasets[did]['label'],scanned_records=source_counts[did],metadata_revision=datasets[did]['metadata_revision'],generation=datasets[did]['generation'],read_at=now(),freshness=source_freshness[did]) for did in sorted(selected)],join_checks=join_checks)
  result['coverage']['reporting_filters']=reporting_filters
  if getattr(self,'demo_context',None):result['coverage']['demo_context']=deepcopy(self.demo_context)
  result.update(ontology_version=self.version['version_id'],scope=dict(workspace_id=auth['subject']['workspace_id'],owner_id=auth['subject']['subject_id']),
   query_sha256=hashlib.sha256(canonical(query).encode()).hexdigest(),field_ids=sorted(set(used)|{fid for edge in edges for fid in (edge['source_field_id'],edge['target_field_id'])}),relationship_ids=[e['relationship_id'] for e in edges])
  result['coverage']['warnings']=['A monetary measure has no recorded currency; no currency or conversion was inferred.'] if any(None in values for values in currency_guards.values()) else []
  reject_secrets(result)
  bounded_page(result)
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
  queries=self.queries.for_workflow(workflow,auth)
  queries.authorize(auth)
  return SubwayQueryConnector(queries,deepcopy(auth),deepcopy(pin))
 def invoke(self,grant,inputs,effect_id):
  if not self.auth or grant.get('tool_id')!='subway_query':fail('Use a workflow-bound Subway query.','SUBWAY_QUERY_DENIED',403)
  p=self.queries.app.state.client_packages.get(self.auth,self.pin['package_id'],self.pin['revision'])
  if p['sha256']!=self.pin['package_sha256']:fail('Pinned Subway package changed.','SUBWAY_QUERY_STALE',409)
  if list(Draft202012Validator(INPUT).iter_errors(inputs)):fail('Use the structured query contract.')
  try:return self.queries.execute(self.auth,inputs['query'])
  except ApiFailure as exc:
   from runtime.service import RuntimeFailure
   raise RuntimeFailure(exc.code,str(exc),exc.status) from None

def definition():
 from .client_packages import package_tool_definition
 tool=package_tool_definition();tool.update(tool_id='subway_query',capability='subway.query',description='Run an allowlisted read-only Subway query over ALL relevant source records. Filters and count/sum/avg/min/max/grouping are complete. Detail limit is display pagination only. Scalar left joins retain unmatched source rows and return exact match coverage. Never use package inspection samples to answer totals or filtered questions.',input_schema=INPUT,output_schema=OUTPUT,timeout_seconds=120)
 return tool

def planning_contract():
 from .capability_contracts import contract,INPUT_SCHEMA
 return contract('subway.plan_query','prepare_validated_query_content','Translate the actual goal into a typed Subway query using only exact catalog dataset/field/relationship IDs. Query content is validated by the executor; never SQL, pipelines or new authority. Preserve requested date/currency/filter semantics.','model',inputs=INPUT_SCHEMA,outputs=PLAN_OUTPUT,domain='restaurant_operations')

def install(app,auth):
 queries=SubwayQueries(app,auth);service=app.state.workflow_service;service.subway_queries=queries
 connector=SubwayQueryConnector(queries)
 jobs=getattr(app.state,'data_query_jobs',None)
 if jobs is not None and (getattr(service,'background_execution',False) or getattr(service,'durable_queries',False)):
  from .subway_query_jobs import SubwayJobEngine,DurableSubwayQuery
  jobs.engines['subway']=SubwayJobEngine(queries)
  connector=DurableSubwayQuery(connector,jobs)
 service.runtime_runner.connectors['subway_query']=connector
 from .subway_documents import SubwayDocuments
 service.runtime_runner.connectors['subway_documents']=SubwayDocuments(queries)
 from .subway_assessments import SubwayAssessments
 service.runtime_runner.connectors['subway_assess']=SubwayAssessments(queries)
