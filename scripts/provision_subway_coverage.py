"""Stage or append Subway's audited v3. Install only while its backend is stopped."""
import argparse,hashlib,json,sqlite3,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
from scripts.onboard_subway import load_env,SCOPE
from scripts.integration_config import private_write
from workflow_api.storage import WorkflowStore
from workflow_api.business_ontology import BusinessOntology
from workflow_api.business_compiler import BusinessCompiler,canonical,check_snapshot
from workflow_api.business_documents import BusinessDocuments
from workflow_api.client_packages import ClientPackages
from workflow_api.subway_onboarding import build_package
AUTH=dict(decision='allow',subject=dict(workspace_id=SCOPE[0],subject_id=SCOPE[1]),roles=['admin','builder'],permissions=['workflow.plan','workflow.execute','workflow.edit','tools.read','tools.assign','tools.manage'],scopes=['workspace:read','workspace:write'])

def main(mode,evidence,directory):
 directory=Path(directory).resolve();directory.mkdir(mode=0o700,parents=True,exist_ok=False);evidence=Path(evidence)
 snapshot=json.loads((evidence/'ontology.json').read_text());check_snapshot(snapshot)
 if snapshot['version_id']!='bov_subway_audited_v3' or snapshot['revision']!=3:raise ValueError('Reviewed v3 required')
 for a in snapshot['coverage_audit']['archives'].values():
  if hashlib.sha256((ROOT/a['name']).read_bytes()).hexdigest()!=a['sha256']:raise ValueError('Archive changed')
 envfile=ROOT/'.local/tenants/subway/backend.env';env=load_env(envfile)
 if env.get('BUILDER_CLIENT_ID')!='subway':raise ValueError('Dedicated Subway required')
 baseline=json.loads((ROOT/'ontology/subway/business-ontology-v2.json').read_text())
 target=directory/'workflows.sqlite3' if mode=='stage' else Path(env['BUILDER_DATABASE_URL'])
 backup=target if mode=='stage' else directory/'workflows.before.sqlite3'
 with sqlite3.connect(env['BUILDER_DATABASE_URL']) as src,sqlite3.connect(backup) as dst:src.backup(dst)
 backup.chmod(0o600);private_write(directory/'backend.before.env',envfile.read_text())
 store=WorkflowStore(target);ontology=BusinessOntology(store);package=build_package(snapshot,3)
 if mode=='stage':
  compiled=None;published=None
 else:
  with sqlite3.connect(evidence.parent/'stage/workflows.sqlite3') as db:
   compiled=db.execute('SELECT compiler_version,document FROM business_ontology_compilations WHERE workspace=? AND owner=? AND version_id=?',(*SCOPE,snapshot['version_id'])).fetchone()
   published=db.execute('SELECT document FROM client_knowledge_packages WHERE workspace=? AND owner=? AND package_id=? AND revision=3',(*SCOPE,package['package_id'])).fetchone()
  if not compiled or not published:raise ValueError('Validated stage required')
  c=json.loads(compiled[1]);p=json.loads(published[0]);p.pop('sha256')
  if p!=package or c['input_sha256']!=hashlib.sha256(canonical(snapshot).encode()).hexdigest() or c['report']['status']!='passed':raise ValueError('Staged evidence changed')
 with store.transaction() as db:
  current=db.execute('SELECT document FROM business_ontology_workspaces WHERE workspace=? AND owner=? AND ontology_id=?',(*SCOPE,'subway')).fetchone()
  old=db.execute('SELECT document FROM business_ontology_versions WHERE workspace=? AND owner=? AND version_id=?',(*SCOPE,baseline['version_id'])).fetchone()
  if not current or json.loads(current[0])!=baseline['workspace'] or not old or json.loads(old[0])!=baseline:raise ValueError('Live ontology changed; do not overwrite it')
  db.execute('INSERT INTO business_ontology_versions VALUES (?,?,?,?)',(*SCOPE,snapshot['version_id'],json.dumps(snapshot)))
  BusinessDocuments.save(db,SCOPE,[s for s in snapshot['sources'] if s['source_id'].startswith('subway_audit_code_')])
  db.execute('UPDATE business_ontology_workspaces SET document=? WHERE workspace=? AND owner=? AND ontology_id=?',(json.dumps(snapshot['workspace']),*SCOPE,'subway'))
  db.execute('INSERT INTO business_ontology_events VALUES (?,?,?,?)',(*SCOPE,'boe_subway_audit_v3',json.dumps({'action':'coverage_audit_enrichment','version_id':snapshot['version_id'],'revision':3})))
  if compiled:
   db.execute('INSERT INTO business_ontology_compilations VALUES (?,?,?,?,?)',(*SCOPE,snapshot['version_id'],*compiled))
   db.execute('INSERT INTO client_knowledge_packages VALUES (?,?,?,?,?)',(*SCOPE,package['package_id'],3,published[0]))
 if mode=='stage':
  result=BusinessCompiler(ontology).compile(AUTH,snapshot['version_id'],{})
  if result['compilation']['report']['status']!='passed':raise ValueError('Compilation failed')
  ClientPackages(store,max_package_bytes=300000).publish(AUTH,package)
  env.update(BUILDER_DATABASE_URL=str(target),BUILDER_PROCESS_ROLE='api')
 env['BUILDER_SUBWAY_PACKAGE_REVISION']='3'
 private_write(directory/'backend.env',''.join(k+'='+json.dumps(v)+'\n' for k,v in env.items()))
 if mode=='install':private_write(envfile,(directory/'backend.env').read_text())
 private_write(directory/'receipt.json',json.dumps(dict(mode=mode,version=snapshot['version_id'],package_revision=3,concepts=len(snapshot['concepts']),relationships=len(snapshot['relationships']),rules=len(snapshot['rules']),read_capabilities=len(package['resource_bindings']),package_bytes=len(canonical(package).encode()),source_writes=0,external_model_calls=0),indent=2)+'\n')
 print((directory/'receipt.json').read_text())
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('mode',choices=['stage','install']);p.add_argument('--evidence',type=Path,required=True);p.add_argument('--directory',type=Path,required=True);a=p.parse_args();main(a.mode,a.evidence,a.directory)
