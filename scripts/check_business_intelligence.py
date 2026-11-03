"""Check curated additions and fixed reports against one owned saved graph.

Reads SQLite in mode=ro. Writes a new private evidence directory. Does not load
credentials, query company systems, call models or modify the input store.
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
from workflow_api.business_reference import load_kit,additions
from workflow_api.business_compiler import compile_snapshot
from workflow_api.business_intelligence import answer,QUESTIONS


def run(database,directory,workspace,owner,graph_id):
    before=sha256(database.read_bytes()).hexdigest()
    with sqlite3.connect(database.resolve().as_uri()+'?mode=ro',uri=True) as db:
        row=db.execute('SELECT document FROM business_ontology_graphs WHERE workspace=? AND owner=? AND graph_id=?',(workspace,owner,graph_id)).fetchone()
        if not row:raise ValueError('Owned graph unavailable')
        graph=json.loads(row[0])
        row=db.execute('SELECT document FROM business_ontology_versions WHERE workspace=? AND owner=? AND version_id=?',(workspace,owner,graph['version_id'])).fetchone()
        if not row:raise ValueError('Owned definition version unavailable')
        snapshot=json.loads(row[0])
    kit,bundle=load_kit();missing,definitions,questions=additions(snapshot,kit,bundle)
    sources={d['source_id']:d for d in snapshot['sources']};sources.update({d['source_id']:d for d in bundle['documents']})
    expanded={**snapshot,**definitions,'questions':questions,'sources':list(sources.values())}
    validation,_=compile_snapshot(expanded)
    if validation['status']!='passed':raise ValueError('Expanded draft failed compilation')
    if any(c not in expanded['concepts'] for c in snapshot['concepts']):raise ValueError('Existing concepts changed')
    results={qid:answer(snapshot,graph,dict(question_id=qid,limit=50,offset=0)) for qid in QUESTIONS}
    unchanged=sha256(database.read_bytes()).hexdigest()==before
    if not unchanged:raise ValueError('Input store changed during offline check')
    report=dict(graph_id=graph_id,version_id=snapshot['version_id'],records=len(graph['records']),source_roles=sorted({r['role'] for r in graph['records']}),retained_concepts=len(snapshot['concepts']),added_modules=len(missing),total_concepts=len(expanded['concepts']),compilation=validation['status'],report_rows={qid:r['total_rows'] for qid,r in results.items()},saved_store_unchanged=unchanged,company_queries=0,company_writes=0,model_calls=0,input_store_writes=0,business_policy_verified=False)
    directory.mkdir(mode=0o700,parents=True,exist_ok=False)
    for name,content in {**results,'report':report}.items():
        path=directory/(name+'.json');path.write_text(json.dumps(content,indent=2)+'\n');os.chmod(path,0o600)
    return report


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--database',type=Path,required=True);p.add_argument('--directory',type=Path,required=True)
    p.add_argument('--workspace',required=True);p.add_argument('--owner',required=True);p.add_argument('--graph-id',required=True)
    args=p.parse_args()
    try:print(json.dumps(run(args.database,args.directory,args.workspace,args.owner,args.graph_id),indent=2))
    except Exception as exc:print(json.dumps(dict(status='unavailable',error_type=type(exc).__name__)));sys.exit(1)
