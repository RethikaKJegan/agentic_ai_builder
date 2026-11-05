"""Phase 2: real cases, Registry, GraphRunner, CrewAI and controlled Google transports."""
from copy import deepcopy
from types import SimpleNamespace
import json
import pytest
from tests.test_connected_action_plans import (connected,composition,investigation,retrieval,knowledge,reference,generation,foundation,auth,release,action,bind,approve,decide,stored)
from tests.test_business_cases import stage,process
from workflow_api.business_cases import BusinessCases
from workflow_api.adaptive_orchestration import AdaptiveOrchestration
from workflow_api.lifecycle_driver import LifecycleDriver
from runtime import RuntimeService
from runtime.graph import GraphRunner
from runtime.service import RuntimeFailure
from workflow_api.service import ApiFailure


def decision(ctx,kind='continue',ids=None,proposal=None,inputs=None,event=None):
    return dict(schema_version='evaluator-decision-v1',decision=kind,plan_revision=ctx['plan_revision'],
        observation_ids=[ctx['observations'][-1]['observation_id']],action_ids=ids or [],completion_criteria=ctx['plan']['completion_criteria'],
        rationale='Decision based on actual scoped observations.',proposal=proposal,input_requests=inputs or [],event_request=event)


class Evaluator:
    def __init__(self):self.contexts=[];self.custom=None
    def evaluate_actions(self,ctx,*,max_output_tokens):
        self.contexts.append(deepcopy(ctx))
        if self.custom:
            result=self.custom(ctx)
            if result is not None:return result
        completed=ctx['completed_actions'];actions=ctx['plan']['actions']
        if all(k in completed for k in ctx['plan']['completion_criteria']):return decision(ctx,'complete',ctx['plan']['completion_criteria'])
        ready=[a['action_id'] for a in actions if a['action_id'] not in completed and all(d in completed for d in a['depends_on'])]
        return decision(ctx,ids=[ready[0]])


def setup(f,client=None,request=None,limits=None):
    cases=BusinessCases(f.general);f.general.business_cases=cases
    req=deepcopy(request or f.request)
    caps=list(dict.fromkeys(a['capability_id'] for a in req.get('action_plan',f.request['action_plan'])['actions']))
    definition=process(stage(required_inputs={},required_capabilities=caps,allowed_tools=list(f.connectors),side_effect_classification='write',
        output_schema={'type':'object'},output_bindings={},timeout_policy=dict(seconds=600,action='block')))
    if client:
        definition['client_id']=client
        definition['domain_id']='retail'
        for s in definition['stages']:s['domain']='retail'
    cases.publish(f.x.a,definition)
    case=cases.create(f.x.a,dict(request_key='adaptive_case_001',process_definition_id=definition['process_definition_id'],process_definition_version=1,
        original_user_goal=req['objective'],business_request=dict(inputs=dict(identifiers=dict(complaint_id='C123')))))
    case=cases.command(f.x.a,case['case_id'],'prepare',dict(request_key='adaptive_prepare_001',expected_revision=case['revision']))
    req.pop('preparation_id',None);req.pop('request_key',None);req['client_id']=case['client_id']
    adaptive=AdaptiveOrchestration(cases)
    case=adaptive.enable(f.x.a,case['case_id'],dict(request_key='adaptive_enable_001',expected_revision=case['revision'],stage_instance_id='first',plan_request=req,limits=limits or {}))
    evaluator=Evaluator();f.general.planner.provider=evaluator
    f.cases=cases;f.adaptive=adaptive;f.evaluator=evaluator;f.counter=0
    return case


def drive(f,commands=32):
    f.counter+=1
    return LifecycleDriver(f.cases).drive(f.x.a,f.case_id,dict(request_key='adaptive_drive_'+str(f.counter).zfill(8),max_commands=commands,max_seconds=120))


def case(f):return f.cases.get(f.x.a,f.case_id)


def approve_work(f):
    c=case(f);a=c['adaptive'];w=f.c.workflow(f.x.a,a['composition_id'])
    if not a.get('run_id'):
        r=f.adapter.approve_pending(w,f.x.a);assert r['ready'],r
        approve(f,w)
    else:
        run=f.runtime.public(stored(f,a['run_id']))
        if run['status']=='paused_for_approval':decide(f,w,run)


