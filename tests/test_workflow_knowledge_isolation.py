"""Direct HTTP knowledge reads across three authenticated scopes; no engine changes."""
from copy import deepcopy
import json
from fastapi.testclient import TestClient
from workflow_api.main import create_app


def test_three_tenant_version_concept_mapping_and_parameter_isolation(tmp_path):
    app=create_app(database=tmp_path/'isolation.sqlite',dev_auth=True,start_workers=False,planning_worker_enabled=False)
    client=TestClient(app)
    assert client.get('/business-ontology/v1/versions/simpsons_v1/knowledge').status_code==401
    client.get('/session');client.cookies.set('builder_dev_session',client.cookies.get('builder_dev_session'),path='/')
    original=deepcopy(app.state.workflow_auth)
    tenants={'simpsons':'Complaint','subway':'Purchase order','third':'Laboratory batch'}
    with app.state.workflow_service.store.transaction() as db:
        for tenant,label in tenants.items():
            doc=dict(version_id=tenant+'_v1',revision=1,kind='foundation',concepts=[dict(id='shared:entity',label=label,parent_id=None)],relationships=[],rules=[],knowledge=dict(source_mappings=[dict(id='mapping:shared',concept_id='shared:entity',collection=tenant+'_private')]))
            db.execute('INSERT INTO business_ontology_versions VALUES (?,?,?,?)',(tenant,'same-owner',doc['version_id'],json.dumps(doc)))
    for tenant,label in tenants.items():
        app.state.workflow_auth['subject']={'workspace_id':tenant,'subject_id':'same-owner'}
        own=f'/business-ontology/v1/versions/{tenant}_v1/knowledge'
        response=client.get(own);assert response.status_code==200,response.text
        assert response.json()['data']['concepts'][0]['label']==label
        assert response.json()['data']['knowledge']['source_mappings'][0]['collection']==tenant+'_private'
        assert client.get(own+'/concepts/shared:entity').status_code==200
        for foreign in set(tenants)-{tenant}:
            for endpoint in [f'/business-ontology/v1/versions/{foreign}_v1',f'/business-ontology/v1/versions/{foreign}_v1/knowledge',f'/business-ontology/v1/versions/{foreign}_v1/knowledge/concepts/shared:entity']:
                denied=client.get(endpoint);assert denied.status_code==404
                assert foreign+'_private' not in denied.text and tenants[foreign] not in denied.text
            tampered=client.get(own+'?workspace_id='+foreign)
            assert foreign+'_private' not in tampered.text
        app.state.workflow_auth['subject']['subject_id']='different-owner'
        assert client.get(own).status_code==404
    app.state.workflow_auth=original
