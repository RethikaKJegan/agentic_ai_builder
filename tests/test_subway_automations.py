"""Synthetic Phase 3 checks through native Registry/GraphRunner and durable queue."""
from copy import deepcopy
from datetime import datetime,timezone
import pytest
from tests.test_subway_autonomy import subway,engine,installed,start,decision,load
from workflow_api.automation import DurableAutomation
from workflow_api.subway_automation import query_consent
from workflow_api.temporal_queries import window


def schedule(f,monkeypatch,evaluate=None):
    import tests.test_subway_autonomy as helpers
    original=helpers.route
    def recurring(selected,**kw):
        return original(selected,**{**kw,**({'temporal':f.temporal_override} if hasattr(f,'temporal_override') else {}),'intent_type':'recurring','recurrence':dict(kind='daily',hour=9,minute=0,weekdays=[],timezone='Asia/Kolkata',date=None,month_day=None)})
    monkeypatch.setattr(helpers,'route',recurring)
    _,doc,w=start(f,evaluate or (lambda ctx,**_:decision(ctx)),'Investigate purchasing every day at 9 AM India time.')
    f.now=f.service.lifecycle.clock()
    f.service.lifecycle.clock=lambda:f.now
    f.service.worker_authenticate=lambda ws,owner:deepcopy(f.auth) if (ws,owner)==('client-subway','subway-client') else None
    auto=DurableAutomation(f.service,clock=lambda:f.now)
    intent=w['metadata']['overview_intent']
    consent=auto.authorize(f.auth,dict(request_key='native_consent_1',connection_id=None,operations={'subway_query':query_consent(doc,intent)},purpose='Reviewed daily purchasing investigation',content_scope='Reviewed native sources only',schedule=dict(cron='0 9 * * *',timezone='Asia/Kolkata'),limits=dict(max_occurrences=getattr(f,'max_occurrences_override',3),max_actions_per_occurrence=getattr(f,'max_actions_override',16)),expires_at=f.now+86400*7))
    record=auto.schedule(f.auth,dict(request_key='native_schedule_1',workflow=dict(workflow_id=w['workflow_id'],workflow_version=1),authorization_id=consent['id'],cron='0 9 * * *',timezone='Asia/Kolkata',missed_run_policy='coalesce',overlap_policy='forbid',inputs={}))
    return auto,record,consent


def dispatch(f,auto):
    for _ in range(10):
        auto.tick(f.service.worker_authenticate)
        jobs=f.service.lifecycle.lease('client-subway')
        for job in jobs:f.service.lifecycle.execute_job(job['job_id'],f.service.runtime_runner)
        occurrences=auto.listing(f.auth,'occurrence')['items']
        if occurrences and all(o['state'] in ('completed','failed','dead_letter') for o in occurrences):return occurrences
    pytest.fail('Durable fixture did not finish within bounded ticks.')


def test_native_daily_adaptive_occurrences_and_dedup(subway,monkeypatch):
    f=subway;auto,record,consent=schedule(f,monkeypatch)
    f.now=record['due']
    first=dispatch(f,auto)
    assert len(first)==1 and first[0]['state']=='completed',first
    run=load(f,first[0]['run_id'])
    assert run['adaptive']['status']=='completed' and not run.get('case_id')
    assert {u['concept_id'] for u in run['action_instances']['read']['ontology_usage']}=={'procurement:finance_purchaseorders'}
    assert run['action_instances']['report']['ontology_usage'] and run['task_checkpoints']['read']
    assert run['automation_reference']['scheduled_due']==record['due']
    auto.tick(f.service.worker_authenticate)
    assert len(auto.listing(f.auth,'occurrence')['items'])==1
    f.now=auto.get(f.auth,record['id'])['due']
    second=dispatch(f,auto)
    assert len(second)==2 and all(o['state']=='completed' for o in second),second
    assert len({o['run_id'] for o in second})==2
    assert auto.get(f.auth,consent['id'])['used_occurrences']==2


