"""Business-grounded workflow creation; fixture provider, no external calls."""
from copy import deepcopy
import json

import pytest
from planner import PlannerService
from planner.provider import RuleBasedStructuredOutputProvider
from tests.test_business_ontology import foundation, auth
from tests.test_business_generation import generation
from tests.test_business_reference import reference
from workflow_api.business_planning import retrieve, bind
from workflow_api.service import WorkflowService


@pytest.fixture
def populated(reference):
    f, jobs, importer, current = reference
    importer.apply(current, dict(expected_revision=1, request_key='planning_reference_001'))
    return f, current


def planner_auth(current):
    return {**current, 'roles': ['admin'], 'permissions': list(set(current['permissions']) | {'workflow.plan', 'workflow.view', 'workflow.edit'})}


class GroundedProvider(RuleBasedStructuredOutputProvider):
    def __init__(self):
        self.contexts = []
    def generate(self, objective, context):
        self.contexts.append(deepcopy(context))
        w = super().generate(objective, context)
        view = context.get('business_ontology_retrieval', {})
        if view.get('state') == 'matched':
            node = next(n for n in w['nodes'] if n['kind'] == 'agent')
            ref = next((r for r in view['references'] if r['kind'] == 'rule'), view['references'][0])
            agent = next(a for a in w['agents'] if a['agent_id'] == node['agent_id'])
            agent['instructions'] += '\nUse this retrieved business definition: ' + ref['definition']
            w['metadata']['business_ontology_step_bindings'] = [dict(node_id=node['node_id'], refs=[ref['ref']], application='Use the retrieved definition to qualify this analysis and its evidence requirements.')]
        w['metadata']['business_ontology'] = {'state': 'FORGED', 'version_id': 'invented'}
        return w


def test_read_only_retrieval_scoping_relevance_and_source_integrity(populated):
    f, current = populated
    before = f.get(current)
    view = retrieve(f.store, current, 'Check engine warranty eligibility for a complaint')
    assert view['state'] == 'matched'
    assert 'warranty' in view['matched_modules']
    assert view['version_id'] == before['current_version_id']
    assert len(view['references']) <= 36
    snapshot = f.version(current, view['version_id'])
    sources = {s['source_id']: s for s in snapshot['sources']}
    for ref in view['references']:
        for e in ref['evidence']:
            assert e['source_sha256'] == sources[e['source_id']]['sha256']
            assert ' '.join(e['quote'].split()) in ' '.join(sources[e['source_id']]['text'].split())
    assert f.get(current) == before
    assert retrieve(f.store, auth(owner='bob'), 'engine warranty')['state'] == 'not_configured'
    assert retrieve(f.store, auth(workspace='two'), 'engine warranty')['references'] == []
    assert retrieve(f.store, current, 'Translate French poetry into Spanish')['state'] == 'no_match'
    assert retrieve(f.store, {**current, 'scopes': []}, 'warranty')['state'] == 'not_authorized'


