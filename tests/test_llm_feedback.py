from copy import deepcopy
from types import SimpleNamespace
from unittest.mock import patch
import pytest
from shared.llm_feedback import correct_once, feedback
from runtime.service import RuntimeFailure
from planner.errors import PlannerFailure
from workflow_api.live_providers import LivePlannerProvider
from tests.test_live_providers import draft


@pytest.mark.parametrize('code', ['APPROVAL_REQUIRED','BUDGET_EXHAUSTED','UNKNOWN_INVOCATION_RESULT',
                                  'EFFECT_REFERENCE_MISMATCH','MODEL_INVOCATION_FAILED'])
def test_non_output_failures_never_trigger_model_correction(code):
    calls=[]
    def invoke(item):
        calls.append(item);raise RuntimeFailure(code,'Do not echo arbitrary content.')
    with pytest.raises(RuntimeFailure) as err:
        correct_once(invoke,lambda item:pytest.fail('Must not retry this failure'))
    assert err.value.code==code and len(calls)==1


def test_planner_feedback_contains_specific_rules_and_safe_prior_draft():
    provider=LivePlannerProvider('gpt-5.6-luna',['owner@example.com'],SimpleNamespace())
    good=draft()
    for a in good['agents']:a['model']['model_id']='gpt-5.6-luna'
    bad=deepcopy(good)
    bad['metadata']['email_recipient_policy']={'mode':'own_inbox'}
    bad['execution_policy']['limits'].pop('max_estimated_cost_usd',None)
    seen=[]
    def generate(objective,context):
        seen.append(deepcopy(context));return deepcopy(bad if len(seen)==1 else good)
    with patch.object(provider.provider,'generate',side_effect=generate):
        assert provider.generate('Send a report to my own inbox.',{})==good
    assert len(seen)==2
    errors={e['code']:e for e in seen[1]['validation_feedback']}
    assert 'omit this policy' in errors['EMAIL_RECIPIENT_POLICY_INVALID']['hint']
    assert 'sum' in errors['WORKFLOW_COST_BUDGET_REQUIRED']['hint']
    assert seen[1]['previous_draft']['metadata']['email_recipient_policy']=={'mode':'own_inbox'}


def test_planner_json_failure_gets_one_correction():
    provider=LivePlannerProvider('gpt-5.6-luna',['owner@example.com'],SimpleNamespace())
    good=draft()
    for a in good['agents']:a['model']['model_id']='gpt-5.6-luna'
    with patch.object(provider.provider,'generate',side_effect=[PlannerFailure('PLANNER_OUTPUT_INVALID_JSON','Invalid.'),good]) as generate:
        assert provider.generate('Generate a report.',{})==good
    assert generate.call_count==2
    assert generate.call_args.args[1]['validation_feedback'][0]['code']=='PLANNER_OUTPUT_INVALID_JSON'
