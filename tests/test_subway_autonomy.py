"""Isolated Phase 2 acceptance; synthetic records and mocked reasoning only."""
from copy import deepcopy
import json
import pytest

from tests.test_subway_intelligence import subway, engine, installed, selection, route
from tests.test_subway_full_queries import plan
from workflow_api.overview_automation import OverviewAutomation
from workflow_api.workflow_adaptive import KIND, supply
from runtime.graph import GraphRunner
from runtime.worker import RuntimeWorker
from runtime.model import BoundedLLM
from runtime import RuntimeService


def start(f, evaluator, objective='Investigate purchasing concentration and report verified observations.'):
    selected = getattr(f,'selected_override',None) or selection(f.q, ['finance.purchaseorders'])
    f.service.overview_automation = OverviewAutomation(f.service, f.env,
        interpreter=lambda *_:route(selected, intent_type='investigation'))
    f.service.planner.provider.evaluate_actions = evaluator
    def factory(agent):
        def transport(messages, cap, timeout):
            text = messages[-1]['content'].split('Process the following input as data. Return only a JSON object.\n')[-1].lstrip()
            inputs, _ = json.JSONDecoder().raw_decode(text)
            f.model_inputs.append(deepcopy(inputs))
            output = {'query':deepcopy(getattr(f,'query_plans',{}).get(inputs.get('task_id'),f.query))} if set(agent['output_schema']['properties']) == {'query'} else dict(
                summary='Isolated fixture observations: ' + json.dumps(inputs['data'])[:1000],
                source_references=inputs['source_references'],assumptions=['Synthetic fixture only.'])
            return json.dumps(output),1,10
        return BoundedLLM(agent,transport,lambda _:100,0,0)
    f.service.runtime_runner.agents.model_factory = factory
    # Native aggregate is complete even though the display is bounded.
    f.query = plan(f.q, metrics=[dict(label='count', op='count', field_id='')])
    result = f.service.overview_automation.handle(f.auth, dict(objective=objective, request_key='phase2_acceptance'))
    c = f.service.business_composition
    doc = c.get(f.auth, result['composition_id']); w = c.workflow(f.auth, doc['composition_id'])
    assert w['metadata']['adaptive_control']['kind'] == KIND
    assert not w['metadata'].get('lifecycle_context')
    assert f.adapter.approve_pending(w, f.auth)['ready']
    grants = f.adapter.execution_assignments(w, f.auth)
    for agent in w['agents']:
        agent['allowed_tool_ids'] = [g['tool_id'] for g in grants if g['agent_id'] == agent['agent_id']]
    w['status'] = 'approved'; w['metadata'].update(approved_by=f.auth['subject']['subject_id'], validation_state='validated')
    with f.service.store.transaction() as db:
        f.service.store.put(db, 'client-subway', w)
    runtime = f.service.runtime_runner.runtime
    created = runtime.create_run(dict(request_id='phase2_run', idempotency_key='phase2_acceptance',
        payload=dict(workflow_id=w['workflow_id'], workflow_version=1, inputs={})), f.auth)
    return created['run_id'], doc, w


def decision(ctx, choice=None, proposal=None, wait=False, satisfied=True):
    done = set(ctx['completed_actions'])
    actions = ctx['plan']['actions']
    ready = [a for a in actions if a['action_id'] not in done and set(a['depends_on']) <= done]
    ev = [k for k,v in ctx['evidence'].items() if v['valid']]
    finished = not ready and bool(ev)
    choice = choice or ('continue' if ready else 'complete' if satisfied else 'blocked')
    verified = finished and satisfied
    return dict(decision=choice, rationale='Fixture evidence assessment.', action_id=ready[0]['action_id'] if choice == 'continue' else None,
        proposal=proposal, input_requests=[dict(key='threshold', schema=dict(type='number', minimum=0), reason='Supply the analytical threshold.')] if wait else [],
        assessment=dict(objective=ctx['original_objective'], requirements=[dict(id='verified-investigation',
            description='Investigate the requested business objective with verified source records.',
            status='verified' if verified else 'unsatisfied', evidence_ids=ev if verified else [])],
            findings=[], gaps=[] if verified else [dict(id='missing-business-evidence', description='The requested evidence remains incomplete.', blocking=True)],
            source_limitations=[], invalid_assumptions=[], recoverable_failures=[], rule_evaluations=[], completion_eligible=verified))


