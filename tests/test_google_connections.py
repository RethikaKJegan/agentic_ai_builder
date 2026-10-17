"""Phase 1 OAuth security/lifecycle tests; Google is replaced only at its HTTP/identity boundary."""
import json
import time
from urllib.parse import parse_qs, urlsplit
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import patch
import pytest
from cryptography.fernet import Fernet
from fastapi.testclient import TestClient
from workflow_api.google_connections import GoogleConnections, BROWSER_COOKIE
from workflow_api.storage import WorkflowStore
from workflow_api.service import ApiFailure
from workflow_api.main import create_app


def auth(owner='alice', workspace='one'):
    return {'subject':{'subject_id':owner,'workspace_id':workspace},'decision':'allow','permissions':['tools.read','tools.assign']}


@pytest.fixture
def setup(tmp_path):
    client=tmp_path/'client.json';key=tmp_path/'key'
    callback='http://localhost:3001/api/backend/integrations/google/callback'
    client.write_text(json.dumps({'web':{'client_id':'test-client','client_secret':'private-client-value','redirect_uris':[callback]}}))
    key.write_bytes(Fernet.generate_key())
    env={'BUILDER_GOOGLE_CLIENT_FILE':str(client),'BUILDER_GOOGLE_KEY_FILE':str(key),'BUILDER_GOOGLE_REDIRECT_URI':callback}
    store=WorkflowStore(tmp_path/'connections.sqlite3')
    return GoogleConnections(store,env),env


def start(manager, actor=None, browser='browser', connection=None, caps=None):
    result=manager.authorize(actor or auth(),browser,caps or ['gmail_send'],connection)
    return parse_qs(urlsplit(result['authorization_url']).query)['state'][0]


def connect(manager, actor=None, browser='browser', account='google-a', email='a@example.com', connection=None, refresh=True):
    state=start(manager,actor,browser,connection)
    tokens={'access_token':'private-access-value','expires_in':3600,'id_token':'private-identity-value','scope':'openid email https://www.googleapis.com/auth/gmail.send'}
    if refresh:tokens['refresh_token']='private-refresh-value'
    with patch.object(manager,'token_request',return_value=tokens),patch.object(manager,'validate_identity',return_value={'sub':account,'email':email,'email_verified':True}):
        manager.complete(state,browser,'private-code-value')
    return manager.list(actor or auth())['items'][-1]


def test_pkce_requested_scopes_and_no_public_secrets(setup):
    m,_=setup;public=m.authorize(auth(),'browser',['sheets_write'])
    q=parse_qs(urlsplit(public['authorization_url']).query)
    assert q['code_challenge_method']==['S256'] and q['access_type']==['offline'] and q['nonce']
    assert 'client_secret' not in public['authorization_url']
    record=connect(m)
    assert record['capabilities']['gmail_send'] and not record['capabilities']['calendar_write']
    schema=json.load(open('shared/contracts/integrations/google-connections-v1.schema.json'))
    from jsonschema import validate
    validate(record,schema)
    assert 'private-' not in json.dumps(m.list(auth()))
    with m.store.transaction(write=False) as db:
        stored=db.execute('SELECT credentials FROM google_connections').fetchone()[0]
        assert 'private-' not in stored
        assert json.loads(m.cipher.decrypt(stored.encode()))['refresh_token']=='private-refresh-value'


def test_single_use_browser_binding_expiry_and_cancel(setup):
    m,_=setup;state=start(m)
    with pytest.raises(ApiFailure,match='browser'):m.complete(state,'other','code')
    assert m.complete(state,'browser',denied=True)=='cancelled'
    with pytest.raises(ApiFailure):m.complete(state,'browser',denied=True)
    state=start(m)
    with m.store.transaction() as db:db.execute('UPDATE google_oauth_sessions SET expires_at=0')
    with pytest.raises(ApiFailure):m.complete(state,'browser','code')
    assert not m.list(auth())['items']


def test_ownership_permissions_and_multiple_accounts(setup):
    m,_=setup;a=connect(m);connect(m,account='google-b',email='b@example.com')
    assert len(m.list(auth())['items'])==2
    assert not m.list(auth('bob'))['items'] and not m.list(auth(workspace='two'))['items']
    with pytest.raises(ApiFailure):m.disconnect(auth('bob'),a['connection_id'])
    viewer=auth();viewer['permissions']=['tools.read']
    with pytest.raises(ApiFailure):start(m,viewer)
    with pytest.raises(ApiFailure):m.authorize(auth(),'browser',['unsupported'])


def test_incremental_access_keeps_refresh_and_rejects_wrong_account(setup):
    m,_=setup;a=connect(m)
    updated=connect(m,connection=a['connection_id'],refresh=False)
    assert updated['connection_id']==a['connection_id']
    assert len(m.list(auth())['items'])==1
    with pytest.raises(ApiFailure,match='same account'):connect(m,connection=a['connection_id'],account='wrong')
    assert len(m.list(auth())['items'])==1


