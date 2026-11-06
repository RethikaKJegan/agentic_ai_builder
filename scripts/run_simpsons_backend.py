"""Run the full existing backend with only the private Simpsons configuration."""
import argparse
import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def configured_environment(path, role):
    env = {}
    for line in Path(path).read_text().splitlines():
        if line.strip() and not line.lstrip().startswith('#'):
            key, raw = line.split('=', 1)
            env[key] = json.loads(raw)
    if env.get('BUILDER_CLIENT_ID') != 'simpsons':
        raise ValueError('Use the private Simpsons backend configuration.')
    for key in list(os.environ):
        if key.startswith(('BUILDER_', 'GOOGLE_', 'GMAIL_', 'SMTP_', 'OPENAI_', 'SLACK_')):
            del os.environ[key]
    env['BUILDER_PROCESS_ROLE'] = role
    os.environ.update(env)
    return env


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--config', type=Path, required=True)
    p.add_argument('--port', type=int, default=8020)
    p.add_argument('--role', choices=['api', 'worker', 'combined'], default='combined')
    p.add_argument('--check', action='store_true', help='Validate startup without listeners, worker execution or network calls.')
    a = p.parse_args()
    env = configured_environment(a.config, a.role)
    from workflow_api.live_providers import create_configured_app
    app = create_configured_app(env)
    if a.check:
        import hashlib
        import hmac
        import secrets
        import time
        from fastapi.testclient import TestClient
        payload = f'simpsons.{int(time.time()) + 60}.{secrets.token_hex(24)}'
        assertion = payload + '.' + hmac.new(env['BUILDER_SIMPSONS_PROXY_SECRET'].encode(), payload.encode(), hashlib.sha256).hexdigest()
        # Deliberately omit the lifespan context so no background job can run.
        client = TestClient(app)
        try:
            assert client.get('/session').status_code == 401
            client.headers['x-builder-client-assertion'] = assertion
            session = client.get('/session')
            assert session.status_code == 200 and session.json()['data']['mode'] == 'client-isolated'
            sources = client.get('/data-sources')
            assert sources.status_code == 200 and len(sources.json()['data']['items']) == 2
            ontology = client.get('/business-ontology/v1')
            assert ontology.status_code == 200 and ontology.json()['data']['workspace'] is not None
            assert client.get('/data-sources/foreign-company/metadata').status_code == 404
        finally:
            client.close()
        print(json.dumps(dict(client_id='simpsons', subject=app.state.workflow_auth['subject'],
            runtime_available=app.state.workflow_service.runtime_runner is not None,
            planner_available=app.state.workflow_service.planner is not None,
            source_connections=len(app.state.data_sources.client_sources), authenticated_http_checks=5, network_calls=0)))
    elif a.role == 'worker':
        import asyncio
        import signal
        async def serve():
            stop = asyncio.Event()
            loop = asyncio.get_running_loop()
            for sig in (signal.SIGINT, signal.SIGTERM):
                loop.add_signal_handler(sig, stop.set)
            async with app.router.lifespan_context(app):
                await stop.wait()
        asyncio.run(serve())
    else:
        import uvicorn
        uvicorn.run(app, host='127.0.0.1', port=a.port)
