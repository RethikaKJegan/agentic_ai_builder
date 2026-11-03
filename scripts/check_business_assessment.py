"""Assess saved complaints without a policy, using read-only private snapshots.

No credentials or company/model services are loaded. The explicit timestamp is
a diagnostic input, not a claim's verified failure date. No policy is inferred.
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
from workflow_api.business_assessment import missing_policy,ASSESSMENT_VERSION
from workflow_api.business_intelligence import check_graph
from workflow_api.business_warranty import parse_date


def run(database,directory,workspace,owner,graph_id,assessment_at):
    parsed=parse_date(assessment_at)
    if not parsed or parsed['precision']!='datetime':raise ValueError('Explicit timezone-qualified timestamp required')
    before=sha256(database.read_bytes()).hexdigest()
    with sqlite3.connect(database.resolve().as_uri()+'?mode=ro',uri=True) as db:
        row=db.execute('SELECT document FROM business_ontology_graphs WHERE workspace=? AND owner=? AND graph_id=?',(workspace,owner,graph_id)).fetchone()
        if not row:raise ValueError('Owned graph unavailable')
        graph=json.loads(row[0])
        row=db.execute('SELECT document FROM business_ontology_versions WHERE workspace=? AND owner=? AND version_id=?',(workspace,owner,graph['version_id'])).fetchone()
        if not row:raise ValueError('Owned definition version unavailable')
        snapshot=json.loads(row[0])
    check_graph(snapshot,graph)
    reports=[missing_policy(snapshot,graph,dict(policy_id=None,ticket_node_id=r['node_id'],invoice_node_id=None,assessment_at=assessment_at))
        for r in graph['records'] if r['collection']=='tickets' and r['role']=='service']
    unchanged=sha256(database.read_bytes()).hexdigest()==before
    if not unchanged:raise ValueError('Input store changed during offline check')
    summary=dict(assessment_version=ASSESSMENT_VERSION,graph_id=graph_id,version_id=snapshot['version_id'],tickets=len(reports),assessment_at=assessment_at,
        cases=[dict(ticket_node_id=r['ticket_node_id'],classification=r['classification'],policy_id=r['policy_id'],draft_calculation=r['draft_calculation'],blockers=[b['code'] for b in r['blockers']],report_sha256=r['report_sha256']) for r in reports],
        input_store_unchanged=unchanged,company_queries=0,company_writes=0,model_calls=0,input_store_writes=0,coverage_calculations_performed=False,eligibility_final=False)
    directory.mkdir(mode=0o700,parents=True,exist_ok=False)
    for index,report in enumerate(reports):
        path=directory/('case-'+str(index+1)+'.json');path.write_text(json.dumps(report,indent=2)+'\n');os.chmod(path,0o600)
    path=directory/'report.json';path.write_text(json.dumps(summary,indent=2)+'\n');os.chmod(path,0o600)
    return summary


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--database',type=Path,required=True);p.add_argument('--directory',type=Path,required=True)
    p.add_argument('--workspace',required=True);p.add_argument('--owner',required=True);p.add_argument('--graph-id',required=True)
    p.add_argument('--assessment-at',required=True)
    args=p.parse_args()
    try:print(json.dumps(run(args.database,args.directory,args.workspace,args.owner,args.graph_id,args.assessment_at),indent=2))
    except Exception as exc:print(json.dumps(dict(status='unavailable',error_type=type(exc).__name__)));sys.exit(1)