def finish(f):
    for _ in range(30):
        result=drive(f)
        if result['stop_reason']=='approval_wait':approve_work(f);continue
        if result['stop_reason']=='terminal':return result
        assert result['stop_reason']=='budget_exhausted',(result.get('error_code'),result['adaptive'].get('failure'))
    raise AssertionError('Adaptive loop did not finish')


@pytest.mark.parametrize('client',[None])
def test_five_states_same_evaluator_persistent_completion_and_restart(connected,client,tmp_path):
    f=connected;c=setup(f,client);f.case_id=c['case_id']
    result=drive(f);assert result['stop_reason']=='approval_wait',(result.get('error_code'),result['adaptive'].get('failure'),result['adaptive']['reasoning_usage'])
    approve_work(f)
    result=drive(f);assert result['stop_reason']=='approval_wait',(result.get('error_code'),result['adaptive'].get('failure'),result['adaptive']['reasoning_usage'])
    approve_work(f)
    result=drive(f);assert result['stop_reason']=='approval_wait',(result.get('error_code'),result['adaptive'].get('failure'),result['adaptive']['reasoning_usage'])
    assert f.http.write_count==1 and not f.http.sent
    # Reconstruct services after the completed Sheet action and pending email approval.
    f.cases=BusinessCases(f.general);f.general.business_cases=f.cases;f.adaptive=AdaptiveOrchestration(f.cases)
    f.runtime=RuntimeService(f.general);f.runner=GraphRunner(f.runtime,agents=f.runner.agents,connectors=f.connectors);f.general.runtime_runner=f.runner
    approve_work(f);result=finish(f)
    assert len(f.http.sent)==1 and f.http.write_count==1
    saved=case(f);assert saved['adaptive']['status']=='completed'
    states={e['target'] for e in saved['execution_history'] if e['event_type']=='adaptive.state'}
    assert {'PLAN','GATHER_AND_ASSESS','EXECUTE','EVALUATE'}<=states
    assert f.evaluator.contexts[0]['scope']['client_id']==saved['client_id']
    assert f.evaluator.contexts[-1]['completed_actions']['sheet']['verified_receipt']
    assert drive(f)['stop_reason']=='terminal' and len(f.http.sent)==1
    (tmp_path/('adaptive-'+str(client or 'simpson')+'-trace.json')).write_text(json.dumps(dict(case=saved,plans=[f.c.get(f.x.a,h['composition_id']) for h in saved['adaptive']['revision_history']],run=stored(f,saved['adaptive']['run_id']),contexts=f.evaluator.contexts,events=f.runtime.events(saved['adaptive']['run_id'],f.x.a)['items'],qualification='Controlled model, source and Google transports; actual Registry/GraphRunner/CrewAI/adapters; no live external write or verified physical outcome.'),indent=2)+'\n')


def test_missing_evidence_adds_read_action_and_reevaluates(connected,tmp_path):
    f=connected;req=deepcopy(f.request);req['user_values']['inspection_task']='inspection';c=setup(f,request=req);f.case_id=c['case_id'];changed=[]
    def custom(ctx):
        if 'read' in ctx['completed_actions'] and not changed:
            p=dict(actions=deepcopy(ctx['plan']['actions']),completion_criteria=ctx['plan']['completion_criteria'],missing_inputs=[])
            extra=action('more_evidence','business.read.inspection',[bind('context','preparation_id','preparation_id'),bind('literal','task','inspection_task')],['read'])
            # Expand evidence within the same ontology/mapping/source pins; inputs remain explicit.
            p['actions'].insert(1,extra)
            p['actions'][2]['depends_on'].append('more_evidence')
            changed.append(True);return decision(ctx,'gather_context',['read'],p)
    f.evaluator.custom=custom
    result=finish(f)
    assert case(f)['adaptive']['plan_revision']==2
    assert stored(f,case(f)['adaptive']['run_id'])['action_instances']['more_evidence']['verified_receipt']
    assert len(f.http.sent)==1 and f.http.write_count==1
    saved=case(f);rid=saved['adaptive']['run_id']
    (tmp_path/'adaptive-gather-trace.json').write_text(json.dumps(dict(case=saved,plans=[f.c.get(f.x.a,h['composition_id']) for h in saved['adaptive']['revision_history']],run=stored(f,rid),contexts=f.evaluator.contexts,events=f.runtime.events(rid,f.x.a)['items']),indent=2)+'\n')