def test_native_revoked_worker_cannot_dispatch(subway,monkeypatch):
    f=subway;auto,record,_=schedule(f,monkeypatch);f.now=record['due']
    auto.tick(f.service.worker_authenticate)
    f.service.worker_authenticate=lambda *_:None
    for job in f.service.lifecycle.lease('client-subway'):f.service.lifecycle.execute_job(job['job_id'],f.service.runtime_runner)
    occurrence=auto.listing(f.auth,'occurrence')['items'][0]
    assert occurrence['state']=='failed' and occurrence['last_error_code']=='AUTOMATION_AUTH_REVOKED'
    assert occurrence['run_id'] is None


@pytest.mark.parametrize('period,expected',[
 ('previous_quarter',('2025-10-01T04:00:00+00:00','2026-01-01T05:00:00+00:00')),
 ('current_quarter',('2026-01-01T05:00:00+00:00','2026-04-01T04:00:00+00:00')),
 ('yesterday',('2026-03-08T05:00:00+00:00','2026-03-09T04:00:00+00:00'))])
def test_calendar_windows_quarter_and_dst(period,expected):
    due=datetime(2026,3,9,14,tzinfo=timezone.utc).timestamp()
    assert window(period,'America/New_York',due)==expected


class FixtureEvents:
    """Explicitly synthetic authenticated provider; never installed in live config."""
    def __init__(self,auth):self.auth=deepcopy(auth);self.events=[]
    def workflow_sources(self,auth):
        if auth['subject']!=self.auth['subject']:return []
        return [dict(source_id='synthetic-finance',event_type='invoice.created',payload_schema=dict(type='object',additionalProperties=False,properties={'invoice_id':dict(type='string')},required=['invoice_id']),**({'query_bindings':self.query_bindings} if getattr(self,'query_bindings',None) else {}))]
    def authenticate(self,sub,event,auth):return auth['subject']==self.auth['subject'] and event.get('event_id','').startswith('fixture:')
    def poll_workflow(self,sub,auth):return deepcopy(self.events),len(self.events)


def event_schedule(f,monkeypatch):
    import tests.test_subway_autonomy as helpers
    original=helpers.route
    f.auth['permissions']=sorted(set(f.auth['permissions'])|{'events.ingest'})
    adapter=FixtureEvents(f.auth)
    adapter.query_bindings=getattr(f,'event_query_bindings',[])
    if getattr(f,'numeric_event_identity',False):
        original_sources=adapter.workflow_sources
        def numeric_sources(auth):
            result=original_sources(auth)
            for source in result:source['payload_schema']['properties']['invoice_id']={'type':'integer'}
            return result
        adapter.workflow_sources=numeric_sources
    auto=DurableAutomation(f.service,providers={'fixture':adapter})
    def routed(selected,**kw):
        return original(selected,**{**kw,'intent_type':'event','event_selection':dict(provider='fixture',source_id='synthetic-finance',event_type='invoice.created',conditions=getattr(f,'event_conditions',[]))})
    monkeypatch.setattr(helpers,'route',routed)
    _,doc,w=start(f,getattr(f,'event_evaluator',None) or (lambda ctx,**_:decision(ctx)),getattr(f,'event_objective','Whenever a synthetic invoice arrives investigate its purchasing evidence.'))
    f.now=auto.clock();auto.clock=lambda:f.now;f.service.lifecycle.clock=lambda:f.now
    f.service.worker_authenticate=lambda ws,owner:deepcopy(f.auth) if (ws,owner)==('client-subway','subway-client') else None
    result=f.service.overview_automation.handle(f.auth,dict(operation='activate',request_key='phase2_acceptance'))
    return auto,auto.get(f.auth,result['schedule_id']),adapter


def event(f,identity='fixture:invoice-1',**kw):
    return dict(event_id=identity,payload={'invoice_id':'synthetic-1'},occurred_at=datetime.fromtimestamp(f.now,timezone.utc).isoformat(),**kw)


def test_authenticated_event_overview_to_adaptive_run_and_replay(subway,monkeypatch):
    f=subway;auto,sub,adapter=event_schedule(f,monkeypatch)
    e=event(f,sequence=1)
    accepted=auto.accept(f.auth,sub['id'],e)
    assert accepted['accepted']
    assert auto.accept(f.auth,sub['id'],e)['duplicate']
    occurrences=dispatch(f,auto)
    assert len(occurrences)==1 and occurrences[0]['state']=='completed',occurrences
    run=load(f,occurrences[0]['run_id'])
    assert run['adaptive']['status']=='completed'
    assert run['automation_reference']['trigger']['event_id']==e['event_id']
    assert f.model_inputs[0]['context']['trigger_event']['payload']==e['payload']
    assert not run.get('case_id')


