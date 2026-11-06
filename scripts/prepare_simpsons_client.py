"""Prepare a private, undeployed Simpsons login and backend from explicit inputs."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import secrets
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from scripts.integration_config import private_write
from scripts.provision_simpsons_client import provision


def prepare(source, directory, source_env, connection_ids, scope, knowledge_ids=(), email='alex.simpsons@example.test'):
    directory = Path(directory).resolve()
    directory.mkdir(mode=0o700, parents=True, exist_ok=False)
    os.chmod(directory, 0o700)
    source_key = source_env.get('BUILDER_DATA_SOURCE_KEY_FILE') or source_env.get('BUILDER_GOOGLE_KEY_FILE')
    if not source_key:
        raise ValueError('Supply the existing source encryption-key configuration.')
    report = provision(source, directory / 'workflows.sqlite3', ROOT / source_key,
                       directory / 'data-source.key', scope, connection_ids, knowledge_ids)
    password = secrets.token_urlsafe(24)
    salt = secrets.token_hex(16)
    digest = hashlib.scrypt(password.encode(), salt=salt.encode(), n=16384, r=8, p=1, dklen=64).hex()
    proxy_secret = secrets.token_urlsafe(48)
    backend = {k: v for k, v in source_env.items() if k.startswith('OPENAI_') or k in {
        'BUILDER_MODEL_RATES', 'BUILDER_MODEL_TOKENIZER', 'BUILDER_ENFORCE_USAGE_BUDGETS',
        'BUILDER_PLANNER_TIMEOUT_SECONDS'}}
    backend.update(BUILDER_CLIENT_ID='simpsons', BUILDER_DATABASE_URL=str(directory / 'workflows.sqlite3'),
        BUILDER_DATA_SOURCE_KEY_FILE=str(directory / 'data-source.key'), BUILDER_ENVIRONMENT='development',
        BUILDER_DEV_AUTH='1', BUILDER_PROCESS_ROLE='api', BUILDER_CLIENT_INTEGRATIONS='business-only',
        BUILDER_SIMPSONS_PROXY_SECRET=proxy_secret)
    frontend = dict(BUILDER_SIMPSONS_API_URL='http://127.0.0.1:8020',
        BUILDER_SIMPSONS_PROXY_SECRET=proxy_secret, BUILDER_SIMPSONS_LOGIN_EMAIL=email,
        BUILDER_SIMPSONS_LOGIN_PASSWORD_HASH=salt + ':' + digest)
    for name, values in [('backend.env', backend), ('frontend.env', frontend)]:
        private_write(directory / name, ''.join(k + '=' + json.dumps(v) + '\n' for k, v in values.items()))
    private_write(directory / 'login.txt', 'Temporary account: Alex Simpsons\nEmail: ' + email + '\nPassword: ' + password + '\n')
    private_write(directory / 'provisioning.json', json.dumps(report, indent=2) + '\n')
    return report


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source', type=Path, required=True)
    p.add_argument('--source-env', type=Path, required=True)
    p.add_argument('--directory', type=Path, required=True)
    p.add_argument('--workspace', required=True)
    p.add_argument('--owner', required=True)
    p.add_argument('--connection-id', action='append', required=True)
    p.add_argument('--knowledge-id', action='append', default=[])
    p.add_argument('--email', default='alex.simpsons@example.test')
    a = p.parse_args()
    # Parse without exporting the shared environment into this tenant process.
    env = {}
    for line in a.source_env.read_text().splitlines():
        if line.strip() and not line.lstrip().startswith('#') and '=' in line:
            key, value = line.split('=', 1)
            key = key.strip().removeprefix('export ')
            value = value.strip()
            env[key] = json.loads(value) if value.startswith('"') else value.strip("'")
    try:
        print(json.dumps(prepare(a.source, a.directory, env, a.connection_id,
            (a.workspace, a.owner), a.knowledge_id, a.email), indent=2))
    except Exception:
        raise SystemExit('Preparation failed. Inspect the explicit Simpsons inputs and use a fresh private output directory. No deployment occurred.') from None
