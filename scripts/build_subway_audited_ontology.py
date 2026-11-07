"""Extend Subway's immutable ontology from a complete static business-model inventory."""
from copy import deepcopy
import argparse,hashlib,json,re,sys
from collections import Counter
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
from scripts.audit_subway_coverage import inventory
from scripts.build_subway_code_ontology import ARCHIVES
from scripts.integration_config import private_write
from workflow_api.business_compiler import check_snapshot,compile_snapshot
from workflow_api.google_connections import now

# Explicit correspondence to already restored collections, not pluralization guesses.
RESTORED={
 'finance':{'CFApprovalMapping':'approvals:finance_cfapprovalmappings','VendorGrnStageTimeLine':'receipts:finance_vendorgrnstagetimelines','AdvancePaymentReport':'evidence:finance_advancepaymentreports','GrnReport':'evidence:finance_grnreports','PoReport':'evidence:finance_poreports','ReportFile':'evidence:finance_reportfiles','Asset':'evidence:finance_assets','ExtraCharge':'procurement:finance_extracharges','FaItems':'procurement:finance_faitems','ForeignCurrency':'organization:finance_foreigncurrencies','SmallwarePoConfig':'smallwares:finance_smallwarepoconfigs','SmallwareGrn':'smallwares:finance_smallwaregrns','SmallwareItem':'smallwares:finance_smallwareitems','SmallwarePo':'smallwares:finance_smallwarepos','SmallwareStage':'smallwares:finance_smallwarestages','Vendormapping':'organization:finance_vendormappings','VendorMappingHistory':'organization:finance_vendormappinghistories'},
 'intranet':{'ARold':'performance:central_arolds','Dc':'stores:central_dcs','DepartmentRole':'organization:central_departmentroles','ElectricityConsumption':'stores:central_electricityconsumptions','PlActual':'performance:central_plactuals','PlAop':'performance:central_plaops','PlReport':'performance:central_plreports','PlUem':'performance:central_pluems','StateGst':'organization:central_stategsts','Vendor':'organization:central_vendors','UserRole':'organization:central_userroles','Blog':'evidence:central_blogs','BlogProject':'evidence:central_blogprojects','BlogCategory':'evidence:central_blogcategories'}}