def test_event_auth_poison_out_of_order_and_identity_conflict(subway,monkeypatch):
    from workflow_api.service import ApiFailure
    f=subway;auto,sub,_=event_schedule(f,monkeypatch)
    with pytest.raises(ApiFailure) as error:auto.accept(f.auth,sub['id'],event(f,'untrusted'))
    assert error.value.code=='AUTOMATION_EVENT_AUTH_FAILED'
    poisoned=event(f,'fixture:bad');poisoned['payload']={'wrong':True}
    assert auto.accept(f.auth,sub['id'],poisoned)['reason']=='invalid_payload'
    assert auto.accept(f.auth,sub['id'],poisoned)['duplicate']
    e=event(f,sequence=2);assert auto.accept(f.auth,sub['id'],e)['accepted']
    assert auto.accept(f.auth,sub['id'],event(f,'fixture:old',sequence=1))['reason']=='out_of_order'
    altered=deepcopy(e);altered['payload']['invoice_id']='different'
    with pytest.raises(ApiFailure) as error:auto.accept(f.auth,sub['id'],altered)
    assert error.value.code=='AUTOMATION_CONFLICT'
    assert len(auto.listing(f.auth,'occurrence')['items'])==1


def test_overview_activation_pause_resume_and_history(subway,monkeypatch):
    f=subway;auto,record,_=schedule(f,monkeypatch)
    activated=f.service.overview_automation.handle(f.auth,dict(operation='activate',request_key='phase2_acceptance'))
    scheduled=auto.get(f.auth,activated['schedule_id'])
    # Retire the separately created API fixture to keep one logical schedule.
    auto.control(f.auth,record['id'],dict(request_key='retire_fixture_schedule',action='cancel'))
    f.now=scheduled['due'];auto.tick(f.service.worker_authenticate)
    auto.control(f.auth,scheduled['id'],dict(request_key='pause_before_dispatch',action='pause'))
    before=len(f.model_inputs)
    for job in f.service.lifecycle.lease('client-subway'):f.service.lifecycle.execute_job(job['job_id'],f.service.runtime_runner)
    occurrence=auto.history(f.auth,scheduled['id'])[0]
    assert occurrence['state']=='waiting' and occurrence['run_id'] is None
    assert len(f.model_inputs)==before
    auto.control(f.auth,scheduled['id'],dict(request_key='resume_after_pause',action='resume'))
    completed=dispatch(f,auto)
    assert completed[0]['state']=='completed'
    read=f.service.overview_automation.handle(f.auth,dict(operation='get',request_key='phase2_acceptance'))
    assert read['automation_history'][0]['run_id']==completed[0]['run_id']
    auto.control(f.auth,scheduled['id'],dict(request_key='disable_after_execution',action='cancel'))
    assert auto.history(f.auth,scheduled['id'])[0]['state']=='completed'


def test_scheduled_replan_uses_same_approved_root(subway,monkeypatch):
    f=subway
    def evaluate(ctx,**_):
        if 'read' in ctx['completed_actions'] and ctx['plan']['revision']==1:
            actions=deepcopy(ctx['plan']['actions'])
            q=deepcopy(actions[0]);q.update(action_id='additional_plan',depends_on=['read'])
            read=deepcopy(actions[1]);read.update(action_id='additional_read',depends_on=['additional_plan'])
            read['bindings']=[dict(kind='output',action_id='additional_plan',path=['query'],target=['query'])]
            report=next(a for a in actions if a['action_id']=='report');report['depends_on'].append('additional_read');report['evidence_references'].append('additional_read')
            return decision(ctx,choice='retrieve_more',proposal=dict(actions=actions+[q,read],completion_criteria=['report'],missing_inputs=[]))
        return decision(ctx)
    auto,record,_=schedule(f,monkeypatch,evaluate);f.now=record['due']
    occurrences=dispatch(f,auto)
    assert occurrences[0]['state']=='completed',occurrences
    run=load(f,occurrences[0]['run_id']);assert run['adaptive']['revision']==2
    assert run['action_instances']['read']['output']['query_id']!=run['action_instances']['additional_read']['output']['query_id']