def test_missing_recipient_is_persisted_wait_and_typed_supply(connected):
    f=connected;req=deepcopy(f.request);req['user_values'].pop('recipient');c=setup(f,request=req);f.case_id=c['case_id']
    result=drive(f);assert result['stop_reason']=='external_or_input_wait',(result.get('error_code'),result['adaptive'].get('failure'))
    cc=case(f);wait=cc['adaptive']['pending_wait'];assert 'recipient' in wait['schemas'] and cc['case_status']=='WAITING_FOR_INPUT'
    assert not f.http.sent and f.http.write_count==0
    supplied=f.adaptive.supply(f.x.a,f.case_id,dict(request_key='supply_recipient_001',expected_revision=cc['revision'],wait_id=wait['wait_id'],inputs={'recipient':'engineer@example.com'}))
    assert supplied['adaptive']['wait_history'][0]['status']=='SATISFIED'
    assert finish(f)['stop_reason']=='terminal' and len(f.http.sent)==1


@pytest.mark.parametrize('prior_approval',[False,True])
def test_revision_preserves_completed_sheet_and_invalidates_old_send_approval(connected,tmp_path,prior_approval):
    f=connected;c=setup(f);f.case_id=c['case_id']
    for _ in range(3):
        result=drive(f);assert result['stop_reason']=='approval_wait',(result.get('error_code'),result['adaptive'].get('failure'),result['adaptive']['reasoning_usage'])
        if f.http.write_count:break
        approve_work(f)
    cc=case(f);oldrid=cc['adaptive']['run_id'];oldrun=stored(f,oldrid);oldsheet=deepcopy(oldrun['action_instances']['sheet']);oldapproval=oldrun['approvals'][-1]
    assert not f.http.sent and oldapproval['status']=='pending'
    if prior_approval:
        decide(f,f.c.workflow(f.x.a,cc['adaptive']['composition_id']),oldrun)
        oldrun=stored(f,oldrid);oldapproval=oldrun['approvals'][-1]
        assert oldapproval['status']=='approved'
    doc=f.c.get(f.x.a,cc['adaptive']['composition_id']);p=dict(actions=deepcopy(doc['action_plan']['actions']),completion_criteria=['send'],missing_inputs=[])
    new=action('email_updated','content.prepare',[bind('generated','data',action='analysis'),bind('receipt','artifact_url',action='sheet',path=['spreadsheet_url'])],['analysis','sheet'],['analysis','sheet'])
    new['instructions']='Include new evidence and the verified link.'
    p['actions'].insert(-1,new);p['actions'][-1]['depends_on']=['email_updated']
    for b in p['actions'][-1]['bindings']:
        if b.get('action_id')=='email':b['action_id']='email_updated'
    obs=f.adaptive.context(f.x.a,cc,doc,oldrun)['observations'][-1]['observation_id']
    body=dict(request_key='revision_email_001',expected_revision=cc['revision'],expected_plan_revision=1,proposal=p,rationale='New evidence requires unfinished send content to change.',observation_ids=[obs])
    revised=f.adaptive.revise(f.x.a,f.case_id,body)
    assert revised['adaptive']['plan_revision']==2
    assert stored(f,oldrid)['approvals'][-1]['status']=='superseded'
    with pytest.raises(RuntimeFailure):f.runner.decide(dict(request_id='superseded_approval',idempotency_key='superseded_'+oldapproval['approval_id'],payload=dict(approval_id=oldapproval['approval_id'],workflow_id=oldrun['workflow_id'],workflow_version=1,decision='approved')),f.x.a)
    assert finish(f)['stop_reason']=='terminal'
    run=stored(f,case(f)['adaptive']['run_id'])
    assert run['action_instances']['sheet']==oldsheet
    assert f.http.write_count==1 and len(f.http.sent)==1
    assert run['action_instances']['send']['approval_references']!=[oldapproval['approval_id']]
    assert f.c.get(f.x.a,revised['adaptive']['composition_id'])['action_plan']['previous_revision']['revision']==1
    (tmp_path/'adaptive-revision-trace.json').write_text(json.dumps(dict(case=case(f),plans=[f.c.get(f.x.a,h['composition_id']) for h in case(f)['adaptive']['revision_history']],old_run=stored(f,oldrid),run=run,contexts=f.evaluator.contexts,events=f.runtime.events(run['run_id'],f.x.a)['items']),indent=2)+'\n')


