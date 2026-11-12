"""Production wrapper parity and adaptive scheduling with offline provider transport."""
import inspect,json
from copy import deepcopy
from types import SimpleNamespace
from unittest.mock import Mock
import pytest
from planner.provider import OpenAIStructuredOutputProvider
from planner.evaluator_protocol import encode
from workflow_api.workflow_adaptive import CONTRACT
from workflow_api.live_providers import LivePlannerProvider
from tests.test_subway_autonomy import subway,engine,installed,start,decision,drain,load
from tests.test_subway_automations import schedule,dispatch


def test_all_public_provider_operations_remain_exposed_with_matching_arguments():
    # New provider entry points must explicitly declare wrapper behavior.
    methods={name for name,value in inspect.getmembers(OpenAIStructuredOutputProvider,inspect.isfunction) if not name.startswith('_')}
    assert methods=={'generate','plan_actions','select_capabilities','evaluate_actions','workflow_title'}
    for name in methods:
        assert callable(getattr(LivePlannerProvider,name,None)),name
        assert list(inspect.signature(getattr(LivePlannerProvider,name)).parameters)==list(inspect.signature(getattr(OpenAIStructuredOutputProvider,name)).parameters)


@pytest.mark.parametrize('budget',[2000,6000])
def test_evaluator_forwards_context_budget_result_and_provider_errors(budget):
    wrapper=LivePlannerProvider('offline',[],object());context={'evaluation_kind':'workflow-investigation'}
    result={'decision':'continue'};wrapper.provider.evaluate_actions=Mock(return_value=result)
    assert wrapper.evaluate_actions(context,max_output_tokens=budget) is result
    wrapper.provider.evaluate_actions.assert_called_once_with(context,max_output_tokens=budget)
    failure=RuntimeError('controlled provider error');wrapper.provider.evaluate_actions.side_effect=failure
    with pytest.raises(RuntimeError) as caught:wrapper.evaluate_actions(context,max_output_tokens=budget)
    assert caught.value is failure


def test_title_uses_same_configured_provider():
    wrapper=LivePlannerProvider('offline',[],object());wrapper.provider.workflow_title=Mock(return_value='Purchasing review')
    assert wrapper.workflow_title('Summarize purchasing')=='Purchasing review'
    wrapper.provider.workflow_title.assert_called_once_with('Summarize purchasing')


def live_wrapper(calls):
    def create(**kwargs):
        payload=json.loads(kwargs['input'][1]['content']);ctx=payload['context']
        calls.append(dict(kind=ctx['evaluation_kind'],budget=kwargs['max_output_tokens']))
        assert kwargs['text']['format']['strict'] is True
        result=decision(ctx)
        for eid,item in ctx['evidence'].items():
            if item['valid'] and 'coverage' in item['output']:
                assert 'sources' in item['output'] and 'scope' in item['output']
                result['assessment']['findings'].append(dict(evidence_id=eid,path=['coverage','matched_records'],value=item['output']['coverage']['matched_records'],classification='observation'))
        return SimpleNamespace(status='completed',output_text=json.dumps(encode(result, CONTRACT)))
    return LivePlannerProvider('offline',[],SimpleNamespace(responses=SimpleNamespace(create=create)))


def test_real_adaptive_runtime_uses_live_wrapper_and_finishes(subway):
    f=subway;rid,_,_=start(f,lambda ctx,**_:decision(ctx));calls=[]
    f.service.planner.provider=live_wrapper(calls)
    run=drain(f,rid)
    assert run['status']=='completed' and run['adaptive']['assessment']['completion_eligible']
    assert len(calls)==4 and all(c['budget']==6000 for c in calls)
    assert run['action_instances']['read']['verified_receipt']


def test_recurring_occurrence_uses_real_wrapper_and_verified_reads(subway,monkeypatch):
    f=subway;auto,record,_=schedule(f,monkeypatch);calls=[]
    f.service.planner.provider=live_wrapper(calls);f.now=record['due']
    occurrences=dispatch(f,auto)
    assert len(occurrences)==1 and occurrences[0]['state']=='completed'
    assert load(f,occurrences[0]['run_id'])['adaptive']['status']=='completed' and calls


def test_missing_evaluator_blocks_without_paid_call_reservation(subway):
    f=subway;rid,_,_=start(f,lambda ctx,**_:decision(ctx))
    f.service.planner.provider=SimpleNamespace()
    run=drain(f,rid)
    assert run['error_code']=='ADAPTIVE_PROVIDER_UNAVAILABLE'
    assert run['adaptive']['turns']==0 and run['adaptive_reasoning_usage']['llm_calls']==0
    assert not run.get('action_instances')


def test_unexpected_error_has_safe_diagnostic_without_error_text(subway):
    f=subway;rid,_,_=start(f,lambda ctx,**_:decision(ctx));wrapper=live_wrapper([])
    wrapper.provider.evaluate_actions=Mock(side_effect=AttributeError('private provider content'))
    f.service.planner.provider=wrapper;run=drain(f,rid)
    assert run['error_code']=='ADAPTIVE_EVALUATION_FAILED'
    with f.service.store.transaction(write=False) as db:
        events=[json.loads(row[0]) for row in db.execute('SELECT document FROM runtime_events WHERE run_id=?',(rid,))]
    event=next(e for e in events if e['event_type']=='adaptive.evaluation_failed')
    assert event['details']['exception_type']=='AttributeError' and 'private provider content' not in json.dumps(events)


def test_invalid_decision_records_only_safe_validation_stage(subway):
    from planner.errors import PlannerFailure
    f=subway;rid,_,_=start(f,lambda ctx,**_:decision(ctx));wrapper=live_wrapper([])
    wrapper.provider.evaluate_actions=Mock(side_effect=PlannerFailure('ADAPTIVE_DECISION_INVALID',
        'private provider message',details=dict(validation_stage='canonical',response='private response')))
    f.service.planner.provider=wrapper;run=drain(f,rid)
    assert run['error_code']=='ADAPTIVE_DECISION_INVALID' and not run.get('action_instances')
    with f.service.store.transaction(write=False) as db:
        events=[json.loads(row[0]) for row in db.execute('SELECT document FROM runtime_events WHERE run_id=?',(rid,))]
    details=next(e['details'] for e in events if e['event_type']=='adaptive.evaluation_failed')
    assert details['exception_type']=='PlannerFailure' and details['validation_stage']=='canonical'
    assert set(details)<= {'exception_type','validation_stage','correlation_id','trace_reference'}
    assert 'private response' not in json.dumps(events)


@pytest.mark.parametrize('code',['ADAPTIVE_PROVIDER_UNAVAILABLE','ADAPTIVE_EVALUATION_FAILED','ADAPTIVE_DECISION_INVALID'])
def test_ui_recovery_reason_identifies_evaluator_service_failure(code):
    from workflow_api.composition_presentation import CompositionPresentation
    view=CompositionPresentation.recovery_view(dict(status='blocked',error_code=code,node_states={}),dict(nodes=[]),0)
    assert not view['eligible'] and 'workflow evaluator' in view['reason']
    assert 'authorization' not in view['reason']
