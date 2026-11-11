"""Existing native Sheets report updates through Registry/runtime and exact consent."""
from copy import deepcopy
from io import BytesIO
import json
from pathlib import Path
from types import SimpleNamespace
import pytest
from tests.test_overview_automation_integration import (automation,google_setup,connected,composition,investigation,retrieval,knowledge,reference,generation,foundation,auth,release,queries,setup_query)
from tests.test_connected_action_plans import proposal,action,bind,approve,stored
from tests.test_durable_automation import drain
from tests.test_overview_automation import intent
from workflow_api.overview_automation import OverviewAutomation
from workflow_api.action_plans import CONTENT_OUTPUT
from runtime.connectors import GoogleSheetsUpdateConnector


def install_update(f,monkeypatch):
    tool=json.loads(Path('shared/contracts/examples/tools/google-sheets-update-row.json').read_text())
    tool['availability']='enabled'
    # Recurring external writes use the existing zero-retry safety policy.
    tool['retry_policy']={'max_retries':0,'retryable_errors':[]}
    tool['input_schema']=dict(type='object',additionalProperties=False,required=['spreadsheet_id','range','values'],properties={
        'spreadsheet_id':{'type':'string'},'range':{'type':'string'},'values':deepcopy(CONTENT_OUTPUT['properties']['tabs']['items']['properties']['rows'])})
    tool['output_schema']=dict(type='object',additionalProperties=False,required=['updated_cells'],properties={'updated_cells':{'type':'integer','minimum':0}})
    policy=deepcopy(f.registry._policy);policy.version+=1
    policy.approved_providers.add(tool['provider_id']);policy.agent_permissions.update(tool['permission_scopes'])
    policy.allowed_destinations.update(tool['allowed_destinations']);policy.remaining_quota[tool['tool_id']]=100
    scopes=set(tool['permission_scopes'])|set(tool['authentication']['scopes'])
    policy.credential_references['cred_report_update']=dict(provider_id=tool['provider_id'],scopes=sorted(scopes))
    for actor in (f.x.a,f.x.current):
        actor['permissions']=sorted(set(actor['permissions'])|set(tool['permission_scopes']))
        actor['scopes']=sorted(set(actor['scopes'])|scopes)
    assert f.registry.update_policy(policy,f.x.a)['status']==200
    assert f.registry.register_tool(tool,f.x.a,'cred_report_update')['status']==200
    calls=[]
    def update(request,timeout):
        assert request.get_method()=='PUT'
        assert '/reviewed_report/values/' in request.full_url
        payload=json.loads(request.data);assert payload['range']=="'Summary'!A1:B20"
        calls.append(payload)
        return BytesIO(json.dumps({'updatedCells':sum(len(row) for row in payload['values'])}).encode())
    monkeypatch.setattr('runtime.connectors._google_credentials',lambda *_:SimpleNamespace(token='controlled'))
    monkeypatch.setattr('runtime.connectors.urlopen',update)
    f.connectors[tool['tool_id']]=GoogleSheetsUpdateConnector(lambda *_:{'provider_id':'google_sheets'},'/tmp/unused-report-token')
    return calls


def test_recurring_existing_report_updates_exact_range_then_emails_with_receipts(automation,queries,monkeypatch):
    f=automation;calls=install_update(f,monkeypatch);jobs,seen,inputs,body=setup_query(f,queries)
    plan=proposal(f.prepared)
    plan['actions'][0]=action('read','tool.workflow_data_query',[bind('context','query','reviewed_query')])
    plan['actions'][2]=action('sheet','tool.google_sheets_update_row',[
        bind('literal','spreadsheet_id','report'),bind('literal','range','report_range'),
        bind('generated','values',action='analysis',path=['tabs',0,'rows'])],['analysis'])
    plan['actions'][3]['bindings'][1]=bind('literal','artifact_url','report_url')
    f.general.planner.provider=SimpleNamespace(plan_actions=lambda *_:deepcopy(plan))
    route=intent();route.update(side_effects=['sheet_update','email_send']);route['temporal']['period']='none'
    router=OverviewAutomation(f.general,dict(BUILDER_OVERVIEW_ROUTING_ENABLED='1',BUILDER_OVERVIEW_ROUTING_WORKSPACES='one'),interpreter=lambda *_:deepcopy(route))
    body.pop('automatic_inputs');body.update(objective='Every day at 6 PM India time, update my reviewed report and email engineer@example.com its summary.',
        user_values={'report':'reviewed_report','report_range':"'Summary'!A1:B20",'report_url':'https://docs.google.com/spreadsheets/d/reviewed_report'})
    result=router.handle(f.x.a,body)
    schema=result['operations']['google_sheets_update_row']
    assert schema['properties']['spreadsheet_id']=={'const':'reviewed_report'}
    assert schema['properties']['range']=={'const':"'Summary'!A1:B20"}
    assert not calls and not f.http.sent
    workflow=f.c.workflow(f.x.a,result['composition_id']);review=f.adapter.approve_pending(workflow,f.x.a);assert review['ready'],json.dumps(review,indent=2);workflow=approve(f,workflow)
    active=router.handle(f.x.a,dict(operation='activate',request_key=body['request_key']))
    for day in range(2):
        f.now=f.auto.get(f.x.a,active['schedule_id'])['due']
        f.auto.tick(f.general.worker_authenticate);drain(f);assert jobs.tick()
        f.now+=2;f.auto.tick(f.general.worker_authenticate);drain(f)
        assert len(calls)==day+1 and len(f.http.sent)==day+1
    occurrences=f.auto.listing(f.x.a,'occurrence')['items']
    for occurrence in occurrences:
        run=stored(f,occurrence['run_id']);assert run['status']=='completed',run.get('error_code')
        assert run['action_instances']['sheet']['verified_receipt']
        assert run['action_instances']['send']['verified_receipt']
    assert len(queries.reader.calls)==2 and f.http.write_count==0
    assert router.handle(f.x.a,dict(operation='activate',request_key=body['request_key']))==active
    assert len(calls)==2


@pytest.mark.parametrize('field',['spreadsheet_id','range'])
def test_report_update_cannot_generate_resource_authority(automation,monkeypatch,field):
    f=automation;calls=install_update(f,monkeypatch)
    request=deepcopy(f.request);request['request_key']='denied_report_'+field
    request['user_values'].update(report='reviewed_report',report_range="'Summary'!A1:B20")
    update=action('sheet','tool.google_sheets_update_row',[
        bind('literal','spreadsheet_id','report'),bind('literal','range','report_range'),
        bind('generated','values',action='analysis',path=['tabs',0,'rows'])],['analysis'])
    for binding in update['bindings']:
        if binding['target']==[field]:binding.clear();binding.update(bind('generated',field,action='analysis',path=['summary']))
    request['action_plan']['actions'][2]=update
    with pytest.raises(Exception) as caught:f.c.prepare_actions(f.x.a,request)
    assert caught.value.code=='ACTION_AUTHORITY_DENIED'
    assert not calls and not f.http.sent