def test_reporting_window_is_logical_due_and_freshness_blocks_completion(subway,monkeypatch):
    from workflow_api.subway_automation import date_filters
    f=subway
    import json
    from tests.test_subway_full_queries import field as source_field
    field=source_field(f.q,'finance.purchaseorders','poDate')
    with f.service.store.transaction() as db:
        row=db.execute('SELECT document FROM data_source_snapshots WHERE connection_id=? AND revision=1',('dbconn_subway_finance',)).fetchone()
        metadata=json.loads(row[0])
        for dataset in metadata['datasets']:
            for info in dataset['fields']:
                if info['field_id']==field:info['types']=['datetime']
        db.execute('UPDATE data_source_snapshots SET document=? WHERE connection_id=? AND revision=1',(json.dumps(metadata),'dbconn_subway_finance'))
    for row in f.rows['subway_finance']['purchaseorders']:row['poDate']=datetime(2020,1,1)

    f.temporal_override=dict(period='yesterday',field_id=field,days=1)
    contexts=[]
    def evaluate(ctx,**_):
        contexts.append(deepcopy(ctx))
        if any(l['code']=='SOURCE_FRESHNESS_UNVERIFIED' for l in ctx['deterministic_limitations']):return decision(ctx,choice='blocked',satisfied=False)
        return decision(ctx)
    auto,record,_=schedule(f,monkeypatch,evaluate)
    w=auto._workflow(f.auth,record['request']['workflow'])
    expected=date_filters(w['metadata']['overview_intent'],dict(automation_reference=dict(scheduled_due=record['due'])))
    f.query['filters']=deepcopy(expected)
    f.now=record['due']+3600 # late worker still uses the reviewed logical occurrence
    occurrences=dispatch(f,auto);run=load(f,occurrences[0]['run_id'])
    assert run['status']=='blocked'
    assert run['action_instances']['read']['resolved_inputs']['query']['filters']==expected
    assert any(l['code']=='SOURCE_FRESHNESS_UNVERIFIED' for c in contexts for l in c['deterministic_limitations'])
    assert run['action_instances']['read']['output']['sources'][0]['freshness']['last_synced_at'] is None
    assert f.model_inputs[0]['context']['subway_date_filters']==expected


def test_scheduler_restart_concurrency_and_stale_claim(subway,monkeypatch):
    from concurrent.futures import ThreadPoolExecutor
    from workflow_api.lifecycle import LifecycleFailure
    f=subway;auto,record,_=schedule(f,monkeypatch);f.now=record['due']
    restarted=DurableAutomation(f.service,clock=lambda:f.now)
    with ThreadPoolExecutor(max_workers=2) as pool:list(pool.map(lambda a:a._due_schedule(f.auth,record),[auto,restarted]))
    assert len(auto.history(f.auth,record['id']))==1
    job=f.service.lifecycle.lease('client-subway',seconds=1)[0]
    old=f.service.lifecycle.leased_tokens[job['job_id']]
    f.now+=2
    recovered=f.service.lifecycle.lease('client-subway')[0]
    with pytest.raises(LifecycleFailure):f.service.lifecycle.execute_job(job['job_id'],f.service.runtime_runner,claim=old)
    f.service.lifecycle.execute_job(recovered['job_id'],f.service.runtime_runner)
    assert auto.history(f.auth,record['id'])[0]['state']=='completed'


def test_failed_pre_dispatch_retry_is_bounded_idempotent(subway,monkeypatch):
    f=subway;auto,record,_=schedule(f,monkeypatch);f.now=record['due'];auto.tick(f.service.worker_authenticate)
    resolver=f.service.worker_authenticate;f.service.worker_authenticate=lambda *_:None
    for job in f.service.lifecycle.lease('client-subway'):f.service.lifecycle.execute_job(job['job_id'],f.service.runtime_runner)
    occurrence=auto.history(f.auth,record['id'])[0]
    f.service.worker_authenticate=resolver
    request=dict(request_key='authorized_retry_one',action='retry')
    retried=auto.control(f.auth,occurrence['id'],request)
    assert retried['retry_count']==1
    assert auto.control(f.auth,occurrence['id'],request)['retry_count']==1
    assert dispatch(f,auto)[0]['state']=='completed'


