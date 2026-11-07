"""Phase 3 acceptance through real cases/queue/Registry/CrewAI and fake clocks/HTTP."""
from copy import deepcopy
from datetime import datetime,timezone
from concurrent.futures import ThreadPoolExecutor
from types import SimpleNamespace
import base64
import json
import time
import pytest
from tests.test_connected_action_plans import (connected,composition,investigation,retrieval,knowledge,reference,generation,foundation,auth,release,action,bind,approve,decide,stored)
from tests.test_business_composition import install_external
from tests.test_business_cases import stage,process
from tests.test_adaptive_orchestration import Evaluator,decision
from tests.test_google_connections import setup as google_setup,connect
from tests.test_google_tools import add_scopes
from workflow_api.google_connections import GoogleConnections
from workflow_api.google_tools import GoogleTools
from workflow_api.business_cases import BusinessCases
from workflow_api.adaptive_orchestration import AdaptiveOrchestration
from workflow_api.lifecycle_driver import LifecycleDriver
from workflow_api.automation import DurableAutomation
from workflow_api.scheduler import TriggerScheduler,CronSchedule
from workflow_api.service import ApiFailure
from workflow_api.lifecycle import LifecycleFailure
from connector_extension.catalog import CATALOG
from connector_extension.mail import MailConnector
from connector_extension.google import GoogleAPI
from runtime.service import RuntimeFailure


@pytest.fixture
def automation(connected,google_setup):
    f=connected;_,env=google_setup;f.now=time.time();clock=lambda:f.now
    f.general.lifecycle.clock=clock;f.runtime.clock=clock
    manager=GoogleConnections(f.general.store,env);record=connect(manager,actor=f.x.a,email='owner@example.com')
    f.connection=record['connection_id'];add_scopes(manager,f.connection,['gmail.send','gmail.readonly','spreadsheets'])
    f.manager=manager;f.general.google_tools=GoogleTools(manager,f.general);f.general.bind_google_connector=f.general.google_tools.bind
    f.x.a['permissions']=sorted(set(f.x.a['permissions'])|{'events.ingest'})
    f.general.worker_authenticate=lambda w,o:deepcopy(f.x.a) if (w,o)==('one','alice') else None
    tool,_=install_external(f,'extension_mail_thread')
    policy=deepcopy(f.registry._policy);policy.version+=1
    policy.credential_references['cred_extension_gmail']['scopes']=sorted(set(policy.credential_references['cred_extension_gmail']['scopes'])|set(tool['authentication']['scopes'])|set(tool['permission_scopes']))
    assert f.registry.update_policy(policy,f.x.a)['status']==200
    assert f.registry.register_tool(tool,f.x.a,'cred_extension_gmail')['status']==200
    f.connectors['extension_mail_thread']=MailConnector(CATALOG['extension_mail_thread'],f.connectors['extension_mail_send'].api,f.connectors['extension_mail_send'].journal,f.connectors['extension_mail_send'].artifacts)
    f.messages=[];original=f.http.request
    def request(method,url,headers,body=None,timeout=30):
        if '/threads/' in url:return dict(id='report_thread',messages=deepcopy(f.messages))
        return original(method,url,headers,body,timeout)
    f.http.request=request
    f.request['google_connection_id']=f.connection
    f.cases=BusinessCases(f.general,clock=clock);f.general.business_cases=f.cases
    f.auto=DurableAutomation(f.general,clock=clock)
    return f


