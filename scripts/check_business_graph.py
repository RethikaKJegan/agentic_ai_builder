"""Bounded real-connector graph check in a fresh private application store.

Reads saved live connection/metadata rows with SQLite mode=ro. Connector secrets
are decrypted in memory only, never copied to the isolated store or output. The
prior real-model draft is copied locally and explicitly mapped for this check.
"""
import argparse
from hashlib import sha256
import json
import os
import re
from pathlib import Path
import sqlite3
import sys
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
from scripts.integration_config import load_env
from workflow_api.storage import WorkflowStore
from workflow_api.data_sources import DataSources
from workflow_api.business_ontology import BusinessOntology
from workflow_api.business_compiler import BusinessCompiler
from workflow_api.business_graph import BusinessGraph


def run(directory,anchor):
    directory.mkdir(mode=0o700,parents=True,exist_ok=False)
    scope=('local-workspace','local-builder');auth=dict(subject=dict(workspace_id=scope[0],subject_id=scope[1]),decision='allow',permissions=['tools.read','tools.assign'],scopes=['workspace:read','workspace:write'])
    with sqlite3.connect((ROOT/'.local/business-ontology/chunk3-payload-review/isolated.sqlite3').resolve().as_uri()+'?mode=ro',uri=True) as db:
        versions=[json.loads(r[0]) for r in db.execute('SELECT document FROM business_ontology_versions WHERE workspace=? AND owner=?',scope)]
    snapshot=max((v for v in versions if v['kind']=='draft'),key=lambda v:v['revision'])
    if not any(c['id']=='warranty:engine_instance' and c['properties']==[dict(name='serial_number',datatype='string',required=True,description='Identifier for the engine instance.')] for c in snapshot['concepts']):raise ValueError('Explicit diagnostic mapping needs review')
    live=(ROOT/'.local/workflows.sqlite3').resolve()
    def owned(db,authority,cid):
        if authority['subject']!=auth['subject'] or cid not in snapshot['workspace']['sources'].values():raise ValueError('Scope mismatch')
        with sqlite3.connect(live.as_uri()+'?mode=ro',uri=True) as source:
            row=source.execute('SELECT secret,document FROM data_source_connections WHERE connection_id=? AND workspace=? AND owner=?',(cid,*scope)).fetchone()
        if not row:raise ValueError('Source unavailable')
        return row[0],json.loads(row[1])
    before={cid:sha256(json.dumps(owned(None,auth,cid),sort_keys=True).encode()).hexdigest() for cid in snapshot['workspace']['sources'].values()}
    store=WorkflowStore(directory/'isolated.sqlite3');manager=DataSources(store,{**load_env(),**os.environ});manager.owned=owned
    f=BusinessOntology(store)
    with store.transaction() as db,sqlite3.connect(live.as_uri()+'?mode=ro',uri=True) as source:
        for cid in snapshot['workspace']['sources'].values():
            _,doc=owned(None,auth,cid)
            safe={k:doc.get(k) for k in ('connection_id','name','engine','connection_status','metadata_revision','generation')}
            db.execute('INSERT INTO data_source_connections VALUES (?,?,?,?,?)',(cid,*scope,None,json.dumps(safe)))
            row=source.execute('SELECT document FROM data_source_snapshots WHERE connection_id=? AND revision=?',(cid,doc['metadata_revision'])).fetchone()
            metadata=json.loads(row[0]);safe_metadata=dict(datasets=[dict(name=d['name'],fields=[dict(name=field['name'],types=field.get('types',[])) for field in d.get('fields',[])]) for d in metadata['datasets']])
            db.execute('INSERT INTO data_source_snapshots VALUES (?,?,?)',(cid,doc['metadata_revision'],json.dumps(safe_metadata)))
        db.execute('INSERT INTO business_ontology_workspaces VALUES (?,?,?,?)',(*scope,'simpson',json.dumps(snapshot['workspace'])))
        db.execute('INSERT INTO business_ontology_versions VALUES (?,?,?,?)',(*scope,snapshot['version_id'],json.dumps(snapshot)))
    compiler=BusinessCompiler(f);compiler.compile(auth,snapshot['version_id'],{})
    cid=snapshot['workspace']['sources']['quality' if anchor=='quality' else 'service'];secret,_=owned(None,auth,cid);config=json.loads(manager.cipher.decrypt(secret.encode()))
    with manager.adapter.connection(config) as client:
        collection,field=('tickets','engineNo') if anchor=='tickets' else ('failedengineanalyses','engineSerialNumber') if anchor=='quality' else ('enginedetails','engineSerialNumber')
        rows=list(client[config['database']][collection].find({field:{'$type':'string'}},{'_id':0,field:1}).limit(20 if anchor=='quality' else 1).max_time_ms(3000))
    valid=[r for r in rows if isinstance(r.get(field),str) and re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9 /_.-]{0,79}',r[field]) and r[field]==r[field].strip()]
    if not valid:raise ValueError('No usable bounded serial anchor')
    serial=valid[0][field];service=BusinessGraph(f,compiler,manager,lambda w,o:auth if (w,o)==scope else None)
    plan=service.plan(auth,snapshot['version_id'])
    result=service.build(auth,snapshot['version_id'],dict(plan_hash=plan['plan_hash'],serial=serial,request_key='isolated_graph_check_001',bindings={'enginedetails':dict(concept_id='warranty:engine_instance',attributes={'serial_number':'engineSerialNumber'})}))
    after={cid:sha256(json.dumps(owned(None,auth,cid),sort_keys=True).encode()).hexdigest() for cid in snapshot['workspace']['sources'].values()}
    report=dict(status='succeeded',anchor=anchor,anchor_candidates=len(rows),anchor_invalid_serials=len(rows)-len(valid),records=len(result['records']),records_by_role={role:sum(r['role']==role for r in result['records']) for role in ('service','quality')},source_references=sum(e['classification']=='source_reference' for e in result['edges']),candidate_edges=sum(e['classification']=='candidate' for e in result['edges']),unresolved=len(result['unresolved']),outcomes=result['outcomes'],instance_validation=result['validation']['status'],mapped_records=result['validation']['mapped_records'],monitoring=result['monitoring']['status'],company_writes=0,model_calls=0,live_application_writes=0,copied_connector_secrets=0,connection_configuration_unchanged=before==after)
    (directory/'report.json').write_text(json.dumps(report,indent=2)+'\n')
    return report

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--directory',type=Path,required=True);p.add_argument('--anchor',choices=['enginedetails','tickets','quality'],default='enginedetails');args=p.parse_args()
    try:print(json.dumps(run(args.directory,args.anchor),indent=2))
    except Exception as exc:
        error=dict(status='unavailable',error_type=type(exc).__name__,error_code=getattr(exc,'code',None))
        if args.directory.exists():(args.directory/'failure.json').write_text(json.dumps(error,indent=2)+'\n')
        print(json.dumps(error));sys.exit(1)
