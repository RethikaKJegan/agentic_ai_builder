"""Release evidence must not manufacture production acceptance or replay jobs."""
from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path
import sqlite3
import subprocess
import sys
from unittest.mock import patch
import pytest
from tests.test_business_graph import graph,build
from tests.test_business_compiler import compiled_draft
from tests.test_business_generation import generation
from tests.test_business_ontology import foundation,auth
from tests.test_business_policies import policies,body
from workflow_api.business_release import run,read_owned,inspect,restore,competency_matrix,manifest,digest,ROOT


def audit(x,path,**changes):return run(Path(x.f.store.path),path,changes.get('workspace','one'),changes.get('owner','alice'),'2026-01-01','2026-12-31')


def test_scoped_recovery_preserves_artifacts_but_never_accepts_production(graph,tmp_path):
    x=graph;g=build(x);database=Path(x.f.store.path);calls=len(x.reader.calls)
    with x.f.store.transaction() as db:
        db.execute('INSERT INTO business_ontology_versions SELECT workspace,?,version_id,document FROM business_ontology_versions WHERE owner=?',('foreign','alice'))
    before=sha256(database.read_bytes()).hexdigest()
    with patch('socket.create_connection',side_effect=AssertionError('No network')):result=audit(x,tmp_path/'audit')
    assert result['recovery']['status']=='passed' and result['public_release_status']=='not_ready' and result['accepted_business_answers']==0
    assert result['artifact_checks']['graphs'][0]['graph_id']==g['graph_id']
    assert result['recovery']['snapshot_sha256']==result['recovery']['restored_sha256']
    assert result['release_gates'][0]['status']=='blocked_by_current_code' and len(result['competency_matrix'])==22
    assert len(x.reader.calls)==calls and sha256(database.read_bytes()).hexdigest()==before
    assert result['company_queries']==result['company_writes']==result['model_calls']==result['input_store_writes']==result['services_started']==0
    with sqlite3.connect(tmp_path/'audit/ontology-artifacts.sqlite3') as db:
        tables={r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        assert 'data_source_connections' not in tables and not any('credential' in t for t in tables)
        assert db.execute("SELECT COUNT(*) FROM business_ontology_versions WHERE owner='foreign'").fetchone()[0]==0
    assert (tmp_path/'audit').stat().st_mode&0o777==0o700 and (tmp_path/'audit/ontology-artifacts.sqlite3').stat().st_mode&0o777==0o600
    assert (tmp_path/'audit/report.json').stat().st_mode&0o777==0o600


@pytest.mark.parametrize('state',['queued','running'])
def test_policy_history_and_pending_jobs_are_retained_without_execution(policies,tmp_path,state):
    x,service,source=policies;p=service.save(auth(),body(source));build(x)
    with x.f.store.transaction() as db:
        db.execute('INSERT INTO business_ontology_jobs VALUES (?,?,?,?,?,?,?,?,?,?)',('active_fixture','one','alice','active_release_key','fp',state,json.dumps({'module_id':'warranty'}),'claim' if state=='running' else None,10.0,1.0))
    result=audit(x,tmp_path/'audit');restored=read_owned(tmp_path/'audit/ontology-artifacts.sqlite3','one','alice')
    assert result['artifact_checks']['policy_revisions']==1 and result['recovery']['active_jobs']==1
    assert next(r for r in restored['business_ontology_jobs'] if r['job_id']=='active_fixture')['state']==state
    assert json.loads(restored['business_policy_versions'][0]['document'])==p
    assert result['recovery']['workers_started']==result['recovery']['model_jobs_replayed']==0
    with sqlite3.connect(tmp_path/'audit/ontology-artifacts.sqlite3') as db:
        with pytest.raises(sqlite3.IntegrityError):
            db.execute('INSERT INTO business_ontology_jobs SELECT ?,workspace,owner,?,fingerprint,state,document,claim,deadline,created FROM business_ontology_jobs WHERE job_id=?',('second_active','different_key','active_fixture'))


@pytest.mark.parametrize('scope',[{'owner':'foreign'},{'workspace':'foreign'}])
def test_foreign_scope_fails_without_creating_output(graph,tmp_path,scope):
    with pytest.raises(ValueError):audit(graph,tmp_path/'audit',**scope)
    assert not (tmp_path/'audit').exists()


@pytest.mark.parametrize('damage',['source','version','graph','compilation','policy'])
def test_corrupt_artifacts_are_not_restored(policies,tmp_path,damage):
    x,service,source=policies;service.save(auth(),body(source));build(x);data=read_owned(x.f.store.path,'one','alice')
    table={'source':'business_ontology_documents','version':'business_ontology_versions','graph':'business_ontology_graphs','compilation':'business_ontology_compilations','policy':'business_policy_versions'}[damage]
    row=data[table][-1];doc=json.loads(row['document'])
    if damage=='source':doc['text']+=' changed'
    elif damage=='version':doc['version_id']='foreign'
    elif damage=='graph':doc['records'][0]['fields'][0]['value']='changed'
    elif damage=='compilation':doc['artifacts'][0]['content']+=' changed'
    else:doc['title']='changed'
    row['document']=json.dumps(doc)
    with pytest.raises(Exception):inspect(data,'2026-01-01','2026-12-31')


def test_existing_output_and_reversed_window_are_never_overwritten(graph,tmp_path):
    target=tmp_path/'exists';target.mkdir();sentinel=target/'keep';sentinel.write_text('keep')
    with pytest.raises(ValueError):audit(graph,target)
    assert sentinel.read_text()=='keep'
    with pytest.raises(ValueError):run(Path(graph.f.store.path),tmp_path/'bad','one','alice','2026-12-31','2026-01-01')
    assert not (tmp_path/'bad').exists()


def test_modified_recovery_and_input_changes_fail_closed(graph,tmp_path):
    x=graph;build(x)
    def corrupt(data,path):
        restore(data,path)
        with sqlite3.connect(path) as db:db.execute('DELETE FROM business_ontology_graphs')
    with patch('workflow_api.business_release.restore',side_effect=corrupt):
        with pytest.raises(ValueError,match='Recovery verification'):audit(x,tmp_path/'bad')
    original=read_owned(x.f.store.path,'one','alice');changed=deepcopy(original);changed['business_ontology_events']=[]
    with patch('workflow_api.business_release.read_owned',side_effect=[original,original,changed]):
        with pytest.raises(ValueError,match='Input changed'):audit(x,tmp_path/'drift')


def test_matrix_and_manifest_cannot_turn_tool_support_into_acceptance():
    rows=competency_matrix();assert len(rows)==22 and {r['acceptance'] for r in rows}=={'not_accepted'}
    assert all(r['prerequisites'] and r['implementation_gap'] and r['inspection_tool'] for r in rows)
    assert 'not verified failure date' in rows[0]['implementation_gap']
    assert 'not all claims' in rows[2]['implementation_gap'] and 'currency' in rows[19]['implementation_gap']
    files=manifest();assert files['files_sha256']==digest(files['files'])
    assert not any('.env' in p or '.local' in p for p in files['files'])
    assert all(sha256((ROOT/path).read_bytes()).hexdigest()==value for path,value in files['files'].items())


def test_cli_exit_two_means_completed_not_ready(graph,tmp_path):
    build(graph);output=tmp_path/'cli'
    args=[sys.executable,str(ROOT/'scripts/check_business_release.py'),'--database',graph.f.store.path,'--directory',str(output),'--workspace','one','--owner','alice','--period-start','2026-01-01','--period-end','2026-12-31']
    result=subprocess.run(args,cwd=ROOT,capture_output=True,text=True,timeout=30)
    assert result.returncode==2 and json.loads(result.stdout)['public_release_status']=='not_ready'
    again=subprocess.run(args,cwd=ROOT,capture_output=True,text=True,timeout=30)
    assert again.returncode==1 and json.loads(again.stdout)['status']=='unavailable'


def test_unknown_artifact_columns_and_overlarge_snapshots_require_review(graph):
    path=graph.f.store.path
    with graph.f.store.transaction() as db:db.execute('ALTER TABLE business_ontology_events ADD COLUMN future_field TEXT')
    with pytest.raises(ValueError,match='schema changed'):read_owned(path,'one','alice')
    with graph.f.store.transaction() as db:
        db.execute('ALTER TABLE business_ontology_events DROP COLUMN future_field')
        db.executemany('INSERT INTO business_ontology_events VALUES (?,?,?,?)',[('one','alice','bound_'+str(i),'{}') for i in range(2001)])
    with pytest.raises(ValueError,match='row bound'):read_owned(path,'one','alice')


def test_missing_exports_and_torn_policy_head_cannot_pass(policies):
    x,service,source=policies;service.save(auth(),body(source));data=read_owned(x.f.store.path,'one','alice')
    broken=deepcopy(data);row=broken['business_ontology_compilations'][0];doc=json.loads(row['document']);doc['artifacts']=[];row['document']=json.dumps(doc)
    with pytest.raises(ValueError,match='exports missing'):inspect(broken,'2026-01-01','2026-12-31')
    broken=deepcopy(data);broken['business_policy_heads'][0]['revision']+=1
    with pytest.raises(ValueError,match='history/head mismatch'):inspect(broken,'2026-01-01','2026-12-31')