def test_automatic_workflow_planning_replaces_client_evidence_and_retries_pin_it(populated):
    f, current = populated
    provider = GroundedProvider()
    service = WorkflowService(f.store, PlannerService(provider))
    authority = planner_auth(current)
    request = dict(operation='plan_workflow', request_id='req_business_plan', idempotency_key='business_plan_001',
        payload=dict(objective='Check warranty eligibility for engine complaints', context=dict(business_ontology_retrieval={'state': 'matched', 'references': [{'ref': 'forged'}]})))
    response = service.handle(request, authority)
    assert response['status'] == 200, response
    w = response['data']['workflow']
    trace = w['metadata']['business_ontology']
    assert trace['state'] == 'incorporated'
    assert trace['version_id'] == f.get(current)['current_version_id']
    assert trace['contributions'][0]['node_id'] in {n['node_id'] for n in w['nodes']}
    assert all(r['ref'] != 'forged' for r in trace['references'])
    assert provider.contexts[0]['business_ontology_retrieval']['state'] == 'matched'
    # The existing idempotency boundary pins both evidence and provider output.
    with f.store.transaction() as db:
        doc = f.version(current, trace['version_id'])
        doc['revision'] += 1
        doc['version_id'] = 'bov_later_test'
        db.execute('INSERT INTO business_ontology_versions VALUES (?,?,?,?)', (current['subject']['workspace_id'], current['subject']['subject_id'], doc['version_id'], json.dumps(doc)))
    retry = service.handle(request, authority)
    assert retry['data']['workflow'] == w
    assert len(provider.contexts) == 1
    fresh = service.handle({**request, 'idempotency_key': 'business_plan_002'}, authority)
    assert fresh['status'] == 200, fresh
    assert fresh['data']['workflow']['metadata']['business_ontology']['version_id'] == 'bov_later_test'
    assert fresh['data']['workflow']['workflow_id'] != w['workflow_id']
    # Existing save/get transport retains the complete trace without source DB reads.
    saved = service.handle(dict(operation='save_workflow_version', request_id='req_save_business',
        idempotency_key='business_save_001', payload=dict(workflow_id=w['workflow_id'], workflow_version=1,
            workflow=w, base_version=0)), authority)
    assert saved['status'] == 200, saved
    read = service.handle(dict(operation='get_workflow', request_id='req_get_business',
        payload=dict(workflow_id=w['workflow_id'])), authority)
    assert read['status'] == 200
    assert read['data']['workflow']['metadata']['business_ontology'] == trace


def test_no_match_does_not_claim_incorporation(populated):
    f, current = populated
    context = {'business_ontology_retrieval': retrieve(f.store, current, 'Translate French poetry into Spanish')}
    w = GroundedProvider().generate('Translate French poetry into Spanish', context)
    bind(w, context)
    assert w['metadata']['business_ontology']['state'] == 'no_match'
    assert w['metadata']['business_ontology']['contributions'] == []


@pytest.mark.parametrize('mutation', [
    lambda w: w['metadata'].pop('business_ontology_step_bindings'),
    lambda w: w['metadata']['business_ontology_step_bindings'][0].update(refs=['concept:invented']),
    lambda w: w['metadata']['business_ontology_step_bindings'][0].update(node_id='absent'),
    lambda w: w['metadata']['business_ontology_step_bindings'][0].update(node_id=w['nodes'][0]['node_id']),
    lambda w: w['metadata']['business_ontology_step_bindings'][0].update(application='used'),
])
def test_unsupported_or_cosmetic_binding_is_rejected(populated, mutation):
    f, current = populated
    context = {'business_ontology_retrieval': retrieve(f.store, current, 'Explain engine warranty eligibility')}
    w = GroundedProvider().generate('Explain engine warranty eligibility', context)
    mutation(w)
    with pytest.raises(Exception) as exc: bind(w, context)
    assert exc.value.code == 'BUSINESS_ONTOLOGY_BINDING_INVALID'


def test_corrupt_source_never_enters_provider_context(populated):
    f, current = populated
    view = f.get(current)
    doc = f.version(current, view['current_version_id'])
    doc['sources'][0]['text'] += ' altered'
    with f.store.transaction() as db:
        db.execute('UPDATE business_ontology_versions SET document=? WHERE version_id=?', (json.dumps(doc), doc['version_id']))
    with pytest.raises(Exception): retrieve(f.store, current, 'engine warranty')


def test_trace_protected_against_draft_forgery_and_foreign_owner(populated):
    from workflow_api.business_planning import record, verify_saved
    f, current = populated
    context = {'business_ontology_retrieval': retrieve(f.store, current, 'engine warranty')}
    w = GroundedProvider().generate('engine warranty', context)
    bind(w, context)
    record(f.store, current, w)
    with f.store.transaction(write=False) as db:
        verify_saved(db, current, w)
        forged = deepcopy(w)
        forged['metadata']['business_ontology']['contributions'][0]['application'] = 'Invented claim that this policy is approved.'
        with pytest.raises(Exception) as exc: verify_saved(db, current, forged)
        assert exc.value.code == 'BUSINESS_ONTOLOGY_TRACE_INVALID'
        with pytest.raises(Exception): verify_saved(db, auth(owner='bob'), w)


