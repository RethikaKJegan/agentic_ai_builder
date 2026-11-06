"""Owned client Google OAuth and execution binding, with provider I/O controlled."""
import json
from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from urllib.parse import urlsplit,parse_qs
import pytest
from cryptography.fernet import Fernet
from fastapi.testclient import TestClient
from workflow_api.google_connections import GoogleConnections,BROWSER_COOKIE
from workflow_api.storage import WorkflowStore
from workflow_api.google_tools import install as install_owned,OwnedToken
from workflow_api.tenant_google import extend_registry,install,definitions
from workflow_api.live_providers import registry_configuration
from workflow_api.service import ApiFailure
from runtime.service import RuntimeFailure
from tests.test_subway_client_auth import token
from workflow_api.client_isolation import HEADER
from scripts.subway_client import provision


def actor(client):
 return dict(subject=dict(workspace_id='client-'+client,subject_id=client+'-client'),decision='allow',permissions=['tools.read','tools.assign'])

@pytest.fixture
def configured(tmp_path):
 callback='http://127.0.0.1:3001/api/backend/integrations/google/callback'
 path=tmp_path/'client.json';path.write_text(json.dumps({'web':{'client_id':'fixture-client','client_secret':'private-fixture','redirect_uris':[callback]}}))
 envs={};managers={}
 for client in ['simpsons','subway']:
  directory=tmp_path/client;directory.mkdir();key=directory/'google.key';key.write_bytes(Fernet.generate_key())
  env=dict(BUILDER_CLIENT_ID=client,BUILDER_CLIENT_GOOGLE_ENABLED='1',BUILDER_GOOGLE_CLIENT_FILE=str(path),BUILDER_GOOGLE_KEY_FILE=str(key),BUILDER_GOOGLE_REDIRECT_URI=callback,BUILDER_DATABASE_URL=str(directory/'app.sqlite3'))
  envs[client]=env;managers[client]=GoogleConnections(WorkflowStore(env['BUILDER_DATABASE_URL']),env)
 return envs,managers


def consent(manager,client):
 browser='fixture-browser';a=actor(client);url=manager.authorize(a,browser,['gmail_send','sheets_read'])['authorization_url'];state=parse_qs(urlsplit(url).query)['state'][0]
 tokens=dict(access_token='private-access',refresh_token='private-refresh',expires_in=3600,id_token='private-identity',scope='openid email https://www.googleapis.com/auth/gmail.send https://www.googleapis.com/auth/spreadsheets.readonly')
 with patch.object(manager,'token_request',return_value=tokens),patch.object(manager,'validate_identity',return_value=dict(sub='fixture-account',email='fixture@example.test')):
  assert manager.complete(state,browser,'private-code')=='connected'
 return manager.list(a)['items'][0]['connection_id']


def test_consent_and_owned_token_stay_in_the_initiating_client(configured):
 envs,managers=configured;m=managers['simpsons'];cid=consent(m,'simpsons')
 assert m.list(actor('simpsons'))['configured'] and not m.list(actor('simpsons'))['shared_demo_identity']
 assert not managers['subway'].list(actor('subway'))['items']
 with pytest.raises(ApiFailure):managers['subway'].credentials(actor('subway'),cid)
 assert OwnedToken(m,actor('simpsons'),cid)(['gmail.send'],15)=='private-access'
 with pytest.raises(RuntimeFailure):OwnedToken(m,actor('subway'),cid)(['gmail.send'],15)
 with pytest.raises(RuntimeFailure):OwnedToken(m,actor('simpsons'),cid)(['calendar.events'],15)
 state=parse_qs(urlsplit(m.authorize(actor('simpsons'),'browser',['gmail_send'])['authorization_url']).query)['state'][0]
 with pytest.raises(ApiFailure):managers['subway'].complete(state,'browser',denied=True)
 assert m.complete(state,'browser',denied=True)=='cancelled'


def test_google_catalogue_uses_existing_connectors_and_no_unbound_token_fallback(configured):
 envs,managers=configured;env=envs['simpsons'];config=registry_configuration(env)
 tools={t['definition']['tool_id']:t for t in config['tools']}
 assert 'extension_mail_send' in tools and 'extension_calendar_list' in tools and 'google_sheets_read_rows' in tools
 assert all(t['credential_reference'].startswith('cred_extension_') for t in tools.values() if t['definition']['provider_id'] in {'gmail','google_sheets','google_calendar'})
 service=SimpleNamespace(runtime_runner=SimpleNamespace(connectors={}),store=managers['simpsons'].store)
 owned=install_owned(service,managers['simpsons']);app=SimpleNamespace(state=SimpleNamespace(workflow_service=service,google_connections=managers['simpsons']))
 install(app,env)
 connector=service.runtime_runner.connectors['extension_mail_send']
 with pytest.raises(RuntimeFailure,match='Choose a connected'):connector.api.token(['gmail.send'],15)
 cid=consent(managers['simpsons'],'simpsons')
 bound=owned.bind(connector,dict(metadata={'google_connection_id':cid}),{},actor('simpsons'),{'tool_id':'extension_mail_send'})
 assert bound.api.token(['gmail.send'],15)=='private-access'
 assert bound.account=='fixture@example.test'
 with pytest.raises(RuntimeFailure):owned.bind(connector,dict(metadata={'google_connection_id':cid}),{},actor('subway'),{'tool_id':'extension_mail_send'})
 assert not list(Path(env['BUILDER_DATABASE_URL']).parent.glob('*token*'))
