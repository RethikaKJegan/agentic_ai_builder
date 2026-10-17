"""Selected-account adapters use real journals/storage and fake provider HTTP only."""
from copy import deepcopy
from types import SimpleNamespace
from unittest.mock import patch
import json
import pytest
from test_google_connections import setup, auth, connect
from workflow_api.google_tools import GoogleTools, OwnedToken, GOOGLE
from runtime.service import RuntimeFailure
from workflow_api.service import ApiFailure
from connector_extension.google import GoogleAPI
from connector_extension.calendar import CalendarConnector
from connector_extension.mail import MailConnector
from connector_extension.catalog import CATALOG
from connector_extension.common import EffectJournal, ArtifactStore
from connector_extension.tests.test_connectors import grant
from runtime.connectors import GoogleSheetsConnector


def tools_for(manager):
    return GoogleTools(manager,SimpleNamespace(store=manager.store))


def add_scopes(manager,identifier,scopes):
    with manager.store.transaction() as db:
        db.execute('UPDATE google_connections SET scopes=? WHERE connection_id=?',(json.dumps(['openid','email',*[GOOGLE+s for s in scopes]]),identifier))


def workflow(identifier,version=1):
    return {'workflow_id':'selected_google_test','version':version,'metadata':{'workspace_id':'one','google_connection_id':identifier}}


class Transport:
    def __init__(self):self.calls=[]
    def request(self,method,url,headers,body=None,timeout=30):
        self.calls.append((method,url,dict(headers),body))
        if url.endswith('/messages/send'):return {'id':'gmail-result','threadId':'thread-result'}
        if url.endswith('/drafts'):return {'id':'draft-result','message':{'id':'draft-message','threadId':'draft-thread'}}
        if '/calendar/' in url:return {'items':[]}
        return {}


def test_selected_account_overrides_mail_sender_but_preserves_recipient_policy(setup,tmp_path):
    manager,_=setup;record=connect(manager,email='selected@example.com');tools=tools_for(manager);http=Transport()
    original=MailConnector(CATALOG['extension_mail_send'],GoogleAPI(lambda *_:'legacy-token',http),EffectJournal(tmp_path),ArtifactStore(tmp_path),'legacy@example.com',['vendor@example.com']).bind_workflow(workflow(record['connection_id']))
    bound=tools.bind(original,workflow(record['connection_id']),{},auth(),grant('extension_mail_send'))
    result=bound.invoke(grant('extension_mail_send'),{'to':'vendor@example.com','subject':'Check','body':'Test'},'effect-1')
    assert result['message_id']=='gmail-result'
    assert http.calls[0][2]['Authorization']=='Bearer private-access-value'
    import base64
    from email import message_from_bytes
    message=message_from_bytes(base64.urlsafe_b64decode(http.calls[0][3]['raw']+'=='))
    assert message['From']=='selected@example.com' and original.account=='legacy@example.com'
    assert bound.google_connection_info['account_email']=='selected@example.com'
    with pytest.raises(RuntimeFailure):bound.invoke(grant('extension_mail_send'),{'to':'other@example.com','subject':'Check','body':'Test'},'effect-2')
    assert len(http.calls)==1


def test_missing_scope_and_disconnect_do_not_use_legacy_token(setup,tmp_path):
    manager,_=setup;record=connect(manager);token=OwnedToken(manager,auth(),record['connection_id'])
    with pytest.raises(RuntimeFailure) as missing:token(['calendar.events'],10)
    assert missing.value.code=='GOOGLE_SCOPE_REQUIRED'
    manager.disconnect(auth(),record['connection_id'])
    with pytest.raises(RuntimeFailure) as disconnected:token(['gmail.send'],10)
    assert disconnected.value.code=='GOOGLE_RECONNECT_REQUIRED'


def test_cross_owner_and_workspace_cannot_resolve_selected_account(setup):
    manager,_=setup;record=connect(manager)
    for actor in [auth('bob'),auth(workspace='two')]:
        with pytest.raises(RuntimeFailure):OwnedToken(manager,actor,record['connection_id'])(['gmail.send'],10)


