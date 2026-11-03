"""Prepare an isolated private extraction request; real calls require explicit --send.

No company database queries/writes. Reads only saved application metadata. Default
mode writes the exact provider payload locally for review and makes no model call.
"""
import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import sqlite3
import sys

ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
from scripts.integration_config import load_env
from workflow_api.storage import WorkflowStore
from workflow_api.data_sources import DataSources
from workflow_api.business_ontology import BusinessOntology
from workflow_api.business_documents import BusinessDocuments,REFERENCE
from workflow_api.business_generation import BusinessGeneration
from workflow_api.business_extraction import OpenAIExtraction,SYSTEM,OUTPUT_SCHEMA


def run(directory,module,send=False):
    directory.mkdir(mode=0o700,parents=True,exist_ok=False)
    store=WorkflowStore(directory/'isolated.sqlite3');DataSources(store,{})
    scope=('local-workspace','local-builder');bundle=json.loads(REFERENCE.read_text())
    with sqlite3.connect((ROOT/'.local/workflows.sqlite3').resolve().as_uri()+'?mode=ro',uri=True) as source:
        with store.transaction() as db:
            for cid in bundle['required_sources'].values():
                row=source.execute('SELECT document FROM data_source_connections WHERE connection_id=? AND workspace=? AND owner=?',(cid,*scope)).fetchone()
                if not row:raise ValueError('Scoped source unavailable')
                original=json.loads(row[0]);safe={k:original.get(k) for k in ('connection_id','name','engine','connection_status','metadata_revision','generation')}
                db.execute('INSERT INTO data_source_connections VALUES (?,?,?,?,?)',(cid,*scope,None,json.dumps(safe)))
                snapshot=source.execute('SELECT document FROM data_source_snapshots WHERE connection_id=? AND revision=?',(cid,original['metadata_revision'])).fetchone()
                if snapshot:
                    safe_snapshot=dict(datasets=[dict(name=d['name'],fields=[dict(name=f['name'],types=f.get('types',[])) for f in d.get('fields',[])]) for d in json.loads(snapshot[0]).get('datasets',[])])
                    db.execute('INSERT INTO data_source_snapshots VALUES (?,?,?)',(cid,original['metadata_revision'],json.dumps(safe_snapshot)))
    f=BusinessOntology(store)
    auth=dict(subject=dict(workspace_id=scope[0],subject_id=scope[1]),decision='allow',permissions=['tools.read','tools.assign'],scopes=['workspace:read','workspace:write'])
    f.initialize(auth,dict(sources=bundle['required_sources']));BusinessDocuments(f).import_reference(auth,{})
    provider=OpenAIExtraction({**load_env(),**os.environ})
    jobs=BusinessGeneration(f,lambda w,o:auth if (w,o)==scope else None,provider=provider)
    job=jobs.submit(auth,dict(module_id=module,expected_revision=1,request_key='isolated_smoke_001'))
    with store.transaction(write=False) as db:
        doc=json.loads(db.execute('SELECT document FROM business_ontology_jobs WHERE job_id=?',(job['job_id'],)).fetchone()[0])
    payload=doc['payload']
    preview=dict(model=provider.model,store=False,max_output_tokens=8000,timeout_seconds=180,system=SYSTEM,user=payload,json_schema=OUTPUT_SCHEMA)
    (directory/'payload-preview.json').write_text(json.dumps(preview,indent=2)+'\n')
    if send:jobs.tick()
    result=jobs.get(auth,job['job_id']);view=f.get(auth)
    report=dict(checked_at=datetime.now(timezone.utc).isoformat(),state=result['state'] if send else 'prepared_not_sent',module_id=module,counts=view['counts'],usage=result.get('usage'),error=result.get('error'),
                company_queries=0,company_writes=0,live_application_mutations=0,copied_connector_secrets=0,model_calls=int(send),
                payload_characters=len(json.dumps(payload)),sources=[dict(title=d['title'],kind=d['kind'],sha256=d['sha256']) for d in payload['documents']],
                isolated_store=str(directory/'isolated.sqlite3'))
    (directory/'report.json').write_text(json.dumps(report,indent=2)+'\n')
    return report


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--directory',type=Path,required=True);parser.add_argument('--module',default='warranty');parser.add_argument('--send',action='store_true');args=parser.parse_args()
    try:
        report=run(args.directory,args.module,args.send);print(json.dumps(report,indent=2));sys.exit(0 if report['state'] in ('succeeded','prepared_not_sent') else 1)
    except Exception as exc:
        print(json.dumps(dict(state='unavailable',error_type=type(exc).__name__)));sys.exit(1)
