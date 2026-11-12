"""Synthetic conditional-analysis contexts; no customer data or external actions."""
from copy import deepcopy
from types import SimpleNamespace
import json
import pytest
from planner.evaluator_protocol import ANALYSIS_POLICY,encode
from planner.provider import OpenAIStructuredOutputProvider
from workflow_api.workflow_adaptive import CONTRACT,validate_decision
from runtime.service import RuntimeFailure


def scenario(kind='conditional',frozen=True):
    objective='Compare available invoice and linked order amounts. Report numeric differences only where currencies and units are comparable. Identify missing links, explain evidence and freshness limitations, and create a Calendar review with the findings.'
    descriptions=['Compare available invoice and linked order records.','Report numeric differences only where currencies and units are comparable.','Identify missing or unmatched links and explain evidence and freshness limitations.']
    if kind=='unconditional':
        objective='Calculate the exact invoice-to-order monetary difference for every invoice in a verified common currency, and create a Calendar review with the complete results.'
        descriptions=['Calculate exact comparable monetary differences for every invoice.']
    if kind=='exhaustive':
        objective='Compare every invoice with its linked order and include an exhaustive row-by-row difference listing in a Calendar review. Do not deliver a partial review.'
        descriptions=['Produce an exhaustive row-by-row comparison of every invoice.']
    reqs=[dict(id='requirement_'+str(i),description=d) for i,d in enumerate(descriptions)]
    output=dict(query_id='synthetic-query',scope=dict(workspace_id='synthetic',owner_id='synthetic'),
        columns=[dict(label=n) for n in ['invoice.id','invoice.amount','order.amount','order.totalAmount','order.currency']],
        rows=[{'invoice.id':1,'invoice.amount':'12.50','order.amount':'10','order.totalAmount':'12.50','order.currency':1}],
        coverage=dict(complete_scan=True,matched_records=100,total_result_rows=100,returned_rows=1,has_more=True,aggregate_complete=False,offset=0,next_offset=1,display_limited_by='response_bytes',warnings=[]),
        join_checks=[dict(source_rows=100,matched_rows=100,missing_reference_rows=0,unmatched_reference_rows=0)],
        sources=[dict(source_id='synthetic-invoices',freshness=dict(status='historical_snapshot',extracted_at=None,last_synced_at=None))])
    ev={'evidence:synthetic':dict(evidence_id='evidence:synthetic',action_id='read',valid=kind!='invalid',output=output,provenance='ACTUAL',plan_revision=1)}
    actions=[dict(action_id='read',capability_id='tool.synthetic_query',depends_on=[]),dict(action_id='report',capability_id='content.prepare',depends_on=['read']),dict(action_id='event',capability_id='tool.synthetic_calendar',depends_on=['report'])]
    plan=dict(goal=objective,actions=actions,completion_criteria=['event'],missing_inputs=[])
    previous=dict(objective=objective,requirements=[{**r,'status':'unsatisfied','evidence_ids':[]} for r in reqs],findings=[],gaps=[dict(id='previous_gap',description='Currency comparability and unreturned detail are unavailable.',blocking=True)],source_limitations=[],invalid_assumptions=[],recoverable_failures=[],rule_evaluations=[],completion_eligible=False)
    ctx=dict(evaluation_kind='workflow-investigation',original_objective=objective,analysis_policy=ANALYSIS_POLICY,
        execution_scope=dict(kind='automation_occurrence',business_requirements='Source-backed analysis only; schedule and external actions are tracked separately.'),
        plan=plan,frozen_requirements=reqs if frozen else [],evidence=ev,previous_assessment=previous if frozen else None,
        completed_actions=['read','report'],failures=[],remaining_limits=dict(max_reasoning_turns=8,max_tool_calls=8),
        deterministic_limitations=[dict(action_id='read',code='QUERY_DETAIL_PAGINATED',details=output['coverage'])],
        evidence_projection='The displayed row is a page. Complete-scan join coverage is population-wide; no invoice currency was returned. No comparable numeric difference can be established. A limited descriptive review may withhold differences and disclose limitations.',
        working_memory={'report':dict(summary='Available invoice and order measures remain distinct. No numeric differences were calculated because invoice currency/units are unavailable. One detail row is returned out of 100; this is not an exhaustive comparison. Full-scan join coverage reports no missing or unmatched links. Data is a historical snapshot, not current production.')},
        allowed_capabilities={'tool.synthetic_query':dict(side_effect='read'),'content.prepare':dict(side_effect='none'),'tool.synthetic_calendar':dict(side_effect='write')})
    return ctx