def adaptive_case(f,stop_at=None,*,use_planner=False):
    req=deepcopy(f.request)
    read=action('reply_read','tool.extension_mail_thread',[bind('receipt','thread_id',action='send',path=['thread_id'])],['send'])
    content=action('reply_analysis','content.prepare',[bind('output','data',action='reply_read')],['reply_read'],['reply_read'])
    req['action_plan']['actions'] += [read,content];req['action_plan']['completion_criteria']=['reply_analysis']
    planned=deepcopy(req['action_plan'])
    caps=list(dict.fromkeys(a['capability_id'] for a in req['action_plan']['actions']))
    definition=process(stage(required_inputs={},required_capabilities=caps,allowed_tools=list(f.connectors),side_effect_classification='write',output_schema={'type':'object'},output_bindings={},timeout_policy={'seconds':600,'action':'block'}))
    f.cases.publish(f.x.a,definition)
    c=f.cases.create(f.x.a,dict(request_key='automation_case_001',process_definition_id=definition['process_definition_id'],process_definition_version=1,original_user_goal=req['objective'],google_connection_id=f.connection,business_request={'inputs':{'identifiers':{'complaint_id':'C123'}}}))
    c=f.cases.command(f.x.a,c['case_id'],'prepare',dict(request_key='automation_prepare_001',expected_revision=c['revision']))
    req.pop('request_key');req.pop('preparation_id')
    if use_planner:req.pop('action_plan')
    c=AdaptiveOrchestration(f.cases).enable(f.x.a,c['case_id'],dict(request_key='automation_enable_001',expected_revision=c['revision'],stage_instance_id='first',plan_request=req))
    evaluator=Evaluator();asked=[]
    if use_planner:
        f.planner_contexts=[]
        def plan_actions(goal,context):
            f.planner_contexts.append(deepcopy(context))
            return deepcopy(planned)
        evaluator.plan_actions=plan_actions
    def custom(ctx):
        if 'send' in ctx['completed_actions'] and not asked:
            asked.append(True)
            return decision(ctx,'wait_for_event',['reply_read'],event={'event_type':'mail.reply','expected_source':'gmail','schema':{'type':'object','required':['finding'],'additionalProperties':False,'properties':{'finding':{'type':'string'}}},'deadline_seconds':86400})
    evaluator.custom=custom;f.general.planner.provider=evaluator;f.evaluator=evaluator;f.case_id=c['case_id']
    for i in range(8):
        result=LifecycleDriver(f.cases).drive(f.x.a,c['case_id'],dict(request_key='before_reply_'+str(i),max_commands=32,max_seconds=120))
        c=f.cases.get(f.x.a,c['case_id']);a=c['adaptive']
        assert result['stop_reason'] in ('approval_wait','external_or_input_wait'),result.get('error_code')
        workflow=f.c.workflow(f.x.a,a['composition_id'])
        if result['stop_reason']=='external_or_input_wait':return c
        assert result['stop_reason']=='approval_wait',result.get('error_code')
        if not a.get('run_id'):
            assert f.adapter.approve_pending(workflow,f.x.a)['ready'];approve(f,workflow)
        else:
            saved=stored(f,a['run_id'])
            if stop_at and saved['action_instances'].get(stop_at,{}).get('state')=='waiting_for_approval':return c
            decide(f,workflow,saved)
    raise AssertionError('Did not reach reply wait')


def subscription(f,c):
    run=stored(f,c['adaptive']['run_id']);receipt=run['action_instances']['send']['output'];w=f.c.workflow(f.x.a,c['adaptive']['composition_id'])
    body=dict(request_key='subscribe_reply_001',case_id=c['case_id'],wait_id=c['adaptive']['pending_wait']['wait_id'],stage_id='first',provider='gmail',connection_id=f.connection,correlation={'thread_id':receipt['thread_id'],'sent_message_id':receipt['message_id'],'rfc_message_id':receipt['rfc_message_id']},participants=['engineer@example.com'],expected_information='Field inspection observations.',payload_mapping={'finding':'text'},deadline=f.now+7*86400,poll_workflow={'workflow_id':w['workflow_id'],'workflow_version':1})
    return f.auto.subscribe(f.x.a,body)


def reply(f,sub,identifier='incoming_1',sender='engineer@example.com',thread='report_thread',reference=None,text='Inspection reported a loose hose connection.'):
    rfc=reference or sub['request']['correlation']['rfc_message_id']
    return dict(id=identifier,threadId=thread,internalDate=str(int(f.now*1000)),payload={'mimeType':'text/plain','headers':[{'name':'From','value':sender},{'name':'To','value':'owner@example.com'},{'name':'Message-ID','value':'<'+identifier+'@example.com>'},{'name':'In-Reply-To','value':rfc}], 'body':{'data':base64.urlsafe_b64encode(text.encode()).decode()}})


