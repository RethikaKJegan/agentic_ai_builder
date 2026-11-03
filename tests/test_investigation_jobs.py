from copy import deepcopy
import json
import pytest
from tests.test_business_investigations import investigation,OBJECTIVE
from tests.test_business_retrieval import retrieval
from tests.test_business_knowledge import knowledge
from tests.test_business_reference import reference
from tests.test_business_generation import generation
from tests.test_business_ontology import foundation,auth
from workflow_api.investigation_jobs import InvestigationJobs
from workflow_api.investigation_planning import InvestigationPlanner
from workflow_api.service import ApiFailure

@pytest.fixture
def jobs(investigation):
 x=investigation
 x.a['permissions'].append('workflow.plan');x.current['permissions'].append('workflow.plan')
 x.service.planner=InvestigationPlanner(provider=lambda payload,feedback:deepcopy(payload['reference_graph']))
 x.jobs=InvestigationJobs(x.service,lambda w,o:x.current if (w,o)==('one','alice') else None)
 return x

def body():return dict(request_key='job_plan_key_001',kind='plan',payload=dict(objective=OBJECTIVE,request_key='job_plan_payload_001',planning_mode='model',analysis_mode='crewai'))

def test_durable_plan_job_and_scoped_listing(jobs):
 x=jobs;j=x.jobs.submit(x.a,body())
 assert j['state']=='queued' and 'payload' not in j and not x.reader.calls
 assert x.jobs.submit(x.a,body())==j
 assert x.jobs.tick()
 j=x.jobs.get(x.a,j['job_id']);assert j['state']=='succeeded'
 p=x.service.get_plan(x.a,j['workflow_id']);assert p['planning']['mode']=='model'
 assert x.jobs.list(x.a)['items'][0]['workflow_id']==p['workflow_id']
 assert not x.reader.calls
 with pytest.raises(ApiFailure):x.jobs.get(auth(owner='bob'),j['job_id'])
 bad=body();bad['payload']['objective']='Show complaints for engine E123.'
 with pytest.raises(ApiFailure):x.jobs.submit(x.a,bad)

def test_permission_rechecked_before_paid_planning(jobs):
 x=jobs;j=x.jobs.submit(x.a,body());x.current['permissions'].remove('workflow.plan')
 assert x.jobs.tick()
 j=x.jobs.get(x.a,j['job_id']);assert j['state']=='failed' and j['error']['code']=='INVESTIGATION_DENIED'
 assert not x.jobs.list(x.a)['items'] and not x.reader.calls

def test_interrupted_jobs_are_not_replayed(jobs):
 x=jobs;j=x.jobs.submit(x.a,body())
 with x.f.store.transaction() as db:
  d=json.loads(db.execute('SELECT document FROM business_investigation_jobs').fetchone()[0]);d['state']='running'
  db.execute("UPDATE business_investigation_jobs SET state='running',claim='old',deadline=0,document=?",(json.dumps(d),))
 assert not x.jobs.tick()
 assert x.jobs.get(x.a,j['job_id'])['error']['code']=='INVESTIGATION_INTERRUPTED'
 assert not x.jobs.tick() and not x.jobs.list(x.a)['items']

def test_queued_work_survives_service_restart(jobs):
 x=jobs;j=x.jobs.submit(x.a,body())
 restarted=InvestigationJobs(x.service,lambda w,o:x.current)
 assert restarted.tick()
 assert restarted.get(x.a,j['job_id'])['state']=='succeeded'

def test_execute_jobs_call_same_executor_with_exact_run_id(jobs,monkeypatch):
 x=jobs;j=x.jobs.submit(x.a,body());x.jobs.tick();j=x.jobs.get(x.a,j['job_id'])
 r=x.service.create_run(x.a,j['workflow_id'],dict(request_key='queued_run_001'))
 calls=[]
 def execute(a,rid,b,resume):
  calls.append((rid,b,resume));return x.service.get_run(a,rid)
 monkeypatch.setattr(x.service,'execute',execute)
 queued=x.jobs.submit(x.a,dict(request_key='execute_job_001',kind='execute',payload={'run_id':r['run_id']}));x.jobs.tick()
 assert calls==[(r['run_id'],{},False)] and x.jobs.get(x.a,queued['job_id'])['state']=='succeeded'
 assert x.jobs.list(x.a)['items'][0]['run_id']==r['run_id']
 with pytest.raises(ApiFailure):x.jobs.submit(x.a,dict(request_key='bad_execute_001',kind='execute',payload={'run_id':r['run_id'],'graph':{}}))
