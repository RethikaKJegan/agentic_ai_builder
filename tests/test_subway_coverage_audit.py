"""Coverage, rule-only retrieval and expanded read authority; no external providers."""
from copy import deepcopy
import hashlib,json,subprocess
from pathlib import Path
from types import SimpleNamespace
import pytest
from cryptography.fernet import Fernet
from workflow_api.storage import WorkflowStore
from workflow_api.business_ontology import BusinessOntology
from workflow_api.business_sources import BusinessSources
from workflow_api.business_planning import retrieve
from workflow_api.business_compiler import check_snapshot,compile_snapshot
from workflow_api.client_packages import ClientPackages
from workflow_api.capability_contracts import validate_tasks
from workflow_api.subway_onboarding import build_package,install_package_sources
from workflow_api.data_sources import DataSources
from workflow_api.service import ApiFailure

ROOT=Path(__file__).resolve().parents[1]
VERSIONS=[json.loads((ROOT/f'ontology/subway/business-ontology-v{n}.json').read_text()) for n in [1,2,3]]
V=VERSIONS[-1]
AUTH=dict(decision='allow',subject=dict(workspace_id='client-subway',subject_id='subway-client'),roles=['admin','builder'],permissions=['workflow.plan','workflow.edit','workflow.execute','tools.read','tools.assign','tools.manage'],scopes=['workspace:read','workspace:write'])

@pytest.fixture
def installed(tmp_path):
 store=WorkflowStore(tmp_path/'app.sqlite3');ontology=BusinessOntology(store);key=tmp_path/'key';key.write_bytes(Fernet.generate_key());manager=DataSources(store,{'BUILDER_DATA_SOURCE_KEY_FILE':str(key)})
 scope=('client-subway','subway-client');packages=ClientPackages(store,max_package_bytes=300000)
 with store.transaction() as db:
  db.execute('INSERT INTO business_ontology_workspaces VALUES (?,?,?,?)',(*scope,'subway',json.dumps(V['workspace'])))
  for version in VERSIONS:db.execute('INSERT INTO business_ontology_versions VALUES (?,?,?,?)',(*scope,version['version_id'],json.dumps(version)))
  for role in ['central','finance']:
   cid='dbconn_subway_'+role;datasets=[]
   for c in V['concepts']:
    prefix=':'+role+'_'
    if prefix not in c['id']:continue
    name=c['id'].split(prefix)[1];fields=[dict(name=p['name'],field_id=p['name'],types=['integer' if p['name']=='_id' else 'string']) for p in c['properties']]
    datasets.append(dict(dataset_id=name,name=name,fields=fields,sample_count=25 if fields else 0,indexes=[dict(name='_id_')]))
   doc=dict(connection_id=cid,name=cid,engine='mongodb',database='subway_'+role,connection_status='connected',profiling_status='ready',metadata_revision=1,generation=1)
   secret=manager.cipher.encrypt(json.dumps(dict(engine='mongodb',database='subway_'+role)).encode()).decode()
   db.execute('INSERT INTO data_source_connections VALUES (?,?,?,?,?)',(cid,*scope,secret,json.dumps(doc)))
   db.execute('INSERT INTO data_source_snapshots VALUES (?,?,?)',(cid,1,json.dumps(dict(datasets=datasets))))
 for i,v in enumerate(VERSIONS,1):packages.publish(AUTH,build_package(v,i))
 service=SimpleNamespace(store=store,business_composition=SimpleNamespace(packages=packages));sources=BusinessSources(ontology,manager)
 app=SimpleNamespace(state=SimpleNamespace(workflow_service=service,business_ontology=ontology,data_sources=manager,business_sources=sources))
 install_package_sources(app,AUTH,dict(BUILDER_CLIENT_ID='subway',BUILDER_SUBWAY_PACKAGE_REVISION='3'))
 return store,packages,sources,service

@pytest.mark.parametrize('question,expected',[
 ('What happens when initialApproval is false?','procurement:code_rule_budget_approval'),
 ('What does allowConfirm do?','evidence:code_rule_invalidate_confirmations'),
 ('What happens on Saturday and Sunday?','technical_support:code_rule_sla_selection'),
 ('How are duplicates checked for financialyear and vendorCode?','receipts:code_rule_grn_duplicate'),
 ('Can CF_READ_ONLY approve a step?','cf_approvals:code_rule_step_approval')])
def test_rule_only_terms_retrieve_exact_source_evidence_and_keep_owner_scope(installed,question,expected):
 store,*_=installed;r=retrieve(store,AUTH,question,V['version_id'])
 rule=next(x for x in r['references'] if x['id']==expected)
 assert rule['kind']=='rule' and all(e['source_kind']=='application_code' for e in rule['evidence'])
 assert len(r['references'])<=36 and r['definition_sha256']
 foreign=deepcopy(AUTH);foreign['subject']['workspace_id']='client-simpsons'
 assert retrieve(store,foreign,question)['state']=='not_configured'


