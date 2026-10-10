"""FastAPI transport. Local development authentication is explicitly opt-in."""
import hmac
import os
from pathlib import Path
from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from starlette.concurrency import run_in_threadpool
from .service import ApiFailure, WorkflowService
from .storage import WorkflowStore
from .registry_adapter import load_registry_config

ROOT = Path(__file__).resolve().parents[1]
COOKIE = 'builder_dev_session'
ROLE_PERMISSIONS = {
    'builder': ['workflow.view', 'workflow.plan', 'workflow.edit', 'workflow.validate', 'tools.read', 'tools.assign', 'runs.view'],
    'viewer': ['workflow.view', 'tools.read', 'runs.view'],
    'approver': ['workflow.view', 'workflow.approve', 'tools.read', 'runs.view'],
    'admin': ['workflow.view', 'workflow.plan', 'workflow.edit', 'workflow.validate', 'workflow.approve', 'workflow.publish', 'tools.read', 'tools.assign', 'runs.view'],
}


def create_app(service=None, dev_auth=None, roles=None, database=None, planning_available=None, registry_config=None, runtime_enabled=None):
    enabled = dev_auth if dev_auth is not None else os.getenv('BUILDER_DEV_AUTH') == '1'
    configured_roles = roles or os.getenv('BUILDER_DEV_ROLES', 'builder').split(',')
    if any(role not in ROLE_PERMISSIONS for role in configured_roles):
        raise ValueError('Configure known development roles only.')
    adapter, extra_permissions, extra_scopes = None, [], []
    configuration = registry_config or os.getenv('BUILDER_REGISTRY_CONFIG')
    if service is None and configuration:
        adapter, extra_permissions, extra_scopes = load_registry_config(configuration)
    workflow_service = service or WorkflowService(WorkflowStore(database or ROOT / '.local/workflows.sqlite3'), registry_adapter=adapter)
    connect_runtime = runtime_enabled if runtime_enabled is not None else os.getenv('BUILDER_RUNTIME_ENABLED') == '1'
    if connect_runtime:
        from runtime import RuntimeService
        from runtime.graph import GraphRunner
        workflow_service.runtime_runner = workflow_service.runtime_runner or GraphRunner(RuntimeService(workflow_service))
    if workflow_service.runtime_runner is not None:
        # Explicitly configured development admins may execute. Browser/client
        # data never changes these permissions, and builders stay view/edit only.
        runtime_permissions = {'workflow.execute'} if 'admin' in configured_roles else set()
    else:
        runtime_permissions = set()
    session = uuid4().hex
    auth = dict(subject=dict(subject_id='local-builder', workspace_id='local-workspace'),
                roles=configured_roles, permissions=sorted({p for role in configured_roles for p in ROLE_PERMISSIONS[role]}),
                scopes=['workspace:read', 'workspace:write'], decision='allow')
    if {'admin', 'builder'}.intersection(configured_roles):
        auth['permissions'] = sorted(set(auth['permissions']) | set(extra_permissions))
        auth['scopes'] = sorted(set(auth['scopes']) | set(extra_scopes))
    auth['permissions'] = sorted(set(auth['permissions']) | runtime_permissions)
    app = FastAPI(title='Agentic AI Builder workflow API', docs_url=None, redoc_url=None)
    app.state.workflow_service = workflow_service

    def error(code, message, status):
        result = workflow_service.failure(f'req_{uuid4().hex}', ApiFailure(code, message, status))
        return JSONResponse(result, status_code=status, headers={'Cache-Control': 'no-store'})

    @app.middleware('http')
    async def protect(request, call_next):
        host = request.url.hostname
        if not enabled:
            return error('AUTHENTICATION_REQUIRED', 'Configure a trusted session adapter or enable local development authentication.', 401)
        if host not in {'localhost', '127.0.0.1', '::1', 'testserver'}:
            return error('DEVELOPMENT_AUTH_LOCAL_ONLY', 'Development sessions are restricted to loopback hosts.', 403)
        origin = request.headers.get('origin')
        allowed_origins = os.getenv('BUILDER_UI_ORIGINS', 'http://localhost:3000,http://127.0.0.1:3000,http://127.0.0.1:3100').split(',')
        if origin and origin not in allowed_origins:
            return error('ORIGIN_NOT_AUTHORIZED', 'This request origin is not authorized.', 403)
        if request.url.path != '/session' and not hmac.compare_digest(request.cookies.get(COOKIE, ''), session):
            return error('AUTHENTICATION_REQUIRED', 'Open the workspace to establish your local session.', 401)
        response = await call_next(request)
        response.headers['Cache-Control'] = 'no-store'
        return response

    @app.get('/session')
    def get_session():
        data = dict(auth=auth, mode='local-development', planning_available=bool(os.getenv('OPENAI_API_KEY')) if planning_available is None else planning_available,
                    runtime_available=workflow_service.runtime_runner is not None, approval_service_available=workflow_service.runtime_runner is not None)
        response = JSONResponse(workflow_service.envelope(f'req_{uuid4().hex}', 200, data))
        response.set_cookie(COOKIE, session, httponly=True, samesite='strict', path='/api/backend', max_age=28800)
        return response

    async def dispatch(request, operation, additions=None):
        try:
            if request.method == 'GET':
                body = dict(request_id=request.query_params.get('request_id', f'req_{uuid4().hex}'), operation=operation, payload={})
            else:
                body = await request.json()
                if not isinstance(body, dict) or body.get('operation') != operation or not isinstance(body.get('payload'), dict):
                    return error('INVALID_REQUEST', 'Use the canonical request envelope for this route.', 400)
            for key, value in (additions or {}).items():
                if key in body['payload'] and body['payload'][key] != value:
                    return error('REFERENCE_MISMATCH', 'Route and payload revision references must match.', 400)
                body['payload'][key] = value
            result = await run_in_threadpool(workflow_service.handle, body, auth)
            return JSONResponse(result, status_code=result['status'])
        except Exception:
            return error('INVALID_REQUEST', 'The request must contain valid JSON and revision references.', 400)

    @app.post('/workflows/plan')
    async def plan(request: Request):
        return await dispatch(request, 'plan_workflow')

    @app.get('/workflows')
    async def listing(request: Request):
        return await dispatch(request, 'list_workflows')

    @app.get('/workflows/{workflow_id}')
    async def read(workflow_id: str, request: Request):
        additions = {'workflow_id': workflow_id}
        if request.query_params.get('version'):
            try:
                additions['workflow_version'] = int(request.query_params['version'])
            except ValueError:
                return error('INVALID_REQUEST', 'Use an integer revision.', 400)
        return await dispatch(request, 'get_workflow', additions)

    @app.put('/workflows/{workflow_id}/versions/{version}')
    async def save(workflow_id: str, version: int, request: Request):
        return await dispatch(request, 'save_workflow_version', {'workflow_id': workflow_id, 'workflow_version': version})

    @app.post('/workflows/{workflow_id}/validate')
    async def validate_route(workflow_id: str, request: Request):
        return await dispatch(request, 'validate_workflow', {'workflow_id': workflow_id})

    @app.post('/workflows/{workflow_id}/approve')
    async def approve(workflow_id: str, request: Request):
        return await dispatch(request, 'approve_workflow', {'workflow_id': workflow_id})

    @app.post('/workflows/{workflow_id}/execute')
    async def execute(workflow_id: str, request: Request):
        return await dispatch(request, 'execute_workflow', {'workflow_id': workflow_id})

    @app.get('/tools')
    async def tools(request: Request):
        return await dispatch(request, 'list_tools')

    @app.get('/agents/capabilities')
    async def capabilities(request: Request):
        return await dispatch(request, 'list_capabilities')

    @app.get('/runs/{run_id}')
    async def run(run_id: str, request: Request):
        return await dispatch(request, 'get_run', {'run_id': run_id})

    @app.get('/runs/{run_id}/events')
    async def events(run_id: str, request: Request):
        return await dispatch(request, 'list_run_events', {'run_id': run_id})

    @app.post('/approvals/{approval_id}/decision')
    async def decision(approval_id: str, request: Request):
        return await dispatch(request, 'decide_approval', {'approval_id': approval_id})

    return app


app = create_app()
