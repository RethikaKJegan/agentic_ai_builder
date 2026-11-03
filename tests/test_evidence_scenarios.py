from copy import deepcopy
import pytest
from scripts.check_evidence_scenarios import build_scenario,evaluate_scenario,run
from workflow_api.business_evidence import evaluate


@pytest.mark.parametrize('task',['inspection','warranty','replacement','recurrence'])
@pytest.mark.parametrize('variant',['complete','incomplete','ambiguous'])
def test_explicit_isolated_scenarios(task,variant):
    doc=build_scenario(task,variant);before=deepcopy(doc);result=evaluate_scenario(doc)
    assert result['scenario_conclusion_ready']==(variant=='complete')
    assert result['scenario_only'] and result['business_conclusion'] is None
    assert doc==before
    # Production evaluation cannot consume generated fact events as verified facts.
    actual=evaluate(task,dict(doc['evidence'],events=doc['events']),doc['inputs'],doc['policies'])
    assert actual==result['live_evaluation']
    if task!='inspection':assert not actual['conclusion_ready']


@pytest.mark.parametrize('mutation',[
 lambda d:d.update(environment='live'),lambda d:d.update(provenance='source'),
 lambda d:d['events'][0].update(case_id='foreign'),
 lambda d:d['events'][0].update(at='2026-12-01T00:00:00+00:00'),
 lambda d:d['return_receipt'].update(case_id='foreign'),
 lambda d:d['return_receipt'].update(at='2026-12-01T00:00:00+00:00'),
])
def test_scenario_context_and_timeline_are_required(mutation):
    doc=build_scenario('replacement','complete');mutation(doc)
    with pytest.raises(ValueError):evaluate_scenario(doc)


def test_scenario_artifacts_are_fresh_and_private(tmp_path):
    directory=tmp_path/'isolated';summary=run(directory)
    assert summary['passed'] and len(summary['checks'])==12
    assert directory.stat().st_mode&0o777==0o700
    with pytest.raises(ValueError):run(directory)
