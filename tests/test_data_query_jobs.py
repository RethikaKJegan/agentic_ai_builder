"""Durable lifecycle, privacy, authority, fencing and real cancellation tests."""
import copy
import json
import multiprocessing
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import Event, Thread
from uuid import uuid4

import pytest
from jsonschema import Draft202012Validator
from referencing import Registry, Resource

from tests.test_data_queries import queries, saved
from tests.test_data_query_pushdown import postgres
from tests.test_data_relationships import auth
from workflow_api.data_query_control import checkpoint, track_postgres
from workflow_api.data_query_jobs import DataQueryJobs, COLUMNS
from workflow_api.service import ApiFailure


class Clock:
    def __init__(self):self.value=time.time()
    def __call__(self):return self.value
    def advance(self,seconds):self.value+=seconds


@pytest.fixture
def jobs(queries):
    authority=auth()
    clock=Clock()
    value=DataQueryJobs(queries,lambda workspace,owner:authority if (workspace,owner)==('one','alice') else None,clock=clock)
    value.current_auth=authority
    value.heartbeat_interval=.05
    return value


def submit(jobs,key=None):
    plan=saved(jobs.queries)
    return jobs.submit(auth(),{'plan_id':plan['plan_id']},key or 'retry_'+uuid4().hex)


def raw(jobs,job_id):
    with jobs.store.transaction(write=False) as db:
        return jobs.decode(db.execute('SELECT '+','.join(COLUMNS)+' FROM data_query_jobs WHERE job_id=?',(job_id,)).fetchone())


def check_contract(value):
    root=Path(__file__).resolve().parents[1]/'shared/contracts/data-sources'
    queries_schema=json.loads((root/'queries-v1.schema.json').read_text())
    job_schema=json.loads((root/'query-jobs-v1.schema.json').read_text())
    registry=Registry().with_resource(queries_schema['$id'],Resource.from_contents(queries_schema))
    Draft202012Validator(job_schema,registry=registry).validate(value)


def test_job_complete_encrypted_result_contract_and_expiry(jobs):
    item=submit(jobs);check_contract(item)
    assert item['state']=='queued' and jobs.tick()
    status=jobs.get(auth(),item['job_id']);check_contract(status);check_contract(jobs.list(auth()))
    assert status['state']=='succeeded' and status['attempt']==1 and status['result_available']
    result=jobs.result(auth(),item['job_id']);check_contract(result)
    assert result['rows']==[{'sales':'33.360'}]
    record=raw(jobs,item['job_id'])
    assert '33.360' not in json.dumps(record)
    assert json.loads(jobs.manager.cipher.decrypt(record['result_secret'].encode()))==result
    assert 'permissions' not in json.dumps(record) and 'credentials' not in json.dumps(record)
    assert 'context_hash' not in json.dumps(status)
    jobs.clock.advance(901)
    assert jobs.get(auth(),item['job_id'])['state']=='succeeded'
    assert not jobs.get(auth(),item['job_id'])['result_available']
    with pytest.raises(ApiFailure) as error:jobs.result(auth(),item['job_id'])
    assert error.value.code=='DATA_QUERY_RESULT_EXPIRED' and error.value.status==410
    assert raw(jobs,item['job_id'])['result_secret'] is None
    jobs.clock.advance(86401)
    assert jobs.list(auth())=={'items':[]}


def test_idempotency_survives_plan_expiry_and_conflicts(jobs):
    item=submit(jobs,'same_retry_key')
    assert jobs.submit(auth(),{'plan_id':item['plan_id']},'same_retry_key')['job_id']==item['job_id']
    jobs.clock.advance(601)
    again=jobs.submit(auth(),{'plan_id':item['plan_id']},'same_retry_key')
    assert again['job_id']==item['job_id'] and again['state']=='failed'
    with pytest.raises(ApiFailure) as error:jobs.submit(auth(),{'plan_id':'different'},'same_retry_key')
    assert error.value.code=='IDEMPOTENCY_KEY_REUSED'


