"""SIGKILL at real persisted boundaries, followed by fresh runtime construction."""
from contextlib import contextmanager
import json
import multiprocessing
import sqlite3
import time

import pytest

from connector_extension.common import EffectJournal
from runtime import RuntimeService
from runtime.graph import GraphRunner
from tests.test_distributed_execution import f,approved
from tests import test_dynamic_delegation as delegation


def kill_at(target):
    ctx=multiprocessing.get_context('fork')
    entered=ctx.Event();hold=ctx.Event()
    process=ctx.Process(target=target,args=(entered,hold))
    process.start()
    try:
        assert entered.wait(20),'Child never reached the requested persisted boundary.'
        process.kill();process.join(5)
        assert process.exitcode==-9
    finally:
        if process.is_alive():process.kill();process.join(5)


@pytest.mark.parametrize('boundary',['before_execution','during_call','after_effect','after_receipt','after_checkpoint','approval_wait'])
def test_real_process_termination_preserves_effects_and_checkpoints(f,tmp_path,boundary,monkeypatch):
    monkeypatch.setenv('BUILDER_RUNTIME_LEASE_SECONDS','30')
    if boundary=='approval_wait':
        rid=f.runtime.create_run(f.request(),f.auth)['run_id']
    else:rid=approved(f)
    ledger=tmp_path/'external.sqlite3'
    with sqlite3.connect(ledger) as db:db.execute('CREATE TABLE effects (reference TEXT PRIMARY KEY)')
    journal=EffectJournal(tmp_path)
    def child(entered,hold):
        runtime=RuntimeService(f.workflows,clock=lambda:f.now)
        connector=f.connector
        def action(reference):
            if boundary=='during_call':entered.set();hold.wait(60)
            with sqlite3.connect(ledger) as db:db.execute('INSERT INTO effects VALUES (?)',(reference,))
            if boundary=='after_effect':entered.set();hold.wait(60)
            return {'message_id':'controlled_message'}
        def invoke(grant,inputs,reference):
            result=journal.perform(grant['tool_id'],reference,inputs,lambda:action(reference))
            if boundary=='after_receipt':entered.set();hold.wait(60)
            return result
        connector.invoke=invoke
        runner=GraphRunner(runtime,connectors={'smtp_send_email':connector})
        if boundary=='before_execution':entered.set();hold.wait(60)
        if boundary=='after_checkpoint':
            transaction=f.store.transaction
            @contextmanager
            def after_commit(*args,**kwargs):
                with transaction(*args,**kwargs) as db:yield db
                with transaction(write=False) as db:
                    run=runtime.load(db,rid,f.auth)
                if run['node_states'].get('send_email')=='completed':entered.set();hold.wait(60)
            f.store.transaction=after_commit
        runner.advance(rid,f.auth)
        if boundary=='approval_wait':entered.set();hold.wait(60)
    kill_at(child)
    with f.store.transaction(write=False) as db:before=f.runtime.load(db,rid,f.auth)
    f.now+=31
    runtime=RuntimeService(f.workflows,clock=lambda:f.now)
    # Safe restart uses the same original connector intent identity.
    def recovered(grant,inputs,reference):
        def effect():
            with sqlite3.connect(ledger) as db:db.execute('INSERT INTO effects VALUES (?)',(reference,))
            return {'message_id':'controlled_message'}
        return journal.perform(grant['tool_id'],reference,inputs,effect)
    f.connector.invoke=recovered
    runner=GraphRunner(runtime,connectors={'smtp_send_email':f.connector})
    result=runner.advance(rid,f.auth)
    expected='paused_for_approval' if boundary=='approval_wait' else 'completed' if boundary in ('before_execution','after_checkpoint') else 'blocked'
    assert result['status']==expected
    with f.store.transaction(write=False) as db:after=runtime.load(db,rid,f.auth)
    assert after['workflow_digest']==before['workflow_digest']
    if boundary not in ('before_execution','approval_wait'):assert after['usage']==before['usage']
    with sqlite3.connect(ledger) as db:count=db.execute('SELECT COUNT(*) FROM effects').fetchone()[0]
    assert count==(0 if boundary in ('during_call','approval_wait') else 1)
    if boundary=='after_checkpoint':assert after['outputs']['send_email']==before['outputs']['send_email']


def test_killed_delegation_cannot_replay_unknown_model_intent():
    x=delegation.DynamicDelegationTests();x.setUp()
    try:
        x.now=time.time();x.runtime.clock=lambda:x.now
        rid=x.runtime.create_run(x.request(),x.auth)['run_id']
        def child(entered,hold):
            executor=x.executor()
            def interrupted(*args):entered.set();hold.wait(60);return {'facts':'never_committed'}
            executor.invoke=interrupted
            GraphRunner(x.runtime,agents=executor).advance(rid,x.auth)
        kill_at(child)
        with x.store.transaction(write=False) as db:before=x.runtime.load(db,rid,x.auth)
        x.now+=121
        rt=RuntimeService(x.workflows,clock=lambda:x.now)
        assert GraphRunner(rt,agents=x.executor()).advance(rid,x.auth)['status']=='blocked'
        with x.store.transaction(write=False) as db:after=rt.load(db,rid,x.auth)
        assert after['usage']==before['usage']
        assert after['error_code']=='UNKNOWN_INVOCATION_RESULT'
    finally:x.doCleanups()