def test_native_retail_package_uses_same_evaluator_and_registered_read(connected,tmp_path):
    from pathlib import Path
    from workflow_api.client_packages import PackageEvidenceConnector,package_tool_definition
    f=connected;cases=BusinessCases(f.general);f.general.business_cases=cases
    package=json.loads((Path(__file__).resolve().parents[1]/'ontology/client-packages/retail-complaint-fixture-v1.json').read_text())
    package['package_id']='retail_adaptive_fixture'
    definition=process(stage(required_inputs={},required_capabilities=['retail.complaint.read'],allowed_tools=['client_package_read'],side_effect_classification='read',output_schema={'type':'object','required':['evidence'],'properties':{'evidence':{'type':'object'}}},output_bindings={'evidence':{'source':'receipt','path':'read'}}))
    definition.update(process_definition_id='retail_adaptive_fixture',client_id=package['client_id'],domain_id=package['domain'])
    definition['stages'][0]['domain']=package['domain'];package['process_definitions']=[definition]
    f.registry._policy.remaining_quota['client_package_read']=100
    assert f.registry.register_tool(package_tool_definition(),f.x.a)['status']==200
    f.c.packages.publish(f.x.a,package);reads=[]
    def source(auth,binding):
        reads.append(binding['source_id'])
        return [dict(id='retail_order_1',complaint_id='RETAIL-C1',order_id='ORDER-1',purchase_verified=True,product_observation='Reported incorrect item; defect unconfirmed.')]
    f.c.packages.register_source(f.x.a,'retail_orders_fixture',source)
    f.connectors['client_package_read']=PackageEvidenceConnector(f.c.packages)
    c=cases.create(f.x.a,dict(request_key='retail_adaptive_create',process_definition_id=definition['process_definition_id'],process_definition_version=1,client_package_id=package['package_id'],client_package_revision=1,original_user_goal='Review retail complaint RETAIL-C1 using mapped order evidence.'))
    c=cases.command(f.x.a,c['case_id'],'prepare',dict(request_key='retail_adaptive_prepare',expected_revision=c['revision']))
    req=dict(objective=c['original_user_goal'],client_id=package['client_id'],user_values={'capability':'retail.complaint.read'},action_plan=dict(actions=[action('read','retail.complaint.read',[bind('context','package_id','package_id'),bind('context','revision','package_revision'),bind('literal','capability_id','capability')])],completion_criteria=['read'],missing_inputs=[]))
    adaptive=AdaptiveOrchestration(cases);c=adaptive.enable(f.x.a,c['case_id'],dict(request_key='retail_adaptive_enable',expected_revision=c['revision'],stage_instance_id='first',plan_request=req))
    f.cases=cases;f.adaptive=adaptive;f.case_id=c['case_id'];f.evaluator=Evaluator();f.general.planner.provider=f.evaluator;f.counter=0
    result=finish(f);saved=case(f);run=stored(f,saved['adaptive']['run_id'])
    assert result['stop_reason']=='terminal' and reads and run['status']=='completed'
    assert saved['stages']['first']['outputs']['evidence']['provenance_type']=='ACTUAL'
    assert f.evaluator.contexts[-1]['scope']['client_id']==package['client_id']
    assert 'retail.complaint.read' in f.evaluator.contexts[-1]['allowed_capabilities']
    assert not f.http.sent and f.http.write_count==0
    (tmp_path/'adaptive-retail-trace.json').write_text(json.dumps(dict(case=saved,run=run,contexts=f.evaluator.contexts,events=f.runtime.events(run['run_id'],f.x.a)['items']),indent=2)+'\n')


