"""Worker ownership, dispatch fencing, bounded reads and safe crash recovery."""
from copy import deepcopy
import json
from unittest.mock import patch

import pytest
from tests.test_phase2_reliability import context
from workflow_api.lifecycle import LifecycleService,LifecycleFailure
from workflow_api.worker_control import WorkerSupervisor
from runtime.worker import RuntimeWorker


class Component:
    def __init__(self):self.starts,self.stops=0,0
    def start(self):self.starts+=1
    def stop(self):self.stops+=1


def test_only_one_worker_group_starts_and_expired_owner_is_reclaimed(context):
    clock=lambda:context.now
    first_component,second_component=Component(),Component()
    first=WorkerSupervisor(context.service.store,[first_component],clock=clock)
    second=WorkerSupervisor(context.service.store,[second_component],clock=clock)
    assert first.tick() is True
    assert second.tick() is False
    assert (first_component.starts,second_component.starts)==(1,0)
    context.now+=31
    assert second.tick() is True
    assert first.tick() is False
    assert first_component.stops==1
    first.stop()
    with context.service.store.transaction(write=False) as db:
        assert db.execute('SELECT owner FROM builder_worker_leases').fetchone()[0]==second.owner
    second.stop()


def test_api_role_does_not_start_background_components(context):
    component=Component();supervisor=WorkerSupervisor(context.service.store,[component],role='api')
    supervisor.start();assert component.starts==0;assert supervisor.owned is False
    supervisor.stop()


def test_stale_dispatch_claim_cannot_execute_or_overwrite_new_owner(context):
    context.activate()
    job=context.service.lifecycle.ingest('binding_main',{'event_id':'claim','body':'Check'},context.auth)['job']
    first=context.service.lifecycle
    first.lease('local-workspace',seconds=1)
    old_claim=first.leased_tokens[job['job_id']]
    context.now+=2
    second=LifecycleService(context.service,clock=lambda:context.now,adapter=context.adapter)
    second.lease('local-workspace',seconds=30)
    with pytest.raises(LifecycleFailure) as failure:first.execute_job(job['job_id'],context.runner,claim=old_claim)
    assert failure.value.code=='JOB_LEASE_LOST'
    assert second.execute_job(job['job_id'],context.runner)['state']=='completed'
    assert context.runtime.list_runs(context.auth)['total']==1


def test_dispatch_failure_after_run_creation_is_not_automatically_replayed(context):
    context.activate()
    job=context.service.lifecycle.ingest('binding_main',{'event_id':'uncertain','body':'Check'},context.auth)['job']
    context.service.lifecycle.lease('local-workspace')
    class Interrupted:
        runtime=context.runtime
        def advance(self,*_):raise RuntimeError('Uncertain in-flight result')
    failed=context.service.lifecycle.execute_job(job['job_id'],Interrupted())
    assert failed['state']=='dead_letter'
    assert failed['last_error_code']=='RUNTIME_DISPATCH_UNCERTAIN'
    assert context.service.lifecycle.lease('local-workspace')==[]
    assert context.runtime.list_runs(context.auth)['total']==1


def test_dispatch_finish_cannot_undo_cancellation(context):
    release=context.activate()['release']
    job=context.service.lifecycle.ingest('binding_main',{'event_id':'cancel','body':'Check'},context.auth)['job']
    context.service.lifecycle.lease('local-workspace')
    class CancelWhileExecuting:
        runtime=context.runtime
        def advance(self,run_id,auth):
            context.service.lifecycle.disable({'idempotency_key':'disable_while_running','payload':{'workflow_id':context.workflow['workflow_id'],'expected_release_id':release['release_id']}},context.auth)
            return context.runner.advance(run_id,auth)
    assert context.service.lifecycle.execute_job(job['job_id'],CancelWhileExecuting())['state']=='cancelled'


def test_worker_does_not_parse_terminal_history(context):
    with context.service.store.transaction() as db:
        for index in range(100):
            document={'status':'completed','outputs':{'large_terminal_output':'x'*10000}}
            db.execute('INSERT INTO runtime_runs(workspace,run_id,workflow_id,document) VALUES (?,?,?,?)',('local-workspace','terminal_'+str(index),context.workflow['workflow_id'],json.dumps(document)))
    worker=RuntimeWorker(context.runner,lambda *_:context.auth)
    original=json.loads
    def checked(value,*args,**kwargs):
        assert 'large_terminal_output' not in value,'Worker loaded a terminal run document'
        return original(value,*args,**kwargs)
    with patch('runtime.worker.json.loads',side_effect=checked):assert worker.drain()==[]


