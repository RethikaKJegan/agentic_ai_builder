"""Actual scoped HTTP transport for reference imports and saved-only reports."""
import json
from copy import deepcopy
from unittest.mock import patch
from tests.test_business_graph import graph,build
from tests.test_business_compiler import compiled_draft
from tests.test_business_generation import generation
from tests.test_business_ontology import foundation,auth


def test_reference_and_saved_intelligence_http(tmp_path,graph):
    from fastapi.testclient import TestClient
    from workflow_api.main import create_app
    from workflow_api.business_reference import load_kit
    app=create_app(database=tmp_path/'http.sqlite',dev_auth=True,start_workers=False,planning_worker_enabled=False)
    client=TestClient(app);root='/business-ontology/v1'
    assert client.get(root+'/versions/missing/module-coverage').status_code==401
    client.get('/session');client.cookies.set('builder_dev_session',client.cookies.get('builder_dev_session'),path='/')
    kit,bundle=load_kit()
    with app.state.workflow_service.store.transaction() as db:
        for cid in bundle['required_sources'].values():
            doc=dict(connection_id=cid,name=cid,engine='mongodb',connection_status='connected',metadata_revision=1)
            db.execute('INSERT INTO data_source_connections VALUES (?,?,?,?,?)',(cid,'local-workspace','local-builder',None,json.dumps(doc)))
    state=client.post(root+'/initialize',json={'sources':bundle['required_sources']}).json()['data'];old=state['current_version_id']
    assert client.get(root+'/versions/'+old+'/module-coverage').json()['data']['missing_modules']
    body=dict(expected_revision=1,request_key='http_reference_001')
    assert client.post(root+'/reference-modules',json=body,headers={'origin':'https://untrusted.example'}).status_code==403
    assert client.post(root+'/reference-modules',content='invalid').status_code==422
    result=client.post(root+'/reference-modules',json=body)
    assert result.status_code==200 and result.headers['cache-control']=='no-store'
    version=result.json()['data']['version_id']
    assert client.post(root+'/reference-modules',json=body).json()['data']['version_id']==version
    assert client.get(root+'/versions/'+old).json()['data']['concepts']==[]
    assert len(client.get(root+'/versions/'+version+'/module-coverage').json()['data']['modules'])==12
    saved=deepcopy(build(graph));saved['version_id']=version
    with app.state.workflow_service.store.transaction() as db:
        db.execute('INSERT INTO business_ontology_graphs VALUES (?,?,?,?,?,?,?)',('local-workspace','local-builder',version,saved['graph_id'],'http_graph_request','fixture',json.dumps(saved)))
    endpoint=root+'/versions/'+version+'/graphs/'+saved['graph_id']+'/intelligence'
    with patch('socket.create_connection',side_effect=AssertionError('No source or model network')):
        assert len(client.get(endpoint).json()['data']['questions'])==6
        report=client.post(endpoint+'/run',json=dict(question_id='claim_fields',limit=20,offset=0))
    assert report.status_code==200 and report.headers['cache-control']=='no-store'
    assert report.json()['data']['company_queries']==report.json()['data']['model_calls']==0
    assert client.post(endpoint+'/run',json={'prompt':'guess warranty'}).status_code==422
    assert client.get(endpoint.replace(saved['graph_id'],'foreign')).status_code==404
    app.state.workflow_auth['subject']['subject_id']='foreign'
    assert client.get(endpoint).status_code==404
    assert client.get(root+'/versions/'+version+'/module-coverage').status_code==404