def test_every_business_model_and_restored_collection_is_accounted_for():
 inventory=json.loads((ROOT/'ontology/subway/coverage-inventory-v3.json').read_text())
 models=[f for f in inventory['files'] if f['classification']=='business_model']
 assert len(models)==156
 for f in models:
  matches=[c for c in V['concepts'] if any(p['member']==f['member'] and p['member_sha256']==f['sha256'] for p in c.get('code_provenance',[]))]
  assert len(matches)==1,(f['member'],matches)
 assert len(V['concepts'])==158 and len(V['relationships'])==156 and len(V['rules'])==28
 assert check_snapshot(V).startswith('urn:subway-business:')
 assert compile_snapshot(V)[0]['status']=='passed'
 package=build_package(V,3)
 assert len(package['capability_contracts'])==52 and len(package['source_mappings'])==637
 assert package==json.loads((ROOT/'ontology/subway/knowledge-package-v3.json').read_text())
 assert package['rules']==[] and all(r['executable'] is False for r in V['rules'])
 assert len(V['coverage_audit']['unmapped_references'])==111


def test_scanner_covers_array_references_without_executing_or_reading_comments():
 text="const schema=mongoose.Schema({stores:[{type:Number,ref:'Store'}]});const M=mongoose.model('Site',schema); // ref:'Fake'\n"
 out=json.loads(subprocess.check_output(['node',str(ROOT/'scripts/subway_coverage_scan.mjs')],input=json.dumps({'sources':[{'key':'fixture','text':text}]}),text=True))['fixture']
 assert out['models'][0]['name']=='Site'
 assert [(r['path'],r['target']) for r in out['references']]==[('stores','Store')]


def test_all_historical_and_current_providers_remain_exactly_bound(installed,monkeypatch):
 _,packages,_,service=installed;calls=[]
 def read(self,config,dataset,fields,keys,filters,offset,limit,deadline):
  calls.append((config['database'],dataset['name'],limit))
  return [] if dataset['name']=='blogprojects' else [{f['name']:1 if f['name']=='_id' else 'fixture' for f in fields}]
 monkeypatch.setattr('workflow_api.data_queries.QueryReader.objects',read)
 for rev in [1,2,3]:
  p=packages.get(AUTH,'subway-business-v1',rev)
  for cid in p['capability_contracts']:
   r=packages.read(AUTH,dict(package_id=p['package_id'],revision=rev,capability_id=cid));assert r['version_id']==p['ontology_version']
 assert len(calls)==76 and service.default_client_package['revision']==3
 p=packages.get(AUTH,'subway-business-v1',3);b=p['resource_bindings']['subway.read.central_stores'];provider=packages.providers[('client-subway','subway-client',b['source_id'])]
 for change in [dict(collection='users'),dict(fields=['password']),dict(limit=1000),dict(row_budget_bytes=200000)]:
  with pytest.raises(ApiFailure):provider(AUTH,{**b,**change})
 foreign=deepcopy(AUTH);foreign['subject']['subject_id']='another-client'
 with pytest.raises(ApiFailure):provider(foreign,b)


def test_new_large_projection_returns_complete_rows_within_existing_evidence_limit(installed,monkeypatch):
 _,packages,_,_=installed
 def read(self,config,dataset,fields,keys,filters,offset,limit,deadline):
  return [{f['name']:i if f['name']=='_id' else 'x'*1000 for f in fields} for i in range(limit)]
 monkeypatch.setattr('workflow_api.data_queries.QueryReader.objects',read)
 result=packages.read(AUTH,dict(package_id='subway-business-v1',revision=3,capability_id='subway.read.central_stores'))
 assert 0<len(result['records'])<25 and len(json.dumps(result).encode())<100000
 assert result['coverage']['complete_dataset'] is False
 assert all(len(r['values'])==len(result['records'][0]['values']) for r in result['records'])


def test_empty_probe_fails_closed_if_records_appear_and_normal_browsing_stays_unchanged(installed,monkeypatch):
 _,packages,sources,_=installed
 monkeypatch.setattr('workflow_api.data_queries.QueryReader.objects',lambda *a:[{'_id':1}])
 with pytest.raises(ApiFailure,match='Records appeared'):
  packages.read(AUTH,dict(package_id='subway-business-v1',revision=3,capability_id='subway.read.central_blogprojects'))
 with pytest.raises(ApiFailure,match='native identity'):
  sources.binding(AUTH,dict(connection_id='dbconn_subway_central',dataset_id='blogprojects',metadata_revision=1,generation=1))


def test_large_catalog_does_not_increase_execution_task_limit(installed):
 _,packages,_,_=installed;p=packages.get(AUTH,'subway-business-v1',3)
 tasks=[dict(task_id=cid,capability_id=cid,depends_on=[]) for cid in p['capability_contracts']]
 with pytest.raises(ApiFailure,match='sixteen'):validate_tasks(tasks[:17],p['capability_contracts'])
 with pytest.raises(ApiFailure,match='too large'):ClientPackages(packages.store).publish(AUTH,build_package(V,3))
 bad=deepcopy(p);bad.pop('sha256');bad['revision']=4
 keys=list(bad['capability_contracts']);bad['capability_contracts'][keys[0]]['preconditions']=[keys[1]];bad['capability_contracts'][keys[1]]['preconditions']=[keys[0]]
 with pytest.raises(ApiFailure,match='cycle'):packages.publish(AUTH,bad)
