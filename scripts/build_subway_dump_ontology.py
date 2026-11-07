"""Build a dump-centered immutable ontology with exact corresponding code evidence."""
from copy import deepcopy
import argparse,hashlib,json,re,subprocess,sys,zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
from scripts.integration_config import private_write
from workflow_api.business_compiler import check_snapshot,compile_snapshot
from workflow_api.google_connections import now

def build(output):
 output=Path(output);output.mkdir(mode=0o700,parents=True,exist_ok=False)
 old=json.loads((ROOT/'ontology/subway/business-ontology-v3.json').read_text());v=deepcopy(old)
 v['concepts']=[c for c in v['concepts'] if c['id'] in {'evidence:object','evidence:business_record'} or any(':'+r+'_' in c['id'] for r in ['central','finance'])]
 keep={c['id'] for c in v['concepts']};by_model={};correspondence=[];texts={};source_parts={'finance':[],'intranet':[]}
 for app in source_parts:
  filename=old['coverage_audit']['archives'][app]['name']
  with zipfile.ZipFile(ROOT/filename) as archive:
   for member in archive.namelist():
    if '/src/' in member and member.endswith('.js') and member.split('/src/',1)[1].startswith(('models/','services/')):texts[(app,member)]=archive.read(member).decode()
 inputs=[dict(key=app+'|'+member,text=text) for (app,member),text in texts.items() if '/models/' in member]
 scans=json.loads(subprocess.check_output(['node',str(ROOT/'scripts/subway_data_model_refs.mjs')],input=json.dumps({'sources':inputs}),text=True))
 def cite(app,member,quote,start,end):
  from registry.safety import reject_secrets
  reject_secrets({'text':quote})
  if len(quote)>1200 or re.search(r'https?://|[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}',quote):raise ValueError('Excerpt requires narrower review')
  part=f'FILE {member} LINES {start}-{end}\n'+quote
  if part not in source_parts[app]:source_parts[app].append(part)
  return dict(source_id='subway_dump_code_'+app,quote=quote),dict(archive=old['coverage_audit']['archives'][app]['name'],member=member,start_line=start,end_line=end,member_sha256=hashlib.sha256(texts[(app,member)].encode()).hexdigest())
 for c in v['concepts']:
  model=c.get('source_model')
  if not model:continue
  app=model['application'];member=next(p['member'] for p in c['code_provenance'] if p['member_sha256']==model['member_sha256'])
  by_model[(app,model['name'])]=c['id'];c['data_availability']='restored_collection'
  role,collection=c['id'].split(':')[1].split('_',1)
  # Record exact source files referencing the mapped model symbol, including the
  # actual matched line (shortened at syntax boundaries, never synthesized).
  services=[]
  index_member=next(m for a,m in texts if a==app and m.endswith('/models/index.js'))
  relative=member.split('/models/',1)[1].removesuffix('.js')
  exported=re.findall(r"module\.exports\.(\w+)\s*=\s*require\(['\"]\./"+re.escape(relative)+r"['\"]\)",texts[(app,index_member)])
  symbols=sorted(set([model['name'],*exported]))
  pattern=re.compile(r'\b(?:'+'|'.join(re.escape(s) for s in symbols)+r')\s*(?:\.|\()')
  for (a,m),text in texts.items():
   if a!=app or '/services/' not in m:continue
   matches=[(n,line.strip()) for n,line in enumerate(text.splitlines(),1) if pattern.search(line) and not line.lstrip().startswith('//')]
   if not matches:continue
   services.append(dict(member=m,member_sha256=hashlib.sha256(text.encode()).hexdigest(),reference_lines=[n for n,_ in matches]))
  entry=dict(concept_id=c['id'],role=role,collection=collection,model=model,model_member=member,exported_symbols=exported,export_member=index_member,service_files=services,service_evidence_basis='Static model/export-symbol call and constructor references; not a claim that every branch executes or all guards are reviewed.')
  if not services:entry['service_limitation']='No direct model-symbol service usage found; model declaration and dump schema remain mapped.'
  c['dump_mapping']=dict(role=role,collection=collection,connection_id='dbconn_subway_'+role,model_member=member,service_members=[s['member'] for s in services])
  if services:
   service=services[0];n=service['reference_lines'][0]
   quote=texts[(app,service['member'])].splitlines()[n-1].strip()
   if len(quote)<=1200 and not re.search(r'https?://|[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}',quote):
    ev,prov=cite(app,service['member'],quote,n,n)
    if len(c['evidence'])<8:c['evidence'].append(ev);c.setdefault('code_provenance',[]).append(prov)
  correspondence.append(entry)
 # Rebuild model refs from the root schema, resolving embedded schema variables
 # and array paths. This replaces prior syntactic paths such as stages.type.
 relationships=[deepcopy(r) for r in old['relationships'] if r['id'].split(':')[1].startswith('candidate_reference_') and r['source'] in keep and r['target'] in keep]
 for c in v['concepts']:
  if 'source_model' not in c:continue
  m=c['source_model'];app=m['application'];member=c['dump_mapping']['model_member']
  scan=next(s for s in scans[app+'|'+member] if s['name']==m['name'])
  for ref in scan['references']:
   target=by_model.get((app,ref['target']))
   if not target:continue
   ev,prov=cite(app,member,ref['quote'],ref['start_line'],ref['end_line']);mid=c['module_id'];path=ref['path'];rid=mid+':dump_ref_'+hashlib.sha256((c['id']+path+target).encode()).hexdigest()[:16]
   relationships.append(dict(id=rid,label=c['id'].split(':')[1]+' '+path+' reference',definition=f'The corresponding {app} model declares {path} as a reference to {ref["target"]}, mapped to a collection present in the supplied dumps. Identifier compatibility is recorded separately; this declaration does not grant join authority.',layer='domain',source=c['id'],target=target,predicate='references_record',evidence=[ev],confidence=.95,unknowns=['Source-code version alignment and complete referential integrity are not established by a bounded sample.'],module_id=mid,status='draft',relationship_basis='dump_mapped_model_reference',source_field=path,code_provenance=[prov]))
 v['relationships']=relationships
 v['rules']=[]
 for original in old['rules']:
  if not set(original['inputs'])&keep:continue
  rule=deepcopy(original)
  missing=[cid for cid in rule['inputs'] if cid not in keep]
  if missing:
   rule['inputs']=[cid for cid in rule['inputs'] if cid in keep]
   rule['external_prerequisites']=[dict(source_concept_id=cid,
       label=next(c['label'] for c in old['concepts'] if c['id']==cid),
       availability='Not present in the supplied database dumps; relevant only when this specific code guard must be evaluated.') for cid in missing]
   rule['unknowns'].append('This guard also depends on records absent from the supplied dumps: '+', '.join(p['label'] for p in rule['external_prerequisites'])+'. This does not block unrelated reads or analysis.')
  v['rules'].append(rule)
 retained_rules={r['id'] for r in v['rules']}
 removed_rules=[r['id'] for r in old['rules'] if r['id'] not in retained_rules]
 mids={c['module_id'] for c in v['concepts']};v['modules']=[m for m in old['modules'] if m['id'] in mids];v['questions']={mid:['Which supplied records and corresponding code establish the requested fact, and are any specific fields or external prerequisites absent?'] for mid in mids}
 used={e['source_id'] for kind in ['concepts','relationships','rules'] for item in v[kind] for e in item['evidence']}
 v['sources']=[s for s in old['sources'] if s['source_id'] in used]
 for app,parts in source_parts.items():
  text='\n\n'.join(parts)
  if text:v['sources'].append(dict(source_id='subway_dump_code_'+app,title='Subway '+app+' dump-mapped relationship evidence',kind='application_code',module_ids=sorted(mids),text=text,sha256=hashlib.sha256(text.encode()).hexdigest(),origin=dict(archive=old['coverage_audit']['archives'][app]['name'],archive_sha256=old['coverage_audit']['archives'][app]['sha256']),created_at=now()))
 # Sources retained for exact citations can contain historical excerpt bundles;
 # only the current definitions are retrieved, never unconnected classes.
 v.pop('coverage_audit',None);v.pop('code_enrichment',None)
 v.update(version_id='bov_subway_dump_v4',revision=4,created_at=now(),workspace={**old['workspace'],'revision':4})
 v['dump_grounding']=dict(previous_version=old['version_id'],archives=old['coverage_audit']['archives'],collection_count=len(correspondence),excluded_code_only_models=104,excluded_unrelated_or_external_dependency_rules=removed_rules,scope='Only the supplied restored central/finance data and corresponding code.',correspondence=correspondence,source_writes=0,model_calls=0)
 for module in v['modules']:module['concept_count']=sum(c['module_id']==module['id'] for c in v['concepts'])
 check_snapshot(v);report,_=compile_snapshot(v)
 if report['status']!='passed':raise ValueError('Compilation failed')
 for name,obj in [('ontology.json',v),('correspondence.json',correspondence),('validation-report.json',report)]:private_write(output/name,json.dumps(obj,indent=2)+'\n')
 print(json.dumps({k:len(v[k]) for k in ['concepts','relationships','rules','modules']}));print('collection model mappings',len(correspondence),'with service usage',sum(bool(c['service_files']) for c in correspondence))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);a=p.parse_args();build(a.output)