@pytest.mark.parametrize('other',[auth('bob'),auth(workspace='two'),auth(write=False)])
def test_job_access_scoped_for_all_operations(jobs,other):
    item=submit(jobs)
    for operation in (jobs.get,jobs.cancel,jobs.result):
        with pytest.raises(ApiFailure) as error:operation(other,item['job_id'])
        assert error.value.status in (403,404)
    assert jobs.get(auth(),item['job_id'])['state']=='queued'


def test_cancel_queued_never_reads(jobs):
    item=submit(jobs)
    assert jobs.cancel(auth(),item['job_id'])['state']=='cancelled'
    assert not jobs.tick() and not jobs.queries.reader.calls
    assert jobs.get(auth(),item['job_id'])['error'] is None


def test_cancel_wins_publication_race(jobs,monkeypatch):
    item=submit(jobs);ready,release=Event(),Event()
    original=jobs.publish
    def delayed(row,result):
        ready.set();assert release.wait(5);original(row,result)
    monkeypatch.setattr(jobs,'publish',delayed)
    worker=Thread(target=jobs.tick);worker.start();assert ready.wait(5)
    assert jobs.cancel(auth(),item['job_id'])['state']=='cancel_requested'
    release.set();worker.join(5)
    assert not worker.is_alive()
    assert jobs.get(auth(),item['job_id'])['state']=='cancelled'
    assert raw(jobs,item['job_id'])['result_secret'] is None


def test_current_permission_revocation_stops_running_attempt(jobs,monkeypatch):
    item=submit(jobs);ready=Event()
    def running(*_,**__):
        ready.set()
        for _ in range(100):time.sleep(.02);checkpoint()
        raise AssertionError('Revoked authority was not observed')
    monkeypatch.setattr(jobs.queries,'execute',running)
    worker=Thread(target=jobs.tick);worker.start();assert ready.wait(5)
    jobs.current_auth['permissions']=[]
    worker.join(5);assert not worker.is_alive()
    status=jobs.get(auth(),item['job_id'])
    assert status['state']=='failed' and status['error']['code']=='OPERATION_NOT_AUTHORIZED'
    assert not status['result_available']


def test_queued_stale_plan_fails_without_read(jobs):
    item=submit(jobs)
    graph=jobs.manager.relationships.get(auth())['graph']
    jobs.manager.relationships.edit(auth(),'annotation',graph['nodes'][0]['node_id'],dict(revision=graph['revision'],description='Changed metadata'))
    jobs.tick();status=jobs.get(auth(),item['job_id'])
    assert status['state']=='failed' and status['error']['code']=='DATA_QUERY_STALE'
    assert not jobs.queries.reader.calls


def test_expired_queue_and_deadline_no_read(jobs):
    item=submit(jobs);jobs.clock.advance(181)
    assert not jobs.tick()
    status=jobs.get(auth(),item['job_id'])
    assert status['state']=='failed' and status['error']['code']=='DATA_QUERY_TIMEOUT'
    assert not jobs.queries.reader.calls


def test_execution_uses_owned_pinned_plan_after_normal_pruning(jobs):
    item=submit(jobs)
    with jobs.store.transaction() as db:db.execute('DELETE FROM data_query_plans WHERE plan_id=?',(item['plan_id'],))
    jobs.tick();assert jobs.result(auth(),item['job_id'])['rows']==[{'sales':'33.360'}]


def test_fenced_recovery_and_fixed_deadline(jobs):
    item=submit(jobs);old=jobs.claim();deadline=old['deadline']
    jobs.clock.advance(16)
    other=DataQueryJobs(jobs.queries,jobs.authenticate,clock=jobs.clock)
    newer=other.claim()
    assert newer['attempts']==2 and newer['token']!=old['token'] and newer['deadline']==deadline
    result=jobs.queries.execute(auth(),{'plan_id':item['plan_id']})
    with pytest.raises(ApiFailure) as error:jobs.publish(old,result)
    assert error.value.code=='DATA_QUERY_LEASE_LOST'
    other.publish(newer,result)
    jobs.finish_failure(old,ApiFailure('OLD_ATTEMPT','Cannot overwrite',400))
    assert jobs.get(auth(),item['job_id'])['state']=='succeeded'


