"""Prepare a new Subway database snapshot from the two locally restored archives.

Never overwrites a live store or an existing prepared snapshot. No model calls.
"""
import argparse
from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import sys
from urllib.parse import quote

ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
from scripts.integration_config import private_write
from workflow_api.google_connections import now
from workflow_api.storage import WorkflowStore
from workflow_api.data_sources import DataSources, endpoint_identity, changes
from workflow_api.restored_subway_sources import RestoredSubwayAdapters
from workflow_api.business_ontology import BusinessOntology, LAYERS
from workflow_api.business_compiler import BusinessCompiler
from workflow_api.business_extraction import validate_result

SCOPE=('client-subway','subway-client')
GROUPS={
 'organization':('Organization and legal entities',{'central':['departments','departmentroles','roles','userroles','stategsts','vendors'],'finance':['companies','locations','foreigncurrencies','vendormappings']}),
 'stores':('Stores and distribution',{'central':['stores','storeproperties','dcs','electricityconsumptions']}),
 'procurement':('Procurement and catalogue',{'finance':['purchaseorders','items','categories','subcategories','faitems']}),
 'budgets':('Budgets and allocation',{'finance':['budgets','budgetmodifications','lineitems']}),
 'receipts':('Goods receipts and invoices',{'finance':['grns','invoicedatas','vendorgrnstagetimelines']}),
 'approvals':('Operational approvals',{'finance':['approvals','approvalconfigs','stages','cfapprovalmappings']}),
 'smallwares':('Smallwares procurement',{'finance':['smallwaregrns','smallwareitems','smallwarepoconfigs','smallwarepos','smallwarestages']}),
 'performance':('Store performance and balances',{'central':['arolds','plactuals','plaops','pluems','plreports']}),
 'evidence':('Documents and report evidence',{'central':['appdocumentcategories','appdocuments','appproperties','apps','blogcategories','blogprojects','blogs','confirmappdocuments'],'finance':['assets','advancepaymentreports','grnreports','poreports','reportfiles']})}
LABELS={'vendors':'Supplier','departments':'Department','dcs':'Distribution centre','storeproperties':'Store property','budgets':'Budget','budgetmodifications':'Budget modification','approvals':'Approval record','approvalconfigs':'Approval configuration','stages':'Approval stage','smallwarepos':'Smallwares purchase order','smallwaregrns':'Smallwares goods receipt','items':'Procurement item','categories':'Procurement category','subcategories':'Procurement subcategory','locations':'Business location','foreigncurrencies':'Foreign currency','arolds':'Weekly balance record','plaops':'P&L AOP record','pluems':'P&L UEM record','plactuals':'P&L actual record','grns':'Goods receipt','invoicedatas':'Invoice record','purchaseorders':'Purchase order','assets':'Attachment record','stores':'Store','companies':'Legal company','lineitems':'Budget line item','faitems':'FA classification configuration'}
# Candidate references. Native types are preserved; a value match is not a declared FK.
REFERENCES=[('finance','purchaseorders','company','finance','companies'),('finance','purchaseorders','department','central','departments'),('central','stores','dc','central','dcs'),('finance','grns','purchaseOrderId','finance','purchaseorders'),('finance','grns','invoiceDataId','finance','invoicedatas'),('finance','invoicedatas','poId','finance','purchaseorders'),('finance','invoicedatas','grnId','finance','grns'),('finance','lineitems','budgetId','finance','budgets'),('finance','budgetmodifications','budgetId','finance','budgets'),('finance','stages','approvalId','finance','approvals'),('finance','smallwaregrns','smPoId','finance','smallwarepos')]

def load_env(path):
 return {k:json.loads(v) for line in path.read_text().splitlines() if line and not line.startswith('#') for k,v in [line.split('=',1)]}