def test_stale_and_completed_revisions_rejected_and_driver_idempotent(connected):
    f=connected;c=setup(f);f.case_id=c['case_id']
    result=drive(f);approve_work(f);result=drive(f)
    cc=case(f);doc=f.c.get(f.x.a,cc['adaptive']['composition_id']);run=stored(f,cc['adaptive']['run_id'])
    proposal=dict(actions=deepcopy(doc['action_plan']['actions']),completion_criteria=['send'],missing_inputs=[])
    obs=f.adaptive.context(f.x.a,cc,doc,run)['observations'][-1]['observation_id']
    body=dict(request_key='stale_revision_001',expected_revision=cc['revision'],expected_plan_revision=0,proposal=proposal,rationale='Reviewed update.',observation_ids=[obs])
    with pytest.raises(ApiFailure) as exc:f.adaptive.revise(f.x.a,f.case_id,body)
    assert exc.value.code=='ADAPTIVE_STALE_REVISION'
    body.update(request_key='completed_edit_001',expected_plan_revision=1)
    body['proposal']['actions'][0]['instructions']='Change a completed read.'
    with pytest.raises(ApiFailure) as exc:f.adaptive.revise(f.x.a,f.case_id,body)
    assert exc.value.code=='ADAPTIVE_COMPLETED_ACTION'
    body=dict(request_key='idempotent_driver_001',max_commands=1,max_seconds=120)
    one=LifecycleDriver(f.cases).drive(f.x.a,f.case_id,body)
    assert LifecycleDriver(f.cases).drive(f.x.a,f.case_id,body)==one
    assert not f.http.sent and f.http.write_count==0


@pytest.mark.parametrize('bad',['observation','revision','complete','authority','schema_ref'])
def test_evaluator_cannot_invent_observations_completion_or_authority(connected,bad):
    f=connected;c=setup(f);f.case_id=c['case_id']
    def custom(ctx):
        d=decision(ctx,ids=['read'])
        if bad=='observation':d['observation_ids']=['invented_receipt']
        elif bad=='revision':d['plan_revision']=7
        elif bad=='complete':d['decision']='complete'
        elif bad=='authority':d['approved']=True
        else:d.update(decision='request_input',input_requests=[dict(key='recipient',schema={'$ref':'https://example.com/schema'},reason='Input needed.')])
        return d
    f.evaluator.custom=custom
    result=drive(f)
    assert result['stop_reason']=='command_rejected'
    assert case(f)['adaptive']['status']=='blocked'
    assert not f.http.sent and f.http.write_count==0


def test_wait_event_is_scoped_typed_and_restart_safe(connected):
    f=connected;f.x.a['permissions'].append('events.ingest');c=setup(f);f.case_id=c['case_id'];asked=[]
    def custom(ctx):
        if not asked:
            asked.append(True)
            return decision(ctx,'wait_for_event',['read'],event=dict(event_type='additional_findings',expected_source='operator.review',schema={'type':'object','required':['finding'],'additionalProperties':False,'properties':{'finding':{'type':'string'}}},deadline_seconds=120))
    f.evaluator.custom=custom
    result=drive(f);assert result['stop_reason']=='external_or_input_wait'
    cc=case(f);wait=cc['adaptive']['pending_wait'];f.adaptive=AdaptiveOrchestration(BusinessCases(f.general))
    body=dict(request_key='event_supply_001',expected_revision=cc['revision'],wait_id=wait['wait_id'],event=dict(source='wrong',event_type='additional_findings',payload={'finding':'Reported new observation.'}))
    with pytest.raises(ApiFailure):f.adaptive.supply(f.x.a,f.case_id,body)
    body['event']['source']='operator.review'
    supplied=f.adaptive.supply(f.x.a,f.case_id,body)
    assert supplied['adaptive']['input_observations'][0]['kind']=='authenticated_event_report'
    assert finish(f)['stop_reason']=='terminal'


def test_reasoning_budget_workspace_isolation_and_cancel(connected):
    f=connected;c=setup(f,limits={'max_reasoning_turns':1});f.case_id=c['case_id']
    result=drive(f);assert result['stop_reason']=='approval_wait';approve_work(f)
    result=drive(f);assert result['error_code']=='ADAPTIVE_BUDGET_EXHAUSTED'
    other=deepcopy(f.x.a);other['subject']['workspace_id']='different'
    with pytest.raises(ApiFailure):f.cases.get(other,f.case_id)
    cc=case(f);cancelled=f.cases.command(f.x.a,f.case_id,'cancel',dict(request_key='adaptive_cancel_001',expected_revision=cc['revision']))
    assert cancelled['case_status']=='CANCELLED'
    with pytest.raises(ApiFailure):drive(f)
    assert f.http.write_count==0 and not f.http.sent