def test_event_entity_binding_is_enforced_before_native_query(subway,monkeypatch):
    from tests.test_subway_full_queries import field
    f=subway;auto,sub,adapter=event_schedule(f,monkeypatch)
    fid=field(f.q,'finance.purchaseorders','poNumber')
    original=adapter.workflow_sources
    adapter.workflow_sources=lambda auth:[{**s,'query_bindings':[dict(field_id=fid,path='invoice_id')]} for s in original(auth)]
    # The already-reviewed subscription fails closed when an adapter mapping changes.
    from workflow_api.service import ApiFailure
    with pytest.raises(ApiFailure) as error:auto.accept(f.auth,sub['id'],event(f))
    assert error.value.code=='AUTOMATION_SCOPE_DENIED'
    # Review a new subscription with the configured exact entity mapping.
    body={**sub['request'],'request_key':'mapped_event_subscription'}
    mapped=auto.subscribe(f.auth,body)
    e=event(f);e['payload']['invoice_id']='PO99'
    accepted=auto.accept(f.auth,mapped['id'],e);assert accepted['accepted']
    f.query['filters']=[dict(field_id=fid,op='eq',value='PO99')]
    occurrences=dispatch(f,auto);assert occurrences[0]['state']=='completed',occurrences
    run=load(f,occurrences[0]['run_id'])
    assert run['action_instances']['read']['output']['rows']==[{'count':1}]
    assert run['action_instances']['read']['resolved_inputs']['query']['filters']==f.query['filters']


def test_reviewed_definition_replacement_preserves_history(subway,monkeypatch):
    f=subway;auto,record,_=schedule(f,monkeypatch)
    activated=f.service.overview_automation.handle(f.auth,dict(operation='activate',request_key='phase2_acceptance'))
    replacement=activated['schedule_id']
    old=auto.control(f.auth,record['id'],dict(request_key='reviewed_edit_replacement',action='replace',replacement_id=replacement))
    assert old['state']=='cancelled' and old['replaced_by']==replacement
    assert auto.get(f.auth,replacement)['replaces']==old['id']
    assert auto.get(f.auth,old['id'])['request']==record['request']


from tests.test_google_connections import setup as google_setup


