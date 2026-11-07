"""Stage a new code-backed ontology/package in a copied Subway store. No deployment."""
import argparse
import hashlib
import json
from pathlib import Path
import sqlite3
import sys
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
from scripts.integration_config import private_write
from scripts.onboard_subway import load_env
from workflow_api.storage import WorkflowStore
from workflow_api.business_ontology import BusinessOntology
from workflow_api.business_compiler import BusinessCompiler,check_snapshot
from workflow_api.business_documents import BusinessDocuments
from workflow_api.client_packages import ClientPackages
from workflow_api.subway_onboarding import build_package

SCOPE=('client-subway','subway-client')

def prepare(evidence,directory):
    evidence=Path(evidence);directory=Path(directory).resolve();directory.mkdir(mode=0o700,parents=True,exist_ok=False)
    snapshot=json.loads((evidence/'ontology.json').read_text());check_snapshot(snapshot)
    env=load_env(ROOT/'.local/tenants/subway/backend.env');staged=directory/'workflows.sqlite3'
    with sqlite3.connect(env['BUILDER_DATABASE_URL']) as src,sqlite3.connect(staged) as dst:src.backup(dst)
    staged.chmod(0o600);store=WorkflowStore(staged)
    with store.transaction(write=False) as db:
        row=db.execute('SELECT document FROM business_ontology_workspaces WHERE workspace=? AND owner=? AND ontology_id=?',(*SCOPE,'subway')).fetchone()
        current=json.loads(row[0]);assert current['revision']+1==snapshot['revision'],'Stale enrichment baseline'
        baseline=db.execute('SELECT document FROM business_ontology_versions WHERE workspace=? AND owner=? AND version_id=?',(*SCOPE,snapshot['code_enrichment']['previous_version'])).fetchone();assert baseline
    package=build_package(snapshot,2);auth=dict(decision='allow',subject=dict(workspace_id=SCOPE[0],subject_id=SCOPE[1]),roles=['admin','builder'],permissions=['workflow.plan','workflow.execute','workflow.edit','tools.read','tools.assign','tools.manage'],scopes=['workspace:read','workspace:write'])
    ontology=BusinessOntology(store)
    with store.transaction() as db:
        db.execute('INSERT INTO business_ontology_versions VALUES (?,?,?,?)',(*SCOPE,snapshot['version_id'],json.dumps(snapshot)))
        db.execute('UPDATE business_ontology_workspaces SET document=? WHERE workspace=? AND owner=? AND ontology_id=?',(json.dumps(snapshot['workspace']),*SCOPE,'subway'))
        BusinessDocuments.save(db,SCOPE,[s for s in snapshot['sources'] if s['source_id'].startswith('subway_code_')])
        db.execute('INSERT INTO business_ontology_events VALUES (?,?,?,?)',(*SCOPE,'boe_subway_code_v2',json.dumps(dict(action='code_evidence_enrichment',version_id=snapshot['version_id'],revision=snapshot['revision'],archives=snapshot['code_enrichment']['archives']))))
    compiler=BusinessCompiler(ontology);compilation=compiler.compile(auth,snapshot['version_id'],{})['compilation'];assert compilation['report']['status']=='passed'
    ClientPackages(store).publish(auth,package)
    env.update(BUILDER_DATABASE_URL=str(staged),BUILDER_SUBWAY_PACKAGE_REVISION='2',BUILDER_PROCESS_ROLE='api')
    private_write(directory/'backend.env',''.join(k+'='+json.dumps(v)+'\n' for k,v in env.items()))
    private_write(directory/'knowledge-package-v2.json',json.dumps(package,indent=2)+'\n')
    print(json.dumps(dict(staged=str(staged),version=snapshot['version_id'],package_revision=2,package_bytes=len(json.dumps(package)),compilation=compilation['report']['status'])))

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--evidence',type=Path,required=True);p.add_argument('--directory',type=Path,required=True);args=p.parse_args();prepare(args.evidence,args.directory)