def test_initial_model_plan_reuses_phase1_provider(connected):
    f=connected;req=deepcopy(f.request);proposal=req.pop('action_plan');c=setup(f,request=req);f.case_id=c['case_id']
    planned=[]
    f.evaluator.plan_actions=lambda goal,ctx:(planned.append((goal,ctx)) or deepcopy(proposal))
    result=finish(f)
    assert planned and result['stop_reason']=='terminal'
    assert case(f)['adaptive']['reasoning_turns']==len(f.evaluator.contexts)+1


def test_openai_evaluator_adapter_uses_structured_controlled_response():
    from planner.provider import OpenAIStructuredOutputProvider
    from planner.errors import PlannerFailure
    calls=[];ctx={'plan_revision':1,'observations':[{'observation_id':'goal:1'}],'plan':{'completion_criteria':['read']}}
    response=SimpleNamespace(status='completed',output_text=json.dumps(decision(ctx,ids=['read'])))
    client=SimpleNamespace(responses=SimpleNamespace(create=lambda **kw:(calls.append(kw) or response)))
    provider=OpenAIStructuredOutputProvider(client=client,model='controlled-model')
    assert provider.evaluate_actions(ctx)['decision']=='continue'
    assert calls[0]['store'] is False and calls[0]['max_output_tokens']==2000
    response.output_text=json.dumps(decision(ctx,ids=[]))
    with pytest.raises(PlannerFailure):provider.evaluate_actions(ctx)
    response.output_text='{"decision":"invented"}'
    with pytest.raises(PlannerFailure):provider.evaluate_actions(ctx)


def test_runtime_worker_cannot_bypass_evaluation(connected):
    f=connected;c=setup(f);f.case_id=c['case_id']
    assert drive(f)['stop_reason']=='approval_wait';approve_work(f)
    assert drive(f,commands=1)['stop_reason']=='budget_exhausted'
    cc=case(f);assert cc['adaptive']['phase']=='EVALUATE'
    rid=cc['adaptive']['run_id'];before=stored(f,rid);calls=len(f.calls)
    f.runner.advance(rid,f.x.a);after=stored(f,rid)
    assert after['action_instances']==before['action_instances'] and len(f.calls)==calls
    assert after['lease_until']==0 and not f.http.sent and f.http.write_count==0


@pytest.mark.parametrize('limit',[{'max_tokens':1},{'max_plan_revisions':1}])
def test_token_and_revision_budgets_are_enforced_before_provider_or_install(connected,limit):
    f=connected;c=setup(f,limits=limit);f.case_id=c['case_id']
    if 'max_plan_revisions' in limit:
        def custom(ctx):
            proposal=dict(actions=deepcopy(ctx['plan']['actions']),completion_criteria=ctx['plan']['completion_criteria'],missing_inputs=[])
            return decision(ctx,'revise_plan',['read'],proposal)
        f.evaluator.custom=custom
    result=drive(f)
    assert result['error_code'] in ('ADAPTIVE_BUDGET_EXHAUSTED','ADAPTIVE_REVISION_LIMIT')
    assert case(f)['adaptive']['plan_revision']==1
    if 'max_tokens' in limit:assert not f.evaluator.contexts
    assert not f.http.sent and f.http.write_count==0


def test_uncertain_write_blocks_replanning_and_preserves_sheet(connected):
    f=connected;c=setup(f);f.case_id=c['case_id']
    for _ in range(3):
        assert drive(f)['stop_reason']=='approval_wait'
        if f.http.write_count:break
        approve_work(f)
    cc=case(f);rid=cc['adaptive']['run_id']
    with f.general.store.transaction() as db:
        rr=f.runtime.load(db,rid,f.x.a);rr['action_instances']['send'].update(state='blocked',external_effect_status='requires_reconciliation');f.runtime.save(db,rr)
    doc=f.c.get(f.x.a,cc['adaptive']['composition_id']);rr=stored(f,rid)
    body=dict(request_key='uncertain_revision_001',expected_revision=cc['revision'],expected_plan_revision=1,proposal=dict(actions=deepcopy(doc['action_plan']['actions']),completion_criteria=['send'],missing_inputs=[]),rationale='Review changed evidence.',observation_ids=[f.adaptive.context(f.x.a,cc,doc,rr)['observations'][-1]['observation_id']])
    with pytest.raises(ApiFailure) as exc:f.adaptive.revise(f.x.a,f.case_id,body)
    assert exc.value.code=='ADAPTIVE_RECONCILIATION_REQUIRED'
    assert f.http.write_count==1 and not f.http.sent


