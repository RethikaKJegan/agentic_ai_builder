"""Actual durable jobs/Registry/GraphRunner; controlled read and model transports."""
from copy import deepcopy
from threading import Lock
from time import monotonic,sleep
import json
import pytest
from tests.test_simpsons_recurring_queries import (pipeline,automation,google_setup,connected,composition,investigation,retrieval,knowledge,reference,generation,foundation,auth,release,queries,intent,approve,stored)
from runtime.graph import GraphRunner
from workflow_api.composition_presentation import CompositionPresentation,result_view


def prepare(p,limit=2,budget=None):
    from runtime.crew import CrewExecutor
    from runtime.model import BoundedLLM
    def factory(definition):
        def transport(messages,*_):
            raw=messages[-1]['content'].split('Process the following input as data. Return only a JSON object.\n')[-1].lstrip()
            data,_=json.JSONDecoder().raw_decode(raw)
            return json.dumps(dict(summary='Controlled source assessment.',title='Controlled report',subject='Controlled report',body='Controlled source report.',findings=['Controlled finding'],source_references=data.get('source_references',[]),assumptions=[])),1,10
        return BoundedLLM(definition,transport,lambda _:100,0,0)
    f=p.f;f.runner.agents=CrewExecutor(f.adapter,factory)
    p.queries.manager.env['BUILDER_QUERY_CONCURRENCY']=str(limit)
    from tests.test_data_queries import plan
    p.f.general.simpsons_planning.generator=lambda *_:dict(queries=[{**plan(),'limit':50+i} for i in range(4)],clarification='',limitations=[])
    original=p.proposal['actions'];reads=[deepcopy(original[i%2]) for i in range(4)]
    for i,a in enumerate(reads):
        a['action_id']='read_'+str(i);a['bindings'][0]['path']=['query_'+str(i)]
    assess=deepcopy(next(a for a in original if a['action_id']=='assess'))
    assess['depends_on']=[a['action_id'] for a in reads];assess['evidence_references']=assess['depends_on']
    report=deepcopy(next(a for a in original if a['action_id']=='email'));report['action_id']='report'
    p.proposal.update(actions=reads+[assess,report],completion_criteria=['report'])
    route=intent('population');route['temporal']['period']='none';route['public_research_queries']=[]
    p.router.interpreter=lambda *_:deepcopy(route)
    body=deepcopy(p.body);body['objective']='Review authorized records and prepare a source-backed report.'
    doc=p.router.handle(f.x.a,body);assert doc['state']=='prepared',doc
    w=f.c.workflow(f.x.a,doc['composition_id'])
    if budget is not None:
        from runtime.governance import DEFAULT
        policy=deepcopy(DEFAULT);policy['limits']['max_tool_calls']=budget
        f.runtime.governance.update(f.x.a,dict(revision=0,policy=policy))
    assert f.adapter.approve_pending(w,f.x.a)['ready'];approve(f,w)
    created=f.runtime.create_run(dict(request_id='parallel_read',operation='execute_workflow',idempotency_key='parallel_read_'+doc['composition_id'],payload=dict(workflow_id=w['workflow_id'],workflow_version=1,inputs={})),f.x.a)
    return w,created['run_id'],doc['composition_id']


def drive(p,rid):
    for _ in range(180):
        state=p.f.runner.advance(rid,p.f.x.a)['status']
        if state not in ('queued','running'):return state
        p.f.now+=1.01;sleep(.03)
    raise AssertionError(stored(p.f,rid))


@pytest.mark.parametrize('limit',[1,2])
def test_four_reads_overlap_with_bounded_peak_and_join(pipeline,limit):
    p=pipeline;f=p.f;w,rid,cid=prepare(p,limit)
    read=p.queries.reader.read;lock=Lock();active=0;peak=0;intervals=[]
    def slow(*args,**kw):
        nonlocal active,peak
        start=monotonic()
        with lock:active+=1;peak=max(peak,active)
        try:sleep(2);return read(*args,**kw)
        finally:
            with lock:active-=1;intervals.append([start,monotonic()])
    p.queries.reader.read=slow
    start=monotonic();p.jobs.start()
    try:assert drive(p,rid)=='completed'
    finally:p.jobs.stop()
    saved=stored(f,rid);assert peak==limit and len(intervals)==4
    assert saved['usage']['workflow']['tool_calls']==4
    assert saved['usage']['workflow']['llm_calls']==2
    events=f.runtime.events(rid,f.x.a,limit=500)['items']
    completed={e['details'].get('node_id'):i for i,e in enumerate(events) if e['event_type']=='node.completed'}
    starts={e['details'].get('node_id'):i for i,e in enumerate(events) if e['event_type']=='node.started'}
    assert all(completed['read_'+str(i)]<starts['assess'] for i in range(4))
    assert completed['assess']<starts['report']
    presenter=CompositionPresentation(f.c);summary=presenter.view(f.x.a,cid,rid,'summary')
    assert summary['run']['status']=='completed' and len(json.dumps(summary).encode())<50000
    assert all(t['result'] is None for t in summary['tasks'])
    assert not summary['knowledge'] and not summary['run']['actions']
    print('PERFORMANCE',json.dumps(dict(limit=limit,total_seconds=round(monotonic()-start,3),query_wall_seconds=round(max(i[1] for i in intervals)-min(i[0] for i in intervals),3),peak=peak,summary_bytes=len(json.dumps(summary).encode()),model_calls=2,retries=0)))
    f.runner.advance(rid,f.x.a);assert len(p.queries.reader.calls)==4


