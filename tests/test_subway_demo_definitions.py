"""Example assumptions remain separate from source evidence and execution grants."""
from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path

import pytest

from workflow_api.business_compiler import canonical
from workflow_api.business_planning import retrieve
from workflow_api.subway_demo_definitions import selected, SCOPE
from workflow_api.subway_queries import bounded_discovery
from tests.test_subway_intelligence import engine, installed, subway, selection, overview, execute

V = json.loads((Path(__file__).resolve().parents[1] / 'ontology/subway/business-ontology-v4.json').read_text())
PREFIX = 'Use Subway demo definitions v1. '


def test_large_discovery_keeps_all_sources_and_requested_field_within_bound():
    fields = [dict(field_id='f' + str(i), name='unrelated_' + str(i) + '_' + 'x' * 100, types=['string']) for i in range(200)]
    requested = dict(field_id='rare', name='electricityConsumption', types=['number'])
    fields.append(requested)
    original = dict(sources=[dict(dataset_id='d' + str(i), fields=deepcopy(fields)) for i in range(12)], relationships=[dict(relationship_id='declared')])
    view = bounded_discovery(original, 'Show electricityConsumption', max_bytes=20000)
    assert len(canonical(view).encode()) <= 20000
    assert len(view['sources']) == 12
    assert view['relationships'] == original['relationships']
    assert all(requested in s['fields'] and s['field_count'] == 201 for s in view['sources'])
    assert all(s['returned_field_count'] == len(s['fields']) < s['field_count'] for s in view['sources'])
    assert 'metadata only' in view['metadata_coverage']
    assert len(original['sources'][0]['fields']) == 201


def test_profile_requires_explicit_selection_and_exact_owned_snapshot():
    profile = selected(SCOPE, V, PREFIX + 'Summarize spending.')
    assert profile['source_basis'] == 'user_requested_generated_example'
    assert profile['authority'] == 'analytical_assumptions_only'
    stamp = profile.pop('sha256')
    assert stamp == sha256(canonical(profile).encode()).hexdigest()
    assert selected(SCOPE, V, 'Summarize spending.') is None
    assert selected(SCOPE, V, 'Do not use Subway demo definitions v1.') is None
    assert selected(SCOPE, V, 'Explain the phrase "Use Subway demo definitions v1".') is None
    assert selected(SCOPE, V, 'Use Subway demo definitions v10.') is None
    assert selected(('client-simpsons', 'simpsons-client'), V, PREFIX) is None
    assert selected(('client-subway', 'another-owner'), V, PREFIX) is None
    changed = deepcopy(V)
    changed['revision'] += 1
    assert selected(SCOPE, changed, PREFIX) is None
    changed['version_id'] = 'historical-version'
    assert selected(SCOPE, changed, PREFIX) is None


def test_assumptions_are_separate_from_cited_ontology_and_source_records(subway):
    f = subway
    objective = PREFIX + 'Summarize purchase order spending.'
    original = canonical(f.q.version)
    view = retrieve(f.service.store, f.auth, objective, V['version_id'])
    assert view['analytical_assumptions']['profile_id'] == 'subway-demo-definitions-v1'
    assert view['definition_sha256'] == sha256(canonical(V).encode()).hexdigest()
    assert all('demo-definitions' not in r['ref'] for r in view['references'])
    assert canonical(f.q.version) == original
    assert 'analytical_assumptions' not in retrieve(f.service.store, f.auth, 'Purchase order spending', V['version_id'])
    assert 'analytical_assumptions' not in f.q.discovery(f.auth)
    assert f.q.discovery(f.auth, objective)['analytical_assumptions'] == view['analytical_assumptions']
    foreign = deepcopy(f.auth)
    foreign['subject']['workspace_id'] = 'client-simpsons'
    from workflow_api.service import ApiFailure
    with pytest.raises(ApiFailure):
        f.q.discovery(foreign, objective)


def test_selected_assumptions_are_persisted_and_reports_keep_disclosure(subway):
    f = subway
    objective = PREFIX + 'Count purchase orders. No external actions.'
    s = selection(f.q, ['finance.purchaseorders'])
    result = overview(f, objective, s)
    assert result['state'] == 'prepared'
    doc, workflow, run = execute(f, result)
    profile = workflow['metadata']['action_binding_context']['validated_context']['business_knowledge']['analytical_assumptions']
    assert profile['profile_id'] == 'subway-demo-definitions-v1'
    assert profile['sha256'] == f.q.discovery(f.auth, objective)['analytical_assumptions']['sha256']
    report = next(a for a in doc['action_plan']['actions'] if a['capability_id'] == 'content.prepare')
    assert profile['report_label'] in report['instructions']
    assert f.model_inputs[0]['context']['business_knowledge']['analytical_assumptions'] == profile
    assert run['action_instances']['read']['output']['rows'] == [{'records': 100}]
    assert not any(r.get('kind') == 'policy' for r in workflow['metadata']['action_binding_context']['validated_context']['business_knowledge']['references'])
