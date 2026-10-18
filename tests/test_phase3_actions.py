"""Explicit approval submission, confirmed settings and honest read-only probes."""
from copy import deepcopy
from datetime import datetime,timezone
import json
from unittest.mock import patch
import pytest
from tests import test_workflow_api as fixtures
from workflow_api.integration_checks import smtp_probe


@pytest.fixture
def context():
    fixture=fixtures.WorkflowApiTests('test_same_prompt_after_deletion_gets_stable_fresh_identity_and_agents');fixture.setUp()
    try:yield fixture
    finally:fixture.tearDown();fixture.doCleanups()


def validated(context):
    assert context.save().status_code==200
    assert context.mutate('/workflows/'+context.workflow['workflow_id']+'/validate','validate_workflow',context.ref(),'phase3_validate_123').status_code==200


def submission(context,key='phase3_submission_123',version=1):
    return {'request_id':'req_phase3','operation':'submit_workflow_for_approval','idempotency_key':key,
            'payload':{'workflow_id':context.workflow['workflow_id'],'workflow_version':version}}


def test_submission_is_explicit_durable_and_does_not_approve_publish_or_activate(context):
    validated(context);path='/workflows/'+context.workflow['workflow_id']+'/submit-for-approval'
    result=context.client.post(path,json=submission(context));assert result.status_code==200,result.text
    workflow=result.json()['data']['workflow'];assert workflow['status']=='validated'
    assert workflow['metadata']['approval_submission']['submitted_by']=='local-builder'
    replay=context.client.post(path,json=submission(context));assert replay.json()==result.json()
    with context.service.store.transaction(write=False) as db:
        assert db.execute('SELECT COUNT(*) FROM lifecycle_releases').fetchone()[0]==0
        assert db.execute('SELECT COUNT(*) FROM lifecycle_active').fetchone()[0]==0
    assert context.client.post(path,json=submission(context,version=2)).status_code==409


def test_submission_rejects_unvalidated_stale_and_unauthorized_requests(context):
    assert context.save().status_code==200
    path='/workflows/'+context.workflow['workflow_id']+'/submit-for-approval'
    assert context.client.post(path,json=submission(context)).status_code==409
    validated_response=context.mutate('/workflows/'+context.workflow['workflow_id']+'/validate','validate_workflow',context.ref(),'phase3_validate_123')
    assert validated_response.status_code==200
    assert context.client.post(path,json=submission(context,key='stale_submission_123',version=2)).status_code==409
    approver=context.session(['approver'])
    try:assert approver.post(path,json=submission(context)).status_code==403
    finally:approver.close()


def test_submission_allows_real_pending_tool_review_without_granting_approval(context):
    config=context.registry_configuration(approval_required=True)
    client=context.configured_session(config)
    assert context.save(client=client).status_code==200
    path='/workflows/'+context.workflow['workflow_id']
    assert context.mutate(path+'/validate','validate_workflow',context.ref(),'validate_pending_123',client=client).status_code==200
    result=client.post(path+'/submit-for-approval',json=submission(context))
    assert result.status_code==200,result.text
    data=result.json()['data']
    assert data['workflow']['status']=='validated'
    assert data['workflow']['metadata']['approval_submission']
    assert not data['registry_review']['ready']
    assert data['registry_review']['items'][0]['authorization_state']=='pending_approval'
    assert not data['workflow']['agents'][0]['allowed_tool_ids']


@pytest.mark.parametrize('changes,reason',[
    ({'availability':'disabled'},'TOOL_UNAVAILABLE'),
    ({'risk_level':'high'},'RISK_NOT_AUTHORIZED'),
])
def test_submission_still_rejects_denied_tools(context,changes,reason):
    client=context.configured_session(context.registry_configuration(**changes))
    assert context.save(client=client).status_code==200
    path='/workflows/'+context.workflow['workflow_id']
    assert context.mutate(path+'/validate','validate_workflow',context.ref(),'validate_denied_123',client=client).status_code==200
    result=client.post(path+'/submit-for-approval',json=submission(context))
    assert result.status_code==403,result.text
    assert reason in result.json()['data']['error']['details']['reason_codes']


def test_submission_shows_unresolved_destination_requirement(context):
    context.workflow['metadata']['unresolved_requirements']=[
        'Confirm the report spreadsheet destination and product columns.',
        {'requirement':'Choose report destination'}]
    validated(context)
    path='/workflows/'+context.workflow['workflow_id']+'/submit-for-approval'
    result=context.client.post(path,json=submission(context))
    assert result.status_code==403,result.text
    error=result.json()['data']['error']
    assert error['details']['requirements']==[
        'Confirm the report spreadsheet destination and product columns.',
        'Resolve requirement: Choose report destination']
    assert 'UNRESOLVED_REQUIREMENTS' in error['details']['reason_codes']


def test_submission_rejects_uncovered_tool_even_with_pending_approval_summary(context):
    validated(context)
    review={'ready':False,'reason_codes':['APPROVAL_REQUIRED','TOOL_ASSIGNMENT_REQUIRED'],
            'items':[{'tool_id':'missing','authorization_state':'denied','reason_codes':[]}]}
    with patch.object(context.service.registry_adapter,'review',return_value=review):
        result=context.client.post('/workflows/'+context.workflow['workflow_id']+'/submit-for-approval',json=submission(context))
    assert result.status_code==403


