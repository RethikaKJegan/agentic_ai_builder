"""Inspect monitoring evidence using read-only private snapshots.

No credentials or company/model services are loaded. The explicit window is
a diagnostic input, not a verified cohort period. No failure rate is inferred.
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
from workflow_api.business_monitoring import report as monitoring_report,REPORT_VERSION,calendar
from workflow_api.business_intelligence import check_graph


def run(database,directory,workspace,owner,graph_id,period_start,period_end,change_node_id=None):
    if calendar(period_end)<calendar(period_start):raise ValueError('Reversed monitoring window')
    before=sha256(database.read_bytes()).hexdigest()
    with sqlite3.connect(database.resolve().as_uri()+'?mode=ro',uri=True) as db:
        row=db.execute('SELECT document FROM business_ontology_graphs WHERE workspace=? AND owner=? AND graph_id=?',(workspace,owner,graph_id)).fetchone()
        if not row:raise ValueError('Owned graph unavailable')
        graph=json.loads(row[0])
        row=db.execute('SELECT document FROM business_ontology_versions WHERE workspace=? AND owner=? AND version_id=?',(workspace,owner,graph['version_id'])).fetchone()
        if not row:raise ValueError('Owned definition version unavailable')
        snapshot=json.loads(row[0])
    check_graph(snapshot,graph)
    reports=[];offset=0
    while True:
        page=monitoring_report(snapshot,graph,dict(change_node_id=change_node_id,period_start=period_start,period_end=period_end,limit=50,offset=offset))
        reports.append(page)
        if not page['has_more']:break
        offset=page['next_offset']
    unchanged=sha256(database.read_bytes()).hexdigest()==before
    if not unchanged:raise ValueError('Input store changed during offline check')
    summary=dict(report_version=REPORT_VERSION,change_node_id=change_node_id,graph_id=graph_id,version_id=snapshot['version_id'],period_start=period_start,period_end=period_end,
        status=reports[0]['status'],summary=reports[0]['summary'],metrics=reports[0]['metrics'],total_rows=reports[0]['total_rows'],pages=len(reports),
        prerequisite_states={p['prerequisite_id']:p['status'] for p in reports[0]['prerequisites']},
        input_store_unchanged=unchanged,company_queries=0,company_writes=0,model_calls=0,input_store_writes=0,monitoring_scheduled=False)
    directory.mkdir(mode=0o700,parents=True,exist_ok=False)
    for index,report in enumerate(reports):
        path=directory/('page-'+str(index+1)+'.json');path.write_text(json.dumps(report,indent=2)+'\n');os.chmod(path,0o600)
    path=directory/'report.json';path.write_text(json.dumps(summary,indent=2)+'\n');os.chmod(path,0o600)
    return summary


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--database',type=Path,required=True);p.add_argument('--directory',type=Path,required=True)
    p.add_argument('--workspace',required=True);p.add_argument('--owner',required=True);p.add_argument('--graph-id',required=True)
    p.add_argument('--change-node-id');p.add_argument('--period-start',required=True);p.add_argument('--period-end',required=True)
    args=p.parse_args()
    try:print(json.dumps(run(args.database,args.directory,args.workspace,args.owner,args.graph_id,args.period_start,args.period_end,args.change_node_id),indent=2))
    except Exception as exc:print(json.dumps(dict(status='unavailable',error_type=type(exc).__name__)));sys.exit(1)