def drain(f):
    jobs=f.general.lifecycle.lease('one',limit=10,seconds=120)
    return [f.general.lifecycle.execute_job(j['job_id'],f.runner) for j in jobs]


def trace(f,path,case=None):
    with f.general.store.transaction(write=False) as db:
        jobs=[json.loads(r[0]) for r in db.execute('SELECT document FROM lifecycle_jobs').fetchall()]
        runs=[json.loads(r[0]) for r in db.execute('SELECT document FROM runtime_runs').fetchall()]
        events=[json.loads(r[0]) for r in db.execute('SELECT document FROM runtime_events ORDER BY sequence').fetchall()]
        records=[json.loads(r[0]) for r in db.execute('SELECT document FROM automation_records').fetchall()]
    path.write_text(json.dumps(dict(case=case,records=records,jobs=jobs,runs=runs,events=events,qualification='Actual Registry, CrewAI, cases, lifecycle queue, Google adapters and journals; fake clocks and controlled source/model/HTTP transports; no live provider effect.'),indent=2)+'\n')


def test_reply_resumes_same_case_after_days_once(automation,tmp_path):
    f=automation;c=adaptive_case(f);sub=subscription(f,c);before=stored(f,c['adaptive']['run_id'])
    assert f.http.write_count==1 and len(f.http.sent)==1
    f.now+=3*86400
    # Runtime workers must leave a durable external wait suspended.
    f.runner.advance(before['run_id'],f.x.a);assert stored(f,before['run_id'])['status']=='running'
    f.messages=[reply(f,sub,'unrelated',sender='stranger@example.com'),reply(f,sub)]
    f.auto=DurableAutomation(f.general,clock=lambda:f.now)
    f.auto.tick(f.general.worker_authenticate)
    saved=f.cases.get(f.x.a,c['case_id']);assert saved['adaptive']['pending_wait'] is None
    assert saved['automation_evidence'][0]['payload']['message_id']=='incoming_1'
    jobs=drain(f);assert jobs and jobs[0]['state']=='completed',jobs
    saved=f.cases.get(f.x.a,c['case_id']);assert saved['adaptive']['status']=='completed'
    assert saved['adaptive']['waited_seconds']>=3*86400
    assert stored(f,before['run_id'])['action_instances']['sheet']==before['action_instances']['sheet']
    assert f.http.write_count==1 and len(f.http.sent)==1
    event={'event_id':'incoming_1','payload':saved['automation_evidence'][0]['payload']}
    assert f.auto.accept(f.x.a,sub['id'],event)['duplicate']
    assert not drain(f)
    assert any(o['kind']=='authenticated_event_report' for ctx in f.evaluator.contexts for o in ctx['observations'])
    trace(f,tmp_path/'reply-driven-trace.json',saved)


def scheduled(f,missed='coalesce',overlap='forbid',narrow=False):
    doc=f.c.prepare_actions(f.x.a,f.request);w=f.c.workflow(f.x.a,doc['composition_id']);assert f.adapter.approve_pending(w,f.x.a)['ready'];approve(f,w)
    policy=f.auto.authorize(f.x.a,dict(request_key='recurring_consent_001',connection_id=f.connection,operations={'extension_sheets_create_report':{'type':'object','required':['project_id'],'properties':{'project_id':{'const':'complaint_report'}}},'extension_mail_send':{'type':'object','required':['to','subject','body'],'properties':{'to':{'const':'different@example.com' if narrow else 'engineer@example.com'},'subject':{'type':'string','maxLength':1000},'body':{'type':'string','maxLength':12000}},'additionalProperties':False}},purpose='Daily source-backed complaint report.',content_scope='Complaint observations, explicit assumptions and verified report URL.',schedule={'cron':'0 18 * * *','timezone':'Asia/Kolkata'},limits={'max_occurrences':10,'max_actions_per_occurrence':8},expires_at=f.now+30*86400))
    schedule=f.auto.schedule(f.x.a,dict(request_key='daily_report_001',workflow={'workflow_id':w['workflow_id'],'workflow_version':1},authorization_id=policy['id'],cron='0 18 * * *',timezone='Asia/Kolkata',missed_run_policy=missed,overlap_policy=overlap,inputs={}))
    return schedule,policy,w