def build(output):
 output=Path(output);output.mkdir(mode=0o700,parents=True,exist_ok=False)
 base=json.loads((ROOT/'ontology/subway/business-ontology-v2.json').read_text());v=deepcopy(base);inv=inventory();concepts={c['id']:c for c in v['concepts']};aliases={};by_member={};sources={};excluded=[]
 for c in v['concepts']:
  for p in c.get('code_provenance',[]):by_member[(p['archive'],p['member'])]=c['id']
 declarations={}
 for f in inv['files']:
  if f['classification']!='business_model':continue
  for m in f['models']:declarations.setdefault((f['application'],m['name']),[]).append((f,m))
 def evidence(f,quote):
  app=f['application'];sid='subway_audit_code_'+app
  sources.setdefault(app,[])
  text='FILE '+f['member']+'\n'+quote
  if text not in sources[app]:sources[app].append(text)
  return {'source_id':sid,'quote':quote}
 def provenance(f,node):return {'archive':ARCHIVES[f['application']],'member':f['member'],'start_line':node['start_line'],'end_line':node['end_line'],'member_sha256':f['sha256']}
 added=Counter()
 for (app,name),entries in sorted(declarations.items()):
  if len(entries)!=1:excluded.append({'application':app,'model':name,'reason':'ambiguous duplicate model declarations'});continue
  f,m=entries[0];old=by_member.get((ARCHIVES[app],f['member']));cid=old or RESTORED.get(app,{}).get(name)
  if cid not in concepts:cid=None
  ev=evidence(f,m['quote']);prov=provenance(f,m)
  if cid is None:
   # Small modules keep the existing per-module extraction/compiler bounds intact.
   bucket=added[app]//12+1;mid=f'code_{app}_{bucket}';added[app]+=1
   if not any(x['id']==mid for x in v['modules']):
    v['modules'].append(dict(id=mid,label=app.title()+f' application models {bucket}',description='Additional statically declared business models; data availability is separately recorded.',layers=['domain']))
    v['questions'][mid]=['Which connected dataset and production release correspond to these source models?']
   slug=re.sub(r'(?<!^)([A-Z])',r'_\1',name).lower();slug=re.sub('[^a-z0-9_]','_',slug)[:60]
   cid=mid+':'+slug
   c=dict(id=cid,label=app.title()+' '+re.sub(r'(?<!^)([A-Z])',r' \1',name)+' record',definition=f'{name} is a declared model in the {app} application archive. No corresponding data source is connected for this code-only class.',layer='domain',parent_id='evidence:business_record',properties=[],evidence=[ev],confidence=.95,unknowns=['Source code establishes a model declaration, not record availability or approved policy.','Production release equivalence has not been established.'],module_id=mid,status='draft',data_availability='code_only_not_connected',code_provenance=[prov])
   v['concepts'].append(c);concepts[cid]=c
  else:
   c=concepts[cid]
   if ev not in c['evidence'] and len(c['evidence'])<8:c['evidence'].append(ev)
   if prov not in c.setdefault('code_provenance',[]):c['code_provenance'].append(prov)
  aliases.setdefault(app,{})[name]=cid;f['concept_id']=cid
  # All declared typed fields are indexed, without converting source schema types
  # into mandatory instance constraints or claiming they exist in restored records.
  c['declared_fields']=[{k:p[k] for k in ['name','type','schema','start_line','end_line']} for p in f['fields'] if p['schema']==m['schema'] and not re.search('password|secret|token|credential',p['name'],re.I)]
  c['source_model']=dict(application=app,name=name,schema=m['schema'],member_sha256=f['sha256'])
 existing={(p['archive'],p['member'],r.get('source_field'),r['target']) for r in v['relationships'] for p in r.get('code_provenance',[])}
 unmapped=[]
 for f in inv['files']:
  cid=f.get('concept_id')
  if not cid:continue
  app=f['application'];c=concepts[cid]
  for ref in f['references']:
   target=aliases[app].get(ref['target'])
   if not target:unmapped.append({'application':app,'member':f['member'],'field':ref['path'],'target':ref['target'],'reason':'dynamic, excluded, absent or ambiguous same-service model'});continue
   if (ARCHIVES[app],f['member'],ref['path'],target) in existing:continue
   mid=c['module_id'];rid=mid+':audit_ref_'+hashlib.sha256((f['key']+str(ref['schema'])+ref['path']+target).encode()).hexdigest()[:16]
   if any(r['id']==rid for r in v['relationships']):continue
   ev=evidence(f,ref['quote']);prov=provenance(f,ref)
   v['relationships'].append(dict(id=rid,label=f'{cid.split(":")[1]} {ref["schema"]}.{ref["path"]} reference',definition=f'The {app} source declares ref {ref["target"]} in schema {ref["schema"]}, field {ref["path"]}. This may be a nested schema field; it grants no executable join authority.',layer='domain',source=cid,target=target,predicate='declares_reference',evidence=[ev],confidence=.95,unknowns=['Model intent does not establish complete native-ID matches or a cross-service identity.'],module_id=mid,status='draft',relationship_basis='declared_model_reference',source_field=ref['path'],source_schema=ref['schema'],code_provenance=[prov]))
 for app,parts in sources.items():
  text='\n\n'.join(parts);v['sources'].append(dict(source_id='subway_audit_code_'+app,title='Subway '+app+' complete business model declaration evidence',kind='application_code',module_ids=sorted({c['module_id'] for c in v['concepts'] if c.get('source_model',{}).get('application')==app}),text=text,sha256=hashlib.sha256(text.encode()).hexdigest(),origin={'archive':ARCHIVES[app],'archive_sha256':inv['archives'][app]['sha256'],'basis':'static_model_declarations'},created_at=now()))
 v.update(version_id='bov_subway_audited_v3',revision=3,created_at=now(),workspace={**base['workspace'],'revision':3})
 for m in v['modules']:m['concept_count']=sum(c['module_id']==m['id'] for c in v['concepts'])
 v['coverage_audit']=dict(previous_version=base['version_id'],archives=inv['archives'],unmapped_references=unmapped,excluded_declarations=excluded,service_rule_coverage='Selected reviewed guards only; full static service guard inventory is recorded separately. No claim of exhaustive business policy coverage.',source_writes=0,model_calls=0)
 check_snapshot(v);report,artifacts=compile_snapshot(v)
 if report['status']!='passed':raise ValueError('Compilation failed')
 for f in inv['files']:
  for guard in f['guards']:guard['quote_sha256']=hashlib.sha256(guard.pop('quote').encode()).hexdigest()
 private_write(output/'ontology.json',json.dumps(v,indent=2)+'\n');private_write(output/'inventory.json',json.dumps(inv,indent=2)+'\n');private_write(output/'validation-report.json',json.dumps(report,indent=2)+'\n')
 print(json.dumps(dict(counts={k:len(v[k]) for k in ['concepts','relationships','rules','modules']},unmapped_references=len(unmapped),excluded_declarations=excluded)))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);args=p.parse_args();build(args.output)
