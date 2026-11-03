"""Inspect rule catalogue and fixed queries on an existing private offline export.

Reads an explicitly scoped SQLite snapshot in mode=ro and existing compilation
files. Writes a fresh local evidence directory; no models, connectors or services.
"""
import argparse
import json
from pathlib import Path
import sqlite3
import sys
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
from workflow_api.business_rules import catalogue,execute,QUERIES,QUERY_VERSION,question_reference


def run(database,compilation_directory,directory,workspace,owner):
    manifest=json.loads((compilation_directory/'manifest.json').read_text())
    with sqlite3.connect(database.resolve().as_uri()+'?mode=ro',uri=True) as db:
        row=db.execute('SELECT document FROM business_ontology_versions WHERE workspace=? AND owner=? AND version_id=?',(workspace,owner,manifest['version_id'])).fetchone()
    if not row:raise ValueError('Owned version unavailable')
    snapshot=json.loads(row[0])
    compilation={key:manifest[key] for key in ('version_id','compiler_version','input_sha256')}
    compilation['report']=json.loads((compilation_directory/'validation-report.json').read_text())
    # Fixed file names only; do not trust path names from an imported manifest.
    expected={'ontology.ttl','ontology.rdf','instance-shapes.ttl','definition-shapes.ttl','validation-report.ttl','validation-report.json'}
    compilation['artifacts']=[{**a,'content':(compilation_directory/a['name']).read_text()} for a in manifest['artifacts'] if a['name'] in expected]
    rules=catalogue(snapshot)
    results={qid:execute(snapshot,compilation,dict(query_id=qid,focus_id=None,limit=50,offset=0)) for qid in QUERIES}
    directory.mkdir(mode=0o700,parents=True,exist_ok=False)
    (directory/'rules.json').write_text(json.dumps(rules,indent=2)+'\n')
    (directory/'query-results.json').write_text(json.dumps(results,indent=2)+'\n')
    report=dict(version_id=snapshot['version_id'],query_version=QUERY_VERSION,rules=len(rules),basis_counts={basis:sum(r['basis']==basis for r in rules) for basis in ('policy_statement','descriptive_implementation','proposed_logic')},query_row_counts={qid:len(r['rows']) for qid,r in results.items()},query_has_more={qid:r['has_more'] for qid,r in results.items()},business_questions_unavailable=len(question_reference()['items']),model_calls=0,company_queries=0,company_writes=0,input_store_writes=0,business_policy_verified=False,rules_executed=False)
    (directory/'report.json').write_text(json.dumps(report,indent=2)+'\n')
    return report


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--database',type=Path,required=True);p.add_argument('--compilation-directory',type=Path,required=True);p.add_argument('--directory',type=Path,required=True);p.add_argument('--workspace',required=True);p.add_argument('--owner',required=True)
    args=p.parse_args()
    try:print(json.dumps(run(args.database,args.compilation_directory,args.directory,args.workspace,args.owner),indent=2))
    except Exception as exc:print(json.dumps(dict(status='unavailable',error_type=type(exc).__name__)));sys.exit(1)