def test_scheduled_native_analysis_requires_exact_external_approval(subway,google_setup,monkeypatch):
    from types import SimpleNamespace
    from tests.test_business_composition import install_external
    from tests.test_connected_action_plans import action,bind
    from tests.test_google_connections import connect
    from tests.test_google_tools import add_scopes
    from workflow_api.google_connections import GoogleConnections
    from workflow_api.google_tools import GoogleTools
    from workflow_api.overview_automation import OverviewAutomation
    import tests.test_subway_autonomy as helpers
    f=subway;_,env=google_setup
    f.auth['permissions']=sorted(set(f.auth['permissions'])|{'tools.assign'})
    f.auth['roles']=sorted(set(f.auth['roles'])|{'approver'})
    manager=GoogleConnections(f.service.store,env);account=connect(manager,actor=f.auth,email='owner@example.com');add_scopes(manager,account['connection_id'],['gmail.compose'])
    f.service.google_tools=GoogleTools(manager,f.service);f.service.bind_google_connector=f.service.google_tools.bind
    alias=SimpleNamespace(registry=f.adapter.service,x=SimpleNamespace(a=f.auth,current=f.auth),connectors=f.service.runtime_runner.connectors)
    tool,connector=install_external(alias,'extension_mail_draft');connector.definition=tool
    policy=deepcopy(f.adapter.service._policy);policy.version+=1;policy.max_risk='high'
    assert f.adapter.service.update_policy(policy,f.auth)['status']==200
    from registry.policy import authorize_tool
    authorize_tool(tool,dict(permissions=tool['permission_scopes'],limits=policy.agent_limits),f.auth,policy,'cred_test_extension_mail_draft',next(iter(tool['allowed_destinations'])))
    f.app.state.workflow_auth.clear();f.app.state.workflow_auth.update(deepcopy(f.auth))
    original_route=helpers.route
    def routed(selected,**kw):
        return original_route(selected,**{**kw,'intent_type':'recurring','side_effects':['email_draft'],'recurrence':dict(kind='daily',hour=9,minute=0,weekdays=[],timezone='Asia/Kolkata',date=None,month_day=None)})
    monkeypatch.setattr(helpers,'route',routed)
    original_handle=OverviewAutomation.handle
    def selected_account(self,auth,body):
        if body.get('objective'):body={**body,'google_connection_id':account['connection_id']}
        return original_handle(self,auth,body)
    monkeypatch.setattr(OverviewAutomation,'handle',selected_account)
    original_proposal=f.make_proposal
    def proposed(goal,ctx):
        assert 'tool.extension_mail_draft' in ctx['capabilities'],(list(ctx['capabilities']),[t['tool_id'] for t in f.service.business_composition.tools(f.auth)])
        p=original_proposal(goal,ctx)
        p['actions'].append(action('draft','tool.extension_mail_draft',[bind('literal','to','owner@example.com'),bind('literal','subject','Synthetic reviewed report'),bind('output','body',action='report',path=['summary'])],['report'],['report']))
        p['completion_criteria']=['draft'];return p
    f.service.planner.provider.plan_actions=proposed
    def evaluate(ctx,**_):
        d=decision(ctx)
        if d['action_id']=='draft':
            ev=[k for k,v in ctx['evidence'].items() if v['valid']]
            d['assessment']['requirements'][0].update(status='verified',evidence_ids=ev)
            d['assessment'].update(completion_eligible=True,gaps=[])
        return d
    _,doc,w=start(f,evaluate,'Every day investigate purchasing and save a report draft to owner@example.com.')
    import json
    original_factory=f.service.runtime_runner.agents.model_factory
    def with_delivery_content(agent):
        model=original_factory(agent);original_call=model.provider_call
        def transport(*args):
            raw,calls,tokens=original_call(*args);content=json.loads(raw)
            if 'summary' in content:content.update(body=content['summary'],subject='Synthetic reviewed report')
            return json.dumps(content),calls,tokens
        model.provider_call=transport;return model
    f.service.runtime_runner.agents.model_factory=with_delivery_content
    assert 'approve_draft' in {n['node_id'] for n in w['nodes']}
    f.now=f.service.lifecycle.clock();f.service.lifecycle.clock=lambda:f.now
    f.service.worker_authenticate=lambda ws,owner:deepcopy(f.auth) if (ws,owner)==('client-subway','subway-client') else None
    auto=DurableAutomation(f.service,clock=lambda:f.now)
    active=f.service.overview_automation.handle(f.auth,dict(operation='activate',request_key='phase2_acceptance'))
    f.now=active['due']
    occurrences=dispatch(f,auto)
    assert occurrences[0]['state']=='completed',str([(o.get('last_error_code'),o.get('result'),load(f,o['run_id']).get('adaptive') if o.get('run_id') else None) for o in occurrences])
    run=load(f,occurrences[0]['run_id'])
    assert len(connector.calls)==1 and connector.calls[0]['to']=='owner@example.com'
    assert run['automation_approvals'] and run['action_instances']['draft']['verified_receipt']
    auto.tick(f.service.worker_authenticate)
    assert len(connector.calls)==1


def test_case_owned_adaptive_revision_cannot_be_scheduled(subway,monkeypatch):
    from workflow_api.service import ApiFailure
    f=subway;auto,record,_=schedule(f,monkeypatch)
    runtime=f.service.runtime_runner.runtime;original=runtime.revision
    def legacy(*args,**kwargs):
        workflow,grants=original(*args,**kwargs);workflow=deepcopy(workflow);workflow['metadata']['adaptive_control']={'case_id':'simpsons-case','stage_id':'stage'}
        return workflow,grants
    monkeypatch.setattr(runtime,'revision',legacy)
    with pytest.raises(ApiFailure):auto._workflow(f.auth,record['request']['workflow'])


