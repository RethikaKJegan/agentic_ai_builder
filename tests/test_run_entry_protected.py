"""Run's automatic checks keep the existing Google exact-payload gates."""
from copy import deepcopy
import pytest
from tests.test_connected_action_plans import connected,composition,investigation,retrieval,knowledge,reference,generation,foundation,auth,release,decide
from workflow_api.run_entry import start,resume_pending
from workflow_api.service import ApiFailure


@pytest.mark.parametrize('additional_review',[False,True])
def test_sheets_and_mail_still_pause_after_human_workflow_review(connected,additional_review):
    f=connected;a=f.x.a;a['permissions']=sorted(set(a['permissions'])|{'workflow.validate'})
    a['roles']=sorted(set(a['roles'])|{'admin'})
    a['permissions']=sorted(set(a['permissions'])|{'workflow.edit'})
    policy=f.runner.runtime.governance.get(a)
    f.runner.runtime.governance.update(a,dict(revision=policy['revision'],policy={**policy['policy'],'require_action_approval':additional_review}))
    document=f.c.prepare_actions(a,f.request);w=f.c.workflow(a,document['composition_id'])
    saved=f.general.handle(dict(request_id='save_before_run',operation='save_workflow_version',idempotency_key='save_before_run_123',payload=dict(workflow_id=w['workflow_id'],workflow_version=w['version'],base_version=0,workflow=w)),a)
    assert saved['status']==200,saved
    request=dict(request_id='protected_run',operation='execute_workflow',idempotency_key='protected_run_1234',payload=dict(workflow_id=w['workflow_id'],workflow_version=1,inputs={}))
    with pytest.raises(ApiFailure) as pending:start(f.general,request,a)
    assert pending.value.code=='WORKFLOW_APPROVAL_REQUIRED'
    assert not f.http.books and not f.http.sent
    approved=f.general.handle(dict(request_id='human_approval',operation='approve_workflow',idempotency_key='human_protected_approval',payload=dict(workflow_id=w['workflow_id'],workflow_version=1,action='approve')),a)
    assert approved['status']==200,approved
    f.general.worker_authenticate=lambda workspace,owner:deepcopy(a) if (workspace,owner)==(a['subject']['workspace_id'],a['subject']['subject_id']) else None
    resumed=resume_pending(f.general,w['workflow_id'],1,a);assert len(resumed)==1
    run=f.runner.advance(resumed[0]['run_id'],a)
    assert run['status']=='paused_for_approval';assert not f.http.books and not f.http.sent
    # A real explicit decision is needed for the exact Sheets payload.
    decide(f,w,run);run=f.runner.advance(run['run_id'],a)
    assert run['status']=='paused_for_approval';assert len(f.http.books)==1 and not f.http.sent
    decide(f,w,run);run=f.runner.advance(run['run_id'],a)
    assert run['status']=='completed' and len(f.http.sent)==1
