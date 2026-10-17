"""Phase 2 lock, activation race and crash-recovery regressions; no live providers."""
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
import json
import sqlite3
from threading import Barrier
import time

from fastapi.testclient import TestClient
import pytest
from tests import test_lifecycle as fixtures
from workflow_api.lifecycle import LifecycleFailure, LifecycleService
from workflow_api.main import create_app, COOKIE
from workflow_api.storage import WorkflowStore


@pytest.fixture
def context():
    fixture=fixtures.LifecycleTests();fixture.setUp()
    try:yield fixture
    finally:fixture.tearDown()


def test_read_only_transactions_reject_accidental_mutations(context):
    with pytest.raises(sqlite3.OperationalError):
        with context.service.store.transaction(write=False) as db:
            db.execute('DELETE FROM revisions')
    with context.service.store.transaction(write=False) as db:
        assert db.execute('SELECT COUNT(*) FROM revisions').fetchone()[0]==1


def test_runtime_and_workspace_reads_do_not_acquire_writer_lock(context):
    context.auth['permissions']+=['workflow.edit']
    app=create_app(context.service,dev_auth=True,roles=['admin'])
    client=TestClient(app);session=client.get('/session');client.cookies.set(COOKIE,session.cookies[COOKIE],path='/')
    # Create the valid deterministic run before holding a writer reservation.
    request={'request_id':'req_read','idempotency_key':'phase2_read_check','payload':{'workflow_id':context.workflow['workflow_id'],'workflow_version':1,'inputs':{'request_text':'read check'}}}
    run=context.runtime.create_run(request,context.auth)
    with sqlite3.connect(context.path,timeout=.05) as writer:
        writer.execute('BEGIN IMMEDIATE')
        assert context.runtime.get_run(run['run_id'],context.auth)['run_id']==run['run_id']
        assert context.runtime.list_runs(context.auth)['total']==1
        assert context.runtime.list_approvals(context.auth)['items']==[]
        assert context.runtime.events(run['run_id'],context.auth)['total']>=1
        assert context.runtime.monitoring(context.auth)['runs']['total']==1
        assert context.service.lifecycle.overview(context.auth)['items']
        assert client.get('/workspace/settings').status_code==200
        writer.rollback()
    client.close()


def test_busy_timeout_is_bounded_and_classified(tmp_path,caplog):
    store=WorkflowStore(tmp_path/'busy.sqlite3',busy_timeout_ms=25)
    with sqlite3.connect(store.path) as writer:
        writer.execute('BEGIN IMMEDIATE')
        started=time.monotonic()
        with pytest.raises(sqlite3.OperationalError):
            with store.transaction():pass
        assert time.monotonic()-started<.75
        writer.rollback()
    assert store.metrics['contention']==1
    assert any(getattr(record,'database_category',None)=='contention' for record in caplog.records)
    assert not any('deadlock' in record.message.lower() for record in caplog.records)


def test_activation_persists_preparation_before_external_call_without_locks(context):
    original=context.adapter.prepare;observed=[]
    def prepare(trigger):
        with sqlite3.connect(context.path,timeout=.05) as writer:
            writer.execute('BEGIN IMMEDIATE')
            operation=json.loads(writer.execute('SELECT document FROM lifecycle_operations').fetchone()[0])
            identity=json.loads(writer.execute('SELECT document FROM lifecycle_identities').fetchone()[0])
            assert operation['state']=='preparing'
            assert identity['active'] is False
            observed.append(trigger['binding_id']);writer.rollback()
        return original(trigger)
    context.adapter.prepare=prepare
    active=context.activate()
    assert active['release']['state']=='active'
    assert observed==['binding_main']