def test_calendar_primary_scope_and_no_invitation_side_effect(setup,tmp_path):
    manager,_=setup;record=connect(manager);add_scopes(manager,record['connection_id'],['calendar.events'])
    http=Transport();tools=tools_for(manager)
    original=CalendarConnector(CATALOG['extension_calendar_list'],GoogleAPI(lambda *_:'legacy',http),EffectJournal(tmp_path),['primary']).bind_workflow(workflow(record['connection_id']))
    bound=tools.bind(original,workflow(record['connection_id']),{},auth(),grant('extension_calendar_list'))
    assert bound.invoke(grant('extension_calendar_list'),{'calendar_id':'primary','limit':5},'read-1')['events']==[]
    assert '/calendars/primary/events?' in http.calls[0][1]
    assert http.calls[0][2]['Authorization']=='Bearer private-access-value'
    with pytest.raises(RuntimeFailure):bound.invoke(grant('extension_calendar_list'),{'calendar_id':'unreviewed','limit':5},'read-2')


def test_unselected_binding_is_exact_legacy_object(setup):
    manager,_=setup;connector=object()
    assert tools_for(manager).bind(connector,{'metadata':{}},{},auth(),{'tool_id':'extension_mail_send'}) is connector


def test_legacy_sheets_uses_selected_token_without_mutating_original(setup):
    manager,_=setup;record=connect(manager);add_scopes(manager,record['connection_id'],['spreadsheets'])
    connector=GoogleSheetsConnector(lambda _: {'provider_id':'google_sheets'},'legacy-token.json',timeout=15)
    bound=tools_for(manager).bind(connector,workflow(record['connection_id']),{},auth(),{'tool_id':'google_sheets_read_rows'})
    from runtime.connectors import _google_credentials
    assert _google_credentials(bound.token_file).token=='private-access-value'
    assert str(connector.token_file)=='legacy-token.json'


def test_nested_procurement_wrapper_retains_active_check_and_binding(setup):
    manager,_=setup;record=connect(manager);add_scopes(manager,record['connection_id'],['spreadsheets'])
    connector=GoogleSheetsConnector(lambda _: {'provider_id':'google_sheets'},'legacy.json')
    wrapper=SimpleNamespace(connector=connector,procurement='retained',workflow=workflow(record['connection_id']))
    bound=tools_for(manager).adapt(wrapper,OwnedToken(manager,auth(),record['connection_id']),'google_sheets_read_rows')
    assert bound.procurement=='retained' and callable(bound.connector.token_file) and not callable(wrapper.connector.token_file)


def test_child_inherits_exact_owner_revision_not_latest(setup):
    manager,_=setup;first=connect(manager);second=connect(manager,account='google-b',email='b@example.com')
    with manager.store.transaction() as db:
        manager.store.put(db,'one',workflow(first['connection_id'],1))
        manager.store.put(db,'one',workflow(second['connection_id'],2))
    job={'owner_workflow':{'workflow_id':'selected_google_test','version':1}}
    child={'metadata':{}}
    inherited=tools_for(manager).inherit('one',job,child)
    assert inherited['metadata']['google_connection_id']==first['connection_id'] and child['metadata']=={}
    child['metadata']['google_connection_id']=second['connection_id']
    with pytest.raises(RuntimeFailure):tools_for(manager).inherit('one',job,child)


def test_planning_context_is_scoped_and_discovery_uses_selected_account(setup):
    manager,_=setup;record=connect(manager);add_scopes(manager,record['connection_id'],['spreadsheets.readonly'])
    tools=tools_for(manager)
    connector=GoogleSheetsConnector(lambda _: {},'legacy.json')
    with patch.object(GoogleSheetsConnector,'discover',lambda self,resource:self.token_file() if callable(self.token_file) else 'legacy'):
        with tools.planning(auth(),{'google_connection_id':record['connection_id']}):
            assert tools.discover(connector,'sheet').token=='private-access-value'
        assert tools.discover(connector,'sheet')=='legacy'


def test_binding_validation_rejects_unknown_disconnected_or_invalid_refs(setup):
    manager,_=setup;record=connect(manager);tools=tools_for(manager)
    with manager.store.transaction(write=False) as db:
        tools.validate(workflow(record['connection_id']),auth(),db)
        with pytest.raises(ApiFailure):tools.validate(workflow('not-a-connection'),auth(),db)
    manager.disconnect(auth(),record['connection_id'])
    with manager.store.transaction(write=False) as db:
        with pytest.raises(ApiFailure):tools.validate(workflow(record['connection_id']),auth(),db)