def prepare(directory):
 directory=Path(directory).resolve();base=ROOT/'.local/tenants/subway';onboarding=base/'onboarding'
 directory.mkdir(parents=True,mode=0o700,exist_ok=False)
 env=load_env(base/'backend.env');access=json.loads((onboarding/'mongo-access.json').read_text());receipt=json.loads((onboarding/'restore-receipt.json').read_text())
 uri=f'mongodb://{quote(access["reader_user"])}:{quote(access["reader_password"])}@127.0.0.1:27028/?authSource=admin'
 manifest={'client_id':'subway','sources':{}}
 for role in ['central','finance']:
  cid='dbconn_subway_'+role;info=receipt['databases']['subway_'+role]
  manifest['sources'][cid]=dict(database='subway_'+role,uri_sha256=hashlib.sha256(uri.encode()).hexdigest(),**info)
 private_write(directory/'restored-sources.json',json.dumps(manifest,indent=2)+'\n')
 staged=directory/'workflows.sqlite3'
 with sqlite3.connect(env['BUILDER_DATABASE_URL']) as src,sqlite3.connect(staged) as dst:src.backup(dst)
 os.chmod(staged,0o600)
 env.update(BUILDER_DATABASE_URL=str(staged),BUILDER_SUBWAY_DATA_ENABLED='1',BUILDER_SUBWAY_RESTORED_MANIFEST=str(directory/'restored-sources.json'))
 store=WorkflowStore(staged)
 # Source allowlist is provisioned before creating tenant-aware managers.
 with store.transaction() as db:
  if db.execute('SELECT 1 FROM data_source_connections').fetchone():raise ValueError('Subway already has sources; do not overwrite.')
  for cid in manifest['sources']:db.execute('INSERT INTO client_source_bindings VALUES (?)',(cid,))
 adapter=RestoredSubwayAdapters(env);manager=DataSources(store,env,adapter)
 snapshots={};probes=[]
 from pymongo import MongoClient
 with MongoClient(uri,serverSelectionTimeoutMS=5000) as mongo:
  for role in ['central','finance']:
   cid='dbconn_subway_'+role;dbname='subway_'+role
   config=dict(name='Subway '+role.title(),engine='mongodb',uri=uri,database=dbname,schemas=[],description='Read-only restored '+role+' archive snapshot',mode='direct',host='127.0.0.1',_subway_source_id=cid)
   result=adapter.profile(config,cid);result.update(connection_id=cid,engine='mongodb',revision=1,discovered_at=now(),changes=changes(None,result));snapshots[role]=result
   doc={k:config[k] for k in ('name','engine','database','schemas','description','mode','host')}
   doc.update(connection_id=cid,connection_status='connected',profiling_status='ready',generation=1,metadata_revision=1,created_at=now(),updated_at=now(),last_verified_at=now(),last_profiled_at=now(),last_error_code=None,last_error_message=None)
   with store.transaction() as db:
    db.execute('INSERT INTO data_source_connections VALUES (?,?,?,?,?)',(cid,*SCOPE,manager.cipher.encrypt(json.dumps(config).encode()).decode(),json.dumps(doc)))
    db.execute('INSERT INTO data_source_snapshots VALUES (?,?,?)',(cid,1,json.dumps(result)))
    db.execute('INSERT INTO data_source_identities VALUES (?,?)',(cid,endpoint_identity(config)))
  for sr,sc,field,tr,tc in REFERENCES:
   rows=list(mongo['subway_'+sr][sc].find({field:{'$exists':True,'$ne':None}}, {'_id':0,field:1}).limit(200).max_time_ms(5000));values=[r[field] for r in rows if field in r and isinstance(r[field],(str,int)) and not isinstance(r[field],bool)]
   matches=sum(mongo['subway_'+tr][tc].count_documents({'_id':v},limit=1,maxTimeMS=5000)>0 for v in values)
   probes.append(dict(source_role=sr,source_collection=sc,field=field,target_role=tr,target_collection=tc,sampled=len(values),matched=matches,basis='bounded native-type identifier match; not a declared foreign key'))
  # Authorization failures are exercised with commands that cannot modify data.
  from pymongo.errors import OperationFailure
  for dbname,command in [('admin',{'usersInfo':1}),('simpsons',{'find':'stores','limit':1}),('subway_central',{'find':'tokens','limit':1})]:
   try:mongo[dbname].command(command)
   except OperationFailure as exc:
    if exc.code!=13:raise
   else:raise ValueError('Restore reader accessed a forbidden resource.')
  try:mongo.subway_central.command({'explain':{'update':'stores','updates':[{'q':{'_id':None},'u':{'$set':{'x':1}}}]}})
  except OperationFailure as exc:
   if exc.code!=13:raise
  else:raise ValueError('Restore reader has write authorization.')
 private_write(directory/'reference-probes.json',json.dumps(probes,indent=2)+'\n')
 ontology=BusinessOntology(store);workspace=dict(ontology_id='subway',title='Subway Business Ontology',namespace='urn:subway-business:'+hashlib.sha256(json.dumps(SCOPE).encode()).hexdigest()[:24]+':',revision=1,status='draft',created_at=now(),sources={r:'dbconn_subway_'+r for r in snapshots},source_revisions={r:1 for r in snapshots})
 layers=deepcopy(LAYERS)
 for layer in layers:
  if layer['id']=='domain':layer.update(label='Restaurant operations domain',description='Stores, procurement, receipts, invoices, budgets and operational approvals.')
  if layer['id']=='organization':layer.update(label='Subway organization',description='Observed store network, legal entities, departments, distribution and suppliers.')
  if layer['id']=='business':layer.update(label='Subway business',description='Observed source terminology and descriptive business records; policies remain unverified.')
 modules=[];sources=[];concepts=[];relationships=[];questions={};lookup={}
 for mid,(label,roles) in GROUPS.items():
  modules.append(dict(id=mid,label=label,description=label+' from supplied archive evidence.',layers=['common','domain','organization','business']))
  lines=[]
  for role,names in roles.items():
   for name in names:
    ds=next(d for d in snapshots[role]['datasets'] if d['name']==name)
    scalar=[f for f in ds['fields'] if '.' not in f['name'] and f['name']!='__v' and set(f['types'])-{'null'} <= {'string','integer','number','boolean','date','datetime','ObjectId','decimal','Decimal128'} and set(f['types'])-{'null'}]
    from workflow_api.subway_onboarding import READS
    preferred=next((names for r,n,names in READS if (r,n)==(role,name)),['_id'])
    seen=set(); unique=[]
    for f in sorted(scalar,key=lambda f:(preferred.index(f['name']) if f['name'] in preferred else len(preferred),f['name'])):
     if f['name'].casefold() not in seen:unique.append(f);seen.add(f['name'].casefold())
    scalar=unique[:20]
    quote_line=f"{role}.{name}: {receipt['databases']['subway_'+role]['collections'][name]} records; sampled scalar fields: "+', '.join(f['name']+' ('+'/'.join(f['types'])+')' for f in scalar)+'.'
    lines.append(quote_line);cid=mid+':'+role+'_'+name;lookup[(role,name)]=cid
    props=[]
    for f in scalar:
     types=set(f['types'])-{'null'};dtype='string'
     if types=={'integer'}:dtype='integer'
     elif types<={'integer','number','decimal','Decimal128'}:dtype='decimal'
     elif types=={'boolean'}:dtype='boolean'
     elif types<={'date','datetime'}:dtype='datetime'
     elif types=={'ObjectId'}:dtype='reference'
     props.append(dict(name=f['name'],datatype=dtype,required=f['name']=='_id',description='Observed source field; sampled schema, not a policy constraint.'))
    definition=f"Stored {role}.{name} record in the Subway archive snapshot."
    if name=='assets':definition+=' The observed document URL and description fields identify attachments; physical fixed-asset ownership is not established.'
    if name in ['plaops','pluems','arolds']:definition+=' Source acronym and calculation semantics require confirmation.'
    concepts.append(dict(id=cid,label=LABELS.get(name,role.title()+' '+name),definition=definition,layer='organization' if mid=='organization' else 'domain',parent_id=None,properties=props,evidence=[dict(source_id='subway_schema_'+mid,quote=quote_line[:1100])],confidence=.8,unknowns=['Sampled fields do not establish completeness, current production state or approved business policy.'],module_id=mid,status='draft'))
  text='\n'.join(lines)
  sources.append(dict(source_id='subway_schema_'+mid,title='Subway '+label+' schema evidence',kind='evidence',origin='local_archive_schema_analysis',module_ids=[mid],text=text,sha256=hashlib.sha256(text.encode()).hexdigest(),created_at=now()))
  questions[mid]=['Which source definitions and approved policies govern this business area?']
 for n,p in enumerate(probes):
  if not p['sampled'] or not p['matched']:continue
  source=lookup[(p['source_role'],p['source_collection'])];target=lookup[(p['target_role'],p['target_collection'])];mid=source.split(':')[0]
  quote_line=f"Candidate {p['source_role']}.{p['source_collection']}.{p['field']} -> {p['target_role']}.{p['target_collection']}._id: {p['matched']} of {p['sampled']} bounded records matched with native identifier types; not a declared foreign key."
  sd=next(s for s in sources if s['source_id']=='subway_schema_'+mid);sd['text']+='\n'+quote_line;sd['sha256']=hashlib.sha256(sd['text'].encode()).hexdigest()
  relationships.append(dict(id=f'{mid}:candidate_reference_{n}',label=p['source_collection']+' '+p['field']+' candidate',definition=quote_line,layer='domain',source=source,target=target,predicate='candidate_'+p['field'].lower(),evidence=[dict(source_id=sd['source_id'],quote=quote_line)],confidence=.6,unknowns=['Identifier overlap is possible. This descriptive candidate grants no executable join authority.'],module_id=mid,status='draft'))
 # Explicit modelling blueprint, distinguished from source records and business policy.
 blueprint='An object is an identifiable model subject. A business record is an object representing a stored source document. Source records describe observations; they do not establish approved business policy.'
 sources.append(dict(source_id='subway_modelling_blueprint',title='Subway record modelling blueprint',kind='blueprint',origin='onboarding_modelling_convention',module_ids=['evidence'],text=blueprint,sha256=hashlib.sha256(blueprint.encode()).hexdigest(),created_at=now()))
 for cid,label,layer,parent,definition in [('object','Object','foundational',None,'An identifiable model subject.'),('business_record','Business record','common','evidence:object','A representation of a stored source document, distinct from the business event or physical object it describes.')]:
  concepts.append(dict(id='evidence:'+cid,label=label,definition=definition,layer=layer,parent_id=parent,properties=[],evidence=[dict(source_id='subway_modelling_blueprint',quote=blueprint)],confidence=1.0,unknowns=['Modelling convention; not an approved client policy.'],module_id='evidence',status='draft'))
 for concept in concepts:
  if concept['id'] not in ['evidence:object','evidence:business_record']:concept['parent_id']='evidence:business_record'
  if concept['module_id'] in ['approvals','performance','budgets']:concept['layer']='business'
 snapshot=dict(version_id='bov_subway_archive_v1',revision=1,created_at=now(),kind='draft',workspace=workspace,layers=layers,modules=modules,concepts=concepts,relationships=relationships,rules=[],sources=sources,questions=questions,archive_provenance={r:manifest['sources']['dbconn_subway_'+r]['archive_sha256'] for r in snapshots})
 from workflow_api.business_compiler import check_snapshot
 check_snapshot(snapshot)
 with store.transaction() as db:
  db.execute('INSERT INTO business_ontology_workspaces VALUES (?,?,?,?)',(*SCOPE,'subway',json.dumps(workspace)))
  db.execute('INSERT INTO business_ontology_versions VALUES (?,?,?,?)',(*SCOPE,snapshot['version_id'],json.dumps(snapshot)))
  from workflow_api.business_documents import BusinessDocuments
  BusinessDocuments.save(db,SCOPE,sources)
 auth=dict(decision='allow',subject=dict(workspace_id=SCOPE[0],subject_id=SCOPE[1]),roles=['admin','builder'],permissions=['workflow.plan','workflow.execute','workflow.edit','tools.read','tools.manage','tools.assign'],scopes=['workspace:read','workspace:write'])
 report=BusinessCompiler(ontology).compile(auth,snapshot['version_id'],{})['compilation']['report']
 if report['status']!='passed':raise ValueError('Ontology compilation failed.')
 from workflow_api.subway_onboarding import build_package
 from workflow_api.client_packages import ClientPackages
 package=build_package(snapshot);ClientPackages(store).publish(auth,package)
 private_write(directory/'knowledge-package.json',json.dumps(package,indent=2)+'\n')
 private_write(directory/'ontology.json',json.dumps(snapshot,indent=2)+'\n');private_write(directory/'validation-report.json',json.dumps(report,indent=2)+'\n')
 private_write(directory/'backend.env',''.join(k+'='+json.dumps(v)+'\n' for k,v in env.items()))
 print(json.dumps(dict(staged_database=str(staged),datasets=sum(len(s['datasets']) for s in snapshots.values()),concepts=len(concepts),relationships=len(relationships),compilation=report['status'],records=sum(sum(d['collections'].values()) for d in receipt['databases'].values()),external_model_calls=0)))
 return env,snapshot

if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--directory',required=True);a=p.parse_args();prepare(a.directory)