def check_model_decision(context,result,conditional=True):
    run=dict(adaptive=dict(objective=context['original_objective'],requirements=context['frozen_requirements']),action_instances={'read':dict(state='completed'),'report':dict(state='completed')})
    workflow=dict(metadata=dict(connected_action_plan=context['plan']))
    validate_decision(result,run,workflow,context['evidence'])
    if conditional:
        assert result['decision']=='continue' and result['action_id']=='event',result['rationale']
        assert result['assessment']['completion_eligible'] and result['assessment']['source_limitations']
        assert not result['assessment'].get('calculations'), 'Unknown currency cannot support a difference'
        assert all(r['status']=='verified' and r['evidence_ids'] for r in result['assessment']['requirements'])
    else:
        assert not result['assessment']['completion_eligible']
        assert result['decision'] in ('blocked','request_input','retrieve_more','replan')


def test_policy_is_sent_at_the_provider_boundary_without_changing_contract():
    ctx=scenario();captured=[]
    def create(**kwargs):
        captured.append(kwargs)
        assert ANALYSIS_POLICY in kwargs['input'][0]['content']
        assert json.loads(kwargs['input'][1]['content'])['context']['analysis_policy']==ANALYSIS_POLICY
        assessment=deepcopy(ctx['previous_assessment']);assessment.update(requirements=[{**r,'status':'verified','evidence_ids':['evidence:synthetic']} for r in ctx['frozen_requirements']],gaps=[],source_limitations=['No comparable differences; paginated historical records only.'],completion_eligible=True)
        result=dict(decision='continue',rationale='Deliver qualified findings without unsupported differences.',action_id='event',proposal=None,input_requests=[],assessment=assessment)
        return SimpleNamespace(status='completed',output_text=json.dumps(encode(result,CONTRACT)))
    provider=OpenAIStructuredOutputProvider(client=SimpleNamespace(responses=SimpleNamespace(create=create)),model='synthetic')
    check_model_decision(ctx,provider.evaluate_actions(ctx,max_output_tokens=6000))
    assert len(captured)==1


def test_incomplete_assessment_cannot_claim_completion_or_invent_calculations():
    ctx=scenario();assessment=deepcopy(ctx['previous_assessment']);assessment['completion_eligible']=True
    result=dict(decision='continue',rationale='Incorrectly ready',action_id='event',proposal=None,input_requests=[],assessment=assessment)
    run=dict(adaptive=dict(objective=ctx['original_objective'],requirements=ctx['frozen_requirements']))
    with pytest.raises(RuntimeFailure) as error:validate_decision(result,run,dict(metadata=dict(connected_action_plan=ctx['plan'])),ctx['evidence'])
    assert error.value.code=='ADAPTIVE_FALSE_COMPLETION'


# Native approved recurring delivery: a contradictory model choice must never
# invoke a connector, and one explicit reassessment may correct conditional scope.
from tests.test_subway_autonomy import subway,engine,installed,decision
from tests.test_subway_automations import google_setup


@pytest.mark.parametrize('outcome',['correct','repeat','blocked'])
def test_recurring_delivery_corrects_inconsistent_choice_without_bypassing_approval(subway,google_setup,monkeypatch,outcome):
    import tests.test_subway_automations as native
    original=native.start
    contexts=[];connectors=[]
    import tests.test_business_composition as composition
    original_install=composition.install_external
    def capture(*args,**kwargs):
        tool,connector=original_install(*args,**kwargs);connectors.append(connector);return tool,connector
    monkeypatch.setattr(composition,'install_external',capture)
    def start(f,evaluate,objective):
        def assess(ctx,**_):
            contexts.append(deepcopy(ctx))
            assert ctx['analysis_policy']==ANALYSIS_POLICY
            result=decision(ctx)
            if result.get('action_id')=='draft':
                ev=[key for key,item in ctx['evidence'].items() if item['valid']]
                if ctx.get('decision_feedback'):
                    assert ctx['decision_feedback']['code']=='ADAPTIVE_EVIDENCE_INCOMPLETE'
                    assert connectors and not connectors[0].calls
                    if outcome=='repeat':return result
                    if outcome=='blocked':
                        result.update(decision='blocked',action_id=None);return result
                    result['assessment']['requirements'][0].update(status='verified',evidence_ids=ev)
                    result['assessment'].update(gaps=[],source_limitations=['Only available evidence; unsupported comparisons withheld.'],completion_eligible=True)
                # First delivery decision intentionally retains unsatisfied evidence.
            return result
        return original(f,assess,objective)
    monkeypatch.setattr(native,'start',start)
    if outcome=='correct':
        native.test_scheduled_native_analysis_requires_exact_external_approval(subway,google_setup,monkeypatch)
    else:
        with pytest.raises(AssertionError):native.test_scheduled_native_analysis_requires_exact_external_approval(subway,google_setup,monkeypatch)
        from workflow_api.automation import DurableAutomation
        occurrence=DurableAutomation(subway.service).listing(subway.auth,'occurrence')['items'][0]
        assert occurrence['state']=='failed' and occurrence['last_error_code']==('ADAPTIVE_EVIDENCE_INCOMPLETE' if outcome=='repeat' else 'ADAPTIVE_OBJECTIVE_BLOCKED')
        assert connectors and not connectors[0].calls
    assert sum(bool(c.get('decision_feedback')) for c in contexts)==1
