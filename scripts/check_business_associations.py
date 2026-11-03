"""Resolve supported saved record associations without merging physical engines.

Reads SQLite in mode=ro, never loads credentials or uses company/model services,
and writes only a fresh private evidence directory. No policy is inferred.
"""
import argparse
from hashlib import sha256
import json
import os
from pathlib import Path
import sqlite3
import sys
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
from workflow_api.business_identity import resolve,RESOLVER_VERSION
from workflow_api.business_intelligence import check_graph


def run(database,directory,workspace,owner,graph_id):
    before=sha256(database.read_bytes()).hexdigest()
    with sqlite3.connect(database.resolve().as_uri()+'?mode=ro',uri=True) as db:
        row=db.execute('SELECT document FROM business_ontology_graphs WHERE workspace=? AND owner=? AND graph_id=?',(workspace,owner,graph_id)).fetchone()
        if not row:raise ValueError('Owned graph unavailable')
        graph=json.loads(row[0])
        row=db.execute('SELECT document FROM business_ontology_versions WHERE workspace=? AND owner=? AND version_id=?',(workspace,owner,graph['version_id'])).fetchone()
        if not row:raise ValueError('Owned definition version unavailable')
        snapshot=json.loads(row[0])
    check_graph(snapshot,graph)
    reports=[resolve(snapshot,graph,dict(ticket_node_id=r['node_id'])) for r in graph['records'] if r['collection']=='tickets' and r['role']=='service']
    unchanged=sha256(database.read_bytes()).hexdigest()==before
    if not unchanged:raise ValueError('Input store changed during offline check')
    summary=dict(resolver_version=RESOLVER_VERSION,graph_id=graph_id,version_id=snapshot['version_id'],records=len(graph['records']),tickets=len(reports),
        cases=[dict(ticket_node_id=r['ticket_node_id'],direct_associations=len(r['direct_associations']),native_checked=sum(e['verification']=='native_reference_checked' for e in r['direct_associations']),
            legacy_saved_references=sum(e['verification']=='saved_reference_unverified_types' for e in r['direct_associations']),candidates=len(r['candidates']),invoice_resolution=r['invoice_resolution'],company_conflicts=len(r['conflicts']),physical_engine_identity=r['physical_engine_identity']) for r in reports],
        input_store_unchanged=unchanged,company_queries=0,company_writes=0,model_calls=0,input_store_writes=0,identity_merges=0,eligibility='not_evaluated')
    directory.mkdir(mode=0o700,parents=True,exist_ok=False)
    for index,report in enumerate(reports):
        path=directory/('case-'+str(index+1)+'.json');path.write_text(json.dumps(report,indent=2)+'\n');os.chmod(path,0o600)
    path=directory/'report.json';path.write_text(json.dumps(summary,indent=2)+'\n');os.chmod(path,0o600)
    return summary


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--database',type=Path,required=True);p.add_argument('--directory',type=Path,required=True)
    p.add_argument('--workspace',required=True);p.add_argument('--owner',required=True);p.add_argument('--graph-id',required=True)
    args=p.parse_args()
    try:print(json.dumps(run(args.database,args.directory,args.workspace,args.owner,args.graph_id),indent=2))
    except Exception as exc:print(json.dumps(dict(status='unavailable',error_type=type(exc).__name__)));sys.exit(1)
