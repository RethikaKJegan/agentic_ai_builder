"""Supported polling detects changes without repinning historical workflows."""
from copy import deepcopy
import pytest
from tests.test_account_knowledge import graph,composition,investigation,retrieval,knowledge,reference,generation,foundation,auth,release
from tests.test_agent_memory_recovery import setup_retail
from workflow_api.knowledge_sync import KnowledgeSyncWorker
from runtime import RuntimeFailure


def test_package_poll_creates_new_revision_and_revocation_marks_stale(graph):
    f=graph;g=f.general.account_graph;packages=setup_retail(f);packages.account_graph=g
    req=dict(package_id='retail_fixture',revision=1,capability_id='retail.read')
    first=packages.read(f.x.a,req)['account_graph_pin']
    packages.register_source(f.x.a,'inventory_fixture',lambda *_:[dict(id='stock_1',product='changed',stock=4,threshold=10)])
    worker=KnowledgeSyncWorker(f.general,lambda *_:f.x.a,clock=lambda:f.now)
    f.now+=61
    result=worker.tick();assert result['failed']==0,result
    with pytest.raises(RuntimeFailure):g.get(f.x.a,first)
    assert g.get(f.x.a,first,historical=True)['stale']
    current=packages.read(f.x.a,req)['account_graph_pin'];assert current['revision']==2
    packages.providers.clear();f.now+=61
    result=worker.tick();assert result['failed']>=1
    with pytest.raises(RuntimeFailure):g.get(f.x.a,current)
    assert g.get(f.x.a,current,historical=True)['revision']==2


def test_revoked_polling_identity_cannot_refresh_knowledge(graph):
    f=graph;f.now+=61
    worker=KnowledgeSyncWorker(f.general,lambda *_:None,clock=lambda:f.now)
    assert worker.tick()['failed']==1
    with pytest.raises(RuntimeFailure):f.general.account_graph.get(f.x.a,f.pin)


def test_unchanged_preparation_poll_preserves_pin_and_refreshes_freshness(graph):
    f=graph;worker=KnowledgeSyncWorker(f.general,lambda *_:f.x.a,clock=lambda:f.now)
    f.now+=61
    result=worker.tick();assert result=={'updated':1,'failed':0},result
    assert f.general.account_graph.get(f.x.a,f.pin)['revision']==f.pin['revision']


def test_authentication_exception_marks_stale_and_does_not_wedge_polling(graph):
    f=graph;f.now+=61
    def revoked(*args):raise RuntimeError('Revoked current identity')
    worker=KnowledgeSyncWorker(f.general,revoked,clock=lambda:f.now)
    assert worker.tick()['failed']==1
    with pytest.raises(RuntimeFailure):f.general.account_graph.get(f.x.a,f.pin)


def test_failed_old_poll_cannot_invalidate_a_concurrently_refreshed_revision(graph,monkeypatch):
    f=graph;g=f.general.account_graph;packages=setup_retail(f);packages.account_graph=g
    req=dict(package_id='retail_fixture',revision=1,capability_id='retail.read')
    original=packages.read(f.x.a,req)['account_graph_pin']
    packages.register_source(f.x.a,'inventory_fixture',lambda *_:[dict(id='stock_1',product='new',stock=4,threshold=10)])
    read=packages.read;new=[]
    def refresh_then_fail(*args):
        new.append(read(*args)['account_graph_pin'])
        raise RuntimeFailure('CONNECTOR_TIMEOUT','Controlled late polling failure')
    monkeypatch.setattr(packages,'read',refresh_then_fail)
    f.now+=61;worker=KnowledgeSyncWorker(f.general,lambda *_:f.x.a,clock=lambda:f.now)
    assert worker.tick()['failed']==1
    assert new[0]['revision']==original['revision']+1
    assert not g.get(f.x.a,new[0])['stale']