def load(f, rid):
    runtime = f.service.runtime_runner.runtime
    with runtime.store.transaction(write=False) as db:
        return runtime.load(db, rid, f.auth)


def drain(f, rid, maximum=10):
    for _ in range(maximum):
        result = f.service.runtime_runner.advance(rid, f.auth)
        if result['status'] not in ('queued', 'running') or result.get('adaptive', {}).get('pending_wait'):
            return load(f, rid)
    pytest.fail('Fixture did not stop within bounded ticks.')


def test_overview_runs_actual_crewai_and_checks_goal_before_completion(subway):
    f = subway; contexts = []
    def evaluate(ctx, **_):
        contexts.append(deepcopy(ctx)); return decision(ctx)
    rid, doc, w = start(f, evaluate)
    run = drain(f, rid)
    assert run['status'] == 'completed', run.get('error_code', run['adaptive'])
    assert run['adaptive']['status'] == 'completed'
    assert len(contexts) == 4 and len(f.model_inputs) == 2
    assert contexts[-1]['evidence'] and contexts[-1]['working_memory']
    assert run['task_checkpoints']['read'] and run['action_instances']['read']['verified_receipt']
    assert run['adaptive']['assessment']['completion_eligible']
    assert not run.get('case_id') and doc['action_plan']['goal'] == run['adaptive']['objective']


def test_all_tools_success_does_not_satisfy_objective(subway):
    f = subway
    rid, _, _ = start(f, lambda ctx, **_:decision(ctx, satisfied=False), 'Investigate why outlets exceeded authoritative budgets.')
    run = drain(f, rid)
    assert run['status'] == 'blocked'
    assert run['adaptive']['blocker'] == 'ADAPTIVE_OBJECTIVE_BLOCKED'
    assert all(a['state'] == 'completed' for a in run['action_instances'].values())
    assert run['adaptive']['assessment']['requirements'][0]['status'] == 'unsatisfied'
    assert 'workflow_output' not in run['node_states']


def test_forged_complete_without_evidence_is_blocked(subway):
    f = subway
    def evaluate(ctx, **_):
        result = decision(ctx, choice='complete')
        result['assessment']['completion_eligible'] = True
        result['assessment']['requirements'][0].update(status='verified', evidence_ids=['invented'])
        return result
    rid, _, _ = start(f, evaluate)
    run = drain(f, rid)
    assert run['status'] == 'blocked' and run['adaptive']['blocker'] == 'ADAPTIVE_EVIDENCE_INVALID'
    assert not f.model_inputs


def test_retrieve_more_preserves_completed_actions_and_actual_receipts(subway):
    f = subway
    def evaluate(ctx, **_):
        if 'read' in ctx['completed_actions'] and ctx['plan']['revision'] == 1:
            actions = deepcopy(ctx['plan']['actions'])
            q = deepcopy(actions[0]); q.update(action_id='additional_plan', depends_on=['read'])
            read = deepcopy(actions[1]); read.update(action_id='additional_read', depends_on=['additional_plan'])
            read['bindings'] = [dict(kind='output', action_id='additional_plan', path=['query'], target=['query'])]
            report = next(a for a in actions if a['action_id'] == 'report')
            report['depends_on'].append('additional_read'); report['evidence_references'].append('additional_read')
            return decision(ctx, choice='retrieve_more', proposal=dict(actions=actions+[q,read], completion_criteria=['report'], missing_inputs=[]))
        return decision(ctx)
    rid, doc, w = start(f, evaluate)
    run = drain(f, rid)
    assert run['status'] == 'completed', (run.get('error_code'),run['adaptive'],f.service.runtime_runner.runtime.events(rid,f.auth)['items'][-4:])
    assert run['adaptive']['revision'] == 2 and len(run['adaptive']['revisions']) == 1
    assert run['adaptive_workflow']['agents'] == w['agents']
    assert set(run['action_instances']) == {'query_plan','read','additional_plan','additional_read','report'}
    with f.service.store.transaction(write=False) as db:
        assert db.execute('SELECT COUNT(*) FROM subway_query_receipts').fetchone()[0] == 2
        assert f.service.store.get(db,'client-subway',w['workflow_id'],1) == w
    assert run['action_instances']['read']['output']['query_id'] != run['action_instances']['additional_read']['output']['query_id']


