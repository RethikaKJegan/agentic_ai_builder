"""Whole-envelope bounds preserve knowledge, accounts and metadata identities."""
from copy import deepcopy

import pytest

from tests.test_subway_intelligence import engine, installed, subway, selection, route
from workflow_api.business_knowledge_model import canonical
from workflow_api.overview_automation import OverviewAutomation, MAX_ROUTING_CONTEXT_BYTES
from workflow_api.subway_queries import bounded_discovery
from tests.test_google_connections import setup as google_setup, connect
from workflow_api.google_connections import GoogleConnections
from workflow_api.google_tools import GoogleTools


@pytest.mark.parametrize('padding_bytes,objective', [
    (10000, 'Review purchase orders and email me the largest orders and vendors by value.'),
    (50000, 'Rank vendors by purchasing value, keeping currencies separate, and email me.'),
    (90000, 'Summarize invoices and procurement evidence for an emailed management review.'),
])
def test_complete_context_budget_preserves_siblings_and_every_source(subway, google_setup, monkeypatch, padding_bytes, objective):
    f = subway
    _, env = google_setup
    manager = GoogleConnections(f.service.store, env)
    account = connect(manager, actor=f.auth, email='reviewer@example.invalid')
    f.service.google_tools = GoogleTools(manager, f.service)
    selected = selection(f.q, ['finance.purchaseorders'])
    index = f.q.discovery(f.auth, objective)
    # Grow metadata independently of the business wording and transport fixture.
    index['sources'][0]['fields'].extend([
        dict(field_id='synthetic_extra_' + str(i), name='additional_' + str(i) + '_é' * 50, types=['string'])
        for i in range(1800)
    ])
    expected_sources = {s['dataset_id'] for s in index['sources']}
    seen_budgets = []

    def discovery(auth, goal='', *, max_bytes=180000):
        assert auth == f.auth and goal == objective
        seen_budgets.append(max_bytes)
        return bounded_discovery(index, goal, max_bytes=min(max_bytes, 180000))

    monkeypatch.setattr(f.q, 'discovery', discovery)
    import workflow_api.business_planning as planning
    original = planning.retrieve

    def knowledge(*args, **kwargs):
        value = original(*args, **kwargs)
        value['synthetic_context_padding'] = 'λ' * (padding_bytes // 2)
        return value

    monkeypatch.setattr(planning, 'retrieve', knowledge)
    events = [dict(provider='fixture', source_id='owned', description='é' * 1000)]
    monkeypatch.setattr('workflow_api.workflow_events.sources', lambda *_: deepcopy(events))
    captured = []

    def interpret(goal, context):
        captured.append(context)
        assert len(canonical(context).encode()) <= MAX_ROUTING_CONTEXT_BYTES
        assert context['selected_google_account'] == account['connection_id']
        assert context['resolved_inputs']['user_values']['recipient'] == 'reviewer@example.invalid'
        assert context['event_sources'] == events
        assert context['knowledge']['synthetic_context_padding'] == 'λ' * (padding_bytes // 2)
        assert {s['dataset_id'] for s in context['subway_discovery']['sources']} == expected_sources
        assert context['subway_discovery']['relationships'] == index['relationships']
        unbudgeted = dict(context, subway_discovery=bounded_discovery(index, objective))
        if padding_bytes >= 50000:
            assert len(canonical(unbudgeted).encode()) > MAX_ROUTING_CONTEXT_BYTES
        return route(selected, side_effects=['email_send'], recipient_mode='selected_account')

    router = OverviewAutomation(f.service, f.env, interpreter=interpret)
    prepared = router.prepare_intent(f.auth, dict(objective=objective, request_key='budget_case',
        google_connection_id=account['connection_id'], user_values=dict(recipient='reviewer@example.invalid')))
    assert captured and seen_budgets
    assert prepared['result']['state'] == 'prepared' and prepared['intent'] is not None
    assert prepared['intent']['route']['side_effects'] == ['email_send']


def test_caller_cannot_increase_discovery_component_limit(subway):
    f = subway
    view = f.q.discovery(f.auth, 'Count purchase orders', max_bytes=1000000)
    assert len(canonical(view).encode()) <= 180000