def test_latest_policy_revisions_are_retrieved_with_code_basis(populated):
    from workflow_api.business_policies import BusinessPolicies
    f, current = populated
    # Uses the supplied reference code, never company records.
    policies = BusinessPolicies(f, None, lambda *args: current)
    policies.import_implementation(current, {})
    view = retrieve(f.store, current, 'CNH warranty eligibility')
    refs = [r for r in view['references'] if r['kind'] == 'policy']
    assert len(refs) == 4
    assert all(r['interpretation_basis'] == 'descriptive_implementation' for r in refs)
    assert all(r['clauses']['exclusions']['value'] is None for r in refs)
    assert any(r['clauses']['invoice_months']['value'] == 24 and r['clauses']['sale_months']['value'] == 21 and r['clauses']['max_hours']['value'] == '2000' for r in refs)


def test_trace_matches_versioned_shared_contract(populated):
    from pathlib import Path
    from jsonschema import Draft202012Validator
    f, current = populated
    context = {'business_ontology_retrieval': retrieve(f.store, current, 'engine warranty')}
    w = GroundedProvider().generate('engine warranty', context)
    bind(w, context)
    schema = json.loads((Path(__file__).resolve().parents[1] / 'shared/contracts/data-sources/business-planning-v1.schema.json').read_text())
    Draft202012Validator.check_schema(schema)
    Draft202012Validator(schema).validate(w['metadata']['business_ontology'])


def test_openai_request_contains_real_retrieval_and_step_binding_instruction(populated):
    from types import SimpleNamespace
    from planner.provider import OpenAIStructuredOutputProvider
    f, current = populated
    context = {'business_ontology_retrieval': retrieve(f.store, current, 'engine warranty')}
    expected = GroundedProvider().generate('engine warranty', context)
    calls = []
    def create(**kwargs):
        calls.append(kwargs)
        return SimpleNamespace(output_text=json.dumps(expected))
    provider = OpenAIStructuredOutputProvider(client=SimpleNamespace(responses=SimpleNamespace(create=create)))
    result = provider.generate('engine warranty', context)
    assert result == expected
    assert len(calls) == 1
    assert json.loads(calls[0]['input'][1]['content'])['context']['business_ontology_retrieval'] == context['business_ontology_retrieval']
    assert 'business_ontology_step_bindings MUST' in calls[0]['input'][0]['content']
    assert calls[0]['store'] is False
    schema = json.loads(calls[0]['input'][1]['content'])['canonical_workflow_schema']
    assert schema['properties']['metadata']['required'] == ['business_ontology_step_bindings']
    assert schema['properties']['metadata']['properties']['business_ontology_step_bindings']['items']['properties']['refs']['items']['enum'] == [r['ref'] for r in context['business_ontology_retrieval']['references']]


def test_same_evidence_preserves_workflow_identity_despite_model_wording(populated):
    f, current = populated
    class VaryingProvider(GroundedProvider):
        def generate(self, objective, context):
            w = super().generate(objective, context)
            w['metadata']['business_ontology_step_bindings'][0]['application'] += f' Proposal {len(self.contexts)}.'
            return w
    provider = VaryingProvider()
    service = WorkflowService(f.store, PlannerService(provider))
    authority = planner_auth(current)
    req = dict(operation='plan_workflow', request_id='req_stable_business', idempotency_key='stable_business_001', payload=dict(objective='Assess engine warranty'))
    first = service.handle(req, authority)
    second = service.handle({**req, 'idempotency_key': 'stable_business_002'}, authority)
    assert first['status'] == second['status'] == 200
    assert first['data']['workflow']['workflow_id'] == second['data']['workflow']['workflow_id']
    assert first['data']['workflow']['metadata']['business_ontology']['trace_sha256'] != second['data']['workflow']['metadata']['business_ontology']['trace_sha256']