def test_interrupted_evaluation_keeps_intent_and_never_replays_automatically(connected):
    f=connected;c=setup(f);f.case_id=c['case_id']
    class Interrupted(BaseException):pass
    def interrupt(ctx):raise Interrupted()
    f.evaluator.custom=interrupt
    with pytest.raises(Interrupted):drive(f)
    saved=case(f);assert saved['adaptive']['claim']['provider_intent']
    restarted=BusinessCases(f.general,clock=lambda:saved['adaptive']['claim']['until']+1)
    with pytest.raises(ApiFailure) as exc:LifecycleDriver(restarted).drive(f.x.a,f.case_id,dict(request_key='after_interrupted_eval',max_commands=4,max_seconds=120))
    assert exc.value.code=='ADAPTIVE_UNKNOWN_EVALUATION'
    assert len(f.evaluator.contexts)==1 and f.http.write_count==0 and not f.http.sent


def test_adaptive_optional_condition_preserves_phase1_skip_semantics(connected):
    f=connected;req=deepcopy(f.request);req['user_values']['optional_enabled']=False
    optional=action('optional_analysis','content.prepare',[bind('output','data',action='read')],['read'],['read'],optional=True,when={'binding':bind('literal','condition','optional_enabled'),'equals':True})
    req['action_plan']['actions'].append(optional)
    c=setup(f,request=req);f.case_id=c['case_id']
    def custom(ctx):
        if 'read' in ctx['completed_actions'] and 'optional_analysis' not in ctx['skipped_actions']:
            return decision(ctx,ids=['optional_analysis'])
    f.evaluator.custom=custom
    assert finish(f)['stop_reason']=='terminal'
    rr=stored(f,case(f)['adaptive']['run_id'])
    assert rr['action_instances']['optional_analysis']['state']=='skipped' and rr['status']=='completed'


def test_case_wide_tool_budget_blocks_next_write(connected):
    f=connected;c=setup(f,limits={'max_tool_calls':1});f.case_id=c['case_id']
    assert drive(f)['stop_reason']=='approval_wait';approve_work(f)
    assert drive(f)['stop_reason']=='approval_wait';approve_work(f)
    result=drive(f);assert result['stop_reason']=='command_rejected'
    rr=stored(f,case(f)['adaptive']['run_id'])
    assert rr['error_code']=='ADAPTIVE_BUDGET_EXHAUSTED'
    assert rr['usage']['workflow']['tool_calls']==1 and f.http.write_count==0 and not f.http.sent


def test_evaluator_revises_unfinished_analysis_from_actual_read(connected,tmp_path):
    f=connected;c=setup(f);f.case_id=c['case_id'];revised=[]
    def custom(ctx):
        if 'read' in ctx['completed_actions'] and not revised:
            revised.append(True)
            p=dict(actions=deepcopy(ctx['plan']['actions']),completion_criteria=ctx['plan']['completion_criteria'],missing_inputs=[])
            p['actions'][1]['instructions']='Review the actual complaint observations and explicitly identify unverified diagnosis.'
            return decision(ctx,'revise_plan',['read'],p)
    f.evaluator.custom=custom
    assert finish(f)['stop_reason']=='terminal'
    saved=case(f);rid=saved['adaptive']['run_id'];run=stored(f,rid)
    assert saved['adaptive']['plan_revision']==2
    assert any(d['decision']['decision']=='revise_plan' for d in saved['adaptive']['decisions'])
    assert run['preserved_from_run'] and f.http.write_count==1 and len(f.http.sent)==1
    plans=[f.c.get(f.x.a,h['composition_id']) for h in saved['adaptive']['revision_history']]
    assert plans[0]['action_plan']['actions'][1]!=plans[1]['action_plan']['actions'][1]
    (tmp_path/'adaptive-evaluator-revision-trace.json').write_text(json.dumps(dict(case=saved,plans=plans,run=run,contexts=f.evaluator.contexts,events=f.runtime.events(rid,f.x.a)['items']),indent=2)+'\n')
