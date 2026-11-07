"""Production qualification improvements with explicit controlled failure models."""
from copy import deepcopy
import json
import sqlite3
from concurrent.futures import ThreadPoolExecutor

import pytest

from runtime import RuntimeFailure
from tests.test_distributed_execution import f,approved
from workflow_api.resource_limits import ResourceControls,ResourcePolicy,CapacityDeferred
from workflow_api.operational_alerts import evaluate


def test_shared_credential_quota_is_atomic_across_accounts_and_reconstruction(f):
    policy=ResourcePolicy(provider_per_minute={'smtp':10},shared_provider_per_minute={'shared_mail':1},shared_credential_buckets={'smtp:cred_a':'shared_mail','smtp:cred_b':'shared_mail'})
    c=ResourceControls(f.store,policy)
    def attempt(workspace,credential):
        try:
            with f.store.transaction() as db:c.reserve_provider(db,workspace,'smtp',f.now,credential)
            return 'reserved'
        except CapacityDeferred as e:return e.code
    with ThreadPoolExecutor(2) as pool:
        results=list(pool.map(lambda args:attempt(*args),[('simpson','cred_a'),('subway','cred_b')]))
    assert sorted(results)==['SHARED_PROVIDER_RATE_LIMITED','reserved']
    c=ResourceControls(f.store,policy)
    with f.store.transaction(write=False) as db:
        assert db.execute('SELECT SUM(used) FROM runtime_provider_windows').fetchone()[0]==1
        assert db.execute('SELECT SUM(used) FROM runtime_shared_provider_windows').fetchone()[0]==1
    f.now=(int(f.now//60)+1)*60+1
    assert attempt('subway','cred_b')=='reserved'


def test_reserved_slots_cannot_be_consumed_by_another_account(f):
    c=ResourceControls(f.store,ResourcePolicy(total_concurrency=2,reserved_per_account={'subway':1}))
    rid=approved(f)
    with f.store.transaction() as db:
        r=f.runtime.load(db,rid,f.auth);r.update(status='running',lease_until=f.now+30);f.runtime.save(db,r)
        with pytest.raises(CapacityDeferred) as error:c.claim(db,dict(run_id='new',workspace_id='local-workspace'),f.now)
        assert error.value.code=='SHARED_CAPACITY_EXCEEDED'
        c.claim(db,dict(run_id='subway_run',workspace_id='subway'),f.now)
    for args in [dict(total_concurrency=1,reserved_per_account={'subway':2}),dict(shared_credential_buckets={'smtp:secret':'unconfigured'})]:
        with pytest.raises(ValueError):ResourcePolicy(**args)


def test_alert_conditions_are_deterministic_and_do_not_include_source_records():
    result=evaluate(dict(workers=[],queued=100,oldest_queue_seconds=301,dead_letter=2,unknown_effects=1,failed_runs=1,stale_graphs=3))
    assert {a['code'] for a in result}=={'WORKERS_UNAVAILABLE','QUEUE_BACKLOG','QUEUE_WAIT_EXCEEDED','DEAD_LETTER_JOBS','RECONCILIATION_REQUIRED','RUN_FAILURES','KNOWLEDGE_REFRESH_REQUIRED'}
    assert all(set(a)=={'code','severity','count','action'} for a in result)
    assert evaluate(dict(workers=[dict(state='active')]))==[]


def test_sqlite_main_and_effect_journal_restore_preserves_completed_effect(f,tmp_path):
    from connector_extension.common import EffectJournal
    from runtime import RuntimeService
    from runtime.graph import GraphRunner
    from workflow_api.storage import WorkflowStore
    from workflow_api.service import WorkflowService
    rid=approved(f);(tmp_path/'journal').mkdir();journal=EffectJournal(tmp_path/'journal')
    original=f.connector.invoke
    def action(grant,inputs,key):
        result=journal.perform(grant['tool_id'],key,inputs,lambda:original(grant,inputs,key))
        return result
    f.connector.invoke=action
    assert f.graph.advance(rid,f.auth)['status']=='completed'
    with f.store.transaction(write=False) as db:
        before=db.execute('SELECT document FROM runtime_runs WHERE run_id=?',(rid,)).fetchone()[0]
        events=db.execute('SELECT document FROM runtime_events WHERE run_id=? ORDER BY sequence',(rid,)).fetchall()
    destination=tmp_path/'restored.sqlite'
    with sqlite3.connect(f.store.path) as source,sqlite3.connect(destination) as target:source.backup(target)
    # Restore the actual journal database using SQLite backup, not file-copying WAL.
    files=list((tmp_path/'journal').glob('*.sqlite*'))
    assert files
    for index,path in enumerate(files):
        with sqlite3.connect(path) as source,sqlite3.connect(tmp_path/f'journal-restore-{index}.sqlite') as target:
            source.backup(target);assert target.execute('PRAGMA integrity_check').fetchone()[0]=='ok'
            assert list(source.iterdump())==list(target.iterdump())
    rt=RuntimeService(WorkflowService(WorkflowStore(destination),registry_adapter=f.workflows.registry_adapter))
    with rt.store.transaction(write=False) as db:
        assert db.execute('SELECT document FROM runtime_runs WHERE run_id=?',(rid,)).fetchone()[0]==before
        assert db.execute('SELECT document FROM runtime_events WHERE run_id=? ORDER BY sequence',(rid,)).fetchall()==events
    assert GraphRunner(rt,connectors={'smtp_send_email':f.connector}).advance(rid,f.auth)['status']=='completed'
    assert len(f.invocations)==1


def test_alert_api_requires_admin_and_owns_workspace_scope(tmp_path):
    from fastapi.testclient import TestClient
    from workflow_api.main import create_app
    for roles,expected in [(['viewer'],403),(['admin'],200)]:
        app=create_app(database=tmp_path/(roles[0]+'.sqlite'),dev_auth=True,roles=roles,runtime_enabled=True,start_workers=False)
        with TestClient(app) as client:
            assert client.get('/operational-alerts').status_code==401
            client.get('/session');client.cookies.set('builder_dev_session',client.cookies.get('builder_dev_session'),path='/')
            response=client.get('/operational-alerts');assert response.status_code==expected
            assert client.get('/worker-health').status_code==expected
            if expected==200:
                assert client.get('/operational-alerts?workspace=other').status_code==400
                assert 'WORKERS_UNAVAILABLE' in str(response.json())


def test_run_knowledge_requires_current_owner_and_omits_row_values(f):
    from fastapi.testclient import TestClient
    from workflow_api.main import create_app
    from workflow_api.account_knowledge import AccountKnowledge
    from runtime.graph import GraphRunner
    f.auth['permissions'].append('workflow.plan')
    graph=AccountKnowledge(f.store,f.workflows);f.workflows.account_graph=graph
    rid=approved(f)
    pin=graph._sync(f.auth,'fixture','fixture',{},[dict(node_id='n',kind='record',reference='r',status='reported',values={'private':'source_value'})],[])
    with f.store.transaction() as db:
        workflow=f.store.get(db,'local-workspace',f.workflow['workflow_id'],1)
        workflow['metadata']['account_graph_pin']=pin;f.store.put(db,'local-workspace',workflow)
    f.workflows.runtime_runner=f.graph
    # Route auth subject is the app's existing local-builder, not this operator.
    app=create_app(f.workflows,dev_auth=True,roles=['admin'],runtime_enabled=True,start_workers=False)
    with TestClient(app) as client:
        client.get('/session');client.cookies.set('builder_dev_session',client.cookies.get('builder_dev_session'),path='/')
        response=client.get('/runs/'+rid+'/knowledge')
        assert response.status_code in (403,404),response.text
        assert 'source_value' not in response.text
        app.state.workflow_auth.clear();app.state.workflow_auth.update(deepcopy(f.auth))
        response=client.get('/runs/'+rid+'/knowledge')
        assert response.status_code==200,response.text
        assert response.json()['data']['projections'][0]['nodes'][0]['reference']=='r'
        assert 'source_value' not in response.text


def test_actual_tool_dispatch_resolves_shared_bucket_from_trusted_registry(f):
    ids=[approved(f,index) for index in range(2)]
    policy=ResourcePolicy(shared_provider_per_minute={'mail_shared':1},shared_credential_buckets={'smtp:cred_test':'mail_shared'})
    f.runtime.resource_controls=ResourceControls(f.store,policy)
    assert f.graph.advance(ids[0],f.auth)['status']=='completed'
    assert f.graph.advance(ids[1],f.auth)['status']=='running'
    assert len(f.invocations)==1
    with f.store.transaction(write=False) as db:
        run=f.runtime.load(db,ids[1],f.auth)
        assert run['available_at']>f.now and run['usage']=={}
        event=json.loads(db.execute("SELECT document FROM runtime_events WHERE run_id=? AND json_extract(document,'$.event_type')='run.backpressure'",(ids[1],)).fetchone()[0])
        assert event['details']['error_code']=='SHARED_PROVIDER_RATE_LIMITED'
