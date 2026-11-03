"""Inspect existing private policy evidence without seeding policy or services."""
import argparse
from hashlib import sha256
import json
import os
from pathlib import Path
import sqlite3
import sys
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
from workflow_api.business_intelligence import check_graph


def run(database,directory,workspace,owner,graph_id):
    before=sha256(database.read_bytes()).hexdigest()
    with sqlite3.connect(database.resolve().as_uri()+'?mode=ro',uri=True) as db:
        row=db.execute('SELECT document FROM business_ontology_graphs WHERE workspace=? AND owner=? AND graph_id=?',(workspace,owner,graph_id)).fetchone()
        if not row:raise ValueError('Owned graph unavailable')
        graph=json.loads(row[0])
        row=db.execute('SELECT document FROM business_ontology_versions WHERE workspace=? AND owner=? AND version_id=?',(workspace,owner,graph['version_id'])).fetchone()
        if not row:raise ValueError('Owned definition unavailable')
        snapshot=json.loads(row[0]);check_graph(snapshot,graph)
        documents=[json.loads(r[0]) for r in db.execute('SELECT document FROM business_ontology_documents WHERE workspace=? AND owner=?',(workspace,owner))]
        exists=db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='business_policy_versions'").fetchone()
        policies=db.execute('SELECT COUNT(*) FROM business_policy_versions WHERE workspace=? AND owner=?',(workspace,owner)).fetchone()[0] if exists else 0
    if sha256(database.read_bytes()).hexdigest()!=before:raise ValueError('Input store changed')
    report=dict(graph_id=graph_id,version_id=snapshot['version_id'],saved_tickets=sum(r['collection']=='tickets' and r['role']=='service' for r in graph['records']),
        warranty_policy_documents=sum(d['kind']=='policy' and 'warranty' in d['module_ids'] for d in documents),saved_policy_revisions=policies,
        comparison_status='requires_explicit_policy_selection' if policies else 'no_saved_policy_revision',comparisons_run=0,eligibility='not_evaluated',
        input_store_unchanged=True,input_store_writes=0,company_queries=0,company_writes=0,model_calls=0,business_policy_verified=False,
        note='No policy values were inferred or seeded. Existing code/flags/blueprint are not authoritative coverage/exclusion policy.')
    directory.mkdir(mode=0o700,parents=True,exist_ok=False);path=directory/'report.json';path.write_text(json.dumps(report,indent=2)+'\n');os.chmod(path,0o600)
    return report


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--database',type=Path,required=True);p.add_argument('--directory',type=Path,required=True)
    p.add_argument('--workspace',required=True);p.add_argument('--owner',required=True);p.add_argument('--graph-id',required=True)
    args=p.parse_args()
    try:print(json.dumps(run(args.database,args.directory,args.workspace,args.owner,args.graph_id),indent=2))
    except Exception as exc:print(json.dumps(dict(status='unavailable',error_type=type(exc).__name__)));sys.exit(1)