def test_restart_persistence_disconnect_and_reconnect(setup):
    m,env=setup;a=connect(m)
    restarted=GoogleConnections(WorkflowStore(m.store.path),env)
    assert restarted.list(auth())['items'][0]['connection_id']==a['connection_id']
    state=start(m,connection=a['connection_id'])
    restarted.disconnect(auth(),a['connection_id'])
    with pytest.raises(ApiFailure):m.complete(state,'browser','code')
    with pytest.raises(ApiFailure):m.credentials(auth(),a['connection_id'])
    assert connect(restarted,connection=a['connection_id'])['status']=='connected'


def test_refresh_revocation_and_transient_failure_persist(setup):
    m,_=setup;a=connect(m)
    with patch.object(m,'token_request',side_effect=ApiFailure('GOOGLE_PROVIDER_FAILED','temporary',503)):
        with pytest.raises(ApiFailure):m.credentials(auth(),a['connection_id'],force=True)
    assert m.list(auth())['items'][0]['status']=='verification_failed'
    with patch.object(m,'token_request',side_effect=ApiFailure('GOOGLE_RECONNECT_REQUIRED','revoked',409)):
        with pytest.raises(ApiFailure):m.credentials(auth(),a['connection_id'],force=True)
    assert m.list(auth())['items'][0]['status']=='reconnect_required'


def test_concurrent_expired_refresh_once(setup):
    m,_=setup;a=connect(m)
    with m.store.transaction() as db:
        row=m.owned(db,auth(),a['connection_id']);value=json.loads(m.cipher.decrypt(row[7].encode()));value['expires_at']=0
        db.execute('UPDATE google_connections SET credentials=?',(m.cipher.encrypt(json.dumps(value).encode()).decode(),))
    with patch.object(m,'token_request',return_value={'access_token':'fresh-value','expires_in':3600}) as request:
        with ThreadPoolExecutor(max_workers=2) as pool:
            results=list(pool.map(lambda _:m.credentials(auth(),a['connection_id']),range(2)))
        assert request.call_count==1
        assert all(x['access_token']=='fresh-value' for x in results)


def test_verify_is_read_only_and_disconnect_race_does_not_reenable(setup):
    m,_=setup;a=connect(m)
    class Response:
        status_code=200
        def json(self):return {'sub':'google-a','email_verified':True}
    with patch.object(m,'token_request',return_value={'access_token':'fresh-value','expires_in':3600}),patch('workflow_api.google_connections.httpx.get',return_value=Response()):
        assert m.verify(auth(),a['connection_id'])['status']=='connected'
    def race(*args,**kwargs):
        m.disconnect(auth(),a['connection_id']);return Response()
    with patch.object(m,'token_request',return_value={'access_token':'fresh-value','expires_in':3600}),patch('workflow_api.google_connections.httpx.get',side_effect=race):
        with pytest.raises(ApiFailure):m.verify(auth(),a['connection_id'])
    assert m.list(auth())['items'][0]['status']=='disconnected'


def test_callback_route_only_accepts_browser_bound_flow_without_app_session(setup):
    m,env=setup
    app=create_app(database=m.store.path,dev_auth=True,roles=['admin'],start_workers=False,planning_worker_enabled=False,google_oauth_config=env)
    with TestClient(app) as c:
        c.get('/session')
        session=c.cookies.get('builder_dev_session')
        c.cookies.set('builder_dev_session',session)
        response=c.post('/integrations/google/authorize',json={'capabilities':['gmail_send']})
        assert response.status_code==200 and 'HttpOnly' in response.headers['set-cookie']
        browser=response.cookies.get(BROWSER_COOKIE)
        url=response.json()['data']['authorization_url'];state=parse_qs(urlsplit(url).query)['state'][0]
        c.cookies.clear()
        callback=c.get('/integrations/google/callback',params={'state':state,'error':'access_denied'},headers={'sec-fetch-site':'cross-site','cookie':f'{BROWSER_COOKIE}={browser}'},follow_redirects=False)
        assert callback.status_code==303 and callback.headers['location'].endswith('google=cancelled')
        assert callback.headers['referrer-policy']=='no-referrer'
        assert c.get('/workflows',headers={'sec-fetch-site':'cross-site'}).status_code==403


def test_missing_configuration_is_honest(setup):
    m,_=setup;empty=GoogleConnections(m.store,{})
    assert not empty.list(auth())['configured']
    with pytest.raises(ApiFailure,match='Configure'):start(empty)


def test_identity_validation_rejects_wrong_nonce_and_unverified_email(setup):
    m,_=setup
    with patch('google.oauth2.id_token.verify_oauth2_token',return_value={'sub':'google-a','email':'a@example.com','email_verified':True,'nonce':'wrong'}):
        with pytest.raises(ApiFailure,match='identity'):m.validate_identity('signed','expected')
    with patch('google.oauth2.id_token.verify_oauth2_token',return_value={'sub':'google-a','email':'a@example.com','email_verified':False,'nonce':'expected'}):
        with pytest.raises(ApiFailure,match='identity'):m.validate_identity('signed','expected')


def test_missing_scope_response_does_not_claim_requested_grants(setup):
    m,_=setup;state=start(m)
    with patch.object(m,'token_request',return_value={'access_token':'access','refresh_token':'refresh','expires_in':3600}),patch.object(m,'validate_identity',return_value={'sub':'google-a','email':'a@example.com','email_verified':True}):
        m.complete(state,'browser','code')
    assert not any(m.list(auth())['items'][0]['capabilities'].values())
