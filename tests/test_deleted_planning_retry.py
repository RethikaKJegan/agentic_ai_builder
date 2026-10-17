"""Durable deletion/retry regressions use offline planner and temporary DB only."""
from copy import deepcopy
from concurrent.futures import ThreadPoolExecutor
import json
import pytest
from tests import test_workflow_api as api_fixtures
from workflow_api.planning_jobs import PlanningJobs
from workflow_api.service import ApiFailure

@pytest.fixture
def ctx():
 f=api_fixtures.WorkflowApiTests('test_same_prompt_after_deletion_gets_stable_fresh_identity_and_agents');f.setUp()
 try:yield f
 finally:f.tearDown();f.doCleanups()

def request():
 return {'request_id':'req_recreate','operation':'plan_workflow','idempotency_key':'recreate_durable_key','payload':{'objective':'Summarize inventory','context':{'generation_mode':'hierarchy'}}}

def completed(ctx):
 jobs=ctx.client.app.state.planning_jobs;auth=ctx.client.app.state.workflow_auth
 original=jobs.submit(request(),auth);assert jobs.tick()
 done=jobs.get(original['job_id'],auth);assert done['state']=='succeeded',done
 w=done['result']['data']['workflow'];assert ctx.save(w,key='save_original_recreate').status_code==200
 return jobs,auth,done,w

def tombstone(ctx,w,stamp='2026-10-17T13:00:00Z',workspace='local-workspace'):
 with ctx.service.store.transaction() as db:
  db.execute('INSERT INTO lifecycle_tombstones VALUES (?,?,?,?)',(workspace,w['workflow_id'],stamp,'complete'))

def test_deleted_completed_job_gets_one_fresh_generation_and_keeps_old_job(ctx):
 jobs,auth,original,w=completed(ctx);tombstone(ctx,w)
 restarted=PlanningJobs(jobs.service,jobs.authenticate)
 fresh=restarted.submit(request(),auth);assert fresh['job_id']!=original['job_id'] and fresh['state']=='queued'
 assert restarted.submit(request(),auth)==fresh
 with ctx.service.store.transaction(write=False) as db:
  stored=json.loads(db.execute('SELECT request FROM builder_planning_jobs WHERE job_id=?',(fresh['job_id'],)).fetchone()[0])
 assert stored['idempotency_key']!=request()['idempotency_key']
 assert restarted.tick()
 result=restarted.get(fresh['job_id'],auth);assert result['state']=='succeeded',result
 new=result['result']['data']['workflow'];assert new['workflow_id']!=w['workflow_id']
 assert {a['agent_id'] for a in new['agents']}.isdisjoint(a['agent_id'] for a in w['agents'])
 assert restarted.submit(request(),auth)==result
 assert jobs.get(original['job_id'],auth)==original
 assert ctx.save(new,key='save_recreated_durable').status_code==200
 tombstone(ctx,new,stamp='2026-10-17T14:00:00Z')
 next_job=restarted.submit(request(),auth)
 assert next_job['job_id'] not in {original['job_id'],fresh['job_id']}
 assert restarted.submit(request(),auth)==next_job
 assert restarted.tick()
 third=restarted.get(next_job['job_id'],auth)['result']['data']['workflow']
 assert third['workflow_id'] not in {w['workflow_id'],new['workflow_id']}

def test_concurrent_retry_after_deletion_creates_only_one_queued_job(ctx):
 jobs,auth,original,w=completed(ctx);tombstone(ctx,w)
 with ThreadPoolExecutor(max_workers=4) as pool:
  replies=list(pool.map(lambda _:jobs.submit(request(),auth),range(4)))
 assert len({j['job_id'] for j in replies})==1 and replies[0]['job_id']!=original['job_id']
 with ctx.service.store.transaction(write=False) as db:
  assert db.execute("SELECT count(*) FROM builder_planning_jobs WHERE state='queued'").fetchone()[0]==1

def test_other_workspace_tombstone_does_not_invalidate_completed_job(ctx):
 jobs,auth,original,w=completed(ctx);tombstone(ctx,w,workspace='foreign')
 assert jobs.submit(request(),auth)==original

def test_retry_key_payload_mismatch_still_rejected_after_deletion(ctx):
 jobs,auth,_,w=completed(ctx);tombstone(ctx,w)
 changed=deepcopy(request());changed['payload']['objective']='Different objective'
 with pytest.raises(ApiFailure) as error:jobs.submit(changed,auth)
 assert error.value.code=='IDEMPOTENCY_KEY_REUSED'

def test_deleted_latest_lookup_is_not_found_but_authorized_history_is_retained(ctx):
 _,_,_,w=completed(ctx)
 with ctx.service.store.transaction(write=False) as db:historical=ctx.service.store.get(db,'local-workspace',w['workflow_id'])
 tombstone(ctx,w)
 latest=ctx.client.get('/workflows/'+w['workflow_id'])
 assert latest.status_code==404 and latest.json()['data']['error']['error_code']=='WORKFLOW_NOT_FOUND'
 history=ctx.client.get('/workflows/'+w['workflow_id']+'?version=1')
 assert history.status_code==200,history.text
 assert history.json()['data']['workflow']['workflow_id']==w['workflow_id']
 with ctx.service.store.transaction(write=False) as db:assert ctx.service.store.get(db,'local-workspace',w['workflow_id'])==historical
