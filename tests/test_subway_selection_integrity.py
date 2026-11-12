"""Metadata consistency never substitutes for current source authorization."""
from copy import deepcopy
import json

import pytest
from jsonschema import Draft202012Validator

from tests.test_subway_intelligence import engine, installed, subway, selection, route, execute
from tests.test_subway_full_queries import field, plan
from workflow_api.service import ApiFailure
from workflow_api.subway_queries import SELECTION, selection_schema, schema_identity_budget
from workflow_api.overview_automation import ROUTE, OverviewAutomation


def test_exact_field_owner_is_added_before_strict_catalog_validation(subway):
    f = subway
    company = field(f.q, 'finance.companies', 'name')
    value = selection(f.q, ['finance.purchaseorders'], [company])
    original = deepcopy(value)
    with pytest.raises(ApiFailure) as caught:
        f.q.catalog(f.auth, 'Compare orders by company', value)
    assert caught.value.code == 'SUBWAY_QUERY_DENIED'
    normalized = f.q.selection(f.auth, value)
    view = f.q.catalog(f.auth, 'Compare orders by company', normalized)
    assert {d['label'] for d in view['sources']} == {'finance.purchaseorders', 'finance.companies'}
    assert view['relationships'] == []  # Metadata ownership does not invent a join.
    assert value == original
    assert f.q.selection(f.auth, normalized) == normalized


def test_selected_relationship_adds_only_its_exact_owned_endpoints(subway):
    f = subway
    catalog = f.q.catalog(f.auth)
    po = next(d['dataset_id'] for d in catalog['datasets'].values() if d['label'] == 'finance.purchaseorders')
    companies = next(d['dataset_id'] for d in catalog['datasets'].values() if d['label'] == 'finance.companies')
    edge = next(r for r in catalog['relationships'].values() if r['source_dataset_id'] == po and r['target_dataset_id'] == companies)
    value = selection(f.q, ['finance.purchaseorders'], relationships=[edge['relationship_id']])
    normalized = f.q.selection(f.auth, value)
    assert set(normalized['dataset_ids']) == {po, companies}
    assert normalized['relationship_ids'] == [edge['relationship_id']]
    assert len(f.q.catalog(f.auth, 'Compare linked orders', normalized)['relationships']) == 1


@pytest.mark.parametrize('key,bad', [('dataset_ids', 'foreign_dataset'), ('field_ids', 'foreign_field'), ('field_ids', 'totalAmount'), ('relationship_ids', 'invented_join')])
def test_unknown_names_and_foreign_identities_remain_denied(subway, key, bad):
    f = subway
    value = selection(f.q, ['finance.purchaseorders'])
    value[key].append(bad)
    with pytest.raises(ApiFailure):
        f.q.selection(f.auth, value)


def test_owner_closure_cannot_exceed_source_limit_or_cross_tenant(subway):
    f = subway
    sources = [d for d in f.q.catalog(f.auth)['datasets'].values() if d['fields']][:5]
    value = dict(dataset_ids=[sources[0]['dataset_id']], field_ids=[d['fields'][0]['field_id'] for d in sources], relationship_ids=[], measure_basis='Bounded test metadata.', clarification='')
    with pytest.raises(ApiFailure) as caught:
        f.q.selection(f.auth, value)
    assert caught.value.code == 'SUBWAY_SELECTION_INVALID'
    foreign = deepcopy(f.auth)
    foreign['subject']['workspace_id'] = 'client-simpsons'
    with pytest.raises(ApiFailure):
        f.q.selection(foreign, selection(f.q, ['finance.purchaseorders']))


def test_identifier_schema_is_bounded_and_rejects_labels():
    fields = [dict(field_id='f' + str(i) + 'x' * 80, name='amount' + str(i), types=['number']) for i in range(2000)]
    discovery = dict(sources=[dict(dataset_id='owned', fields=fields)], relationships=[])
    base = deepcopy(ROUTE)
    base['properties']['subway_selection'] = deepcopy(SELECTION)
    budget, chars = schema_identity_budget(base)
    schema = selection_schema(discovery, 'Amount', enum_budget=budget, string_budget=chars)
    base['properties']['subway_selection'] = schema
    assert min(schema_identity_budget(base)) >= 0
    items = schema['properties']['field_ids']['items']
    choices = [v for part in items['anyOf'] for v in part['enum']]
    assert choices and all(len(part['enum']) <= 200 for part in items['anyOf'])
    validator = Draft202012Validator(schema)
    value = dict(dataset_ids=['owned'], field_ids=[choices[0]], relationship_ids=[], measure_basis='Explicit measure.', clarification='',business_resolution=dict(status='ready',question='',notes=''))
    assert validator.is_valid(value)
    assert not validator.is_valid(dict(value, field_ids=['amount']))
    assert not validator.is_valid(dict(value, dataset_ids=['foreign']))
    assert validator.is_valid(dict(value, field_ids=[]))


def test_existing_model_transport_and_runtime_use_bounded_dataset_metadata(subway):
    import httpx
    from openai import OpenAI
    from planner.provider import OpenAIStructuredOutputProvider
    f = subway
    company = field(f.q, 'finance.companies', 'name')
    chosen = selection(f.q, ['finance.purchaseorders','finance.companies'])
    chosen['metadata_mode']='datasets'
    f.query = plan(f.q)
    calls = []

    def respond(request):
        body = json.loads(request.content)
        name = body['text']['format']['name']
        calls.append(name)
        context = json.loads(body['input'][1]['content'])
        if name == 'overview_intent_v1':
            output = dict(route({**chosen,'percentage_basis':'none','filter_branches':[],'business_resolution':dict(status='ready',question='',notes='Explicit count measure.')}), event_selection=None, recipient_mode='none')
            assert Draft202012Validator(body['text']['format']['schema']).is_valid(output)
        else:
            output = f.make_proposal(context['objective'], context)
        return httpx.Response(200, json=dict(id='resp_fixture', object='response', created_at=1, status='completed', model='offline-test-model',
            output=[dict(id='msg_fixture', type='message', role='assistant', status='completed', content=[dict(type='output_text', text=json.dumps(output), annotations=[])])]))

    with httpx.Client(transport=httpx.MockTransport(respond)) as transport:
        f.service.planner.provider = OpenAIStructuredOutputProvider(client=OpenAI(api_key='isolated-no-network-key', http_client=transport, max_retries=0), model='offline-test-model')
        f.service.overview_automation = OverviewAutomation(f.service, f.env)
        result = f.service.overview_automation.handle(f.auth, dict(objective='Count purchase orders and review the company name metadata. No external actions.', request_key='owned_selection_mismatch'))
        _, workflow, run = execute(f, result)
    assert calls == ['overview_intent_v1', 'connected_action_proposal']
    assert run['action_instances']['read']['output']['rows'] == [{'records': 100}]
    assert run['action_instances']['read']['output']['join_checks'] == []
    assert {u['concept_id'] for u in run['action_instances']['read']['ontology_usage']} == {'procurement:finance_purchaseorders'}
    assert len(workflow['metadata']['action_binding_context']['validated_context']['subway_query_catalog']['sources']) == 2