def test_save_timestamp_is_server_confirmed_and_submission_does_not_leak_to_new_draft(context):
    context.workflow['metadata']['updated_at']='1900-01-01T00:00:00Z'
    validated(context)
    path='/workflows/'+context.workflow['workflow_id']+'/submit-for-approval'
    workflow=context.client.post(path,json=submission(context)).json()['data']['workflow']
    assert datetime.fromisoformat(workflow['metadata']['updated_at']).year>=2026
    workflow.update(version=2,status='draft')
    result=context.save(workflow,base=1,key='new_draft_submission_123');assert result.status_code==200,result.text
    assert 'approval_submission' not in result.json()['data']['workflow']['metadata']


def test_settings_need_admin_validate_input_and_return_confirmed_value(context):
    path='/workspace/settings/notifications'
    assert context.client.put(path,json={'value':'email'}).status_code==403
    admin=context.session(['admin'])
    try:
        assert admin.put(path,json={}).status_code==400
        assert admin.put(path,json={'value':{'invalid':'object'}}).status_code==400
        assert admin.put(path,json={'value':'x'*2001}).status_code==400
        response=admin.put(path,json={'value':'email'},headers={'X-Request-ID':'req_confirm_setting'})
        assert response.status_code==200,response.text
        item=response.json()['data'];assert item['value']=='email';assert item['updated_at']
        assert admin.get('/workspace/settings').json()['data']['items'][0]['value']=='email'
        assert admin.put(path,json={'value':'secret=private-key-value'}).status_code==400
        assert admin.get('/workspace/settings').json()['data']['items'][0]['value']=='email'
    finally:admin.close()


def configured_registry(context):
    listing={'data':{'items':[{'definition':{'provider_id':'smtp','availability':'enabled','authentication':{'mode':'api_key'}},'credential_configured':True}]}}
    return patch.object(context.service.registry_adapter.service,'list_tools',return_value=listing)


def test_configuration_is_not_verification_and_unsupported_probes_stay_unverified(context):
    with configured_registry(context):
        response=context.client.post('/integrations/smtp/test',json={});assert response.status_code==200
        data=response.json()['data'];assert data['configured'];assert not data['verified'];assert not data['tested'];assert data['state']=='configured'
        assert context.client.post('/integrations/smtp/test',json={'mode':'connection'}).status_code==403
        admin=context.session(['admin'])
        try:
            result=admin.post('/integrations/smtp/test',json={'mode':'connection'}).json()['data']
            assert result['state']=='configured';assert result['verified'] is False
            assert admin.post('/integrations/smtp/test',json={'url':'https://untrusted.example'}).status_code==400
        finally:admin.close()
    result=context.client.post('/integrations/google_sheets/test',json={}).json()['data']
    assert result['state']=='not_configured';assert not result['tested']


def test_real_probe_runs_outside_database_and_failure_is_redacted(context):
    admin=context.session(['admin']);calls=[]
    def probe():
        with context.service.store.transaction() as db:db.execute('SELECT 1')
        calls.append('read-only')
    context.service.integration_probes={'smtp':probe}
    try:
        with configured_registry(context):
            data=admin.post('/integrations/smtp/test',json={'mode':'connection'}).json()['data']
            assert data['state']=='verified';assert data['tested'];assert calls==['read-only']
            def fail():raise RuntimeError('Bearer private-provider-token')
            context.service.integration_probes['smtp']=fail
            response=admin.post('/integrations/smtp/test',json={'mode':'connection'})
            assert response.status_code==200;assert response.json()['data']['state']=='connection_failed'
            assert 'private-provider-token' not in response.text;assert response.json()['data']['verified'] is False
    finally:admin.close()


def test_smtp_probe_authenticates_and_noops_without_any_delivery_commands():
    calls=[]
    class ReadOnlySMTP:
        def __init__(self,host,port,timeout):assert (host,port,timeout)==('smtp.gmail.com',587,5)
        def __enter__(self):return self
        def __exit__(self,*_):pass
        def ehlo(self):calls.append('ehlo')
        def starttls(self,context):calls.append('starttls')
        def login(self,*_):calls.append('login')
        def noop(self):calls.append('noop');return 250,b'ok'
    smtp_probe({'GMAIL_SMTP_USER':'fixture@example.com','GMAIL_SMTP_PASSWORD':'test-only'},ReadOnlySMTP)()
    assert calls==['ehlo','starttls','ehlo','login','noop']


def test_published_revision_is_visible_before_activation_and_under_newer_draft(context):
    validated(context);admin=context.session(['admin'])
    try:
        path='/workflows/'+context.workflow['workflow_id']+'/approve'
        for action in ['approve','publish']:
            response=context.mutate(path,'approve_workflow',{**context.ref(),'action':action},'phase3_'+action+'_overview',client=admin)
            assert response.status_code==200,response.text
        document=response.json()['data']['workflow']
        item=next(item for item in admin.get('/workflow-overview').json()['data']['items'] if item['workflow_id']==document['workflow_id'])
        assert item['published_version']==1
        assert item['release_id'] is None;assert item['activation_state'] is None
        document.update(version=2,status='draft')
        assert context.save(document,base=1,key='phase3_draft_over_published').status_code==200
        item=next(item for item in admin.get('/workflow-overview').json()['data']['items'] if item['workflow_id']==document['workflow_id'])
        assert item['published_version']==1;assert item['draft_version']==2
    finally:admin.close()
