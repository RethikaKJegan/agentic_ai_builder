"""New distributed invariants on a disposable PostgreSQL schema."""
import json
import multiprocessing
import sqlite3
import time

import pytest

from runtime import RuntimeService
from runtime.graph import GraphRunner
from workflow_api.account_knowledge import AccountKnowledge
from tests import test_runtime as runtime_fixtures
from tests.test_postgres_backend import PostgresFixture
from tests import test_distributed_execution as checks


class ToolPostgresFixture(PostgresFixture,runtime_fixtures.ToolGraphTests):
    __test__=False


@pytest.fixture
def pg():
    f=ToolPostgresFixture();f.setUp();f.configure();f.put()
    f.now=time.time();f.runtime.clock=lambda:f.now
    try:yield f
    finally:f.doCleanups()


@pytest.mark.parametrize('check',[
    checks.test_admission_is_atomic_and_idempotent,
    checks.test_account_concurrency_defers_without_invoking_or_resetting_budget,
    checks.test_provider_rate_window_is_durable_and_tenant_scoped,
    checks.test_four_active_consumers_never_duplicate_the_same_tool,
    checks.test_fair_polling_does_not_let_simpson_backlog_hide_subway,
])
def test_new_invariants_on_postgres(pg,check):check(pg)


def test_graph_revisions_and_owner_isolation_on_postgres(pg):
    from copy import deepcopy
    pg.auth['permissions'].append('workflow.plan')
    g=AccountKnowledge(pg.store,clock=lambda:pg.now)
    pin=g._sync(pg.auth,'controlled','fixture',{},[{'node_id':'a','status':'reported'}],[])
    assert g._sync(pg.auth,'controlled','fixture',{},[{'node_id':'a','status':'reported'}],[])==pin
    other=deepcopy(pg.auth);other['subject']['subject_id']='different-owner'
    from runtime import RuntimeFailure
    with pytest.raises(RuntimeFailure):g.get(other,pin)
    new=g._sync(pg.auth,'controlled','fixture',{},[{'node_id':'b','status':'reported'}],[])
    assert new['revision']==2 and g.get(pg.auth,pin,historical=True)['stale']


def test_four_real_processes_cannot_duplicate_one_postgres_effect(pg,tmp_path):
    rid=checks.approved(pg)
    ledger=tmp_path/'provider.sqlite3'
    with sqlite3.connect(ledger) as db:db.execute('CREATE TABLE effects (reference TEXT PRIMARY KEY)')
    ctx=multiprocessing.get_context('fork');start=ctx.Event();processes=[]
    def consume():
        start.wait(15)
        runtime=RuntimeService(pg.workflows)
        def effect(grant,inputs,reference):
            time.sleep(.1)
            with sqlite3.connect(ledger) as db:db.execute('INSERT INTO effects VALUES (?)',(reference,))
            return {'message_id':'controlled'}
        pg.connector.invoke=effect
        GraphRunner(runtime,connectors={'smtp_send_email':pg.connector}).advance(rid,pg.auth)
    try:
        for _ in range(4):
            p=ctx.Process(target=consume);p.start();processes.append(p)
        start.set()
        for p in processes:p.join(30);assert p.exitcode==0
        assert pg.runtime.get_run(rid,pg.auth)['status']=='completed'
        with sqlite3.connect(ledger) as db:assert db.execute('SELECT COUNT(*) FROM effects').fetchone()[0]==1
    finally:
        for p in processes:
            if p.is_alive():p.kill();p.join(5)


@pytest.mark.parametrize('boundary',['before_execution','during_call','after_effect','after_receipt','after_checkpoint','approval_wait'])
def test_killed_postgres_worker_preserves_effect_boundary(pg,tmp_path,boundary,monkeypatch):
    from tests import test_process_recovery as recovery
    recovery.test_real_process_termination_preserves_effects_and_checkpoints(pg,tmp_path,boundary,monkeypatch)