def test_second_interruption_is_terminal(jobs):
    item=submit(jobs);jobs.claim();jobs.clock.advance(16);jobs.claim();jobs.clock.advance(16)
    assert jobs.claim() is None
    status=jobs.get(auth(),item['job_id'])
    assert status['state']=='failed' and status['error']['code']=='DATA_QUERY_INTERRUPTED'


def test_parallel_claims_enforce_owner_and_global_limit(jobs):
    item=submit(jobs)
    # Independent coordinators over the same serialized store compete for one job.
    coordinators=[DataQueryJobs(jobs.queries,jobs.authenticate,clock=jobs.clock) for _ in range(8)]
    with ThreadPoolExecutor(max_workers=8) as pool:claims=list(pool.map(lambda coordinator:coordinator.claim(),coordinators))
    assert sum(row is not None for row in claims)==1
    with jobs.store.transaction() as db:
        base=list(db.execute('SELECT '+','.join(COLUMNS)+' FROM data_query_jobs WHERE job_id=?',(item['job_id'],)).fetchone())
        for i in range(6):
            values=base.copy();changes={'job_id':'dqj_'+uuid4().hex,'owner':'other'+str(i),'retry_key':'other'+str(i),'state':'queued','token':None,'attempts':0,'lease_until':0}
            for key,value in changes.items():values[COLUMNS.index(key)]=value
            db.execute('INSERT INTO data_query_jobs ('+','.join(COLUMNS)+') VALUES ('+','.join('?' for _ in COLUMNS)+')',values)
    assert sum(jobs.claim() is not None for _ in range(6))==3


def test_admission_and_bad_idempotency_key(jobs):
    for _ in range(5):submit(jobs)
    with pytest.raises(ApiFailure) as error:submit(jobs)
    assert error.value.code=='DATA_QUERY_BUSY'
    with pytest.raises(ApiFailure):jobs.submit(auth(),{'plan_id':'anything'},'bad')


def test_result_access_rechecks_current_graph_and_permissions(jobs):
    item=submit(jobs);jobs.tick()
    with pytest.raises(ApiFailure):jobs.result(auth(write=False),item['job_id'])
    graph=jobs.manager.relationships.get(auth())['graph']
    jobs.manager.relationships.edit(auth(),'annotation',graph['nodes'][0]['node_id'],dict(revision=graph['revision'],description='Change after completion'))
    with pytest.raises(ApiFailure) as error:jobs.result(auth(),item['job_id'])
    assert error.value.code=='DATA_QUERY_STALE'


def test_schema_change_committed_at_publication_is_rejected(jobs,monkeypatch):
    item=submit(jobs);original=jobs.valid_saved;calls=[]
    def mutate_after_validation(authority,document):
        original(authority,document);calls.append(True)
        # submit already validated; worker validates, then publish validates.
        if len(calls)==2:
            graph=jobs.manager.relationships.get(auth())['graph']
            jobs.manager.relationships.edit(auth(),'annotation',graph['nodes'][0]['node_id'],dict(revision=graph['revision'],description='Race publication'))
    monkeypatch.setattr(jobs,'valid_saved',mutate_after_validation)
    jobs.tick();status=jobs.get(auth(),item['job_id'])
    assert status['state']=='failed' and status['error']['code']=='DATA_QUERY_STALE'
    assert not status['result_available']


