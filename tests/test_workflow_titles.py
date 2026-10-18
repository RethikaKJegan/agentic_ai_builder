import json
from copy import deepcopy
import pytest
from workflow_api.workflow_titles import rename
from workflow_api.service import ApiFailure


@pytest.fixture
def case():
    from tests.test_workflow_api import WorkflowApiTests as _Fixture
    value=_Fixture(methodName='test_hierarchy_semantics_fail_validation_until_review');value.setUp()
    try:
        value.workflow['status']='published'
        with value.service.store.transaction() as db:value.service.store.put(db,'local-workspace',value.workflow)
        yield value
    finally:value.tearDown()


def post(case,name,expected=None):
    return case.client.post('/workflows/'+case.workflow['workflow_id']+'/rename',json={'name':name,'expected_name':expected or case.workflow['name']})


def test_rename_persists_display_only_and_overview_and_editor_agree(case):
    before=json.dumps(case.workflow,sort_keys=True)
    response=post(case,'  Purchasing priorities  ')
    assert response.status_code==200,response.text
    assert response.json()['data']['name']=='Purchasing priorities'
    for path in ['/workflows','/workflows/'+case.workflow['workflow_id'],'/workflow-overview']:
        data=case.client.get(path).json()['data']
        title=data['workflow']['name'] if 'workflow' in data else data['items'][0]['name']
        assert title=='Purchasing priorities'
    with case.service.store.transaction(write=False) as db:
        stored=case.service.store.get(db,'local-workspace',case.workflow['workflow_id'])
        assert json.dumps(stored,sort_keys=True)==before
        assert db.execute('SELECT COUNT(*) FROM revisions').fetchone()[0]==1
    assert post(case,'Purchasing priorities').status_code==200
    assert post(case,'Different name').status_code==409


@pytest.mark.parametrize('name',['','   ','x'*201,'Bad\nname'])
def test_invalid_rename_does_not_change_title(case,name):
    assert post(case,name).status_code==400


def test_rename_enforces_workspace_permissions_and_deleted_boundary(case):
    viewer=case.session(['viewer'])
    assert viewer.post('/workflows/'+case.workflow['workflow_id']+'/rename',json={'name':'No','expected_name':case.workflow['name']}).status_code==403
    auth=deepcopy(case.client.get('/session').json()['data']['auth']);auth['subject']['workspace_id']='other'
    with pytest.raises(ApiFailure) as failure:rename(case.service,auth,case.workflow['workflow_id'],{'name':'No','expected_name':case.workflow['name']})
    assert failure.value.status==404
    with case.service.store.transaction() as db:db.execute('INSERT INTO lifecycle_tombstones VALUES (?,?,?,?)',('local-workspace',case.workflow['workflow_id'],'now','complete'))
    assert post(case,'No').status_code==404
    viewer.close()
