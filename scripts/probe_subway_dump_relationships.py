"""Read-only bounded native-ID checks for dump-centered ontology relationships."""
import argparse,hashlib,json,re,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
from scripts.onboard_subway import load_env,REFERENCES
from scripts.integration_config import private_write
from workflow_api.storage import WorkflowStore
from workflow_api.data_sources import DataSources
from workflow_api.restored_subway_sources import RestoredSubwayAdapters
from workflow_api.business_compiler import check_snapshot,compile_snapshot

def values(value,parts):
 if not parts:return [value]
 key=parts[0].removesuffix('[]')
 if isinstance(value,list):return [x for item in value for x in values(item,parts)]
 if not isinstance(value,dict) or key not in value:return []
 child=value[key]
 if parts[0].endswith('[]'):
  return [x for item in (child if isinstance(child,list) else [child]) for x in values(item,parts[1:])]
 return values(child,parts[1:])

def probe(directory):
 from pymongo import MongoClient
 from bson import ObjectId
 directory=Path(directory);v=json.loads((directory/'ontology.json').read_text());env=load_env(ROOT/'.local/tenants/subway/backend.env');store=WorkflowStore(env['BUILDER_DATABASE_URL']);manager=DataSources(store,env,RestoredSubwayAdapters(env));configs={};metadata={};counts={};report=[]
 receipt=json.loads((ROOT/'.local/tenants/subway/onboarding/restore-receipt.json').read_text())
 with store.transaction(write=False) as db:
  for role in ['central','finance']:
   cid='dbconn_subway_'+role
   row=db.execute('SELECT secret,document FROM data_source_connections WHERE connection_id=? AND workspace=? AND owner=?',(cid,'client-subway','subway-client')).fetchone()
   configs[role]=json.loads(manager.cipher.decrypt(row[0].encode()));metadata[role]=json.loads(db.execute('SELECT document FROM data_source_snapshots WHERE connection_id=? AND revision=1',(cid,)).fetchone()[0])
 uri=configs['central']['uri'];concepts={c['id']:c for c in v['concepts']}
 with MongoClient(uri,serverSelectionTimeoutMS=5000,connectTimeoutMS=5000,socketTimeoutMS=10000,maxPoolSize=2,retryWrites=False) as client:
  for role,config in configs.items():
   for name,expected in receipt['databases'][config['database']]['collections'].items():
    count=client[config['database']][name].count_documents({},maxTimeMS=10000)
    if count!=expected:raise ValueError('Restored collection count changed')
    counts[role+'.'+name]=count
  for r in v['relationships']:
   source=concepts[r['source']]['dump_mapping'];target=concepts[r['target']]['dump_mapping']
   if 'source_field' in r:path=r['source_field']
   else:path=REFERENCES[int(r['id'].rsplit('_',1)[1])][2]
   mongo_path=path.replace('[]','');source_db=client[configs[source['role']]['database']];target_db=client[configs[target['role']]['database']]
   docs=list(source_db[source['collection']].find({mongo_path:{'$exists':True,'$ne':None}},{mongo_path:1}).sort('_id',1).limit(200).max_time_ms(5000))
   raw=[x for d in docs for x in values(d,path.split('.'))]
   scalar=[x for x in raw if isinstance(x,(str,int,ObjectId)) and not isinstance(x,bool)][:1000]
   found=[]
   for offset in range(0,len(scalar),200):found.extend(x['_id'] for x in target_db[target['collection']].find({'_id':{'$in':scalar[offset:offset+200]}},{'_id':1}).max_time_ms(5000))
   matched=sum(any(type(x)==type(y) and x==y for y in found) for x in scalar)
   ds=next(d for d in metadata[source['role']]['datasets'] if d['name']==source['collection'])
   normalized=lambda p:p.replace('[]','')
   known=any(normalized(f['name'])==mongo_path for f in ds['fields'])
   item=dict(relationship_id=r['id'],source=source['role']+'.'+source['collection'],target=target['role']+'.'+target['collection'],source_field=path,metadata_path_observed=known,sampled_documents=len(docs),sampled_scalar_references=len(scalar),matched_native_identifiers=matched,unmatched_native_identifiers=len(scalar)-matched,unsupported_values=len(raw)-len(scalar),sample_document_limit=200,sample_reference_limit=1000,basis='First up to 200 native-ID-ordered documents having the reference; up to 1000 scalar references; not exhaustive referential integrity or executable join authority.')
   item['status']='sample_matches' if scalar and matched==len(scalar) else 'partial_matches' if matched else 'no_matches' if scalar else 'no_observed_values'
   r['source_field']=path;r['data_validation']=item;r['unknowns'].append(f'Bounded dump check: {matched}/{len(scalar)} sampled scalar references matched native target IDs; status {item["status"]}.')
   report.append(item)
 v['dump_grounding']['restored_record_counts']=counts;v['dump_grounding']['relationship_checks']=dict(count=len(report),document_limit=200,reference_limit=1000,source_writes=0)
 check_snapshot(v);validation,_=compile_snapshot(v)
 if validation['status']!='passed':raise ValueError('Compilation failed')
 for name,obj in [('ontology.json',v),('relationship-probes.json',report),('validation-report.json',validation)]:private_write(directory/name,json.dumps(obj,indent=2)+'\n')
 from collections import Counter
 print(json.dumps(dict(relationships=len(report),statuses=dict(Counter(x['status'] for x in report)),collections=len(counts),records=sum(counts.values()),source_writes=0)))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--directory',type=Path,required=True);a=p.parse_args();probe(a.directory)