def test_unknown_write_outcome_is_not_replayed_for_selected_mail(setup,tmp_path):
    manager,_=setup;record=connect(manager);tools=tools_for(manager)
    http=Transport()
    def uncertain(*args,**kwargs):http.calls.append(args);raise TimeoutError('unknown result')
    http.request=uncertain
    original=MailConnector(CATALOG['extension_mail_send'],GoogleAPI(lambda *_:'legacy-token',http),EffectJournal(tmp_path),ArtifactStore(tmp_path),'legacy@example.com',['vendor@example.com']).bind_workflow(workflow(record['connection_id']))
    bound=tools.bind(original,workflow(record['connection_id']),{},auth(),grant('extension_mail_send'))
    inputs={'to':'vendor@example.com','subject':'Check','body':'Test'}
    with pytest.raises(Exception):bound.invoke(grant('extension_mail_send'),inputs,'uncertain-1')
    with pytest.raises(RuntimeFailure) as replay:bound.invoke(grant('extension_mail_send'),inputs,'uncertain-1')
    assert replay.value.code=='UNKNOWN_INVOCATION_RESULT' and len(http.calls)==1


def test_tool_check_route_creates_only_draft_and_enforces_account_ownership(setup):
    from fastapi.testclient import TestClient
    from workflow_api.main import create_app,COOKIE
    from runtime.graph import GraphRunner
    from runtime.service import RuntimeService
    manager,env=setup
    # Match this demo application's server-owned authenticated identity.
    actor=auth('local-builder','local-workspace')
    record=connect(manager,actor=actor)
    app=create_app(database=manager.store.path,dev_auth=True,roles=['admin'],start_workers=False,planning_worker_enabled=False,google_oauth_config=env)
    service=app.state.workflow_service
    service.runtime_runner=GraphRunner(RuntimeService(service),connectors={'extension_calendar_list':object()})
    with TestClient(app) as client:
        session=client.get('/session');client.cookies.set(COOKIE,session.cookies[COOKIE],path='/')
        result=client.post('/integrations/google/tool-check-draft',json={'connection_id':record['connection_id'],'tool_id':'extension_calendar_list','inputs':{'calendar_id':'primary','limit':5}})
        assert result.status_code==200,result.text
        doc=result.json()['data']['workflow']
        assert doc['status']=='draft' and doc['metadata']['google_connection_id']==record['connection_id']
        with manager.store.transaction(write=False) as db:
            assert db.execute('SELECT COUNT(*) FROM runtime_runs').fetchone()[0]==0
        denied=client.post('/integrations/google/tool-check-draft',json={'connection_id':'gc_'+'f'*32,'tool_id':'extension_calendar_list','inputs':{'calendar_id':'primary','limit':5}})
        assert denied.status_code==404


def test_smtp_contract_routes_to_selected_gmail_after_existing_safety_checks(setup,tmp_path):
    from runtime.connectors import SMTPConnector
    manager,_=setup;record=connect(manager,email='oauth@example.com');tools=tools_for(manager)
    original=SMTPConnector(lambda _: (_ for _ in ()).throw(AssertionError('legacy SMTP credentials must not resolve')),['vendor@example.com'],['smtp.gmail.com'],timeout=15)
    bound=tools.bind(original,workflow(record['connection_id']),{},auth(),{'tool_id':'smtp_send_email'})
    accepted={'tool_id':'smtp_send_email','authorization_state':'authorized','authorization_reference':'reviewed','credential_reference':'legacy_smtp_reference','destination':'verified_recipients','approval_reference':'approved', 'input_schema':{'type':'object'},'output_schema':{'type':'object','required':['message_id']}}
    with patch.object(tools,'send_mail',return_value={'message_id':'selected-google-message'}) as send:
        assert bound.invoke(accepted,{'to':'vendor@example.com','subject':'Check','body':'Test'},'send-1')['message_id']=='selected-google-message'
        send.assert_called_once()
        with pytest.raises(RuntimeFailure):bound.invoke(accepted,{'to':'unknown@example.com','subject':'Check','body':'Test'},'send-2')
        send.assert_called_once()