def test_live_provider_repairs_missing_links_within_existing_two_attempt_limit(populated):
    from types import SimpleNamespace
    from workflow_api.live_providers import LivePlannerProvider
    f, current = populated
    context = {'business_ontology_retrieval': retrieve(f.store, current, 'engine warranty')}
    provider = LivePlannerProvider('fixture-model', ['owner@example.test'], SimpleNamespace())
    calls = []
    def generate(objective, supplied):
        calls.append(deepcopy(supplied))
        w = GroundedProvider().generate(objective, supplied)
        for agent in w['agents']:
            agent['model'] = deepcopy(supplied['runtime_model'])
        if len(calls) == 1:
            w['metadata'].pop('business_ontology_step_bindings')
        return w
    provider.provider = SimpleNamespace(generate=generate)
    w = provider.generate('Assess engine warranty', context)
    assert len(calls) == 2
    item = next(item for item in calls[1]['validation_feedback'] if item['code'] == 'BUSINESS_ONTOLOGY_BINDING_INVALID')
    assert 'nonempty list' in item['binding_issue']
    assert item['valid_action_node_ids']
    assert item['valid_refs'] == [r['ref'] for r in context['business_ontology_retrieval']['references']]
    assert calls[0]['business_ontology_retrieval'] == calls[1]['business_ontology_retrieval']
    bind(w, context)
    assert w['metadata']['business_ontology']['state'] == 'incorporated'


def test_binding_normalization_preserves_exact_owned_reference_and_action(populated):
    from pathlib import Path
    from jsonschema import Draft202012Validator
    f,current=populated
    context={'business_ontology_retrieval':retrieve(f.store,current,'engine warranty')}
    w=GroundedProvider().generate('engine warranty',context)
    binding=w['metadata']['business_ontology_step_bindings'][0]
    node=next(n for n in w['nodes'] if n['node_id']==binding['node_id'])
    exact=binding['refs'][0]
    binding['node_id']=node['agent_id']
    binding['refs']=[next(r['id'] for r in context['business_ontology_retrieval']['references'] if r['ref']==exact)]
    bind(w,context)
    trace=w['metadata']['business_ontology']
    assert trace['contributions'][0]['node_id']==node['node_id']
    assert trace['contributions'][0]['refs']==[exact]
    assert len(trace['binding_normalizations'])==2
    schema=json.loads((Path(__file__).resolve().parents[1]/'shared/contracts/data-sources/business-planning-v1.schema.json').read_text())
    Draft202012Validator(schema).validate(trace)


def test_repeated_step_bindings_merge_without_inventing_usage(populated):
    f,current=populated
    context={'business_ontology_retrieval':retrieve(f.store,current,'engine warranty')}
    w=GroundedProvider().generate('engine warranty',context)
    b=deepcopy(w['metadata']['business_ontology_step_bindings'][0])
    b['application']='Also preserve the supporting source quotations in this assessment.'
    w['metadata']['business_ontology_step_bindings'].append(b)
    bind(w,context)
    trace=w['metadata']['business_ontology']
    assert len(trace['contributions'])==1
    assert b['application'] in trace['contributions'][0]['application']
    assert trace['binding_normalizations'][0]['reason']=='merged_same_action_node'


def test_unknown_binding_reports_precise_issue_without_relaxing_citations(populated):
    f,current=populated
    context={'business_ontology_retrieval':retrieve(f.store,current,'engine warranty')}
    w=GroundedProvider().generate('engine warranty',context)
    w['metadata']['business_ontology_step_bindings'][0]['refs']=['invented:definition']
    with pytest.raises(Exception) as exc:bind(w,context)
    assert exc.value.code=='BUSINESS_ONTOLOGY_BINDING_INVALID'
    assert exc.value.details['binding_index']==0
    assert 'not an exact retrieved ref' in exc.value.details['binding_issue']


def test_dynamic_specialist_without_actual_node_is_not_falsely_bound(populated):
    f,current=populated
    context={'business_ontology_retrieval':retrieve(f.store,current,'engine warranty')}
    w=GroundedProvider().generate('engine warranty',context)
    specialist=deepcopy(w['agents'][0]);specialist['agent_id']='specialist_without_node'
    w['agents'].append(specialist)
    w['metadata']['business_ontology_step_bindings'][0]['node_id']=specialist['agent_id']
    with pytest.raises(Exception) as exc:bind(w,context)
    assert 'specialist without its own graph node' in exc.value.details['binding_issue']
