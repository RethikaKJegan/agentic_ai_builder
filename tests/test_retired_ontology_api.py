"""Retirement of public legacy actions preserves internal compatibility/history."""
import pytest
from fastapi.testclient import TestClient
from workflow_api.main import create_app
from workflow_api.service import ApiFailure


@pytest.fixture
def retired_client(tmp_path):
    app=create_app(database=tmp_path/'retired.sqlite',dev_auth=True,start_workers=False,planning_worker_enabled=False)
    with TestClient(app) as client:
        client.get('/session');client.cookies.set('builder_dev_session',client.cookies.get('builder_dev_session'),path='/')
        yield client,app


@pytest.mark.parametrize('method,path',[
 ('get',''),('get','/metrics'),('get','/versions/old'),('get','/versions/old/export'),
 ('get','/history/old'),('post','/profile/old'),('post','/review/old'),('post','/replay/old'),
 ('post','/objects'),('post','/objects/expand'),('post','/record'),('post','/sync'),
 ('post','/templates'),('post','/publish'),('post','/select'),('post','/calibrate'),('post','/assess')])
def test_retired_actions_cannot_mutate_saved_definitions(retired_client,method,path):
    client,app=retired_client
    with app.state.workflow_service.store.transaction(write=False) as db:
        before=db.execute('SELECT document FROM ontology_records').fetchall()
    response=getattr(client,method)('/ontology/v1'+path,**({'json':{'record':{'invalid':'shape'}}} if method=='post' else {}))
    assert response.status_code==410 and response.json()['data']['error']['error_code']=='LEGACY_ONTOLOGY_RETIRED'
    with app.state.workflow_service.store.transaction(write=False) as db:
        assert db.execute('SELECT document FROM ontology_records').fetchall()==before
    assert client.get('/business-ontology/v1/sources').status_code==200


def test_new_plans_cannot_create_legacy_selections(retired_client):
    _,app=retired_client
    with pytest.raises(ApiFailure) as exc:
        app.state.database_workflows.enrich(app.state.workflow_auth,{'ontology_concepts':{'version_id':'old','concept_ids':['old']}})
    assert exc.value.code=='LEGACY_ONTOLOGY_RETIRED'