def test_stopped_worker_leaves_queued_runs_durable(context):
    request={'request_id':'req_stop','idempotency_key':'queued_shutdown_check','payload':{'workflow_id':context.workflow['workflow_id'],'workflow_version':1,'inputs':{'request_text':'Queued'}}}
    run=context.runtime.create_run(request,context.auth)
    worker=RuntimeWorker(context.runner,lambda *_:context.auth);worker.stop_event.set()
    assert worker.drain()==[]
    assert context.runtime.get_run(run['run_id'],context.auth)['status']=='queued'


def test_expired_runtime_intent_blocks_instead_of_repeating(context):
    request={'request_id':'req_crash','idempotency_key':'runtime_crash_check','payload':{'workflow_id':context.workflow['workflow_id'],'workflow_version':1,'inputs':{'request_text':'Check'}}}
    run=context.runtime.create_run(request,context.auth)
    with context.service.store.transaction() as db:
        document=context.runtime.load(db,run['run_id'],context.auth)
        document.update(status='running',worker='dead_worker',lease_until=0,node_states={'start':'executing'})
        context.runtime.save(db,document)
    blocked=context.runner.advance(run['run_id'],context.auth)
    assert blocked['status']=='blocked'
    events=context.runtime.events(run['run_id'],context.auth)['items']
    assert any(item['details'].get('error_code')=='UNKNOWN_INVOCATION_RESULT' for item in events)


def test_health_handles_runtime_disabled_without_writing(tmp_path):
    from workflow_api.storage import WorkflowStore
    from workflow_api.worker_control import health
    store=WorkflowStore(tmp_path/'no-runtime.sqlite3')
    writes=store.metrics['writes']
    result=health(store,'workspace_demo')
    assert result['runtime_available'] is False
    assert result['active_runs']==0
    assert result['workers']==[]
    assert store.metrics['writes']==writes


def test_shutdown_waits_for_inflight_worker_and_preserves_lease_until_drained(context):
    from threading import Event,Thread
    from workflow_api.worker_control import health
    finish=Event();entered=Event()
    class InFlight(Component):
        def __init__(self):super().__init__();self.stop_event=Event();self.thread=None
        def start(self):
            super().start()
            self.thread=Thread(target=lambda:(entered.set(),finish.wait(2)))
            self.thread.start()
        def stop(self):super().stop();self.stop_event.set()
    worker=InFlight();supervisor=WorkerSupervisor(context.service.store,[worker],shutdown_timeout=3)
    supervisor.tick();assert entered.wait(1)
    shutdown=Thread(target=supervisor.stop);shutdown.start()
    try:
        assert worker.stop_event.wait(1)
        assert shutdown.is_alive()
        with context.service.store.transaction(write=False) as db:
            assert db.execute('SELECT owner FROM builder_worker_leases').fetchone()[0]==supervisor.owner
    finally:finish.set();shutdown.join(3)
    assert not shutdown.is_alive()
    assert not worker.thread.is_alive()


def test_health_reports_redacted_component_failures(context):
    from workflow_api.worker_control import health
    worker=Component();worker.health={'state':'error','last_success':None,'last_error':'RUNTIME_WORKER_FAILED','private':'must not persist'}
    supervisor=WorkerSupervisor(context.service.store,[worker]);supervisor.tick();supervisor.tick()
    try:
        result=health(context.service.store,'local-workspace')
        assert result['components'][0]['last_error']=='RUNTIME_WORKER_FAILED'
        assert 'private' not in result['components'][0]
    finally:supervisor.stop()


def test_api_execute_only_enqueues_and_worker_completes(context):
    from workflow_api.main import create_app,COOKIE
    from fastapi.testclient import TestClient
    context.service.background_execution=True
    client=TestClient(create_app(context.service,dev_auth=True,roles=['admin']))
    try:
        session=client.get('/session');client.cookies.set(COOKIE,session.cookies[COOKIE],path='/')
        payload={'workflow_id':context.workflow['workflow_id'],'workflow_version':1,'inputs':{'request_text':'API queue check'}}
        with patch.object(context.runner,'advance',side_effect=AssertionError('API executed background work')):
            response=client.post('/workflows/'+context.workflow['workflow_id']+'/execute',json={'request_id':'req_api_queue','operation':'execute_workflow','idempotency_key':'api_queue_check_123','payload':payload})
        assert response.status_code==200,response.text
        run=response.json()['data']['run'];assert run['status']=='queued'
        auth=deepcopy(context.auth);auth['subject']['subject_id']='local-builder'
        worker=RuntimeWorker(context.runner,lambda *_:auth)
        assert worker.drain()[0]['status']=='completed'
    finally:client.close()