def test_daily_report_distinct_occurrences_fresh_reads_and_restart(automation,tmp_path):
    f=automation;s,p,w=scheduled(f)
    from zoneinfo import ZoneInfo
    assert datetime.fromtimestamp(s['due'],timezone.utc).astimezone(ZoneInfo('Asia/Kolkata')).hour==18
    f.now=s['due'];f.auto.tick(f.general.worker_authenticate);one=drain(f);assert one[0]['state']=='completed',one
    first=f.auto.listing(f.x.a,'occurrence')['items'][0];assert first['result']['status']=='completed'
    f.auto=DurableAutomation(f.general,clock=lambda:f.now);f.auto.tick(f.general.worker_authenticate);assert not drain(f)
    f.x.reader.rows['tickets'][0]['complaintRecord']['natureOfCustomerComplaint']='Updated current source observation'
    f.now=f.auto.get(f.x.a,s['id'])['due'];f.auto.tick(f.general.worker_authenticate);two=drain(f);assert two[0]['state']=='completed',two
    occurrences=f.auto.listing(f.x.a,'occurrence')['items'];assert len(occurrences)==2 and len({o['run_id'] for o in occurrences})==2
    runs=[stored(f,o['run_id']) for o in occurrences]
    assert all(r['action_instances']['read']['verified_receipt'] and r['action_instances']['send']['verified_receipt'] for r in runs)
    assert runs[0]['action_instances']['read']['output']!=runs[1]['action_instances']['read']['output']
    assert sum('Updated current source observation' in json.dumps(r['action_instances']['read']['output']) for r in runs)==1
    assert all(r['release_bound'] for r in runs)
    assert f.http.write_count==2 and len(f.http.sent)==2
    assert all(len(r['automation_approvals'])==2 for r in runs)
    trace(f,tmp_path/'daily-schedule-trace.json')


def test_out_of_scope_action_stays_at_exact_payload_approval(automation):
    f=automation;s,p,w=scheduled(f,narrow=True);f.now=s['due'];f.auto.tick(f.general.worker_authenticate);result=drain(f)
    assert result[0]['state']=='waiting' and f.http.write_count==1 and not f.http.sent
    occurrence=f.auto.listing(f.x.a,'occurrence')['items'][0]
    assert stored(f,occurrence['run_id'])['approvals'][-1]['status']=='pending'


@pytest.mark.parametrize('reason',['cancelled','revoked','expired','connection'])
def test_revocation_blocks_scheduled_dispatch(automation,reason):
    f=automation;s,p,w=scheduled(f);f.now=s['due'];f.auto.tick(f.general.worker_authenticate)
    if reason=='cancelled':f.auto.control(f.x.a,s['id'],{'request_key':'cancel_schedule_001','action':'cancel'})
    elif reason=='revoked':f.auto.control(f.x.a,p['id'],{'request_key':'revoke_consent_001','action':'revoke'})
    elif reason=='expired':f.now=p['request']['expires_at']+1
    else:
        with f.manager.store.transaction() as db:db.execute("UPDATE google_connections SET status='revoked' WHERE connection_id=?",(f.connection,))
    result=drain(f);assert result[0]['state']=='dead_letter'
    assert not f.http.sent and f.http.write_count==0


@pytest.mark.parametrize('expression,zone',[('bad','Asia/Kolkata'),('61 18 * * *','UTC'),('0 18 * * *','No/Zone'),('*/0 * * * *','UTC')])
def test_invalid_cron_rejected(expression,zone):
    with pytest.raises(LifecycleFailure):CronSchedule(expression,zone)


