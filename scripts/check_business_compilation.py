"""Compile an existing owned draft offline from a read-only application store.

Does not load environment credentials, call a model or contact company databases.
Writes only a fresh local artifact directory, never the input SQLite store.
"""
import argparse
from hashlib import sha256
import json
from pathlib import Path
import sqlite3
import sys

ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
from workflow_api.business_compiler import compile_snapshot, canonical, COMPILER_VERSION


def run(database, directory, workspace, owner, version_id=None):
    with sqlite3.connect(database.resolve().as_uri()+'?mode=ro',uri=True) as db:
        rows=db.execute('SELECT document FROM business_ontology_versions WHERE workspace=? AND owner=?',(workspace,owner)).fetchall()
    versions=[json.loads(r[0]) for r in rows]
    candidates=[v for v in versions if v['kind']=='draft' and (not version_id or v['version_id']==version_id)]
    if not candidates:raise ValueError('Owned draft unavailable')
    snapshot=max(candidates,key=lambda v:v['revision'])
    report,artifacts=compile_snapshot(snapshot)
    directory.mkdir(mode=0o700,parents=True,exist_ok=False)
    for artifact in artifacts:
        (directory/artifact['name']).write_text(artifact['content'])
    evidence=dict(compiler_version=COMPILER_VERSION,version_id=snapshot['version_id'],input_sha256=sha256(canonical(snapshot).encode()).hexdigest(),
        status=report['status'],counts=report['counts'],warning_count=len(report['warnings']),
        artifacts=[{k:a[k] for k in ('name','media_type','sha256')} for a in artifacts],
        instance_validation='not_run',business_policy_verified=False,model_calls=0,company_queries=0,company_writes=0,input_store_writes=0)
    (directory/'manifest.json').write_text(json.dumps(evidence,indent=2)+'\n')
    return evidence


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--database',type=Path,required=True);p.add_argument('--directory',type=Path,required=True)
    p.add_argument('--workspace',required=True);p.add_argument('--owner',required=True);p.add_argument('--version')
    args=p.parse_args()
    try:
        result=run(args.database,args.directory,args.workspace,args.owner,args.version)
        print(json.dumps(result,indent=2));sys.exit(0 if result['status']=='passed' else 1)
    except Exception as exc:
        print(json.dumps(dict(status='unavailable',error_type=type(exc).__name__)));sys.exit(1)
