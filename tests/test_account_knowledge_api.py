"""Graph routes use the existing session, CSRF, owner and metadata authority."""
from copy import deepcopy
from types import SimpleNamespace

from fastapi.testclient import TestClient
import pytest

from runtime import RuntimeFailure
from workflow_api.account_knowledge import AccountKnowledge
from workflow_api.main import create_app


def test_graph_routes_require_session_and_reject_caller_evidence(tmp_path):
    app=create_app(database=tmp_path/'api.sqlite',dev_auth=True,roles=['admin'],runtime_enabled=True,start_workers=False)
    service=app.state.workflow_service
    service.account_graph=AccountKnowledge(service.store,service)
    with TestClient(app) as client:
        assert client.get('/account-knowledge').status_code==401
        client.get('/session');client.cookies.set('builder_dev_session',client.cookies.get('builder_dev_session'),path='/')
        assert client.get('/account-knowledge').status_code==200
        assert client.get('/account-knowledge?workspace=other').status_code==400
        assert client.post('/account-knowledge/traverse',json={}).status_code==400
        assert client.post('/account-knowledge/refresh',headers={'origin':'https://untrusted.example'}).status_code==403
        assert client.post('/account-knowledge/refresh',json={'evidence':'forged'}).status_code==400
        assert client.post('/account-knowledge/refresh').status_code==200


def test_semantic_projection_preserves_direction_provenance_and_live_revision(tmp_path):
    from workflow_api.storage import WorkflowStore
    view=dict(stale=False,revision='current',relationships=[dict(relationship_id='r',source_dataset_id='a',target_dataset_id='b',predicate='belongs_to',status='confirmed',reversed=True,evidence_refs=['observed:foreign_key'],provenance={'record_evidence':'not_sampled'},semantic_evidence_hash='reviewed_hash')])
    semantic=SimpleNamespace(get=lambda auth:deepcopy(view))
    service=SimpleNamespace(account_semantic=semantic)
    graph=AccountKnowledge(WorkflowStore(tmp_path/'semantic.sqlite'),service)
    auth=dict(subject=dict(workspace_id='one',subject_id='owner'),decision='allow',roles=['admin'],permissions=['workflow.plan','runs.view'],scopes=[])
    pin=graph.sync_semantic(auth,semantic);doc=graph.get(auth,pin)
    edge=doc['edges'][0]
    assert edge['source']==graph.identity(('one','owner'),'dataset','b')
    assert edge['evidence']==['observed:foreign_key'] and edge['provenance']['record_evidence']=='not_sampled'
    view['revision']='changed'
    with pytest.raises(RuntimeFailure) as exc:graph.get(auth,pin)
    assert exc.value.code=='ACCOUNT_GRAPH_STALE'
    assert graph.get(auth,pin,historical=True)['revision']==pin['revision']
    metrics=graph.diagnostics()
    assert metrics['retrieval_calls']==3 and metrics['retrieval_failures']==1
    assert metrics['sync_calls']==1 and metrics['retrieval_seconds']>0