def test_real_postgres_statement_cancellation(jobs,postgres,monkeypatch):
    from workflow_api.data_query_pushdown import postgres_snapshot
    from contextlib import contextmanager
    conn,_=postgres;conn.commit();ready=Event()
    @contextmanager
    def connection(config):yield conn
    jobs.manager.adapter.connection=connection
    def running(*_,**__):
        with postgres_snapshot(jobs.manager,{}) as pg:
            assert pg.execute('SHOW transaction_read_only').fetchone()[0]=='on'
            ready.set();pg.execute('SELECT pg_sleep(10)')
        raise AssertionError('Expected PostgreSQL cancellation')
    monkeypatch.setattr(jobs.queries,'execute',running)
    item=submit(jobs);worker=Thread(target=jobs.tick);worker.start();assert ready.wait(5)
    started=time.monotonic();jobs.cancel(auth(),item['job_id']);worker.join(5)
    assert not worker.is_alive() and time.monotonic()-started<5
    assert jobs.get(auth(),item['job_id'])['state']=='cancelled'


def test_hard_worker_crash_recovers_fresh_attempt(queries):
    jobs=DataQueryJobs(queries,lambda w,o:auth());jobs.lease_seconds=1;jobs.heartbeat_interval=.05
    item=submit(jobs);context=multiprocessing.get_context('fork');ready=context.Event()
    def child():
        def abandoned(*_,**__):ready.set();time.sleep(20)
        queries.execute=abandoned
        jobs.tick()
    process=context.Process(target=child);process.start()
    try:
        assert ready.wait(5);process.terminate();process.join(5);assert not process.is_alive()
        time.sleep(1.2)
        recovered=DataQueryJobs(queries,lambda w,o:auth())
        assert recovered.tick()
        status=recovered.get(auth(),item['job_id'])
        assert status['state']=='succeeded' and status['attempt']==2
        assert recovered.result(auth(),item['job_id'])['rows']==[{'sales':'33.360'}]
    finally:
        if process.is_alive():process.kill();process.join(5)


def test_job_store_postgres_atomic_claim_and_encrypted_result(queries,postgres):
    from psycopg.conninfo import make_conninfo
    from tests.test_postgres_backend import test_dsn
    from workflow_api.storage import WorkflowStore
    from workflow_api.data_sources import DataSources
    from workflow_api.data_queries import DataQueries
    from tests.test_data_queries import Planner,Reader
    _,schema=postgres
    store=WorkflowStore(make_conninfo(test_dsn(),options='-csearch_path='+schema))
    manager=DataSources(store,queries.manager.env)
    for table in ('data_source_connections','data_source_snapshots','data_relationship_graphs','data_relationship_jobs','data_relationship_reviews','data_relationship_annotations'):
        with queries.store.transaction(write=False) as db:
            cursor=db.execute('SELECT * FROM '+table);columns=[v[0] for v in cursor.description];rows=cursor.fetchall()
        with store.transaction() as db:
            for row in rows:
                db.execute('INSERT INTO '+table+' ('+','.join(columns)+') VALUES ('+','.join('?' for _ in columns)+')',row)
    service=DataQueries(manager,Planner(),Reader())
    queue=DataQueryJobs(service,lambda w,o:auth());item=submit(queue)
    competitors=[DataQueryJobs(service,lambda w,o:auth()) for _ in range(5)]
    with ThreadPoolExecutor(max_workers=5) as pool:claims=list(pool.map(lambda value:value.claim(),competitors))
    claim=next(v for v in claims if v is not None);assert sum(v is not None for v in claims)==1
    result=service.execute(auth(),{'plan_id':item['plan_id']})
    queue.publish(claim,result)
    assert queue.result(auth(),item['job_id'])['rows']==[{'sales':'33.360'}]
    assert '33.360' not in raw(queue,item['job_id'])['result_secret']


