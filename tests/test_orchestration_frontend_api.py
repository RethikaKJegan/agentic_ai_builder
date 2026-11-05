"""The public frontend workflow operations must preserve connected-plan authority."""
from copy import deepcopy
from uuid import uuid4
from tests.test_connected_action_plans import (connected,composition,investigation,retrieval,knowledge,reference,generation,foundation,auth,release,stored)


def command(f,operation,payload,key=None):
    return f.general.handle(dict(operation=operation,request_id='frontend_api_request',idempotency_key=key or 'frontend_'+uuid4().hex,payload=payload),f.x.a)


def test_standard_frontend_save_validate_approve_and_execute_connected_plan(connected):
    f=connected;f.x.a['permissions'].append('workflow.validate')
    doc=f.c.prepare_actions(f.x.a,f.request);w=f.c.workflow(f.x.a,doc['composition_id']);original=deepcopy(w['nodes'])
    ref=dict(workflow_id=w['workflow_id'],workflow_version=1)
    saved=command(f,'save_workflow_version',dict(**ref,base_version=0,workflow=w));assert saved['status']==200,saved
    assert saved['data']['workflow']['nodes']==original
    validated=command(f,'validate_workflow',ref);assert validated['status']==200,validated
    approved=command(f,'approve_workflow',dict(**ref,action='approve'));assert approved['status']==200,approved
    assert approved['data']['registry_review']['ready']
    assert approved['data']['workflow']['nodes']==original
    started=command(f,'execute_workflow',dict(**ref,inputs={}),key='frontend_start_once');assert started['status']==200,started
    rid=started['data']['run']['run_id']
    for _ in range(4):
        run=f.runner.advance(rid,f.x.a)
        if run['status']=='completed':break
        assert run['status']=='paused_for_approval',run
        a=run['approvals'][-1];assert a['resolved_payload'] and a['action_digest']
        result=command(f,'decide_approval',dict(approval_id=a['approval_id'],decision='approved',**ref));assert result['status']==200,result
    assert stored(f,rid)['status']=='completed'
    assert f.http.write_count==1 and len(f.http.sent)==1
    replay=command(f,'execute_workflow',dict(**ref,inputs={}),key='frontend_start_once');assert replay['data']['run']['run_id']==rid
    f.runner.advance(rid,f.x.a);assert len(f.http.sent)==1


def test_connected_marker_cannot_bypass_immutable_composition_verification(connected):
    f=connected;doc=f.c.prepare_actions(f.x.a,f.request);w=f.c.workflow(f.x.a,doc['composition_id'])
    # Input changes cannot smuggle identity/content through the legacy save path.
    w['nodes'][1]['label']='Tampered executable plan'
    response=command(f,'save_workflow_version',dict(workflow_id=w['workflow_id'],workflow_version=1,base_version=0,workflow=w))
    assert response['status']>=400,response
    assert not f.http.sent and f.http.write_count==0


def test_forged_connected_marker_cannot_skip_review_without_owned_composition(connected):
    f=connected;doc=f.c.prepare_actions(f.x.a,f.request);w=f.c.workflow(f.x.a,doc['composition_id'])
    w['workflow_id']='forged_connected_workflow';w['metadata'].pop('composition_id')
    response=command(f,'save_workflow_version',dict(workflow_id=w['workflow_id'],workflow_version=1,base_version=0,workflow=w))
    assert response['status']==403,response
    assert response['data']['error']['error_code']=='CAPABILITY_NOT_FOUND'
    assert not f.http.sent and f.http.write_count==0