def test_automation_history_and_native_consent_are_owner_scoped(subway,monkeypatch):
    from workflow_api.service import ApiFailure
    f=subway;auto,record,consent=schedule(f,monkeypatch)
    other=deepcopy(f.auth);other['subject']['subject_id']='different-owner'
    with pytest.raises(ApiFailure):auto.get(other,record['id'])
    with pytest.raises(ApiFailure):auto.history(other,record['id'])
    invalid={**consent['request'],'request_key':'reject_native_external','operations':{'extension_mail_send':{'type':'object'}}}
    with pytest.raises(ApiFailure) as error:auto.authorize(f.auth,invalid)
    assert error.value.code=='AUTOMATION_SCOPE_DENIED'


def test_freshness_attestation_must_cover_the_requested_calendar_period():
    from workflow_api.source_freshness import describe,covers
    from types import SimpleNamespace
    source=dict(freshness=describe(SimpleNamespace(),{},7))
    filters=[dict(field_id='synthetic-date',op='gte',value='2026-11-01T00:00:00+00:00'),dict(field_id='synthetic-date',op='lt',value='2026-12-01T00:00:00+00:00')]
    assert not covers(source,filters)
    source['freshness'].update(status='current',last_synced_at='2026-12-01T00:00:00+00:00',coverage_start='2026-11-01T00:00:00+00:00',coverage_end='2026-12-01T00:00:00+00:00')
    assert covers(source,filters)
    source['freshness']['coverage_end']='2026-11-15T00:00:00+00:00'
    assert not covers(source,filters)


def test_authenticated_poison_envelope_does_not_block_later_event(subway,monkeypatch):
    f=subway;auto,sub,adapter=event_schedule(f,monkeypatch)
    broken=event(f,'fixture:poison-envelope');del broken['occurred_at']
    adapter.events=[broken,event(f,'fixture:valid-after-poison')]
    auto.tick(f.service.worker_authenticate)
    assert auto.get(f.auth,sub['id'])['cursor']==2
    assert len(auto.history(f.auth,sub['id']))==1
    assert auto.listing(f.auth)['metrics']['rejected_events']==1
    occurrences=dispatch(f,auto)
    assert occurrences[0]['state']=='completed'


def test_adaptive_retrieval_cannot_expand_occurrence_action_allowance(subway,monkeypatch):
    f=subway;f.max_actions_override=3
    def evaluate(ctx,**_):
        if 'read' in ctx['completed_actions'] and ctx['plan']['revision']==1:
            actions=deepcopy(ctx['plan']['actions']);extra=deepcopy(actions[0]);extra.update(action_id='extra_plan',depends_on=['read'])
            report=next(a for a in actions if a['action_id']=='report');report['depends_on'].append('extra_plan')
            return decision(ctx,choice='retrieve_more',proposal=dict(actions=actions+[extra],completion_criteria=['report'],missing_inputs=[]))
        return decision(ctx)
    auto,record,_=schedule(f,monkeypatch,evaluate);f.now=record['due'];occurrences=dispatch(f,auto)
    run=load(f,occurrences[0]['run_id'])
    assert run['status']=='blocked' and run['error_code']=='AUTOMATION_ACTION_LIMIT'
    assert sum(1 for a in run['action_instances'].values() if a['state']=='completed')==3
    assert run['action_instances']['report']['state']=='blocked'
    assert not run['action_instances']['report'].get('verified_receipt')


def test_lifecycle_replay_cannot_bypass_occurrence_retry_safety(subway,monkeypatch):
    from workflow_api.service import ApiFailure
    f=subway;auto,record,_=schedule(f,monkeypatch);f.now=record['due'];occurrence=dispatch(f,auto)[0]
    with pytest.raises(ApiFailure) as error:f.service.lifecycle.replay(occurrence['job_id'],f.auth)
    assert error.value.code=='AUTOMATION_RETRY_INELIGIBLE'


def test_final_authorized_occurrence_finishes_automation_without_future_run(subway,monkeypatch):
    f=subway;f.max_occurrences_override=1;auto,record,_=schedule(f,monkeypatch)
    f.now=record['due'];assert dispatch(f,auto)[0]['state']=='completed'
    saved=auto.get(f.auth,record['id'])
    assert saved['state']=='completed' and saved['due'] is None
    f.now+=86400;auto.tick(f.service.worker_authenticate)
    assert len(auto.history(f.auth,record['id']))==1