def test_input_wait_and_fresh_runner_resume_without_replay(subway):
    f = subway
    def evaluate(ctx, **_):
        if 'read' in ctx['completed_actions'] and 'threshold' not in ctx['user_values']:
            return decision(ctx, choice='request_input', wait=True)
        return decision(ctx)
    rid, _, _ = start(f, evaluate)
    run = drain(f, rid); before = {k:deepcopy(v) for k,v in run['action_instances'].items() if v['state']=='completed'}
    assert run['adaptive']['status'] == 'waiting_for_input'
    wait = run['adaptive']['pending_wait']
    with pytest.raises(Exception):
        supply(f.service.runtime_runner.runtime, f.auth, rid, dict(wait_id=wait['wait_id'], values=dict(threshold=-1)))
    supply(f.service.runtime_runner.runtime, f.auth, rid, dict(wait_id=wait['wait_id'], values=dict(threshold=100)))
    previous = f.service.runtime_runner
    # Discard process-local execution and Registry caches; only the existing
    # persisted approved revision, receipts, checkpoints and live auth remain.
    f.adapter.agents.clear();f.adapter._grants.clear()
    f.adapter.service._agents.clear();f.adapter.service._assignments.clear()
    f.service.runtime_runner = GraphRunner(RuntimeService(f.service), agents=previous.agents, connectors=previous.connectors)
    worker = RuntimeWorker(f.service.runtime_runner, lambda *_:f.auth)
    worker.drain()
    run = load(f, rid)
    assert run['status'] == 'completed', run['adaptive']
    assert all(run['action_instances'][k] == v for k,v in before.items())
    assert len(f.model_inputs) == 2


def test_repeated_revisions_without_evidence_stop_with_durable_blocker(subway):
    f=subway
    def evaluate(ctx,**_):
        return decision(ctx,choice='replan',proposal={k:deepcopy(ctx['plan'][k]) for k in ('actions','completion_criteria','missing_inputs')})
    rid,_,_=start(f,evaluate)
    run=drain(f,rid)
    assert run['status']=='blocked' and run['adaptive']['blocker']=='ADAPTIVE_NO_PROGRESS'
    assert run['adaptive']['revision']==3 and not f.model_inputs


def test_revision_cannot_remove_completed_action_or_register_new_capability(subway):
    f=subway
    def evaluate(ctx,**_):
        if 'read' in ctx['completed_actions']:
            proposal={k:deepcopy(ctx['plan'][k]) for k in ('actions','completion_criteria','missing_inputs')}
            proposal['actions'][0]['instructions']='Change already completed work.'
            return decision(ctx,choice='replan',proposal=proposal)
        return decision(ctx)
    rid,_,_=start(f,evaluate)
    run=drain(f,rid)
    assert run['status']=='blocked' and run['adaptive']['blocker']=='ADAPTIVE_COMPLETED_ACTION'
    assert run['action_instances']['read']['state']=='completed'


