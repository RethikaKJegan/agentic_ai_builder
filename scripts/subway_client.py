"""Provision or run Subway authentication only; no datasets, ontology or model setup."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import secrets
import sqlite3
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def provision(directory, email, password):
    from cryptography.fernet import Fernet
    from scripts.integration_config import private_write
    directory = Path(directory).resolve()
    directory.mkdir(mode=0o700, parents=True, exist_ok=False)
    os.chmod(directory, 0o700)
    database = directory / 'workflows.sqlite3'
    with sqlite3.connect(database) as db:
        db.execute('CREATE TABLE client_isolation(client_id TEXT PRIMARY KEY,workspace TEXT NOT NULL,owner TEXT NOT NULL)')
        db.execute('INSERT INTO client_isolation VALUES (?,?,?)', ('subway', 'client-subway', 'subway-client'))
        db.execute('CREATE TABLE client_source_bindings(connection_id TEXT PRIMARY KEY)')
        db.execute('CREATE TABLE data_source_connections(connection_id TEXT PRIMARY KEY,workspace TEXT NOT NULL,owner TEXT NOT NULL,secret TEXT,document TEXT NOT NULL)')
    os.chmod(database, 0o600)
    private_write(directory / 'data-source.key', Fernet.generate_key().decode() + '\n')
    proxy_secret = secrets.token_urlsafe(48)
    salt = secrets.token_hex(16)
    password_hash = hashlib.scrypt(password.encode(), salt=salt.encode(), n=16384, r=8, p=1, dklen=64).hex()
    backend = dict(BUILDER_CLIENT_ID='subway', BUILDER_SUBWAY_PROXY_SECRET=proxy_secret,
        BUILDER_DATABASE_URL=str(database), BUILDER_DATA_SOURCE_KEY_FILE=str(directory / 'data-source.key'))
    frontend = dict(BUILDER_SUBWAY_LOGIN_EMAIL=email, BUILDER_SUBWAY_LOGIN_PASSWORD_HASH=salt + ':' + password_hash,
        BUILDER_SUBWAY_PROXY_SECRET=proxy_secret, BUILDER_SUBWAY_API_URL='http://127.0.0.1:8021')
    for filename, values in [('backend.env', backend), ('frontend.env', frontend)]:
        private_write(directory / filename, ''.join(key + '=' + json.dumps(value) + '\n' for key, value in values.items()))
    private_write(directory / 'login.txt', 'Email: ' + email + '\nPassword: ' + password + '\n')
    return backend


def create_subway_app(env):
    from workflow_api.client_isolation import ClientIsolation
    isolation = ClientIsolation.configured(env)
    if isolation is None or isolation.client != 'subway':
        raise ValueError('Use the dedicated Subway configuration.')
    if isolation.data_enabled:
        from workflow_api.live_providers import create_configured_app
        return create_configured_app(env)
    from workflow_api.main import create_app
    from workflow_api.storage import WorkflowStore
    from workflow_api.service import WorkflowService
    from workflow_api.registry_adapter import RegistryAdapter
    from registry import RegistryService, WorkspacePolicy
    registry = RegistryAdapter(RegistryService(WorkspacePolicy(isolation.subject['workspace_id'])))
    service = WorkflowService(WorkflowStore(isolation.database), registry_adapter=registry)
    return create_app(service, database=isolation.database, roles=['viewer'], dev_auth=False,
        planning_available=False, runtime_enabled=False, start_workers=False,
        planning_worker_enabled=False, google_oauth_config=env, environment_name='development')


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--config', type=Path, required=True)
    p.add_argument('--port', type=int, default=8021)
    a = p.parse_args()
    env = dict((line.split('=', 1)[0], json.loads(line.split('=', 1)[1]))
               for line in a.config.read_text().splitlines() if line.strip() and not line.startswith('#'))
    if env.get('BUILDER_CLIENT_ID') != 'subway':
        raise SystemExit('Use the Subway configuration.')
    # Prevent imported modules from loading shared credentials or configuration.
    for key in list(os.environ):
        if key.startswith(('BUILDER_', 'OPENAI_', 'GOOGLE_', 'GMAIL_', 'SMTP_', 'SLACK_')):
            del os.environ[key]
    os.environ.update(env)
    app = create_subway_app(env)
    import uvicorn
    uvicorn.run(app, host='127.0.0.1', port=a.port)
