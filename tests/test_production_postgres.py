"""Actual PostgreSQL connection loss, contention, deadlock and isolated restore."""
import json
import os
from pathlib import Path
import subprocess
from threading import Barrier
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import urlsplit,parse_qs

import pytest
from tests.test_distributed_postgres import pg
from tests import test_production_reliability as checks
from tests.test_distributed_execution import approved
from workflow_api.postgres import DatabaseFailure


@pytest.mark.parametrize('check',[checks.test_shared_credential_quota_is_atomic_across_accounts_and_reconstruction,checks.test_reserved_slots_cannot_be_consumed_by_another_account])
def test_shared_capacity_on_postgres(pg,check):check(pg)


def test_connection_loss_rolls_back_and_next_transaction_recovers(pg):
    import psycopg
    with pytest.raises(DatabaseFailure) as exc:
        with pg.store.transaction() as db:
            pid=db.connection.execute('SELECT pg_backend_pid()').fetchone()[0]
            # A role can terminate its own backend; no superuser credentials.
            with psycopg.connect(pg.postgres_dsn,autocommit=True) as control:control.execute('SELECT pg_terminate_backend(%s)',(pid,))
            db.execute('CREATE TABLE should_rollback (id TEXT)')
    assert exc.value.retryable
    with pg.store.transaction(write=False) as db:
        assert db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='should_rollback'").fetchone() is None
        assert db.execute('SELECT 1').fetchone()[0]==1


def test_actual_lock_contention_is_classified_and_recovers(pg):
    import psycopg
    lock=psycopg.connect(pg.postgres_dsn)
    try:
        lock.execute("SELECT pg_advisory_xact_lock(hashtextextended(current_database()||':'||current_schema(),0))")
        previous=pg.store.database.busy_timeout_ms;pg.store.database.busy_timeout_ms=50
        try:
            with pytest.raises(DatabaseFailure) as exc:
                with pg.store.transaction():pass
            assert exc.value.category=='contention' and exc.value.retryable
        finally:pg.store.database.busy_timeout_ms=previous
    finally:lock.rollback();lock.close()
    with pg.store.transaction() as db:assert db.execute('SELECT 1').fetchone()[0]==1


def test_postgres_detected_deadlock_is_retryable(pg):
    import psycopg
    from workflow_api.postgres import classify
    with pg.store.transaction() as db:
        db.execute('CREATE TABLE deadlock_probe (id BIGINT PRIMARY KEY, value BIGINT)')
        db.execute('INSERT INTO deadlock_probe VALUES (1,0),(2,0)')
    barrier=Barrier(2)
    def update(order):
        try:
            with psycopg.connect(pg.postgres_dsn) as connection:
                connection.execute('UPDATE deadlock_probe SET value=value+1 WHERE id=%s',(order[0],))
                barrier.wait(timeout=5)
                connection.execute('UPDATE deadlock_probe SET value=value+1 WHERE id=%s',(order[1],))
            return 'committed'
        except psycopg.Error as error:
            failure=classify(error);assert failure.retryable
            return failure.category
    with ThreadPoolExecutor(2) as pool:result=list(pool.map(update,[(1,2),(2,1)]))
    assert sorted(result)==['committed','deadlock']


def test_pg_dump_restore_preserves_approval_history_and_graph(pg,tmp_path):
    import psycopg
    from psycopg import sql
    from workflow_api.account_knowledge import AccountKnowledge
    rid=approved(pg)
    pg.auth['permissions'].append('workflow.plan')
    graph=AccountKnowledge(pg.store)
    pin=graph._sync(pg.auth,'fixture','fixture',{},[dict(node_id='saved',status='reported')],[])
    def state():
        with pg.store.transaction(write=False) as db:
            return (db.execute('SELECT document FROM runtime_runs WHERE run_id=?',(rid,)).fetchone()[0],db.execute('SELECT document FROM runtime_events WHERE run_id=? ORDER BY sequence',(rid,)).fetchall(),graph.get(pg.auth,pin))
    before=state()
    with psycopg.connect(pg.postgres_dsn) as connection:schema=connection.execute('SELECT current_schema()').fetchone()[0]
    assert schema.startswith('check_')
    dump=tmp_path/'backup.dump';dump.touch(mode=0o600)
    from psycopg.conninfo import conninfo_to_dict
    connection_info=conninfo_to_dict(pg.postgres_dsn)
    env={**os.environ,**{'PG'+key.upper():value for key,value in connection_info.items() if key in ('host','port','user','password','options')}}
    env['PGDATABASE']=connection_info['dbname']
    subprocess.run(['/usr/lib/postgresql/16/bin/pg_dump','--format=custom','--no-owner','--schema='+schema,'--file='+str(dump)],env=env,check=True,capture_output=True)
    with psycopg.connect(pg.postgres_dsn,autocommit=True) as connection:connection.execute(sql.SQL('DROP SCHEMA {} CASCADE').format(sql.Identifier(schema)))
    subprocess.run(['/usr/lib/postgresql/16/bin/pg_restore','--dbname='+pg.postgres_dsn,'--no-owner','--exit-on-error',str(dump)],check=True,capture_output=True)
    assert state()==before


@pytest.mark.parametrize('revoked',[False,True])
def test_semantic_polling_refresh_and_revocation_on_postgres(pg,revoked):
    from types import SimpleNamespace
    from workflow_api.account_knowledge import AccountKnowledge
    from workflow_api.knowledge_sync import KnowledgeSyncWorker
    from runtime import RuntimeFailure
    pg.auth['permissions'].append('workflow.plan')
    current=dict(stale=False,revision='one',relationships=[])
    pg.workflows.account_semantic=SimpleNamespace(get=lambda auth:dict(current))
    graph=AccountKnowledge(pg.store,pg.workflows,clock=lambda:pg.now)
    pg.workflows.account_graph=graph
    pin=graph.sync_semantic(pg.auth,pg.workflows.account_semantic)
    current['revision']='two';pg.now+=61
    worker=KnowledgeSyncWorker(pg.workflows,lambda *_:None if revoked else pg.auth,clock=lambda:pg.now)
    result=worker.tick()
    assert result==({'updated':0,'failed':1} if revoked else {'updated':1,'failed':0})
    with pytest.raises(RuntimeFailure):graph.get(pg.auth,pin)
    assert graph.get(pg.auth,pin,historical=True)['revision']==1