def test_same_objective_with_different_selected_accounts_has_distinct_plan_identity():
    from planner import PlannerService
    from planner.provider import RuleBasedStructuredOutputProvider
    service=PlannerService(RuleBasedStructuredOutputProvider())
    def request(identifier,key):
        return service.plan({'request_id':'req_test','operation':'plan_workflow','idempotency_key':key,
            'payload':{'objective':'Summarize customer support messages','context':{'google_connection_id':identifier},
                'auth_context':{'workspace_id':'local-workspace','subject_id':'local-builder','roles':['admin'],'permissions':['workflow.plan']}}})
    first=request('gc_'+'a'*32,'first-plan-key')
    second=request('gc_'+'b'*32,'second-plan-key')
    assert first['status']==200 and second['status']==200
    assert first['data']['workflow']['workflow_id']!=second['data']['workflow']['workflow_id']


def test_selected_account_flows_through_native_procurement_and_tracking(tmp_path):
    from test_integrated_procurement import IntegratedTests
    from workflow_api.google_connections import GoogleConnections
    from workflow_api.google_tools import install
    from cryptography.fernet import Fernet
    case=IntegratedTests('test_native_prompt_to_approved_sends_and_tracking')
    case.setUp()
    try:
        # Stop only legacy credential mocks: selected execution must obtain real fixture-stored OAuth credentials.
        case.patches[1].stop();case.patches[2].stop()
        client=tmp_path/'google-client.json';key=tmp_path/'google-key'
        client.write_text(json.dumps({'web':{'client_id':'fixture-client','client_secret':'fixture-secret','redirect_uris':['http://localhost:3001/api/backend/integrations/google/callback']}}))
        key.write_bytes(Fernet.generate_key())
        manager=GoogleConnections(case.service.store,{'BUILDER_GOOGLE_CLIENT_FILE':str(client),'BUILDER_GOOGLE_KEY_FILE':str(key),'BUILDER_GOOGLE_REDIRECT_URI':'http://localhost:3001/api/backend/integrations/google/callback'})
        install(case.service,manager)
        record=connect(manager,actor=case.auth,email='selected@example.com')
        add_scopes(manager,record['connection_id'],['spreadsheets','gmail.readonly','gmail.compose','gmail.send','calendar.events'])
        seen=[];previous=case.urlopen
        def capture(request,timeout):
            seen.append(request.get_header('Authorization'));return previous(request,timeout)
        with patch('runtime.connectors.urlopen',side_effect=capture):
            w=case.call('plan_workflow',{'objective':'Procurement RFQ simulation from https://docs.google.com/spreadsheets/d/requirements_book/edit and https://docs.google.com/spreadsheets/d/vendors_book/edit','context':{'execution_input_mode':'automatic','google_connection_id':record['connection_id']}})['workflow']
            case.plan=w['metadata']['procurement_plan'];case.ref={'workflow_id':w['workflow_id'],'workflow_version':1}
            case.call('save_workflow_version',{**case.ref,'base_version':0,'workflow':w})
            case.call('validate_workflow',case.ref);case.call('approve_workflow',{**case.ref,'action':'approve'});case.call('approve_workflow',{**case.ref,'action':'publish'})
            case.service.lifecycle.activate({'request_id':'activate','idempotency_key':'selected_activate','payload':{**case.ref,'triggers':[]}},case.auth)
            run=case.call('execute_workflow',{**case.ref,'inputs':{}})['run']
            assert run['status']=='completed',run
            state=case.procurement.status('local-workspace',case.plan['project_id'])
            ingestion=state['actions']['ingestion']
            events=case.service.runtime_runner.runtime.events(ingestion['run_id'],case.auth)['items']
            provenance=[e['details']['google_connection'] for e in events if e['event_type']=='node.started' and 'google_connection' in e['details']]
            assert provenance and all(e['connection_id']==record['connection_id'] for e in provenance)
            for _ in range(25):
                if state['phase']=='RFQS_SENT':break
                if any(a['state']=='paused_for_approval' for a in state['actions'].values()):case.approve(state)
                state=case.advance()
                assert state['phase']!='STOPPED',[(name,[(e['event_type'],e['details'].get('error_code')) for e in case.service.runtime_runner.runtime.events(action['run_id'],case.auth)['items'] if e['event_type'] in {'node.failed','runtime.denied'}]) for name,action in state['actions'].items() if action.get('run_id') and action.get('state') in {'failed','blocked'}]
            assert state['phase']=='RFQS_SENT' and len(case.http.sent)==4
            assert all(message['From']=='selected@example.com' for message in case.http.sent)
            assert seen and all(value=='Bearer private-access-value' for value in seen)
    finally:case.doCleanups()