def test_cron_dst_and_dom_dow_semantics():
    stamp=lambda v:datetime.fromisoformat(v).timestamp()
    cron=CronSchedule('30 2 * * *','America/New_York')
    # Spring gap has no 02:30 occurrence.
    assert cron.next(stamp('2026-03-08T06:59:00+00:00'))==stamp('2026-03-09T06:30:00+00:00')
    cron=CronSchedule('30 1 * * *','America/New_York')
    first=cron.next(stamp('2026-11-01T04:00:00+00:00'));second=cron.next(first)
    assert second-first==3600


def test_timer_deadline_reevaluates_and_requires_fresh_followup_approval(automation,tmp_path):
    f=automation;c=adaptive_case(f);sub=subscription(f,c);changed=[]
    def custom(ctx):
        if any(o['kind']=='timer_expired' for o in ctx['observations']) and not changed:
            changed.append(True)
            # Required registered thread capability stays in the reviewed plan;
            # absence of replies is represented by its actual empty thread read.
            p={'actions':deepcopy(ctx['plan']['actions']),'completion_criteria':['followup_send'],'missing_inputs':[]}
            content=action('followup_content','content.prepare',[bind('generated','data',action='analysis'),bind('receipt','artifact_url',action='sheet',path=['spreadsheet_url'])],['analysis','sheet'],['analysis','sheet'])
            content['instructions']='Draft a follow-up stating that the deadline expired without a received reply.'
            follow=action('followup_send','tool.extension_mail_send',[bind('literal','to','recipient'),bind('generated','subject',action='followup_content',path=['subject']),bind('generated','body',action='followup_content',path=['body'])],['followup_content'])
            p['actions'] += [content,follow]
            return decision(ctx,'revise_plan',['reply_read'],p)
    f.evaluator.custom=custom
    timer=f.auto.timer(f.x.a,dict(request_key='reply_followup_timer',case_id=c['case_id'],wait_id=c['adaptive']['pending_wait']['wait_id'],stage_id='first',due=f.now+2*86400,purpose='follow_up'))
    f.now=timer['due'];f.auto.tick(f.general.worker_authenticate);jobs=drain(f)
    assert jobs[0]['state']=='waiting' and len(f.http.sent)==1
    for _ in range(6):
        current=f.cases.get(f.x.a,c['case_id']);a=current['adaptive'];w=f.c.workflow(f.x.a,a['composition_id'])
        if not a['run_id']:
            assert f.adapter.approve_pending(w,f.x.a)['ready'];approve(f,w)
        else:
            run=stored(f,a['run_id'])
            if run['status']=='paused_for_approval':decide(f,w,run)
        f.auto.tick(f.general.worker_authenticate);drain(f)
        if f.cases.get(f.x.a,c['case_id'])['adaptive']['status']=='completed':break
    current=f.cases.get(f.x.a,c['case_id'])
    assert current['adaptive']['status']=='completed' and len(f.http.sent)==2 and f.http.write_count==1
    assert f.auto.get(f.x.a,timer['id'])['state']=='completed'
    f.auto.tick(f.general.worker_authenticate);drain(f);assert len(f.http.sent)==2
    trace(f,tmp_path/'deadline-followup-trace.json',current)


def test_crash_after_event_commit_recovers_leased_job_and_rejects_stale_worker(automation):
    f=automation;c=adaptive_case(f);sub=subscription(f,c);f.messages=[reply(f,sub)]
    f.auto.tick(f.general.worker_authenticate)
    leased=f.general.lifecycle.lease('one',limit=1,seconds=5)[0];old=f.general.lifecycle.leased_tokens[leased['job_id']]
    # Process loss after evidence+job commit, before the driver is invoked.
    f.now+=6;f.auto=DurableAutomation(f.general,clock=lambda:f.now)
    new=f.general.lifecycle.lease('one',limit=1,seconds=120)[0]
    with pytest.raises(LifecycleFailure):f.general.lifecycle.execute_job(new['job_id'],f.runner,claim=old)
    assert f.general.lifecycle.execute_job(new['job_id'],f.runner)['state']=='completed'
    assert len(f.http.sent)==1 and f.http.write_count==1