def test_tenant_and_subject_cannot_continue_or_supply_foreign_run(subway):
    f=subway;rid,_,_=start(f,lambda ctx,**_:decision(ctx,choice='request_input',wait=True))
    run=drain(f,rid);wait=run['adaptive']['pending_wait']
    foreign=deepcopy(f.auth);foreign['subject']['subject_id']='other-owner'
    with pytest.raises(Exception,match='subject|owner'):
        f.service.runtime_runner.advance(rid,foreign)
    with pytest.raises(Exception,match='owner'):
        supply(f.service.runtime_runner.runtime,foreign,rid,dict(wait_id=wait['wait_id'],values=dict(threshold=1)))
    foreign['subject']['workspace_id']='client-simpsons'
    with pytest.raises(Exception):
        f.service.runtime_runner.advance(rid,foreign)
    assert load(f,rid)['adaptive']['pending_wait']==wait


def test_live_claim_prevents_concurrent_evaluation_and_expired_claim_blocks_unknown(subway):
    f=subway;calls=[]
    rid,_,_=start(f,lambda ctx,**_:(calls.append(ctx) or decision(ctx)))
    runtime=f.service.runtime_runner.runtime
    with runtime.store.transaction() as db:
        run=runtime.load(db,rid,f.auth)
        run['adaptive']['claim']=dict(token='interrupted-provider',until=runtime.clock()+60)
        runtime.save(db,run)
    f.service.runtime_runner.advance(rid,f.auth)
    assert not calls
    with runtime.store.transaction() as db:
        run=runtime.load(db,rid,f.auth);run['adaptive']['claim']['until']=0;runtime.save(db,run)
    run=drain(f,rid)
    assert run['adaptive']['blocker']=='ADAPTIVE_UNKNOWN_EVALUATION' and not calls


def test_known_temporary_provider_rejection_retries_with_reserved_budget(subway):
    f=subway;calls=[]
    class TemporaryRejection(Exception):status_code=503
    def evaluate(ctx,**_):
        calls.append(ctx)
        if len(calls)==1:raise TemporaryRejection()
        return decision(ctx)
    rid,_,_=start(f,evaluate)
    result=f.service.runtime_runner.advance(rid,f.auth)
    assert result['status']=='queued'
    assert load(f,rid)['adaptive']['provider_failures']==1
    with f.service.store.transaction() as db:
        runtime=f.service.runtime_runner.runtime;run=runtime.load(db,rid,f.auth)
        run['available_at']=0;runtime.save(db,run)
    run=drain(f,rid)
    assert run['status']=='completed' and run['adaptive_reasoning_usage']['llm_calls']==5


def test_missing_company_policy_is_not_invented(subway):
    f=subway
    def evaluate(ctx,**_):
        result=decision(ctx,choice='blocked')
        result['assessment']['rule_evaluations']=[dict(id='approval-threshold',scope='Subway purchasing',
            source_ref=None,inputs={},result='No authoritative company threshold is available.',
            missing_prerequisites=['Authoritative approval threshold'],version=None,classification='missing_policy')]
        return result
    rid,_,_=start(f,evaluate,'Investigate purchase orders that exceeded the company approval threshold.')
    run=drain(f,rid)
    assert run['adaptive']['assessment']['rule_evaluations'][0]['classification']=='missing_policy'
    assert run['status']=='blocked' and not f.model_inputs


def test_query_and_actual_saved_document_passages_share_scoped_investigation(subway):
    from workflow_api.subway_documents import definition
    from tests.test_connected_action_plans import action,bind
    from hashlib import sha256
    f=subway;tool=definition();registry=f.adapter.service
    registry._policy.remaining_quota['subway_documents']=20
    assert registry.register_tool(tool,f.auth)['status']==200
    text='Isolated synthetic scenario: purchasing records are observations; they do not establish the cause of budget variances.'
    document=dict(source_id='scenario-doc',title='Isolated scenario document',kind='evidence',module_ids=[],text=text,
        sha256=sha256(text.encode()).hexdigest(),origin='owner_supplied')
    with f.service.store.transaction() as db:
        db.execute('INSERT INTO business_ontology_documents VALUES (?,?,?,?)',('client-subway','subway-client','scenario-doc',json.dumps(document)))
    original=f.make_proposal
    def proposal(goal,context):
        result=original(goal,context)
        doc=action('documents','tool.subway_documents',[bind('context','query','goal')],['read'])
        result['actions'].insert(2,doc)
        result['actions'][-1]['depends_on'].append('documents')
        result['actions'][-1]['evidence_references'].append('documents')
        return result
    f.service.planner.provider.plan_actions=proposal
    rid,_,_=start(f,lambda ctx,**_:decision(ctx),'Investigate purchasing records and budget variances with supporting documents.')
    run=drain(f,rid)
    assert run['status']=='completed',json.dumps({'adaptive':run['adaptive'],'error':run.get('error_code')},default=str)
    output=run['action_instances']['documents']['output']
    assert output['scope']==dict(workspace_id='client-subway',owner_id='subway-client')
    record=next(r for r in output['records'] if r['source_id']=='scenario-doc')
    assert record['text']==text and record['excerpt_sha256']==sha256(text.encode()).hexdigest()
    assert record['location']==dict(character_start=0,character_end=len(text))


