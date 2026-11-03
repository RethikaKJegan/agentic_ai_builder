"""Phase 1 integration check in an isolated private store.

Reads source application with SQLite mode=ro; copies safe metadata, definitions and
policy artifacts, never credentials or company records. --live-sources adds the
existing bounded aggregate-only company probe. No model calls or source writes.
"""
import argparse
from collections import Counter
from contextlib import contextmanager
import json
from pathlib import Path
import sqlite3
import sys
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
from workflow_api.business_knowledge import BusinessKnowledge
from workflow_api.business_knowledge_model import digest
from workflow_api.business_ontology import BusinessOntology
from workflow_api.business_compiler import BusinessCompiler
from workflow_api.business_policies import BusinessPolicies
from workflow_api.storage import WorkflowStore
from workflow_api.data_sources import DataSources


@contextmanager
def readonly(path):
    db=sqlite3.connect(path.resolve().as_uri()+'?mode=ro',uri=True)
    try:
        db.execute('PRAGMA query_only=ON');db.execute('BEGIN');yield db
    finally:db.rollback();db.close()


def run(database,directory,scope,live_sources=False):
    directory.mkdir(mode=0o700,parents=True,exist_ok=False)
    auth=dict(subject=dict(workspace_id=scope[0],subject_id=scope[1]),decision='allow',permissions=['tools.read','tools.assign'],scopes=['workspace:read','workspace:write'])
    def originals():
        with readonly(database) as db:
            versions=db.execute('SELECT version_id,document FROM business_ontology_versions WHERE workspace=? AND owner=? ORDER BY version_id',scope).fetchall()
            workspace=db.execute('SELECT document FROM business_ontology_workspaces WHERE workspace=? AND owner=? AND ontology_id=?',(*scope,'simpson')).fetchone()
        return versions,workspace
    before=originals();latest=max((json.loads(r[1]) for r in before[0]),key=lambda x:x['revision'])
    store=WorkflowStore(directory/'isolated.sqlite3');DataSources(store,{});ontology=BusinessOntology(store);BusinessPolicies(ontology,None,None)
    with readonly(database) as source,store.transaction() as db:
        for cid in latest['workspace']['sources'].values():
            connection=json.loads(source.execute('SELECT document FROM data_source_connections WHERE connection_id=? AND workspace=? AND owner=?',(cid,*scope)).fetchone()[0])
            safe={k:connection.get(k) for k in ('connection_id','name','engine','connection_status','metadata_revision','generation')}
            db.execute('INSERT INTO data_source_connections VALUES (?,?,?,?,?)',(cid,*scope,None,json.dumps(safe)))
            row=source.execute('SELECT document FROM data_source_snapshots WHERE connection_id=? AND revision=?',(cid,connection['metadata_revision'])).fetchone()
            if row:
                metadata=json.loads(row[0]);safe_metadata=dict(datasets=[dict(name=d['name'],fields=[dict(name=f['name'],types=f.get('types',[])) for f in d['fields']]) for d in metadata['datasets']])
                db.execute('INSERT INTO data_source_snapshots VALUES (?,?,?)',(cid,connection['metadata_revision'],json.dumps(safe_metadata)))
        db.execute('INSERT INTO business_ontology_workspaces VALUES (?,?,?,?)',(*scope,'simpson',before[1][0]))
        for vid,document in before[0]:db.execute('INSERT INTO business_ontology_versions VALUES (?,?,?,?)',(*scope,vid,document))
        for table,columns in [('business_policy_heads','workspace,owner,policy_key,revision'),('business_policy_versions','workspace,owner,policy_id,policy_key,revision,request_key,fingerprint,document')]:
            if source.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",(table,)).fetchone():
                for row in source.execute('SELECT '+columns+' FROM '+table+' WHERE workspace=? AND owner=?',scope):db.execute('INSERT INTO '+table+' VALUES ('+','.join('?' for _ in row)+')',row)
    service=BusinessKnowledge(ontology)
    result=service.import_package(auth,dict(expected_revision=latest['revision'],request_key='phase1_isolated_integration'))
    saved=ontology.version(auth,result['version_id']);inspection=service.inspect(auth,result['version_id'],'inspection:inspection_report')
    compiled=BusinessCompiler(ontology).compile(auth,result['version_id'],{})['compilation']
    k=saved['knowledge']
    report=dict(status='succeeded',base_revision=latest['revision'],isolated_version_id=result['version_id'],isolated_revision=result['revision'],concepts=len(saved['concepts']),relationships=len(saved['relationships']),parent_links=sum(bool(c['parent_id']) for c in saved['concepts']),mapping_count=len(k['source_mappings']),mapping_status=dict(Counter(m['status'] for m in k['manifest']['source_status'] if m['id'].startswith('mapping:'))),mapping_issues=[m for m in k['manifest']['source_status'] if m['id'].startswith('mapping:') and m['status']!='observed_in_metadata'],policy_revisions_pinned=len(k['manifest']['policy_refs']),compilation=compiled['report']['status'],concept_inspection_has_mappings=bool(inspection['mappings']),company_writes=0,live_application_writes=0,model_calls=0,copied_credentials=0,source_ontology_unchanged=originals()==before,definition_sha256=digest(saved))
    if live_sources:
        from scripts.verify_simpson_business_sources import verify
        live=verify(database);(directory/'live-source-check.json').write_text(json.dumps(live,indent=2)+'\n')
        report['live_source_check']=dict(complete=live['complete'],status_counts=live['status_counts'],limits=live['limits'],configuration_unchanged=live['connection_configuration_unchanged_during_probe'])
    (directory/'report.json').write_text(json.dumps(report,indent=2)+'\n')
    if not report['source_ontology_unchanged'] or compiled['report']['status']!='passed' or live_sources and not report['live_source_check']['complete']:raise ValueError('Integration check did not pass')
    return report


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--database',type=Path,required=True);p.add_argument('--directory',type=Path,required=True);p.add_argument('--workspace',required=True);p.add_argument('--owner',required=True);p.add_argument('--live-sources',action='store_true');a=p.parse_args()
    try:
        print(json.dumps(run(a.database,a.directory,(a.workspace,a.owner),a.live_sources),indent=2))
    except Exception as e:
        print(json.dumps(dict(status='failed',error_type=type(e).__name__,code=getattr(e,'code',None),message=str(e) if getattr(e,'code',None) else 'Inspect source availability and scoped inputs.')));sys.exit(1)