def test_concurrent_due_ticks_and_workers_do_not_duplicate_occurrence(automation):
    f=automation;s,p,w=scheduled(f);f.now=s['due']
    with ThreadPoolExecutor(max_workers=2) as pool:list(pool.map(lambda _:f.auto.tick(f.general.worker_authenticate),range(2)))
    with ThreadPoolExecutor(max_workers=2) as pool:batches=list(pool.map(lambda _:f.general.lifecycle.lease('one',limit=1),range(2)))
    jobs=[j for batch in batches for j in batch];assert len(jobs)==1
    assert f.general.lifecycle.execute_job(jobs[0]['job_id'],f.runner)['state']=='completed'
    assert len(f.auto.listing(f.x.a,'occurrence')['items'])==1 and len(f.http.sent)==1


def test_restart_after_completed_send_before_job_commit_never_resends(automation,tmp_path):
    from unittest.mock import patch
    f=automation;s,p,w=scheduled(f);f.now=s['due'];f.auto.tick(f.general.worker_authenticate)
    job=f.general.lifecycle.lease('one',limit=1,seconds=120)[0]
    class Crash(BaseException):pass
    with patch.object(f.general.lifecycle,'_finish_job',side_effect=Crash):
        with pytest.raises(Crash):f.general.lifecycle.execute_job(job['job_id'],f.runner)
    assert len(f.http.sent)==1 and f.http.write_count==1
    f.now+=121;f.auto=DurableAutomation(f.general,clock=lambda:f.now)
    result=drain(f);assert result[0]['state']=='completed'
    assert len(f.http.sent)==1 and f.http.write_count==1
    trace(f,tmp_path/'restart-recovery-trace.json')


def test_uncertain_gmail_send_is_not_retried_and_blocks_overlap(automation,tmp_path):
    f=automation;s,p,w=scheduled(f);original=f.http.request
    def uncertain(method,url,headers,body=None,timeout=30):
        if url.endswith('/messages/send'):
            original(method,url,headers,body,timeout)
            raise TimeoutError('controlled ambiguous transport')
        return original(method,url,headers,body,timeout)
    f.http.request=uncertain;f.now=s['due'];f.auto.tick(f.general.worker_authenticate);out=drain(f)
    assert out[0]['state']=='dead_letter' and out[0]['last_error_code']=='ACTION_EFFECT_UNVERIFIED' and len(f.http.sent)==1
    occurrence=f.auto.listing(f.x.a,'occurrence')['items'][0];assert occurrence['state']=='requires_reconciliation' and occurrence['last_error_code']=='ACTION_EFFECT_UNVERIFIED'
    f.now=f.auto.get(f.x.a,s['id'])['due'];f.auto.tick(f.general.worker_authenticate);assert not drain(f)
    assert len(f.http.sent)==1
    trace(f,tmp_path/'uncertain-send-trace.json')


def test_subscription_revocation_cancellation_and_cross_workspace(automation):
    f=automation;c=adaptive_case(f);sub=subscription(f,c);f.messages=[reply(f,sub)]
    other=deepcopy(f.x.a);other['subject']['workspace_id']='another'
    with pytest.raises(ApiFailure):f.auto.get(other,sub['id'])
    with f.manager.store.transaction() as db:db.execute("UPDATE google_connections SET status='revoked' WHERE connection_id=?",(f.connection,))
    f.auto.tick(f.general.worker_authenticate)
    assert not drain(f) and f.auto.get(f.x.a,sub['id'])['last_error_code']=='GOOGLE_RECONNECT_REQUIRED'
    c=f.cases.get(f.x.a,c['case_id']);f.cases.command(f.x.a,c['case_id'],'cancel',dict(request_key='cancel_waiting_case',expected_revision=c['revision']))
    f.now+=60;f.auto.tick(f.general.worker_authenticate);assert f.auto.get(f.x.a,sub['id'])['state']=='cancelled'
    assert f.http.write_count==1 and len(f.http.sent)==1