def test_connected_overview_projection_exposes_current_revision_and_evidence(subway):
    from workflow_api.composition_presentation import CompositionPresentation
    f=subway
    def evaluate(ctx,**_):
        if ctx['plan']['revision']==1 and 'read' in ctx['completed_actions']:
            proposal={k:deepcopy(ctx['plan'][k]) for k in ('actions','completion_criteria','missing_inputs')}
            report=next(a for a in proposal['actions'] if a['action_id']=='report')
            report['instructions']='Summarize the verified count and preserve source limitations.'
            return decision(ctx,choice='replan',proposal=proposal)
        return decision(ctx)
    rid,doc,_=start(f,evaluate)
    run=drain(f,rid)
    view=CompositionPresentation(f.service.business_composition).view(f.auth,doc['composition_id'],rid)
    assert run['status']=='completed',json.dumps({'adaptive':run['adaptive'],'error':run.get('error_code')},default=str)
    assert view['run']['adaptive']['revision']==2
    assert view['run']['action_plan']['revision']==2
    assert view['run']['action_instances']['read']['plan_revision']==1
    assert view['run']['action_instances']['report']['plan_revision']==2
    assert view['run']['adaptive']['assessment']['completion_eligible']


def test_input_api_validates_wait_and_returns_exact_effective_workflow(subway):
    import hashlib,hmac,time
    from fastapi.testclient import TestClient
    f=subway;rid,_,w=start(f,lambda ctx,**_:decision(ctx,choice='request_input',wait=True))
    run=drain(f,rid);wait=run['adaptive']['pending_wait']
    payload='subway.'+str(int(time.time())+60)+'.'+'b'*48
    assertion=payload+'.'+hmac.new(f.env['BUILDER_SUBWAY_PROXY_SECRET'].encode(),payload.encode(),hashlib.sha256).hexdigest()
    with TestClient(f.app,headers={'x-builder-client-assertion':assertion}) as client:
        before=client.get('/runs/'+rid+'/workflow')
        assert before.status_code==200 and before.json()['data']['workflow']['workflow_id']==w['workflow_id']
        wrong=client.post('/runs/'+rid+'/input',json=dict(wait_id='stale',values=dict(threshold=10)))
        assert wrong.status_code==409
        accepted=client.post('/runs/'+rid+'/input',json=dict(wait_id=wait['wait_id'],values=dict(threshold=10)))
        assert accepted.status_code==200,accepted.text
        assert accepted.json()['data']['run']['adaptive']['pending_wait'] is None


def test_unsupported_policy_and_source_finding_cannot_be_promoted(subway):
    f=subway
    def evaluate(ctx,**_):
        result=decision(ctx,choice='blocked')
        result['assessment']['rule_evaluations']=[dict(id='made-up-policy',scope='purchasing',source_ref='filename-only',
            inputs={},result='Approved',missing_prerequisites=[],version='invented',classification='verified_policy')]
        return result
    rid,_,_=start(f,evaluate)
    run=drain(f,rid)
    assert run['adaptive']['blocker']=='ADAPTIVE_RULE_UNVERIFIED'
    assert not f.model_inputs


