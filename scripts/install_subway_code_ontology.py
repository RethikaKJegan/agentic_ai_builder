"""Atomically append reviewed Subway v2 artifacts; never replace a live app store.

Stop the dedicated Subway service before invoking. Existing versions, packages,
workflows, credentials and source data are retained. A private backup is mandatory.
"""
import argparse
import hashlib
import json
from pathlib import Path
import sqlite3
import sys
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
from scripts.onboard_subway import load_env
from scripts.integration_config import private_write
from workflow_api.business_compiler import canonical,check_snapshot
from workflow_api.business_documents import BusinessDocuments
from workflow_api.subway_onboarding import build_package
from workflow_api.storage import WorkflowStore
from workflow_api.client_isolation import ClientIsolation

SCOPE=('client-subway','subway-client')

def install(evidence,stage,release):
    evidence=Path(evidence);stage=Path(stage);release=Path(release).resolve();release.mkdir(mode=0o700,parents=True,exist_ok=False)
    envfile=ROOT/'.local/tenants/subway/backend.env';env=load_env(envfile)
    isolation=ClientIsolation.configured(env)
    if isolation.client!='subway':raise ValueError('Subway store required.')
    snapshot=json.loads((evidence/'ontology.json').read_text());check_snapshot(snapshot)
    package=build_package(snapshot,2)
    manifest=json.loads((evidence/'source-manifest.json').read_text())
    for entry in manifest['archives'].values():
        if hashlib.sha256((ROOT/entry['name']).read_bytes()).hexdigest()!=entry['sha256']:raise ValueError('Archive fingerprint changed.')
    with sqlite3.connect(stage/'workflows.sqlite3') as db:
        compiled=db.execute('SELECT compiler_version,document FROM business_ontology_compilations WHERE workspace=? AND owner=? AND version_id=?',(*SCOPE,snapshot['version_id'])).fetchall()
        stored=db.execute('SELECT document FROM client_knowledge_packages WHERE workspace=? AND owner=? AND package_id=? AND revision=2',(*SCOPE,package['package_id'])).fetchone()
    if len(compiled)!=1 or not stored:raise ValueError('Validated staged artifacts required.')
    compilation=json.loads(compiled[0][1])
    if compilation['input_sha256']!=hashlib.sha256(canonical(snapshot).encode()).hexdigest() or compilation['report']['status']!='passed':raise ValueError('Compilation changed.')
    baseline=json.loads((ROOT/'ontology/subway/business-ontology-v1.json').read_text())
    private_write(release/'backend.before.env',envfile.read_text())
    with sqlite3.connect(isolation.database) as src,sqlite3.connect(release/'workflows.before.sqlite3') as backup:src.backup(backup)
    (release/'workflows.before.sqlite3').chmod(0o600)
    store=WorkflowStore(isolation.database)
    with store.transaction() as db:
        old=db.execute('SELECT document FROM business_ontology_versions WHERE workspace=? AND owner=? AND version_id=?',(*SCOPE,baseline['version_id'])).fetchone()
        current=db.execute('SELECT document FROM business_ontology_workspaces WHERE workspace=? AND owner=? AND ontology_id=?',(*SCOPE,'subway')).fetchone()
        if not old or json.loads(old[0])!=baseline or not current or json.loads(current[0])!=baseline['workspace']:raise ValueError('Current ontology differs from reviewed baseline; nothing appended.')
        db.execute('INSERT INTO business_ontology_versions VALUES (?,?,?,?)',(*SCOPE,snapshot['version_id'],json.dumps(snapshot)))
        BusinessDocuments.save(db,SCOPE,[s for s in snapshot['sources'] if s['source_id'].startswith('subway_code_')])
        db.execute('INSERT INTO business_ontology_compilations VALUES (?,?,?,?,?)',(*SCOPE,snapshot['version_id'],compiled[0][0],compiled[0][1]))
        db.execute('INSERT INTO client_knowledge_packages VALUES (?,?,?,?,?)',(*SCOPE,package['package_id'],2,stored[0]))
        db.execute('UPDATE business_ontology_workspaces SET document=? WHERE workspace=? AND owner=? AND ontology_id=?',(json.dumps(snapshot['workspace']),*SCOPE,'subway'))
        db.execute('INSERT INTO business_ontology_events VALUES (?,?,?,?)',(*SCOPE,'boe_subway_code_v2',json.dumps(dict(action='code_evidence_enrichment',version_id=snapshot['version_id'],revision=snapshot['revision'],archive_sha256={k:a['sha256'] for k,a in manifest['archives'].items()}))))
    env['BUILDER_SUBWAY_PACKAGE_REVISION']='2'
    private_write(envfile,''.join(k+'='+json.dumps(v)+'\n' for k,v in env.items()))
    private_write(release/'installation.json',json.dumps(dict(version=snapshot['version_id'],package_revision=2,counts={k:len(snapshot[k]) for k in ['concepts','relationships','rules']},source_writes=0,old_versions_preserved=True),indent=2)+'\n')
    print('Appended Subway ontology and package revision 2; original rows preserved.')

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--evidence',type=Path,required=True);parser.add_argument('--stage',type=Path,required=True);parser.add_argument('--release',type=Path,required=True);args=parser.parse_args();install(args.evidence,args.stage,args.release)