@pytest.mark.parametrize('policy',['skip','coalesce','catch_up'])
def test_missed_run_policies_and_idempotent_controls(automation,policy):
    f=automation;s,p,w=scheduled(f,missed=policy,overlap='allow');f.now=s['due']+3*86400
    f.auto.tick(f.general.worker_authenticate);occurrences=f.auto.listing(f.x.a,'occurrence')['items']
    assert len(occurrences)=={'skip':0,'coalesce':1,'catch_up':4}[policy]
    one=f.auto.control(f.x.a,s['id'],{'request_key':'pause_schedule_once','action':'pause'})
    assert f.auto.control(f.x.a,s['id'],{'request_key':'pause_schedule_once','action':'pause'})==one
    with pytest.raises(ApiFailure):f.auto.control(f.x.a,s['id'],{'request_key':'pause_schedule_once','action':'resume'})


def test_approval_deadline_timer_never_grants_send_authority(automation):
    f=automation;s,p,w=scheduled(f,narrow=True);f.now=s['due'];f.auto.tick(f.general.worker_authenticate);drain(f)
    occurrence=f.auto.listing(f.x.a,'occurrence')['items'][0];rr=stored(f,occurrence['run_id'])
    # Recurring run gates are governed by their existing runtime approval deadline.
    f.now=rr['approval_context']['expires_at']+1;f.runner.advance(rr['run_id'],f.x.a)
    assert stored(f,rr['run_id'])['approvals'][-1]['status']=='timed_out'
    assert not f.http.sent and f.http.write_count==1


def test_generic_worker_scheduler_with_native_retail_package(automation,tmp_path):
    from tests.test_simpson_lifecycle import configure
    from tests.test_generic_lifecycle_phase6 import retail
    f=automation;cases,_,_=configure(f,True);f.general.business_cases=cases;cases.clock=lambda:f.now
    f.runner=f.general.runtime_runner;f.runtime=f.runner.runtime;f.runtime.clock=lambda:f.now;f.cases=cases
    _,reads=retail(f,cases)
    doc=f.c.prepare(f.x.a,dict(request_key='retail_scheduled_plan',objective='Read mapped retail complaint evidence and prepare a source-backed report.',client_package_id='retail_complaint_fixture',client_package_revision=1,google_connection_id=f.connection,operations=[{'capability_id':'retail.complaint.read','inputs':{}}]))
    w=f.c.workflow(f.x.a,doc['composition_id']);assert f.adapter.approve_pending(w,f.x.a)['ready'];approve(f,w)
    policy=f.auto.authorize(f.x.a,dict(request_key='retail_recurring_consent',connection_id=f.connection,operations={'client_package_read':{'type':'object','required':['package_id'],'properties':{'package_id':{'const':'retail_complaint_fixture'}}}},purpose='Retail test report.',content_scope='Mapped retail order evidence; no commercial authorization.',schedule={'cron':'0 18 * * *','timezone':'Asia/Kolkata'},limits={'max_occurrences':3,'max_actions_per_occurrence':16},expires_at=f.now+7*86400))
    schedule=f.auto.schedule(f.x.a,dict(request_key='retail_daily_schedule',workflow={'workflow_id':w['workflow_id'],'workflow_version':1},authorization_id=policy['id'],cron='0 18 * * *',timezone='Asia/Kolkata',missed_run_policy='coalesce',overlap_policy='forbid',inputs={}))
    before=len(reads);f.now=schedule['due'];f.auto.tick(f.general.worker_authenticate)
    assert drain(f)[0]['state']=='completed'
    assert len(reads)>before
    occurrence=f.auto.listing(f.x.a,'occurrence')['items'][0]
    assert stored(f,occurrence['run_id'])['status']=='completed'
    trace(f,tmp_path/'retail-schedule-trace.json')