def test_revision_change_during_provider_preparation_aborts_and_compensates(context):
    original=context.adapter.prepare
    def prepare(trigger):
        with context.service.store.transaction() as db:
            changed=deepcopy(context.workflow);changed['metadata']['changed_during_prepare']=True
            context.service.store.put(db,'local-workspace',changed)
        return original(trigger)
    context.adapter.prepare=prepare
    with pytest.raises(LifecycleFailure) as failure:context.activate()
    assert failure.value.code=='REVISION_CONFLICT'
    with context.service.store.transaction(write=False) as db:
        assert db.execute('SELECT COUNT(*) FROM lifecycle_active').fetchone()[0]==0
        assert json.loads(db.execute('SELECT document FROM lifecycle_operations').fetchone()[0])['state']=='failed'
    assert 'binding_main' in context.adapter.cleaned


def test_two_preparations_cannot_activate_conflicting_releases(context):
    barrier=Barrier(2);original=context.adapter.prepare
    def prepare(trigger):
        barrier.wait(timeout=5)
        return original(trigger)
    context.adapter.prepare=prepare
    def activate(index):
        try:return context.activate(key=f'concurrent_activation_{index}',triggers=[context.trigger(binding_id=f'binding_{index}')])
        except LifecycleFailure as exc:return exc.code
    with ThreadPoolExecutor(max_workers=2) as pool:results=list(pool.map(activate,[1,2]))
    assert sum(isinstance(result,dict) for result in results)==1
    assert 'RELEASE_CONFLICT' in results
    with context.service.store.transaction(write=False) as db:
        assert db.execute("SELECT COUNT(*) FROM lifecycle_releases WHERE state='active'").fetchone()[0]==1
        states=[json.loads(row[0])['state'] for row in db.execute('SELECT document FROM lifecycle_operations')]
    assert sorted(states)==['failed','succeeded']


def test_same_key_retry_during_preparation_does_not_repeat_provider_setup(context):
    original=context.adapter.prepare;replays=[]
    def prepare(trigger):
        replays.append(context.activate())
        return original(trigger)
    context.adapter.prepare=prepare
    active=context.activate()
    assert replays[0]['operation']['state']=='preparing'
    assert active['release']['release_id']==replays[0]['release']['release_id']
    assert context.adapter.prepared==['binding_main']
    assert context.activate()==active


def test_crashed_preparation_is_lease_aware_and_recoverable(context):
    def crash(_trigger):raise SystemExit('simulated process interruption')
    context.adapter.prepare=crash
    with pytest.raises(SystemExit):context.activate()
    restarted=LifecycleService(context.service,clock=lambda:context.now,adapter=context.adapter)
    with context.service.store.transaction(write=False) as db:
        assert db.execute('SELECT state FROM lifecycle_releases').fetchone()[0]=='preparing'
    context.now+=1801
    restarted.reconcile_cleanup('local-workspace')
    with context.service.store.transaction(write=False) as db:
        assert db.execute('SELECT state FROM lifecycle_releases').fetchone()[0]=='failed'
        assert json.loads(db.execute('SELECT document FROM lifecycle_operations').fetchone()[0])['state']=='failed'
        assert db.execute('SELECT COUNT(*) FROM lifecycle_active').fetchone()[0]==0


def test_disable_and_reconciliation_cleanup_do_not_hold_locks(context):
    active=context.activate();original=context.adapter.cleanup
    def cleanup(trigger):
        with sqlite3.connect(context.path,timeout=.05) as writer:
            writer.execute('BEGIN IMMEDIATE');writer.rollback()
        return original(trigger)
    context.adapter.cleanup=cleanup;context.adapter.cleanup_result=False
    result=context.service.lifecycle.disable({'idempotency_key':'disable_outside_locks','payload':{'workflow_id':context.workflow['workflow_id'],'expected_release_id':active['release']['release_id']}},context.auth)
    assert result['operation']['state']=='cleanup_pending'
    context.adapter.cleanup_result=True
    assert context.service.lifecycle.reconcile_cleanup('local-workspace')==['binding_main']


def test_invalid_transaction_state_is_distinct_from_contention(context,caplog):
    with pytest.raises(sqlite3.OperationalError):
        with context.service.store.transaction() as db:db.execute('BEGIN IMMEDIATE')
    assert any(getattr(record,'database_category',None)=='transaction_state' for record in caplog.records)
    assert context.service.store.metrics['contention']==0
