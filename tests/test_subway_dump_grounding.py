"""Dump-only active context, traceable source correspondence and historical reads."""
from copy import deepcopy
import hashlib,json,subprocess,zipfile
from pathlib import Path
import pytest
from tests.test_subway_coverage_audit import installed,AUTH
from workflow_api.subway_onboarding import build_package,install_package_sources
from workflow_api.business_ontology import BusinessOntology
from workflow_api.business_sources import BusinessSources
from workflow_api.business_planning import retrieve
from workflow_api.business_compiler import compile_snapshot
from workflow_api.service import ApiFailure
from types import SimpleNamespace
ROOT=Path(__file__).resolve().parents[1]
V=json.loads((ROOT/'ontology/subway/business-ontology-v4.json').read_text())
OLD=json.loads((ROOT/'ontology/subway/business-ontology-v3.json').read_text())

def test_only_supplied_collections_and_modelling_parents_remain_active():
 assert len(V['concepts'])==54 and len(V['modules'])==9 and len(V['rules'])==13
 assert all(c['id'] in {'evidence:object','evidence:business_record'} or c.get('data_availability')=='restored_collection' for c in V['concepts'])
 ids={c['id'] for c in V['concepts']}
 assert all(r['source'] in ids and r['target'] in ids for r in V['relationships'])
 assert all(set(r['inputs'])<=ids and not r['executable'] for r in V['rules'])
 assert sum('external_prerequisites' in r for r in V['rules'])==2
 assert all(p['source_concept_id'] not in ids for r in V['rules'] for p in r.get('external_prerequisites',[]))
 assert not any(c['id'].startswith(('code_','technical_support:','quality_cases:','franchise_records:','cf_approvals:')) for c in V['concepts'])
 p=build_package(V,4);old=build_package(OLD,3)
 assert p['resource_bindings']==old['resource_bindings'] and p['source_mappings']==old['source_mappings']
 assert len(p['concepts'])==54 and len(p['capability_contracts'])==52
 assert p==json.loads((ROOT/'ontology/subway/knowledge-package-v4.json').read_text())
 assert compile_snapshot(V)[0]['status']=='passed'


def test_every_collection_has_exact_model_hash_and_recorded_service_correspondence():
 mappings=V['dump_grounding']['correspondence'];assert len(mappings)==52
 assert len({(c['role'],c['collection']) for c in mappings})==52
 assert sum(bool(c['service_files']) for c in mappings)==48
 for app in ['finance','intranet']:
  archive=V['dump_grounding']['archives'][app]
  assert hashlib.sha256((ROOT/archive['name']).read_bytes()).hexdigest()==archive['sha256']
  with zipfile.ZipFile(ROOT/archive['name']) as z:
   for m in [m for m in mappings if m['model']['application']==app]:
    assert hashlib.sha256(z.read(m['model_member'])).hexdigest()==m['model']['member_sha256']
    for service in m['service_files']:
     raw=z.read(service['member']);assert hashlib.sha256(raw).hexdigest()==service['member_sha256']
     assert all(1<=n<=len(raw.decode().splitlines()) for n in service['reference_lines'])
    if not m['service_files']:assert m['service_limitation']
 sources={s['source_id']:s for s in V['sources']}
 for kind in ['concepts','relationships','rules']:
  for item in V[kind]:
   for e in item['evidence']:assert ' '.join(e['quote'].split()) in ' '.join(sources[e['source_id']]['text'].split())


def test_relationships_resolve_real_root_array_paths_and_keep_sample_qualifications():
 assert len(V['relationships'])==67
 assert not any('.type' in r['source_field'] for r in V['relationships'])
 assert any(r['source_field']=='items[].lineItem' for r in V['relationships'])
 assert any(r['source_field']=='stages[]' for r in V['relationships'])
 from collections import Counter
 assert Counter(r['data_validation']['status'] for r in V['relationships'])==dict(sample_matches=57,partial_matches=2,no_observed_values=8)
 assert sum(V['dump_grounding']['restored_record_counts'].values())==1218822
 for r in V['relationships']:
  d=r['data_validation'];assert d['matched_native_identifiers']<=d['sampled_scalar_references']<=1000
  assert d['sampled_documents']<=200 and 'not exhaustive' in d['basis']


def test_root_schema_scanner_follows_embedded_schemas_and_ignores_unrelated_schema():
 source="const child=mongoose.Schema({item:{type:Number,ref:'Item'}});const unused=mongoose.Schema({secret:{ref:'Foreign'}});const root=mongoose.Schema({items:[child],stages:{type:[{type:Number,ref:'Stage'}]}});const Order=mongoose.model('Order',root);"
 out=json.loads(subprocess.check_output(['node',str(ROOT/'scripts/subway_data_model_refs.mjs')],input=json.dumps({'sources':[{'key':'fixture','text':source}]}),text=True))['fixture']
 assert {(r['path'],r['target']) for r in out[0]['references']}=={('items[].item','Item'),('stages[]','Stage')}


def test_all_four_revisions_and_dump_only_planner_context(installed,monkeypatch):
 store,packages,sources,service=installed;ontology=BusinessOntology(store)
 with store.transaction() as db:
  db.execute('INSERT INTO business_ontology_versions VALUES (?,?,?,?)',('client-subway','subway-client',V['version_id'],json.dumps(V)))
  db.execute('UPDATE business_ontology_workspaces SET document=? WHERE workspace=? AND owner=?',(json.dumps(V['workspace']),'client-subway','subway-client'))
 packages.publish(AUTH,build_package(V,4))
 app=SimpleNamespace(state=SimpleNamespace(workflow_service=service,business_ontology=ontology,data_sources=sources.manager,business_sources=sources))
 install_package_sources(app,AUTH,dict(BUILDER_CLIENT_ID='subway',BUILDER_SUBWAY_PACKAGE_REVISION='4'))
 monkeypatch.setattr('workflow_api.data_queries.QueryReader.objects',lambda self,config,ds,fields,keys,filters,offset,limit,deadline: [] if ds['name']=='blogprojects' else [{f['name']:1 if f['name']=='_id' else 'fixture' for f in fields}])
 count=0
 for rev in [1,2,3,4]:
  p=packages.get(AUTH,'subway-business-v1',rev)
  for cid in p['capability_contracts']:
   r=packages.read(AUTH,dict(package_id=p['package_id'],revision=rev,capability_id=cid));assert r['version_id']==p['ontology_version'];count+=1
 assert count==128 and service.default_client_package['revision']==4
 for question,expected in [('What happens when initialApproval is false?','procurement:code_rule_budget_approval'),('What does allowConfirm do?','evidence:code_rule_invalidate_confirmations')]:
  r=retrieve(store,AUTH,question,V['version_id'])
  assert any(ref['id']==expected for ref in r['references'])
  assert r['source_coverage']['code_only_concepts']==[] and len(r['source_coverage']['connected_collection_concepts'])==52
  assert all(ref['id'] in {i['id'] for k in ['concepts','relationships','rules'] for i in V[k]} for ref in r['references'])
 r=retrieve(store,AUTH,'Technical ticket SLA weekend and quality credit issuance',V['version_id'])
 assert not any(ref['module_id'] in {'technical_support','quality_cases'} for ref in r['references'])
 foreign=deepcopy(AUTH);foreign['subject']['workspace_id']='client-simpsons'
 assert retrieve(store,foreign,'purchase order')['state']=='not_configured'
