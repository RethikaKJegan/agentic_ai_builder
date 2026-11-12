"""Complete local automation with provider-sized usage and no external delivery."""
from copy import deepcopy
from types import SimpleNamespace
import json
from decimal import Decimal
import pytest
from runtime.model_usage import validate_confirmed
from runtime.service import RuntimeFailure
from tests.test_subway_autonomy import subway,engine,installed,start,decision,drain,load
from tests.test_subway_automations import schedule,dispatch,google_setup


@pytest.mark.parametrize('managed',[False,True])
def test_accounting_policy_preserves_real_usage_and_bounded_caps(managed):
    reservation=dict(llm_calls=1,tokens=20000,estimated_cost_usd=10)
    actual=dict(llm_calls=1,tokens=60000,estimated_cost_usd=12)
    if managed:validate_confirmed(actual,reservation,enforce_usage_budgets=False)
    else:
        with pytest.raises(RuntimeFailure):validate_confirmed(actual,reservation)


@pytest.mark.parametrize('actual',[
    dict(llm_calls=2,tokens=1,estimated_cost_usd=0),dict(llm_calls=0,tokens=1,estimated_cost_usd=0),
    dict(llm_calls=True,tokens=1,estimated_cost_usd=0),dict(llm_calls=1,tokens=float('inf'),estimated_cost_usd=0),
    dict(llm_calls=1,tokens=float('nan'),estimated_cost_usd=0),dict(llm_calls=1,tokens=-1,estimated_cost_usd=0),
    dict(llm_calls=1,tokens='1',estimated_cost_usd=0),dict(llm_calls=1,tokens=1),
])
def test_invalid_counters_are_rejected_in_provider_managed_mode(actual):
    with pytest.raises(RuntimeFailure):validate_confirmed(actual,dict(llm_calls=1,tokens=20,estimated_cost_usd=1),enforce_usage_budgets=False)


def large_models(f):
    original=f.service.runtime_runner.agents.model_factory
    def factory(agent):
        model=original(agent);provider=model.provider_call
        def respond(messages,cap,timeout):
            assert cap is None
            text,_,_=provider(messages,cap,timeout)
            return text,40000,20000
        model.provider_call=respond;model.token_policy='provider';model.enforce_usage_budgets=False
        return model
    f.service.runtime_runner.agents.model_factory=factory
    f.service.runtime_runner.runtime.enforce_usage_budgets=False


def test_actual_recurring_occurrence_settles_large_usage_and_is_idempotent(subway,monkeypatch):
    f=subway;auto,record,_=schedule(f,monkeypatch);large_models(f)
    from tests.test_subway_full_queries import field,plan
    for row in f.rows['subway_finance']['purchaseorders']:
        row['currency']=1 if row['_id']<=50 else 3
        row['amount']=Decimal(row['_id'])
    f.query=plan(f.q,group_by=[field(f.q,'finance.purchaseorders',name) for name in ('status','currency')],metrics=[dict(label='records',op='count',field_id='')]+[dict(label=name+'_sum',op='sum',field_id=field(f.q,'finance.purchaseorders',name)) for name in ('amount','totalAmount')])
    f.now=record['due'];occurrences=dispatch(f,auto)
    assert len(occurrences)==1 and occurrences[0]['state']=='completed'
    run=load(f,occurrences[0]['run_id'])
    assert run['usage']['workflow']['tokens']==120000
    assert run['usage']['workflow']['llm_calls']==2
    assert run['action_instances']['read']['verified_receipt'] and run['action_instances']['report']['state']=='completed'
    assert run['action_instances']['read']['output']['coverage']['matched_records']==100
    results=run['action_instances']['read']['output']['rows']
    assert len(results)==4 and sum(row['records'] for row in results)==100
    assert sum(Decimal(row['amount_sum']) for row in results)==Decimal('5050')
    assert sum(Decimal(row['totalAmount_sum']) for row in results)==Decimal('5051')
    auto.tick(f.service.worker_authenticate)
    assert len(auto.history(f.auth,record['id']))==1


def test_scheduled_reviewed_delivery_still_requires_authority_and_completes_locally(subway,google_setup,monkeypatch):
    import tests.test_subway_automations as automation_tests
    original=automation_tests.start
    contexts=[]
    def adapted_start(f,evaluate,objective):
        rid,doc,workflow=original(f,evaluate,objective)
        large_models(f)
        from workflow_api.live_providers import LivePlannerProvider
        def create(**kwargs):
            context=json.loads(kwargs['input'][1]['content'])['context'];contexts.append(deepcopy(context))
            assert 'Future email receipt' not in context['execution_scope']['business_requirements']
            assert 'Never require a future email receipt' in kwargs['input'][0]['content']
            result=decision(context)
            ev=[key for key,value in context['evidence'].items() if value['valid']]
            if ev:
                result['assessment']['requirements'][0].update(status='verified',evidence_ids=ev)
                result['assessment'].update(completion_eligible=True,gaps=[])
            return SimpleNamespace(status='completed',output_text=json.dumps(result))
        f.service.planner.provider=LivePlannerProvider('offline',[],SimpleNamespace(responses=SimpleNamespace(create=create)))
        return rid,doc,workflow
    monkeypatch.setattr(automation_tests,'start',adapted_start)
    # Existing native recurring test exercises the full recurring authorization,
    # report, Google-account binding and fake connector delivery/dedup boundaries.
    automation_tests.test_scheduled_native_analysis_requires_exact_external_approval(subway,google_setup,monkeypatch)
    assert contexts and all(c['execution_scope']['kind']=='automation_occurrence' for c in contexts)
    assert any(c['completed_actions'] and not all(a['action_id'] in c['completed_actions'] for a in c['plan']['actions']) for c in contexts)


def test_provider_managed_repeated_turn_keeps_capacity_but_bounded_shrinks():
    from runtime.graph import GraphRunner
    agent=dict(agent_id='a',limits=dict(max_tokens=20000,max_estimated_cost_usd=10,max_llm_calls=2))
    workflow=dict(metadata=dict(adaptive_control=dict(kind='workflow-investigation')))
    run=dict(usage={'a':dict(tokens=60000,estimated_cost_usd=12)})
    assert GraphRunner.model_pass_binding(agent,None,workflow,run,enforce_usage_budgets=False)['limits']['max_tokens']==20000
    assert GraphRunner.model_pass_binding(agent,None,workflow,run)['limits']['max_tokens']==0