def test_invalid_unfinished_query_can_be_replaced_without_replaying_success(subway):
    from workflow_api.service import ApiFailure
    f=subway;execute=f.q.execute;attempts=[]
    def query(auth,body):
        attempts.append(deepcopy(body))
        if len(attempts)==1:raise ApiFailure('SUBWAY_QUERY_INVALID','Isolated invalid aggregation.',422)
        return execute(auth,body)
    f.q.execute=query
    def evaluate(ctx,**_):
        if ctx['failures'] and ctx['plan']['revision']==1:
            proposal={k:deepcopy(ctx['plan'][k]) for k in ('actions','completion_criteria','missing_inputs')}
            read=next(a for a in proposal['actions'] if a['action_id']=='read');read['action_id']='corrected_read'
            report=next(a for a in proposal['actions'] if a['action_id']=='report')
            report['depends_on']=['corrected_read'];report['evidence_references']=['corrected_read']
            for binding in report['bindings']:
                if binding.get('action_id')=='read':binding['action_id']='corrected_read'
            return decision(ctx,choice='replan',proposal=proposal)
        return decision(ctx)
    rid,_,_=start(f,evaluate)
    run=drain(f,rid)
    assert run['status']=='completed',json.dumps({'adaptive':run['adaptive'],'error':run.get('error_code')},default=str)
    assert run['action_instances']['read']['state']=='failed'
    assert run['action_instances']['corrected_read']['state']=='completed'
    assert len(attempts)==2 and len(f.model_inputs)==2


def test_budget_scenario_retrieves_baseline_and_verifies_variances_without_inventing_cause(subway):
    from decimal import Decimal
    from tests.test_subway_full_queries import field
    f=subway;c=f.q.catalog(f.auth)
    f.rows['subway_finance']['purchaseorders']=[dict(_id=1,budget=11,totalAmount=Decimal('130'),currency='INR'),dict(_id=2,budget=22,totalAmount=Decimal('90'),currency='INR')]
    f.rows['subway_finance']['budgets']=[dict(_id=11,storeId=1),dict(_id=22,storeId=2)]
    f.rows['subway_finance']['lineitems']=[dict(_id=101,budgetId=11,initialAmount=Decimal('100')),dict(_id=102,budgetId=22,initialAmount=Decimal('100'))]
    po=plan(f.q);baseline=plan(f.q,'finance.lineitems')
    def budget_edge(query):
        return next(r for r in c['relationships'].values() if r['source_dataset_id']==query['base_dataset_id'] and c['datasets'][r['target_dataset_id']]['label']=='finance.budgets')
    po_edge=budget_edge(po);baseline_edge=budget_edge(baseline)
    budget_id=po_edge['target_field_id']
    amount=field(f.q,'finance.purchaseorders','totalAmount');currency=field(f.q,'finance.purchaseorders','currency')
    initial=field(f.q,'finance.lineitems','initialAmount')
    po.update(joins=[po_edge['relationship_id']],group_by=[budget_id,currency],metrics=[dict(label='amount',op='sum',field_id=amount)],order_by=[dict(column=budget_id,direction='asc')])
    baseline.update(joins=[baseline_edge['relationship_id']],group_by=[budget_id],metrics=[dict(label='baseline',op='sum',field_id=initial)],order_by=[dict(column=budget_id,direction='asc')])
    f.query_plans=dict(query_plan=po,baseline_plan=baseline)
    f.selected_override=selection(f.q,['finance.purchaseorders','finance.lineitems','finance.budgets'],[amount,currency,initial,budget_id],
        [po_edge['relationship_id'],baseline_edge['relationship_id']])
    def evaluate(ctx,**_):
        if 'read' in ctx['completed_actions'] and ctx['plan']['revision']==1:
            actions=deepcopy(ctx['plan']['actions'])
            query=deepcopy(actions[0]);query.update(action_id='baseline_plan',depends_on=['read'])
            read=deepcopy(actions[1]);read.update(action_id='baseline_read',depends_on=['baseline_plan'])
            read['bindings']=[dict(kind='output',action_id='baseline_plan',path=['query'],target=['query'])]
            report=next(a for a in actions if a['action_id']=='report')
            report['depends_on'].append('baseline_read');report['evidence_references'].append('baseline_read')
            return decision(ctx,choice='retrieve_more',proposal=dict(actions=actions+[query,read],completion_criteria=['report'],missing_inputs=[]),satisfied=False)
        result=decision(ctx,satisfied=False)
        if result['decision']=='blocked':
            refs={v['action_id']:key for key,v in ctx['evidence'].items()}
            result['assessment']['calculations']=[dict(id='scenario-budget-'+str(i),operation='difference',operands=[
                dict(evidence_id=refs['read'],path=['rows',i,'amount']),dict(evidence_id=refs['baseline_read'],path=['rows',i,'baseline'])],result=value) for i,value in enumerate(['30','-10'])]
            result['assessment']['source_limitations']=['Isolated synthetic scenario: initialAmount is a scenario comparison baseline. Official budget basis, reporting period and actual root cause remain unverified. Purchase orders are committed order values, not proven payments.']
        return result
    rid,_,_=start(f,evaluate,'Investigate Subway outlets that exceeded their budgets, examine purchasing records, and explain verified contributing factors.')
    run=drain(f,rid)
    assert run['status']=='blocked' and run['adaptive']['revision']==2,json.dumps(run['adaptive'])
    assert [v['result'] for v in run['adaptive']['assessment']['calculations']]==['30','-10']
    assert 'actual root cause remain unverified' in run['adaptive']['assessment']['source_limitations'][0]
    assert run['action_instances']['read']['output']['relationship_ids']==[po_edge['relationship_id']]


