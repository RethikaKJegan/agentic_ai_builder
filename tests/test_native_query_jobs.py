"""Native engine reads reuse durable ownership, encrypted results and quotas."""
from copy import deepcopy
from concurrent.futures import ThreadPoolExecutor
from types import SimpleNamespace
from threading import Lock
from time import sleep,monotonic
import json
import pytest
from tests.test_subway_full_queries import engine,installed,AUTH,plan,V
from workflow_api.data_queries import DataQueries
from workflow_api.data_query_jobs import DataQueryJobs
from workflow_api.subway_queries import SubwayQueryConnector
from workflow_api.subway_query_jobs import SubwayJobEngine,DurableSubwayQuery
from workflow_api.subway_onboarding import build_package
from workflow_api.workflow_queries import QueryPending
from runtime.service import RuntimeFailure

@pytest.fixture
def native(engine):
 q,_=engine;manager=q.sources.manager
 packages=q.service.business_composition.packages
 packages.publish(AUTH,build_package(V,4))
 q.app.state.client_packages=packages
 package=packages.get(AUTH,'subway-business-v1',4)
 pin=dict(package_id=package['package_id'],revision=4,package_sha256=package['sha256'],ontology_version=V['version_id'])
 jobs=DataQueryJobs(DataQueries(manager),lambda *_:deepcopy(AUTH));jobs.engines['subway']=SubwayJobEngine(q)
 # Only the already-owned parent is needed to exercise the query queue itself.
 with q.store.transaction() as db:
  db.execute('CREATE TABLE runtime_runs (workspace TEXT,subject TEXT,run_id TEXT,document TEXT)')
  db.execute('INSERT INTO runtime_runs VALUES (?,?,?,?)',('client-subway','subway-client','native_parent',json.dumps(dict(status='running',query_concurrency=2,governance_policy={}))))
 def adapter(index):
  return DurableSubwayQuery(SubwayQueryConnector(q,deepcopy(AUTH),pin),jobs,dict(run_id='native_parent',node_id='read_'+str(index)))
 return SimpleNamespace(q=q,jobs=jobs,adapter=adapter)


def enqueue(n,index):
 inputs=dict(query=plan(n.q,limit=10+index))
 with pytest.raises(QueryPending) as wait:n.adapter(index).invoke(dict(tool_id='subway_query'),inputs,'native_effect_'+str(index))
 return inputs,wait.value.job


def test_native_reads_overlap_and_reattach_without_duplicate_results(native):
 n=native;pairs=[enqueue(n,i) for i in range(4)];original=n.q.execute;lock=Lock();active=peak=0
 def slow(*args):
  nonlocal active,peak
  with lock:active+=1;peak=max(peak,active)
  try:sleep(.3);return original(*args)
  finally:
   with lock:active-=1
 n.q.execute=slow;start=monotonic()
 with ThreadPoolExecutor(max_workers=4) as pool:first=sum(pool.map(lambda _:n.jobs.tick(),range(4)))
 with ThreadPoolExecutor(max_workers=4) as pool:second=sum(pool.map(lambda _:n.jobs.tick(),range(4)))
 assert first+second==4
 assert peak==2
 for i,(inputs,job) in enumerate(pairs):
  result=n.adapter(i).invoke(dict(tool_id='subway_query'),inputs,'native_effect_'+str(i))
  assert result['rows']==[{'records':100}]
  with n.q.store.transaction(write=False) as db:
   secret=db.execute('SELECT result_secret FROM data_query_jobs WHERE job_id=?',(job['job_id'],)).fetchone()[0]
   assert secret and 'records' not in secret
 assert n.jobs.list(AUTH)['items']==[]
 with n.q.store.transaction(write=False) as db:assert db.execute('SELECT COUNT(*) FROM data_query_jobs').fetchone()[0]==4
 print('NATIVE_PERFORMANCE',json.dumps(dict(peak=peak,seconds=round(monotonic()-start,3))))


def test_native_stopped_parent_cancels_before_any_source_read(native):
 n=native;_,job=enqueue(n,0)
 with n.q.store.transaction() as db:db.execute("UPDATE runtime_runs SET document=?",(json.dumps(dict(status='cancelled')),))
 n.q.execute=lambda *_:pytest.fail('Cancelled native read executed')
 n.jobs.tick();assert n.jobs.get(AUTH,job['job_id'],_workflow=True)['state']=='cancelled'


