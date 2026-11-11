"""Actual failure shape, worker fencing and independent execution regression."""
from copy import deepcopy
from threading import Event,Thread
import json
from types import SimpleNamespace
import pytest
from tests.test_workflow_query_integration import (automation,google_setup,connected,composition,investigation,retrieval,knowledge,reference,generation,foundation,auth,release,queries,setup_query)
from tests.test_connected_action_plans import compile_run,stored,complete
from tests.test_data_queries import plan
from tests.test_phase2_reliability import context
from workflow_api.data_queries import canonical_model_projection,QueryPlanner
from runtime.worker import RuntimeWorker
from runtime.graph import GraphRunner


def test_duplicate_model_projection_is_stable_without_repairing_other_semantics():
 p=plan();p['metrics']=[];p['fields']=['first','second','first','third','second']
 original=deepcopy(p);out=canonical_model_projection(p)
 assert out['fields']==['first','second','third'] and p==original
 out['fields']=p['fields'];assert out==original
 for fields in [[1,1],['field']*31]:
  p['fields']=fields;assert canonical_model_projection(p)==p


def test_direct_query_model_transport_canonicalizes_projection(monkeypatch):
 from unittest.mock import patch
 p=plan();p['metrics']=[];p['fields']=['a','b','a']
 with patch('openai.OpenAI') as client:
  client.return_value.responses.create.return_value=SimpleNamespace(status='completed',output_text=json.dumps(p))
  out=QueryPlanner({'OPENAI_API_KEY':'controlled','OPENAI_MODEL':'controlled'}).generate('Read records.',{})
 assert out['fields']==['a','b']


def test_generated_query_deduplicates_before_durable_read_without_extra_model_call(automation,queries):
 f=automation;typed=plan();typed.update(metrics=[],fields=['price','price'],limit=100)
 # Use the controlled catalog's actual queryable numeric field.
 numeric='pg_lines_price'
 typed['fields']=[numeric,numeric]
 jobs,_,_,body=setup_query(f,queries,typed_query=typed)
 _,w,rid=compile_run(f,body);result=f.runner.advance(rid,f.x.a)
 assert result['status']=='running',stored(f,rid)
 snapshot=stored(f,rid);assert snapshot['outputs']['query_plan']['query']['fields']==[numeric]
 assert snapshot['action_instances']['read']['state']=='waiting_for_query'
 assert len(jobs.list(f.x.a)['items'])==1
 assert snapshot['usage']['workflow']['llm_calls']==1
 assert not f.http.sent and f.http.write_count==0


def test_finished_owner_releases_lease_without_waiting_for_expiry(context,monkeypatch):
 f=context;created=f.runtime.create_run(dict(request_id='finish',idempotency_key='finish_owner_1',payload=dict(workflow_id=f.workflow['workflow_id'],workflow_version=1,inputs={'request_text':'Controlled worker regression.'})),f.auth)
 def finish(run_id,auth,worker,seconds):
  with f.runtime.store.transaction() as db:
   r=f.runtime.load(db,run_id,auth);r.update(status='failed',worker=worker,lease_until=f.now+120,error_code='DATA_QUERY_INVALID');f.runtime.save(db,r)
  return {'status':'failed'}
 monkeypatch.setattr(f.runner,'_advance',finish)
 assert f.runner.advance(created['run_id'],f.auth)['status']=='failed'
 with f.runtime.store.transaction(write=False) as db:assert f.runtime.load(db,created['run_id'],f.auth)['lease_until']==0


@pytest.mark.parametrize('status,owner',[('running','same'),('failed','different')])
def test_returning_worker_does_not_clear_running_or_another_owners_lease(context,monkeypatch,status,owner):
 f=context;created=f.runtime.create_run(dict(request_id='fence',idempotency_key='fence_'+status+owner,payload=dict(workflow_id=f.workflow['workflow_id'],workflow_version=1,inputs={'request_text':'Controlled worker regression.'})),f.auth)
 def finish(run_id,auth,worker,seconds):
  with f.runtime.store.transaction() as db:
   r=f.runtime.load(db,run_id,auth);r.update(status=status,worker=worker if owner=='same' else 'replacement',lease_until=f.now+120);f.runtime.save(db,r)
  return {'status':status}
 monkeypatch.setattr(f.runner,'_advance',finish);f.runner.advance(created['run_id'],f.auth)
 with f.runtime.store.transaction(write=False) as db:assert f.runtime.load(db,created['run_id'],f.auth)['lease_until']==f.now+120