def test_invoice_po_scenario_uses_declared_reference_and_preserves_unmatched_invoice(subway):
    from tests.test_subway_full_queries import field
    f=subway;c=f.q.catalog(f.auth)
    f.rows['subway_finance']['purchaseorders']=[dict(_id=1,totalAmount=100,currency='INR')]
    f.rows['subway_finance']['invoicedatas']=[dict(_id=5,poId=1,invoiceAmount=120),dict(_id=6,poId=999,invoiceAmount=90)]
    query=plan(f.q,'finance.invoicedatas')
    edge=next(r for r in c['relationships'].values() if r['source_dataset_id']==query['base_dataset_id'] and c['datasets'][r['target_dataset_id']]['label']=='finance.purchaseorders')
    iid=field(f.q,'finance.invoicedatas','_id');invoice=field(f.q,'finance.invoicedatas','invoiceAmount');amount=field(f.q,'finance.purchaseorders','totalAmount')
    query.update(joins=[edge['relationship_id']],fields=[iid,invoice,amount],metrics=[],order_by=[dict(column=iid,direction='asc')])
    f.query_plans=dict(query_plan=query)
    f.selected_override=selection(f.q,['finance.invoicedatas','finance.purchaseorders'],[iid,invoice,amount],[edge['relationship_id']])
    def evaluate(ctx,**_):
        result=decision(ctx,satisfied=False)
        if result['decision']=='blocked':
            ref=next(iter(ctx['evidence']))
            result['assessment']['calculations']=[dict(id='invoice-po-difference',operation='difference',operands=[
                dict(evidence_id=ref,path=['rows',0,invoice]),dict(evidence_id=ref,path=['rows',0,amount])],result='20')]
            result['assessment']['source_limitations']=['Synthetic fixture: one invoice has no matching purchase order. No company discrepancy tolerance or causal explanation was invented. Numeric difference only; payment and currency equivalence need evidence.']
        return result
    rid,_,_=start(f,evaluate,'Find purchase orders with related invoice discrepancies and summarize verified discrepancies.')
    run=drain(f,rid)
    assert run['status']=='blocked',json.dumps(run['adaptive'])
    output=run['action_instances']['read']['output']
    assert output['rows'][1][amount] is None
    assert output['join_checks'][0]['unmatched_reference_rows']==1
    assert run['adaptive']['assessment']['calculations'][0]['result']=='20'