def test_waiting_approvals_cannot_starve_new_queued_runs(context):
    request={'request_id':'req_fair','idempotency_key':'fair_run_seed','payload':{'workflow_id':context.workflow['workflow_id'],'workflow_version':1,'inputs':{'request_text':'Check'}}}
    seed=context.runtime.create_run(request,context.auth)
    with context.service.store.transaction() as db:
        document=context.runtime.load(db,seed['run_id'],context.auth)
        document['status']='paused_for_approval';document['approval_context']={'expires_at':context.now+1000}
        for index in range(5):
            paused=deepcopy(document);paused['run_id']='approval_wait_'+str(index)
            db.execute('INSERT INTO runtime_runs(workspace,run_id,workflow_id,subject,document) VALUES (?,?,?,?,?)',('local-workspace',paused['run_id'],context.workflow['workflow_id'],'owner',json.dumps(paused)))
        db.execute('DELETE FROM runtime_runs WHERE run_id=?',(seed['run_id'],))
    request['idempotency_key']='fair_run_new'
    queued=context.runtime.create_run(request,context.auth)
    worker=RuntimeWorker(context.runner,lambda *_:context.auth,batch_size=2)
    worker.drain();worker.drain();worker.drain()
    assert context.runtime.get_run(queued['run_id'],context.auth)['status']=='completed'


def test_scheduler_claims_each_job_when_ready_to_execute(context):
    from workflow_api.scheduler import TriggerScheduler
    context.activate()
    for index in range(2):context.service.lifecycle.ingest('binding_main',{'event_id':'slow_'+str(index),'body':'Check'},context.auth)
    original=context.runner.advance
    def slow(run_id,auth):
        result=original(run_id,auth);context.now+=121;return result
    with patch.object(context.runner,'advance',side_effect=slow):
        result=TriggerScheduler(context.service,lambda *_:context.auth).tick()
    assert result['dispatched']==2
    with context.service.store.transaction(write=False) as db:
        assert db.execute("SELECT COUNT(*) FROM lifecycle_jobs WHERE state='completed' AND attempt=1").fetchone()[0]==2


def test_procurement_worker_can_restart_after_lease_loss():
    from threading import Event
    from types import SimpleNamespace
    from connector_extension.procurement.routes import ProcurementWorker
    ticked=Event();calls=[]
    def tick():calls.append('tick');ticked.set()
    worker=ProcurementWorker(SimpleNamespace(tick=tick))
    try:
        worker.start();assert ticked.wait(5);worker.stop()
        count=len(calls);ticked.clear()
        worker.start();assert ticked.wait(5);worker.stop()
        assert len(calls)>count
        assert worker.health['state']=='ready'
    finally:worker.stop()


def test_graceful_drain_renews_group_lease_and_cannot_steal_new_owner(context):
    from threading import Event,Thread
    from types import SimpleNamespace
    import time
    entered=Event();finish=Event()
    class Draining(Component):
        def __init__(self):super().__init__();self.stop_event=Event();self.thread=None
        def start(self):
            self.thread=Thread(target=lambda:(entered.set(),finish.wait(5)));self.thread.start()
        def stop(self):self.stop_event.set()
    worker=Draining()
    first=WorkerSupervisor(context.service.store,[worker],ttl=.6,shutdown_timeout=4)
    second=WorkerSupervisor(context.service.store,[Component()],ttl=.6)
    first.tick();assert entered.wait(1)
    stop=Thread(target=first.stop);stop.start()
    try:
        assert worker.stop_event.wait(1)
        time.sleep(.9)
        assert second.tick() is False
        assert stop.is_alive()
    finally:finish.set();stop.join(3)
    assert second.tick() is True
    assert first.renew_owned() is False
    second.stop()


def test_worker_entrypoint_runs_framework_lifespan_and_clean_shutdown():
    import asyncio
    from contextlib import asynccontextmanager
    from fastapi import FastAPI
    from scripts.run_builder_worker import run_app
    states=[]
    async def check():
        stop=asyncio.Event()
        @asynccontextmanager
        async def lifespan(app):
            states.append('started');stop.set()
            try:yield
            finally:states.append('stopped')
        await run_app(FastAPI(lifespan=lifespan),stop)
    asyncio.run(check())
    assert states==['started','stopped']
