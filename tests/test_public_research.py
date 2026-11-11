from types import SimpleNamespace
from copy import deepcopy
import time
import pytest
from runtime.supplier_search import SEARCH,PAGE,SupplierSearchConnector
from runtime.service import RuntimeFailure
from workflow_api.public_research import PublicResearch,enabled,extend_registry,install
from workflow_api.live_providers import registry_configuration


@pytest.mark.parametrize('client',['simpsons','subway','another-client'])
def test_public_research_is_explicit_and_uses_existing_bounded_definitions(client):
    env={'BUILDER_CLIENT_ID':client}
    assert not enabled(env)
    assert not {'supplier_web_search','supplier_read_page'} & {t['definition']['tool_id'] for t in registry_configuration(env)['tools']}
    env['BUILDER_CLIENT_WEB_ENABLED']='1'
    config=registry_configuration(env)
    assert {'supplier_web_search','supplier_read_page'} <= {t['definition']['tool_id'] for t in config['tools']}
    assert 'ddgs' in config['policy']['approved_providers']
    service=SimpleNamespace(runtime_runner=SimpleNamespace(connectors={}))
    install(service)
    assert all(isinstance(c,SupplierSearchConnector) and not c.external_write for c in service.runtime_runner.connectors.values())
    registered={t['definition']['tool_id']:t['definition'] for t in config['tools']}
    for template in (SEARCH,PAGE):
        actual=registered[template['tool_id']]
        assert actual['availability']=='enabled'
        assert actual['input_schema']==template['input_schema']
        assert actual['output_schema']==template['output_schema']
        assert actual['authentication']=={'mode':'none','credential_reference_required':False,'scopes':[]}
        assert service.runtime_runner.connectors[template['tool_id']].definition==actual
        assert template['availability']=='needs_configuration'
        actual['input_schema']['description']='Mutation in one tenant'
        other=registry_configuration(env)
        assert all('description' not in t['definition']['input_schema'] for t in other['tools'])
    with pytest.raises(ValueError):enabled({'BUILDER_CLIENT_WEB_ENABLED':'yes'})


@pytest.mark.parametrize('query',['Complaint A-2025-9-070 guidance','A 2025 9 070 engine','contact private@example.test','A%2D2025%2D9%2D070','contact private%40example.test'])
def test_public_research_rejects_private_identifiers_before_network(query,monkeypatch):
    service=SimpleNamespace(business_preparation=SimpleNamespace(checked=lambda *args:{'inputs':{'identifiers':{'complaint_id':'A-2025-9-070'}}}))
    connector=PublicResearch(SEARCH,service).bind_context({'metadata':{'business_preparation':{'preflight_id':'p'}}},{},{},{})
    calls=[];monkeypatch.setattr(SupplierSearchConnector,'execute',lambda *args:calls.append(args))
    with pytest.raises(RuntimeFailure) as error:connector.execute({}, {'query':query},'ref',time.monotonic()+10)
    assert error.value.code=='PUBLIC_QUERY_PRIVATE_DATA' and not calls


def test_public_research_keeps_bound_privacy_context_isolated(monkeypatch):
    parent=PublicResearch(SEARCH,SimpleNamespace())
    bound=parent.bind_context({'metadata':{'action_binding_context':{'user_values':{'complaint_id':'PRIVATE123'}}}},{},{},{})
    assert not parent.private_identifiers
    monkeypatch.setattr(SupplierSearchConnector,'execute',lambda *args:{'results':[]})
    assert bound.execute({}, {'query':'manufacturer engine maintenance manual'},'ref',time.monotonic()+10)=={'results':[]}


def test_public_research_blocks_serial_observed_in_pinned_records(monkeypatch):
    doc={'inputs':{'identifiers':{'complaint_id':'C123'}},'available_evidence':{'complaints':{'records':[{'values':{'mapping:ticket_serial':{'state':'value','value':'PRIVATE-ENGINE-789'}}}]}}}
    service=SimpleNamespace(business_preparation=SimpleNamespace(checked=lambda *args:doc))
    bound=PublicResearch(SEARCH,service).bind_context({'metadata':{'business_preparation':{'preflight_id':'p'}}},{},{},{})
    calls=[];monkeypatch.setattr(SupplierSearchConnector,'execute',lambda *args:calls.append(args))
    with pytest.raises(RuntimeFailure):bound.execute({}, {'query':'PRIVATE ENGINE 789 maintenance'},'ref',time.monotonic()+10)
    assert not calls


def test_content_and_private_query_failures_have_actionable_classification():
    from runtime.recovery import classify
    assert classify('ACTION_CONTENT_UNVERIFIED')['category']=='invalid_model_output'
    assert classify('PUBLIC_QUERY_PRIVATE_DATA')['category']=='missing_evidence'