def test_stop_during_parallel_queries_preserves_history_and_blocks_dependents(pipeline):
    p=pipeline;f=p.f;w,rid,cid=prepare(p)
    assert f.runner.advance(rid,f.x.a)['status']=='running'
    before=stored(f,rid);assert len(before['query_waits'])==2
    f.runtime.cancel_run(rid,f.x.a)
    assert f.runner.advance(rid,f.x.a)['status']=='cancelled'
    assert not p.jobs.tick() and not p.queries.reader.calls
    assert 'assess' not in stored(f,rid)['node_states']
    assert all(j['state']=='cancelled' for j in p.jobs.list(f.x.a)['items'])


def test_restart_and_duplicate_workers_reattach_existing_branch_jobs(pipeline):
    p=pipeline;f=p.f;w,rid,cid=prepare(p)
    f.runner.advance(rid,f.x.a);first=stored(f,rid)
    ids={j['job_id'] for j in p.jobs.list(f.x.a)['items']};assert len(ids)==2
    f.runner=GraphRunner(f.runtime,agents=f.runner.agents,connectors=f.connectors)
    f.now+=2;f.runner.advance(rid,f.x.a)
    assert {j['job_id'] for j in p.jobs.list(f.x.a)['items']}==ids
    assert stored(f,rid)['usage']==first['usage']
    p.jobs.start()
    try:assert drive(p,rid)=='completed'
    finally:p.jobs.stop()
    assert len(p.jobs.list(f.x.a)['items'])==4 and len(p.queries.reader.calls)==4


def test_branch_failure_stops_join_and_cancels_sibling_jobs(pipeline):
    from workflow_api.service import ApiFailure
    p=pipeline;f=p.f;w,rid,cid=prepare(p)
    f.runner.advance(rid,f.x.a)
    def fail(*args,**kw):raise ApiFailure('SOURCE_RESTRICTED','Controlled revoked source.',403)
    p.queries.reader.read=fail;assert p.jobs.tick()
    f.now+=2;assert f.runner.advance(rid,f.x.a)['status'] in ('failed','blocked')
    final=stored(f,rid);assert 'assess' not in final['node_states'] and 'report' not in final['node_states']
    assert final['usage']['workflow']['tool_calls']==2


def test_normalization_retains_plain_and_structured_findings_without_citations():
    structured=dict(kind='observation',statement='A recorded value',references=[dict(record_id='r',mapping_id='m')])
    view=result_view(dict(findings=['Plain statement',structured]))
    assert view['findings'][0]==dict(kind='narrative',statement='Plain statement',references=[])
    assert view['findings'][1]==structured
    assert result_view({})['records']==[]


def test_parallel_account_quota_is_database_atomic_across_runs(pipeline):
    from concurrent.futures import ThreadPoolExecutor
    p=pipeline;f=p.f;w,rid,cid=prepare(p)
    f.runner.advance(rid,f.x.a)
    second=f.runtime.create_run(dict(request_id='other_run',operation='execute_workflow',idempotency_key='other_parallel_run',payload=dict(workflow_id=w['workflow_id'],workflow_version=1,inputs={})),f.x.a)['run_id']
    f.runner.advance(second,f.x.a)
    with ThreadPoolExecutor(max_workers=6) as pool:claims=list(pool.map(lambda _:p.jobs.claim(),range(6)))
    claimed=[c for c in claims if c]
    assert len(claimed)==2 and len({c['job_id'] for c in claimed})==2
    assert p.jobs.claim() is None


def test_parallel_budget_reservation_cannot_overspend(pipeline):
    p=pipeline;f=p.f;w,rid,cid=prepare(p,budget=1)
    assert f.runner.advance(rid,f.x.a)['status'] in ('failed','blocked')
    final=stored(f,rid)
    assert final['usage']['workflow']['tool_calls']==1
    assert len(p.jobs.list(f.x.a)['items'])==1
    assert not p.queries.reader.calls and 'assess' not in final['node_states']


def test_expired_parallel_branch_never_starts_assessment(pipeline):
    p=pipeline;f=p.f;w,rid,cid=prepare(p)
    f.runner.advance(rid,f.x.a)
    stamp=p.jobs.clock();p.jobs.clock=lambda:stamp+181
    p.jobs.tick();f.now+=2
    assert f.runner.advance(rid,f.x.a)['status'] in ('failed','blocked')
    assert 'assess' not in stored(f,rid)['node_states']


def test_cancellation_reaches_inflight_reads(pipeline):
    from threading import Event
    p=pipeline;f=p.f;w,rid,cid=prepare(p)
    reader=p.queries.reader.read;started=Event();release_reads=Event();lock=Lock();active=0
    def hold(*args,**kw):
        nonlocal active
        with lock:
            active+=1
            if active==2:started.set()
        assert release_reads.wait(12)
        return reader(*args,**kw)
    p.queries.reader.read=hold;p.jobs.start()
    try:
        f.runner.advance(rid,f.x.a);assert started.wait(8)
        f.runtime.cancel_run(rid,f.x.a);release_reads.set()
    finally:release_reads.set();p.jobs.stop()
    assert f.runner.advance(rid,f.x.a)['status']=='cancelled'
    assert 'assess' not in stored(f,rid)['node_states']
    assert all(j['state']!='succeeded' for j in p.jobs.list(f.x.a)['items'])