def test_native_snapshot_revocation_and_cross_tenant_access_fail_closed(native):
 n=native;_,job=enqueue(n,0)
 foreign=deepcopy(AUTH);foreign['subject']['workspace_id']='client-simpsons'
 with pytest.raises(Exception):n.jobs.get(foreign,job['job_id'])
 with n.q.store.transaction() as db:db.execute("UPDATE data_source_connections SET secret=secret||'changed'")
 n.q.execute=lambda *_:pytest.fail('Stale native read executed')
 assert n.jobs.tick();assert n.jobs.get(AUTH,job['job_id'],_workflow=True)['state']=='failed'


def test_native_restart_uses_same_job_and_conservative_per_run_limit(native):
 n=native;inputs,job=enqueue(n,0)
 with pytest.raises(QueryPending) as repeated:n.adapter(0).invoke(dict(tool_id='subway_query'),inputs,'native_effect_0')
 assert repeated.value.job['job_id']==job['job_id']
 n.jobs.tick();assert n.adapter(0).invoke(dict(tool_id='subway_query'),inputs,'native_effect_0')['coverage']['matched_records']==100

from tests.test_subway_intelligence import subway,selection,overview
from tests.test_connected_action_plans import action,bind


def test_configured_native_graph_waits_for_all_four_receipts_before_report(subway):
    from workflow_api.subway_queries import install
    f=subway;f.service.durable_queries=True;install(f.app,f.auth);q=f.service.subway_queries
    f.q=q;reads=[]
    for i in range(4):
        a=action('read_'+str(i),'tool.subway_query',[bind('literal','query','query_'+str(i))])
        a['budget']['timeout_seconds']=120;reads.append(a)
    report=action('report','content.prepare',[bind('output','data',action='read_0')],[a['action_id'] for a in reads],[a['action_id'] for a in reads])
    f.service.planner.provider.plan_actions=lambda *_:dict(actions=deepcopy(reads)+[report],completion_criteria=['report'],missing_inputs=[])
    c=f.service.business_composition
    doc=c.prepare_actions(f.auth,dict(objective='Count four independently scoped purchase order sources and report all receipts.',request_key='native_four_query_001',action_plan=dict(actions=deepcopy(reads)+[report],completion_criteria=['report'],missing_inputs=[]),user_values={'query_'+str(i):plan(q,limit=10+i) for i in range(4)}))
    w=c.workflow(f.auth,doc['composition_id']);assert f.adapter.approve_pending(w,f.auth)['ready']
    assignments=f.adapter.execution_assignments(w,f.auth)
    for agent in w['agents']:agent['allowed_tool_ids']=[g['tool_id'] for g in assignments if g['agent_id']==agent['agent_id']]
    w['status']='approved';w['metadata'].update(approved_by='fixture-reviewer',validation_state='validated')
    with f.service.store.transaction() as db:f.service.store.put(db,'client-subway',w)
    rt=f.service.runtime_runner.runtime;clock=rt.clock;offset=[0];rt.clock=lambda:clock()+offset[0]
    rid=rt.create_run(dict(request_id='native_graph',idempotency_key='native_graph_0001',payload=dict(workflow_id=w['workflow_id'],workflow_version=1,inputs={})),f.auth)['run_id']
    for _ in range(30):
        state=f.service.runtime_runner.advance(rid,f.auth)['status']
        if state not in ('queued','running'):break
        with ThreadPoolExecutor(max_workers=2) as pool:list(pool.map(lambda _:f.app.state.data_query_jobs.tick(),range(2)))
        offset[0]+=1.01
    with f.service.store.transaction(write=False) as db:run=rt.load(db,rid,f.auth)
    assert state=='completed',run.get('error_code')
    assert all(run['action_instances']['read_'+str(i)]['verified_receipt'] for i in range(4))
    events=rt.events(rid,f.auth,limit=500)['items']
    done={e['details'].get('node_id'):i for i,e in enumerate(events) if e['event_type']=='node.completed'}
    started={e['details'].get('node_id'):i for i,e in enumerate(events) if e['event_type']=='node.started'}
    assert all(done['read_'+str(i)]<started['report'] for i in range(4))
    assert run['usage']['workflow']['tool_calls']==4