def test_job_http_routes_and_authority(queries):
    from fastapi.testclient import TestClient
    from workflow_api.main import create_app, COOKIE
    app=create_app(database=queries.store.path,dev_auth=True,roles=['admin'],planning_worker_enabled=False)
    # Use the real route boundary with an isolated server-defined fixture identity.
    authority=app.state.workflow_auth;authority['subject']={'workspace_id':'one','subject_id':'alice'}
    route_jobs=app.state.data_query_jobs
    route_jobs.queries.reader=queries.reader;route_jobs.queries.pushdown_enabled=False
    route_jobs.manager.cipher=queries.manager.cipher
    item=saved(queries)
    with TestClient(app) as client:
        session=client.get('/session');client.cookies.set(COOKIE,session.cookies[COOKIE],path='/')
        response=client.post('/data-queries/jobs',json={'plan_id':item['plan_id']},headers={'Idempotency-Key':'http_retry_key'})
        assert response.status_code==202 and response.headers['cache-control']=='no-store'
        job=response.json()['data'];check_contract(job)
        again=client.post('/data-queries/jobs',json={'plan_id':item['plan_id']},headers={'Idempotency-Key':'http_retry_key'})
        assert again.json()['data']['job_id']==job['job_id']
        assert client.get('/data-queries/jobs').json()['data']['items'][0]['job_id']==job['job_id']
        assert route_jobs.tick()
        assert client.get('/data-queries/jobs/'+job['job_id']+'/result').json()['data']['rows']==[{'sales':'33.360'}]
        authority['permissions']=['tools.read']
        assert client.get('/data-queries/jobs/'+job['job_id']).status_code==403
        assert client.post('/data-queries/jobs/'+job['job_id']+'/cancel').status_code==403


def test_progress_reports_observed_fragments_only(jobs,monkeypatch):
    item=submit(jobs);original=jobs.queries.execute
    def execute(*args,**kwargs):
        checkpoint('Completed dimension',fragment={'transferred_rows':8,'transferred_bytes':100})
        checkpoint('Completed key domain',fragment={'transferred_rows':8,'transferred_bytes':120})
        result=original(*args,**kwargs)
        return result
    monkeypatch.setattr(jobs.queries,'execute',execute)
    jobs.tick();status=jobs.get(auth(),item['job_id'])
    # The application source read also reports its actual 3 rows / fixture 100 bytes.
    assert status['progress']=={'stage':'Complete','completed_fragments':3,'transferred_rows':19,'transferred_bytes':320}


def test_authority_revocation_cancels_real_postgres_with_authority_error(jobs,postgres,monkeypatch):
    from contextlib import contextmanager
    from workflow_api.data_query_pushdown import postgres_snapshot
    conn,_=postgres;conn.commit();ready=Event()
    @contextmanager
    def connection(config):yield conn
    jobs.manager.adapter.connection=connection
    def execute(*_,**__):
        try:
            with postgres_snapshot(jobs.manager,{}) as pg:
                ready.set();pg.execute('SELECT pg_sleep(10)')
        except Exception:
            checkpoint()
            raise
    monkeypatch.setattr(jobs.queries,'execute',execute)
    item=submit(jobs);worker=Thread(target=jobs.tick);worker.start();assert ready.wait(5)
    jobs.current_auth['permissions']=[];worker.join(5)
    assert not worker.is_alive()
    value=jobs.get(auth(),item['job_id'])
    assert value['state']=='failed' and value['error']['code']=='OPERATION_NOT_AUTHORIZED'


def test_publication_capacity_is_bounded_even_with_already_queued_work(jobs):
    item=submit(jobs);row=jobs.claim()
    result=jobs.queries.execute(auth(),{'plan_id':item['plan_id']})
    with jobs.store.transaction() as db:
        base=list(db.execute('SELECT '+','.join(COLUMNS)+' FROM data_query_jobs WHERE job_id=?',(item['job_id'],)).fetchone())
        for i in range(20):
            values=base.copy()
            for name,value in {'job_id':'dqj_'+uuid4().hex,'retry_key':'full_'+str(i),'state':'succeeded','token':None,'lease_until':0,'result_secret':'encrypted-placeholder','result_expires':jobs.clock()+900}.items():values[COLUMNS.index(name)]=value
            db.execute('INSERT INTO data_query_jobs ('+','.join(COLUMNS)+') VALUES ('+','.join('?' for _ in COLUMNS)+')',values)
    with pytest.raises(ApiFailure) as error:jobs.publish(row,result)
    assert error.value.code=='DATA_QUERY_BUSY'
    assert raw(jobs,item['job_id'])['result_secret'] is None