def test_second_slot_finishes_new_run_while_first_call_is_waiting(context,monkeypatch):
 f=context;ids=[]
 for i in range(2):ids.append(f.runtime.create_run(dict(request_id='parallel',idempotency_key='parallel_'+str(i),payload=dict(workflow_id=f.workflow['workflow_id'],workflow_version=1,inputs={'request_text':'Controlled worker regression.'})),f.auth)['run_id'])
 entered,finish,new_done=Event(),Event(),Event();calls=[]
 def advance(rid,auth):
  calls.append(rid)
  if rid==ids[0]:
   entered.set();assert finish.wait(10)
  else:
   assert entered.wait(5);new_done.set()
  return {'run_id':rid}
 monkeypatch.setattr(f.runner,'advance',advance)
 worker=RuntimeWorker(f.runner,lambda *_:f.auth,concurrency=2)
 thread=Thread(target=worker.drain);thread.start()
 try:assert new_done.wait(5) and not finish.is_set()
 finally:finish.set();thread.join(10)
 assert not thread.is_alive() and sorted(calls)==sorted(ids)


def test_foreign_dataset_field_gets_one_budgeted_correction_before_source_call(automation,queries):
 from runtime.crew import CrewExecutor
 from runtime.model import BoundedLLM
 f=automation;jobs,_,_,body=setup_query(f,queries)
 calls=[]
 def factory(definition):
  def transport(messages,cap,timeout):
   calls.append(messages)
   q=plan();q.update(metrics=[],fields=['mongo_categories_name'] if len(calls)==1 else ['pg_lines_price'])
   return json.dumps({'query':q}),1,10
  return BoundedLLM(definition,transport,lambda messages:100,0,0)
 f.runner.agents=CrewExecutor(f.adapter,factory)
 doc,w,rid=compile_run(f,body)
 assert next(a for a in doc['action_plan']['actions'] if a['action_id']=='query_plan')['budget']['max_llm_calls']==2
 result=f.runner.advance(rid,f.x.a);snapshot=stored(f,rid)
 assert result['status']=='running',snapshot
 assert len(calls)==2 and 'Validation correction' in json.dumps(calls[1])
 assert snapshot['outputs']['query_plan']['query']['fields']==['pg_lines_price']
 assert snapshot['usage']['workflow']['llm_calls']==2
 agent=next(c['definition'] for c in doc['configurations'] if c['assigned_task']=='query_plan')
 usage=snapshot['usage'][agent['agent_id']]
 assert usage['tokens']<=agent['limits']['max_tokens'] and usage['estimated_cost_usd']<=agent['limits']['max_estimated_cost_usd']
 assert len(jobs.list(f.x.a)['items'])==1 and not queries.reader.calls
 assert not f.http.sent and not f.http.write_count


def test_explicit_query_payload_is_not_silently_repaired(queries):
 from tests.test_data_queries import auth as query_auth
 from workflow_api.service import ApiFailure
 q=plan();q.update(metrics=[],fields=['pg_lines_price','pg_lines_price'])
 with pytest.raises(ApiFailure,match='Output columns must be unique'):
  queries.validate(q,queries.context(query_auth()))
 assert q['fields']==['pg_lines_price','pg_lines_price']


def test_two_invalid_model_queries_stop_without_source_call_or_stale_lease(automation,queries):
 from runtime.crew import CrewExecutor
 from runtime.model import BoundedLLM
 f=automation;jobs,_,_,body=setup_query(f,queries);calls=[]
 def factory(definition):
  def transport(messages,cap,timeout):
   calls.append(1);q=plan();q.update(metrics=[],fields=['mongo_categories_name'])
   return json.dumps({'query':q}),1,10
  return BoundedLLM(definition,transport,lambda messages:100,0,0)
 f.runner.agents=CrewExecutor(f.adapter,factory)
 _,_,rid=compile_run(f,body);result=f.runner.advance(rid,f.x.a);snapshot=stored(f,rid)
 assert result['status']=='failed' and snapshot['error_code']=='AGENT_OUTPUT_INVALID'
 assert len(calls)==2 and snapshot['lease_until']==0
 assert not jobs.list(f.x.a)['items'] and not queries.reader.calls and not f.http.sent
 with f.general.store.transaction(write=False) as db:
  rejected=[json.loads(row[0]) for row in db.execute("SELECT document FROM runtime_events WHERE run_id=? AND json_extract(document,'$.event_type')='agent.output_rejected'",(rid,))]
 assert len(rejected)==2
 assert all('Plan references an unavailable field.' in e['details']['validation_rule'] for e in rejected)