def test_durable_approval_timer_queues_reevaluation_without_send(automation):
    f=automation;c=adaptive_case(f,stop_at='send');run=stored(f,c['adaptive']['run_id'])
    timer=f.auto.timer(f.x.a,dict(request_key='approval_deadline_timer',case_id=c['case_id'],stage_id='first',wait_id=run['approvals'][-1]['approval_id'],due=f.now+3600,purpose='approval_deadline'))
    f.evaluator.custom=lambda ctx:decision(ctx,'request_input',['send'],inputs=[{'key':'review_required','schema':{'type':'boolean'},'reason':'The authorization deadline expired; review is required.'}])
    f.now=timer['due'];f.auto.tick(f.general.worker_authenticate)
    assert stored(f,run['run_id'])['approvals'][-1]['status']=='timed_out'
    result=drain(f);assert result[0]['state']=='completed'
    current=f.cases.get(f.x.a,c['case_id'])
    assert current['adaptive']['pending_wait']['kind']=='input'
    assert not f.http.sent and f.http.write_count==1


def test_automation_api_authentication_and_invalid_schedule_contract(google_setup):
    from fastapi.testclient import TestClient
    from workflow_api.main import create_app,COOKIE
    from workflow_api.service import WorkflowService
    manager,env=google_setup
    app=create_app(service=WorkflowService(manager.store),dev_auth=True,roles=['builder'],start_workers=False,planning_worker_enabled=False,google_oauth_config=env)
    with TestClient(app) as client:
        assert client.get('/business-ontology/v1/automation').status_code==401
        session=client.get('/session');client.cookies.set(COOKIE,session.cookies[COOKIE],path='/')
        response=client.get('/business-ontology/v1/automation')
        assert response.status_code==200 and response.json()['data']['items']==[]
        response=client.post('/business-ontology/v1/automation/schedules',json={'request_key':'invalid_schedule_001'})
        assert response.status_code==422 and response.json()['data']['error']['error_code']=='AUTOMATION_REQUEST_INVALID'
        app.state.workflow_auth['roles']=['viewer'];app.state.workflow_auth['permissions']=['workflow.view']
        response=client.post('/business-ontology/v1/automation/absent/control',json={'request_key':'unauthorized_control','action':'pause'})
        assert response.status_code==403


def test_processed_reply_cannot_satisfy_a_later_subscription(automation):
    f=automation;c=adaptive_case(f);sub=subscription(f,c);asked=[]
    def custom(ctx):
        if 'reply_analysis' in ctx['completed_actions'] and not asked:
            asked.append(True)
            return decision(ctx,'wait_for_event',['reply_analysis'],event={'event_type':'mail.reply','expected_source':'gmail','schema':{'type':'object','required':['finding'],'properties':{'finding':{'type':'string'}},'additionalProperties':False},'deadline_seconds':86400})
    f.evaluator.custom=custom;f.now+=2;f.messages=[reply(f,sub)]
    f.auto.tick(f.general.worker_authenticate);assert drain(f)[0]['state']=='completed'
    current=f.cases.get(f.x.a,c['case_id']);wait=current['adaptive']['pending_wait'];assert wait
    new_body=deepcopy(sub['request']);new_body.update(request_key='second_reply_subscription',wait_id=wait['wait_id'])
    second=f.auto.subscribe(f.x.a,new_body);f.auto.tick(f.general.worker_authenticate)
    assert f.auto.get(f.x.a,second['id'])['state']=='active' and not drain(f)
    f.now+=16;f.messages.append(reply(f,second,'incoming_second'))
    f.auto.tick(f.general.worker_authenticate);assert drain(f)[0]['state']=='completed'
    final=f.cases.get(f.x.a,c['case_id']);assert final['adaptive']['status']=='completed'
    assert len(final['automation_evidence'])==2 and len(f.http.sent)==1 and f.http.write_count==1


def test_existing_trigger_scheduler_dispatches_owner_scoped_automation(automation):
    f=automation;s,p,w=scheduled(f)
    del f.general.worker_authenticate
    authenticate=lambda workspace,owner:deepcopy(f.x.a) if (workspace,owner)==('one','alice') else None
    scheduler=TriggerScheduler(f.general,authenticate,interval=1)
    f.now=s['due'];result=scheduler.tick()
    assert result['dispatched']==1 and len(f.http.sent)==1 and f.http.write_count==1
    assert f.auto.listing(f.x.a,'occurrence')['items'][0]['state']=='completed'
