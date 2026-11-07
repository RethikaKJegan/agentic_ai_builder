"""Multi-consumer correctness, admission, fairness and provider backpressure."""
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
import json
import time

import pytest

from runtime import RuntimeFailure
from runtime.worker import RuntimeWorker
from tests import test_runtime as fixtures
from tests.test_phase2_workers import Component
from workflow_api.resource_limits import ResourcePolicy,ResourceControls
from workflow_api.worker_control import WorkerSupervisor
from workflow_api.auxiliary_database import scoped_dsn


@pytest.fixture
def f():
    x=fixtures.ToolGraphTests();x.setUp();x.configure();x.put()
    x.now=time.time();x.runtime.clock=lambda:x.now
    try:yield x
    finally:x.doCleanups()


def approved(f,index=0):
    req=f.request();req['idempotency_key']='distributed_request_'+str(index)
    rid=f.runtime.create_run(req,f.auth)['run_id']
    paused=f.graph.advance(rid,f.auth)
    req=f.decision(paused,'approved');req['idempotency_key']+='_'+str(index)
    f.graph.decide(req,f.approver())
    return rid


def test_parallel_consumers_preserve_singleton_coordination(f):
    singleton=[Component(),Component()];parallel=[Component(),Component()]
    a,b=[WorkerSupervisor(f.store,[s],parallel_workers=[p]) for s,p in zip(singleton,parallel)]
    try:
        assert a.tick() and not b.tick()
        assert [p.starts for p in parallel]==[1,1]
        assert [s.starts for s in singleton]==[1,0]
        a.tick();b.tick();assert [p.starts for p in parallel]==[1,1]
    finally:a.stop();b.stop()
    assert [p.stops for p in parallel]==[1,1]


def test_four_active_consumers_never_duplicate_the_same_tool(f):
    rid=approved(f)
    workers=[RuntimeWorker(f.graph,lambda *_:f.auth) for _ in range(4)]
    with ThreadPoolExecutor(max_workers=4) as pool:list(pool.map(lambda w:w.drain(),workers))
    assert f.runtime.get_run(rid,f.auth)['status']=='completed'
    assert len(f.invocations)==1


def test_admission_is_atomic_and_idempotent(f):
    f.runtime.resource_controls=ResourceControls(f.store,ResourcePolicy(queued_per_account=1))
    req=f.request();first=f.runtime.create_run(req,f.auth)
    assert f.runtime.create_run(req,f.auth)==first
    req['idempotency_key']='new_queue_request'
    with pytest.raises(RuntimeFailure) as error:f.runtime.create_run(req,f.auth)
    assert error.value.code=='QUEUE_CAPACITY_EXCEEDED'


def test_account_concurrency_defers_without_invoking_or_resetting_budget(f):
    ids=[approved(f,i) for i in range(2)]
    f.runtime.resource_controls=ResourceControls(f.store,ResourcePolicy(running_per_account=1))
    with f.store.transaction() as db:
        run=f.runtime.load(db,ids[0],f.auth);run.update(status='running',worker='busy',lease_until=f.now+30)
        f.runtime.save(db,run)
    result=f.graph.advance(ids[1],f.auth)
    assert result['status']=='running' and not f.invocations
    with f.store.transaction(write=False) as db:
        run=f.runtime.load(db,ids[1],f.auth)
        assert run['available_at']>f.now and run['usage']=={}
    f.now+=31
    assert f.graph.advance(ids[1],f.auth)['status']=='completed'
    assert len(f.invocations)==1


def test_provider_rate_window_is_durable_and_tenant_scoped(f):
    ids=[approved(f,i) for i in range(2)]
    policy=ResourcePolicy(provider_per_minute={'smtp':1})
    f.runtime.resource_controls=ResourceControls(f.store,policy)
    assert f.graph.advance(ids[0],f.auth)['status']=='completed'
    assert f.graph.advance(ids[1],f.auth)['status']=='running'
    assert len(f.invocations)==1
    f.runtime.resource_controls=ResourceControls(f.store,policy)
    with f.store.transaction() as db:
        f.runtime.resource_controls.reserve_provider(db,'subway','smtp',f.now)
    f.now=(int(f.now//60)+1)*60+1
    assert f.graph.advance(ids[1],f.auth)['status']=='completed'
    assert len(f.invocations)==2


def test_fair_polling_does_not_let_simpson_backlog_hide_subway(f):
    # Scheduling must inspect both accounts even if one fills an entire batch.
    with f.store.transaction() as db:
        for i in range(20):
            run={'run_id':'fair_'+str(i),'workspace_id':'simpson' if i<19 else 'subway',
                 'subject_id':'operator','status':'queued'}
            db.execute('INSERT INTO runtime_runs(workspace,run_id,document) VALUES (?,?,?)',(run['workspace_id'],run['run_id'],json.dumps(run)))
    seen=[]
    class Runner:
        runtime=f.runtime
        def advance(self,rid,auth):seen.append(auth['subject']['workspace_id']);return {'status':'completed'}
    def auth(workspace,subject):
        a=deepcopy(f.auth);a['subject']={'workspace_id':workspace,'subject_id':subject};return a
    RuntimeWorker(Runner(),auth,batch_size=2,fair=True).drain()
    assert seen==['simpson','subway']
    seen.clear()
    RuntimeWorker(Runner(),auth,batch_size=4,fair=True).drain()
    assert seen[:2]==['simpson','subway']


def test_server_policy_rejects_unbounded_or_model_style_overrides():
    for values in ({'running_per_account':0},{'agents_per_workflow':5},{'provider_per_minute':{'openai':True}}):
        with pytest.raises(ValueError):ResourcePolicy(**values)


def test_waiting_approvals_cannot_fill_a_fair_account_batch(f):
    for index in range(4):
        req=f.request();req['idempotency_key']='waiting_approval_'+str(index)
        rid=f.runtime.create_run(req,f.auth)['run_id']
        assert f.graph.advance(rid,f.auth)['status']=='paused_for_approval'
    ready=approved(f,99)
    RuntimeWorker(f.graph,lambda *_:f.auth,batch_size=1,fair=True).drain()
    assert f.runtime.get_run(ready,f.auth)['status']=='completed'


def test_socket_dsn_remains_a_valid_postgres_uri(monkeypatch,tmp_path):
    from contextlib import nullcontext
    from urllib.parse import urlsplit,parse_qs
    class Connection:
        def execute(self,*args):pass
    monkeypatch.setattr('psycopg.connect',lambda *a,**k:nullcontext(Connection()))
    dsn=scoped_dsn('postgresql:///isolated?host=%2Ftmp%2Fsocket&user=test_role',tmp_path/'journal.db')
    assert dsn.startswith('postgresql:///isolated?')
    assert parse_qs(urlsplit(dsn).query)['host']==['/tmp/socket']
