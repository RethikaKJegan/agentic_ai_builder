"""Standalone loopback transport using existing services, without importing main.app.

Importing workflow_api.main constructs its default database. This separate factory
avoids that side effect while retaining the canonical envelopes and operation handlers.
"""
import hmac
import os
from uuid import uuid4
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from starlette.concurrency import run_in_threadpool
from workflow_api.service import ApiFailure

COOKIE = 'builder_extension_session'
PERMISSIONS = ['workflow.view', 'workflow.plan', 'workflow.edit', 'workflow.validate', 'workflow.approve',
               'workflow.publish', 'workflow.delete', 'workflow.execute', 'events.ingest',
               'tools.read', 'tools.assign', 'tools.manage', 'runs.view']


def create_transport(service, auth, planning_available=False):
    app = FastAPI(title='Builder optional connector extension', docs_url=None, redoc_url=None)
    app.state.workflow_service = service
    session = uuid4().hex

    def error(code, message, status):
        return JSONResponse(service.failure('req_' + uuid4().hex, ApiFailure(code, message, status)), status_code=status,
                            headers={'Cache-Control': 'no-store'})

    @app.middleware('http')
    async def protect(request, call_next):
        if request.url.hostname not in {'localhost', '127.0.0.1', '::1', 'testserver'}:
            return error('DEVELOPMENT_AUTH_LOCAL_ONLY', 'The extension is restricted to loopback hosts.', 403)
        allowed = os.getenv('BUILDER_EXTENSION_UI_ORIGINS', ','.join(
            f'http://{host}:{port}' for host in ['localhost', '127.0.0.1'] for port in [3000, 3001, 3002, 3100])).split(',')
        if request.headers.get('origin') and request.headers['origin'] not in allowed:
            return error('ORIGIN_NOT_AUTHORIZED', 'This origin is not authorized for the extension.', 403)
        if request.url.path != '/session' and not hmac.compare_digest(request.cookies.get(COOKIE, ''), session):
            return error('AUTHENTICATION_REQUIRED', 'Open the extension workspace to establish its local session.', 401)
        response = await call_next(request)
        response.headers['Cache-Control'] = 'no-store'
        return response

    @app.get('/session')
    def get_session():
        response = JSONResponse(service.envelope('req_' + uuid4().hex, 200,
            {'auth': auth, 'mode': 'local-development', 'planning_available': planning_available,
             'runtime_available': True, 'approval_service_available': True}))
        response.set_cookie(COOKIE, session, httponly=True, samesite='strict', path='/api/backend', max_age=28800)
        return response

    def register(path, method, operation, lifecycle=False):
        async def endpoint(request: Request):
            try:
                additions = dict(request.path_params)
                if 'version' in additions: additions['workflow_version'] = int(additions.pop('version'))
                if method == 'GET':
                    payload = dict(additions)
                    if request.query_params.get('version'): payload['workflow_version'] = int(request.query_params['version'])
                    body = {'request_id': 'req_' + uuid4().hex, 'operation': operation, 'payload': payload}
                else:
                    body = await request.json()
                    if not isinstance(body, dict) or body.get('operation') != operation or not isinstance(body.get('payload'), dict):
                        return error('INVALID_REQUEST', 'Use the canonical operation envelope.', 400)
                    for key, value in additions.items():
                        if key in body['payload'] and body['payload'][key] != value:
                            return error('REFERENCE_MISMATCH', 'Route and payload references must match.', 400)
                        body['payload'][key] = value
                if lifecycle:
                    context = dict(additions, after_sequence=int(request.query_params.get('after_sequence', '0')))
                    result = await run_in_threadpool(service.handle_lifecycle, operation, body, auth, **context)
                else:
                    result = await run_in_threadpool(service.handle, body, auth)
                return JSONResponse(result, status_code=result['status'])
            except (TypeError, ValueError):
                return error('INVALID_REQUEST', 'Use valid JSON and exact revision references.', 400)
            except Exception:
                return error('SERVICE_UNAVAILABLE', 'The extension operation is unavailable.', 503)
        app.add_api_route(path, endpoint, methods=[method], name=operation)

    for path, method, operation in [
        ('/workflows/plan', 'POST', 'plan_workflow'), ('/workflows', 'GET', 'list_workflows'),
        ('/workflows/{workflow_id}', 'GET', 'get_workflow'),
        ('/workflows/{workflow_id}/versions/{version}', 'PUT', 'save_workflow_version'),
        ('/workflows/{workflow_id}/validate', 'POST', 'validate_workflow'),
        ('/workflows/{workflow_id}/approve', 'POST', 'approve_workflow'),
        ('/workflows/{workflow_id}/execute', 'POST', 'execute_workflow'),
        ('/tools', 'GET', 'list_tools'), ('/agents/capabilities', 'GET', 'list_capabilities'),
        ('/runs', 'GET', 'list_runs'), ('/runs/{run_id}', 'GET', 'get_run'),
        ('/runs/{run_id}/events', 'GET', 'list_run_events'), ('/approvals', 'GET', 'list_approvals'),
        ('/approvals/{approval_id}/decision', 'POST', 'decide_approval')]:
        register(path, method, operation)
    for path, method, operation in [('/workflow-overview', 'GET', 'list_workflow_overview'),
        ('/workflow-overview/events', 'GET', 'subscribe_workflow_overview'),
        ('/workflows/{workflow_id}/releases', 'POST', 'activate_release'),
        ('/workflows/{workflow_id}/disable', 'POST', 'disable_release'),
        ('/workflows/{workflow_id}', 'DELETE', 'delete_workflow'),
        ('/lifecycle-operations/{operation_id}', 'GET', 'get_lifecycle_operation')]:
        register(path, method, operation, True)

    @app.get('/monitoring')
    async def monitoring():
        data = await run_in_threadpool(service.runtime_runner.runtime.monitoring, auth)
        return JSONResponse(service.envelope('req_' + uuid4().hex, 200, data))

    @app.post('/integrations/{provider}/test')
    def readiness(provider: str):
        tools = service.registry.list_tools(auth)['data'].get('items', [])
        matches = [item for item in tools if item['definition']['provider_id'] == provider]
        if not matches: return error('INTEGRATION_UNSUPPORTED', 'This extension provider is not registered.', 400)
        configured = any(item['definition']['availability'] == 'enabled' for item in matches)
        return JSONResponse(service.envelope('req_' + uuid4().hex, 200, {
            'provider': provider, 'configured': configured, 'tested': False,
            'message': 'Extension configuration is available; no live connection test was performed.' if configured else 'Configure this provider in the separate extension setup.'}))
    return app