def test_incorrect_model_arithmetic_cannot_become_a_verified_finding(subway):
    f=subway
    def evaluate(ctx,**_):
        result=decision(ctx,satisfied=False)
        if ctx['evidence']:
            ref=next(iter(ctx['evidence']))
            result=decision(ctx,choice='blocked',satisfied=False)
            result['assessment']['calculations']=[dict(id='invalid-difference',operation='difference',operands=[
                dict(evidence_id=ref,path=['rows',0,'count']),dict(evidence_id=ref,path=['rows',0,'count'])],result='1')]
        return result
    rid,_,_=start(f,evaluate)
    run=drain(f,rid)
    assert run['status']=='blocked' and run['adaptive']['blocker']=='ADAPTIVE_CALCULATION_INVALID'


def test_resumed_query_receives_new_business_input_instead_of_old_snapshot(subway):
    f=subway
    def evaluate(ctx,**_):
        if 'threshold' not in ctx['user_values']:return decision(ctx,choice='request_input',wait=True)
        return decision(ctx)
    rid,_,_=start(f,evaluate)
    run=drain(f,rid)
    assert not f.model_inputs
    wait=run['adaptive']['pending_wait']
    supply(f.service.runtime_runner.runtime,f.auth,rid,dict(wait_id=wait['wait_id'],values=dict(threshold=125)))
    run=drain(f,rid)
    assert run['status']=='completed',json.dumps(run['adaptive'])
    assert f.model_inputs[0]['context']['user_values']['threshold']==125


def test_exhausted_provider_capacity_persists_a_blocker_instead_of_polling_forever(subway):
    from types import SimpleNamespace
    from workflow_api.resource_limits import CapacityDeferred
    from runtime.service import RuntimeFailure
    f=subway;rid,_,_=start(f,lambda ctx,**_:decision(ctx))
    def reserve(*_):raise CapacityDeferred('PROVIDER_RATE_LIMITED',0)
    def defer(*_):raise RuntimeFailure('BACKPRESSURE_EXHAUSTED','Deferral budget exhausted.')
    f.service.runtime_runner.runtime.resource_controls=SimpleNamespace(reserve_provider=reserve,defer=defer)
    run=drain(f,rid)
    assert run['status']=='blocked' and run['adaptive']['blocker']=='BACKPRESSURE_EXHAUSTED'
    assert not f.model_inputs


def test_revoked_source_scope_blocks_before_evaluation(subway):
    from workflow_api.service import ApiFailure
    f=subway;calls=[]
    rid,_,_=start(f,lambda ctx,**_:(calls.append(ctx) or decision(ctx)))
    def unavailable(*_):raise ApiFailure('SUBWAY_QUERY_STALE','Owned source scope changed.',409)
    f.q.catalog=unavailable
    run=drain(f,rid)
    assert run['status']=='blocked' and run['adaptive']['blocker']=='SUBWAY_QUERY_STALE'
    assert not calls and not f.model_inputs


def test_existing_openai_evaluator_transport_uses_additive_investigation_schema(subway):
    from types import SimpleNamespace
    from planner.provider import OpenAIStructuredOutputProvider
    f=subway;requests=[]
    def create(**request):
        requests.append(deepcopy(request))
        payload=json.loads(request['input'][1]['content'])
        assert payload['schema']['$id'].endswith('/investigation-assessment-v1.json')
        assert request['store'] is False and request['max_output_tokens']==6000
        assert request['text']['format']['type']=='json_object'
        assert payload['context']['evaluation_kind']==KIND
        return SimpleNamespace(status='completed',output_text=json.dumps(decision(payload['context'])))
    provider=OpenAIStructuredOutputProvider(client=SimpleNamespace(responses=SimpleNamespace(create=create)),model='controlled-fixture-model')
    rid,_,_=start(f,provider.evaluate_actions)
    run=drain(f,rid)
    assert run['status']=='completed',json.dumps(run['adaptive'])
    assert len(requests)==4