def test_natural_language_event_conditions_are_reviewed_and_evaluated(subway,monkeypatch):
    from workflow_api.service import ApiFailure
    f=subway;f.event_conditions=[dict(path='invoice_id',op='eq',value='qualified-invoice')]
    auto,sub,_=event_schedule(f,monkeypatch)
    assert auto.accept(f.auth,sub['id'],event(f))['reason']=='conditions_not_matched'
    qualified=event(f,'fixture:qualified');qualified['payload']['invoice_id']='qualified-invoice'
    assert auto.accept(f.auth,sub['id'],qualified)['accepted']
    assert dispatch(f,auto)[0]['state']=='completed'
    with pytest.raises(ApiFailure):auto.subscribe(f.auth,{**sub['request'],'request_key':'expanded_event_conditions','conditions':[]})


def test_invoice_event_queries_declared_po_and_persists_verified_difference(subway,monkeypatch):
    import json
    from tests.test_subway_intelligence import selection
    from tests.test_subway_full_queries import plan,field
    f=subway;catalog=f.q.catalog(f.auth)
    f.rows['subway_finance']['purchaseorders']=[dict(_id=1,totalAmount=100,currency='INR')]
    f.rows['subway_finance']['invoicedatas']=[dict(_id=5,poId=1,invoiceAmount=120),dict(_id=6,poId=999,invoiceAmount=90)]
    query=plan(f.q,'finance.invoicedatas')
    edge=next(r for r in catalog['relationships'].values() if r['source_dataset_id']==query['base_dataset_id'] and catalog['datasets'][r['target_dataset_id']]['label']=='finance.purchaseorders')
    iid=field(f.q,'finance.invoicedatas','_id');invoice=field(f.q,'finance.invoicedatas','invoiceAmount');amount=field(f.q,'finance.purchaseorders','totalAmount')
    # These are explicitly numeric synthetic identities, not restored production IDs.
    with f.service.store.transaction() as db:
        metadata=json.loads(db.execute('SELECT document FROM data_source_snapshots WHERE connection_id=? AND revision=1',('dbconn_subway_finance',)).fetchone()[0])
        for dataset in metadata['datasets']:
            for info in dataset['fields']:
                if info['field_id']==iid:info['types']=['integer']
        db.execute('UPDATE data_source_snapshots SET document=? WHERE connection_id=? AND revision=1',(json.dumps(metadata),'dbconn_subway_finance'))
    query.update(joins=[edge['relationship_id']],fields=[iid,invoice,amount],metrics=[],filters=[dict(field_id=iid,op='eq',value=5)])
    f.query_plans=dict(query_plan=query)
    f.selected_override=selection(f.q,['finance.invoicedatas','finance.purchaseorders'],[iid,invoice,amount],[edge['relationship_id']])
    f.event_query_bindings=[dict(field_id=iid,path='invoice_id')];f.numeric_event_identity=True
    f.event_objective='Whenever a synthetic invoice arrives compare its numeric amount to its declared purchase order and report the difference without inferring company policy.'
    def evaluate(ctx,**_):
        result=decision(ctx)
        if result['decision']=='complete':
            ref=next(iter(ctx['evidence']))
            result['assessment']['calculations']=[dict(id='invoice-po-difference',operation='difference',operands=[dict(evidence_id=ref,path=['rows',0,invoice]),dict(evidence_id=ref,path=['rows',0,amount])],result='20')]
            result['assessment']['source_limitations']=['Synthetic numeric comparison only. No company tolerance, payment status, causal explanation or overbilling conclusion is established.']
        return result
    f.event_evaluator=evaluate
    auto,sub,_=event_schedule(f,monkeypatch);e=event(f);e['payload']['invoice_id']=5
    accepted=auto.accept(f.auth,sub['id'],e);assert accepted['accepted']
    assert auto.accept(f.auth,sub['id'],e)['duplicate']
    occurrence=dispatch(f,auto)[0];run=load(f,occurrence['run_id'])
    assert occurrence['state']=='completed' and run['adaptive']['assessment']['calculations'][0]['result']=='20'
    assert run['action_instances']['read']['output']['rows']==[{iid:5,invoice:120,amount:100}]
    assert run['action_instances']['read']['output']['relationship_ids']==[edge['relationship_id']]
    assert auto.history(f.auth,sub['id'])[0]['run_id']==run['run_id']
