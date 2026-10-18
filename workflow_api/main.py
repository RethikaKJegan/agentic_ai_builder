"""FastAPI transport. Local development authentication is explicitly opt-in."""
import hmac
import os
import re
from pathlib import Path
from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, StreamingResponse
import json
from starlette.concurrency import run_in_threadpool
from starlette.exceptions import HTTPException as StarletteHTTPException
from .service import ApiFailure, WorkflowService
from .storage import WorkflowStore
from .registry_adapter import load_registry_config
from .security import origins, deployment_mode, request_correlation, planning_deadline
from contextvars import ContextVar

request_reference = ContextVar("builder_request_reference", default=None)

ROOT = Path(__file__).resolve().parents[1]
COOKIE = 'builder_dev_session'
ROLE_PERMISSIONS = {
    'builder': ['workflow.view', 'workflow.plan', 'workflow.edit', 'workflow.validate', 'tools.read', 'tools.assign', 'runs.view'],
    'viewer': ['workflow.view', 'tools.read', 'runs.view'],
    'approver': ['workflow.view', 'workflow.approve', 'tools.read', 'runs.view'],
    'admin': ['workflow.view', 'workflow.plan', 'workflow.edit', 'workflow.validate', 'workflow.approve', 'workflow.publish', 'workflow.delete', 'events.ingest', 'tools.read', 'tools.assign', 'runs.view'],
}


def create_app(service=None, dev_auth=None, roles=None, database=None, planning_available=None, registry_config=None,
               runtime_enabled=None, lifecycle_adapter=None, trigger_secrets=None, start_workers=True,
               ui_origins=None, environment_name=None, planner_timeout_seconds=180, planning_worker_enabled=True, google_oauth_config=None):
    enabled = dev_auth if dev_auth is not None else os.getenv('BUILDER_DEV_AUTH') == '1'
    mode = deployment_mode(environment_name or os.getenv('BUILDER_ENVIRONMENT', 'development'))
    allowed_origins = origins(ui_origins if ui_origins is not None else os.getenv('BUILDER_UI_ORIGINS'))
    configured_roles = roles or os.getenv('BUILDER_DEV_ROLES', 'builder').split(',')
    if any(role not in ROLE_PERMISSIONS for role in configured_roles):
        raise ValueError('Configure known development roles only.')
    adapter, extra_permissions, extra_scopes = None, [], []
    configuration = registry_config or os.getenv('BUILDER_REGISTRY_CONFIG')
    if service is None and configuration:
        adapter, extra_permissions, extra_scopes = load_registry_config(configuration)
    workflow_service = service or WorkflowService(WorkflowStore(database or os.getenv('BUILDER_DATABASE_URL') or ROOT / '.local/workflows.sqlite3'), registry_adapter=adapter,
                                                  lifecycle_adapter=lifecycle_adapter, trigger_secrets=trigger_secrets)
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
    workers = []
    if start_workers and workflow_service.runtime_runner is not None and os.getenv('BUILDER_RUNTIME_WORKER') == '1':
        from runtime.worker import RuntimeWorker
        runtime_worker = RuntimeWorker(workflow_service.runtime_runner, lambda workspace, subject: auth if auth['subject'] == {'workspace_id': workspace, 'subject_id': subject} else None,
                                       interval=float(os.getenv('BUILDER_RUNTIME_WORKER_INTERVAL', '1')))
        runtime_worker.start(); workers.append(runtime_worker)
    if start_workers and workflow_service.runtime_runner is not None and os.getenv('BUILDER_TRIGGER_WORKER') == '1':
        from .scheduler import TriggerScheduler
        scheduler = TriggerScheduler(workflow_service, lambda workspace, subject: auth if auth['subject'] == {'workspace_id': workspace, 'subject_id': subject} else None,
                                     poll_source=getattr(workflow_service, 'trigger_poller', None),
                                     interval=float(os.getenv('BUILDER_TRIGGER_INTERVAL', '5')))
        scheduler.start(); workers.append(scheduler)
    app = FastAPI(title='Agentic AI Builder workflow API', docs_url=None, redoc_url=None)
    app.state.workflow_service = workflow_service
    app.state.workflow_auth = auth
    from .planning_jobs import PlanningJobs
    planning_jobs = PlanningJobs(workflow_service,
        lambda workspace, subject: auth if auth['subject'] == {'workspace_id': workspace, 'subject_id': subject} else None,
        deadline=planning_deadline(planner_timeout_seconds))
    app.state.planning_jobs = planning_jobs
    from .worker_control import WorkerSupervisor
    app.state.worker_registration = WorkerSupervisor(workflow_service.store,[],role='api')
    app.state.workers = workers
    app.state.allowed_origins = allowed_origins
    app.state.environment_name = mode

    @app.on_event('startup')
    def start_planning():
        if planning_worker_enabled:
            planning_jobs.start()
            app.state.data_source_worker.start()
            app.state.data_query_jobs.start()

    @app.on_event('shutdown')
    async def stop_workers():
        planning_jobs.stop()
        app.state.data_source_worker.stop()
        app.state.data_query_jobs.stop()
        for worker in app.state.workers:
            worker.stop()

    def error(code, message, status):
        result = workflow_service.failure(request_reference.get() or f'req_{uuid4().hex}', ApiFailure(code, message, status))
        return JSONResponse(result, status_code=status, headers={'Cache-Control': 'no-store'})

    @app.exception_handler(StarletteHTTPException)
    async def route_error(request, exc):
        if exc.status_code == 404 and request.url.path.startswith('/procurement/'):
            return error('PROCUREMENT_UNAVAILABLE', 'Procurement is unavailable in this backend. Enable BUILDER_PROCUREMENT_ENABLED=1 and restart scripts/run_live_backend.py on the frontend configured port.', 503)
        return error('API_ROUTE_UNAVAILABLE', 'This API route is unavailable. Restart the configured Builder backend with the current code.', exc.status_code)

    from .google_connection_routes import install as install_google_connections
    install_google_connections(app, workflow_service, auth, google_oauth_config or dict(os.environ), lambda: request_reference.get() or f'req_{uuid4().hex}')
    from .google_tools import install as install_google_tools
    install_google_tools(workflow_service, app.state.google_connections)
    from .google_tool_routes import install as install_google_tool_routes
    install_google_tool_routes(app, workflow_service, auth, lambda: request_reference.get() or f'req_{uuid4().hex}')

    from .data_source_routes import install as install_data_sources
    install_data_sources(app, workflow_service, auth, google_oauth_config or dict(os.environ), lambda: request_reference.get() or f'req_{uuid4().hex}')

    @app.middleware('http')
    async def protect(request, call_next):
        candidate = request.headers.get('x-request-id', '')
        reference = candidate if re.fullmatch(r'[a-zA-Z0-9_-]{1,128}', candidate) else f'req_{uuid4().hex}'
        reference_token = request_reference.set(reference)
        candidate_correlation = request.headers.get('x-correlation-id', reference)
        correlation = candidate_correlation if re.fullmatch(r'[a-zA-Z0-9_-]{1,128}', candidate_correlation) else reference
        correlation_token = request_correlation.set(correlation)
        try:
            google_callback = request.method == 'GET' and request.url.path == '/integrations/google/callback'
            if google_callback:
                request.state.google_oauth_query = dict(request.query_params)
                request.scope['query_string'] = b''  # Keep authorization codes out of upstream access logs.
            host = request.url.hostname
            origin = request.headers.get('origin')
            if origin and origin not in allowed_origins:
                response = error('ORIGIN_NOT_AUTHORIZED', 'This request origin is not authorized.', 403)
            elif not enabled:
                response = error('AUTHENTICATION_REQUIRED', 'Authentication is not configured. Enable development authentication only for local use.', 401)
            elif host not in {'localhost', '127.0.0.1', '::1', 'testserver'} or (request.headers.get('sec-fetch-site') == 'cross-site' and not google_callback):
                response = error('DEVELOPMENT_AUTH_LOCAL_ONLY', 'Development sessions are restricted to loopback hosts and origins.', 403)
            elif not google_callback and request.url.path != '/session' and not request.url.path.startswith('/webhooks/') and not hmac.compare_digest(request.cookies.get(COOKIE, ''), session):
                response = error('AUTHENTICATION_REQUIRED', 'Your local session expired or is invalid. Reopen the workspace to recover it.', 401)
            else:
                response = await call_next(request)
            response.headers['Cache-Control'] = 'no-store'
            response.headers['X-Builder-Service'] = 'workflow-api'
            response.headers['X-Request-ID'] = reference
            response.headers['X-Correlation-ID'] = correlation
            return response
        finally:
            request_reference.reset(reference_token)
            request_correlation.reset(correlation_token)

    @app.get('/session')
    def get_session():
        data = dict(auth=auth, mode='local-development', planning_jobs_available=True, planning_available=bool(os.getenv('OPENAI_API_KEY')) if planning_available is None else planning_available,
                    runtime_available=workflow_service.runtime_runner is not None, approval_service_available=workflow_service.runtime_runner is not None)
        response = JSONResponse(workflow_service.envelope(request_reference.get() or f'req_{uuid4().hex}', 200, data))
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
            if operation == 'list_workflows':
                result = await run_in_threadpool(workflow_service.handle, body, auth, read_cursor=request.query_params.get('cursor'))
            else:
                result = await run_in_threadpool(workflow_service.handle, body, auth)
            return JSONResponse(result, status_code=result['status'])
        except Exception:
            return error('INVALID_REQUEST', 'The request must contain valid JSON and revision references.', 400)

    @app.post('/planning-jobs')
    async def submit_planning(request: Request):
        try:
            job = await run_in_threadpool(planning_jobs.submit, await request.json(), auth)
            return JSONResponse(workflow_service.envelope(request_reference.get(), 202, job), status_code=202)
        except ApiFailure as exc:
            return error(exc.code, str(exc), exc.status)
        except Exception:
            return error('INVALID_REQUEST', 'Use a valid canonical planning request.', 400)

    @app.get('/planning-jobs/{job_id}')
    async def get_planning(job_id: str):
        try:
            job = await run_in_threadpool(planning_jobs.get, job_id, auth)
            return JSONResponse(workflow_service.envelope(request_reference.get(), 200, job))
        except ApiFailure as exc:
            return error(exc.code, str(exc), exc.status)

    @app.delete('/planning-jobs/{job_id}')
    async def cancel_planning(job_id: str):
        try:
            job = await run_in_threadpool(planning_jobs.cancel, job_id, auth)
            return JSONResponse(workflow_service.envelope(request_reference.get(), 200, job))
        except ApiFailure as exc:
            return error(exc.code, str(exc), exc.status)

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

    async def lifecycle_dispatch(request, operation, additions=None):
        try:
            if request.method == 'GET':
                body = {'request_id': request.query_params.get('request_id', f'req_{uuid4().hex}'), 'payload': {}}
            else:
                body = await request.json()
                if not isinstance(body, dict) or body.get('operation') != operation or not isinstance(body.get('payload'), dict):
                    return error('INVALID_REQUEST', 'Use the workflow operations v2 envelope for this route.', 400)
            additions = additions or {}
            payload = body['payload']
            for key, value in additions.items():
                if key in payload and payload[key] != value:
                    return error('REFERENCE_MISMATCH', 'Route and payload references must match.', 400)
                payload[key] = value
            result = await run_in_threadpool(workflow_service.handle_lifecycle, operation, body, auth,
                                             signature=request.headers.get('x-builder-signature'),
                                             timestamp=request.headers.get('x-builder-timestamp'),
                                             after_sequence=int(request.query_params.get('after_sequence', '0')),
                                             workflow_cursor=request.query_params.get('cursor'),
                                             operation_id=additions.get('operation_id'), binding_id=additions.get('binding_id'),
                                             job_id=additions.get('job_id'))
            return JSONResponse(result, status_code=result['status'])
        except (ValueError, TypeError):
            return error('INVALID_REQUEST', 'The lifecycle request is invalid.', 400)

    @app.get('/workflows/{workflow_id}/release-state')
    async def release_state(workflow_id: str):
        if auth.get('decision') != 'allow' or 'workflow.view' not in auth['permissions']:
            return error('OPERATION_NOT_AUTHORIZED', 'Workflow read permission is required.', 403)
        from .release_read import read_release_state
        data = await run_in_threadpool(read_release_state, workflow_service.store, auth['subject']['workspace_id'], workflow_id)
        return JSONResponse(workflow_service.envelope(request_reference.get(), 200, data))

    @app.post('/workflows/{workflow_id}/releases')
    async def activate_release(workflow_id: str, request: Request):
        return await lifecycle_dispatch(request, 'activate_release', {'workflow_id': workflow_id})

    @app.post('/workflows/{workflow_id}/disable')
    async def disable_release(workflow_id: str, request: Request):
        return await lifecycle_dispatch(request, 'disable_release', {'workflow_id': workflow_id})

    @app.delete('/workflows/{workflow_id}')
    async def delete_workflow(workflow_id: str, request: Request):
        return await lifecycle_dispatch(request, 'delete_workflow', {'workflow_id': workflow_id})

    @app.get('/workflow-overview')
    async def workflow_overview(request: Request):
        return await lifecycle_dispatch(request, 'list_workflow_overview')

    @app.get('/workflow-overview/events')
    async def workflow_overview_events(request: Request):
        if 'text/event-stream' in request.headers.get('accept', ''):
            try:
                raw_cursor = request.headers.get('last-event-id') or request.query_params.get('after_sequence', '0')
                events = await run_in_threadpool(workflow_service.lifecycle.overview, auth, int(raw_cursor))
                async def stream():
                    yield 'retry: 2000\n\n'
                    for item in events['items']:
                        yield f"id: {item['sequence']}\ndata: {json.dumps(item, separators=(',', ':'))}\n\n"
                    if not events['items']:
                        yield ': keepalive\n\n'
                return StreamingResponse(stream(), media_type='text/event-stream', headers={'X-Accel-Buffering': 'no', 'X-Builder-Update-Strategy': 'bounded-polling', 'Cache-Control': 'no-store'})
            except (ValueError, TypeError):
                return error('INVALID_REQUEST', 'Use a non-negative event sequence.', 400)
        return await lifecycle_dispatch(request, 'subscribe_workflow_overview')

    @app.get('/lifecycle-operations/{operation_id}')
    async def lifecycle_operation(operation_id: str, request: Request):
        return await lifecycle_dispatch(request, 'get_lifecycle_operation', {'operation_id': operation_id})

    @app.post('/trigger-bindings/{binding_id}/events')
    async def trigger_event(binding_id: str, request: Request):
        return await lifecycle_dispatch(request, 'ingest_trigger_event', {'binding_id': binding_id})

    @app.post('/webhooks/{provider_id}/{binding_id}')
    async def provider_webhook(provider_id: str, binding_id: str, request: Request):
        """Provider-facing delivery endpoint. Signature verification happens on raw bytes."""
        try:
            raw = await request.body()
            trigger = await run_in_threadpool(workflow_service.lifecycle.verify_webhook, binding_id, provider_id, raw,
                                              request.headers.get('x-hub-signature-256') if provider_id == 'github_webhook' else request.headers.get('x-slack-signature') if provider_id == 'slack_events' else request.headers.get('x-builder-signature'),
                                              request.headers.get('x-slack-request-timestamp') if provider_id == 'slack_events' else request.headers.get('x-builder-timestamp'))
            event = json.loads(raw)
            if not isinstance(event, dict):
                return error('INVALID_EVENT', 'The webhook payload must be an object.', 400)
            if provider_id == 'slack_events' and event.get('type') == 'url_verification':
                return JSONResponse({'challenge': event.get('challenge', '')})
            # In production this is an isolated provider principal. The local
            # server uses the configured development administrator only after
            # the provider signature has been verified.
            result = await run_in_threadpool(workflow_service.lifecycle.ingest, binding_id, event, auth)
            return JSONResponse(workflow_service.envelope(f'req_{uuid4().hex}', 200, result))
        except Exception:
            return error('SOURCE_VERIFICATION_FAILED', 'The webhook could not be verified or processed.', 401)

    @app.post('/trigger-bindings/{binding_id}/poll')
    async def poll_trigger(binding_id: str, request: Request):
        return await lifecycle_dispatch(request, 'poll_trigger', {'binding_id': binding_id})

    @app.post('/dispatch-jobs/{job_id}/replay')
    async def replay_dispatch(job_id: str, request: Request):
        return await lifecycle_dispatch(request, 'replay_dispatch_job', {'job_id': job_id})

    @app.get('/tools')
    async def tools(request: Request):
        return await dispatch(request, 'list_tools')

    @app.get('/agents/capabilities')
    async def capabilities(request: Request):
        return await dispatch(request, 'list_capabilities')

    async def runtime_history(request, kind, run_id=None):
        from runtime.history import query_options
        from runtime.service import RuntimeFailure
        try:
            if workflow_service.runtime_runner is None:
                return error('SERVICE_UNAVAILABLE', 'The runtime is not connected.', 503)
            runtime = workflow_service.runtime_runner.runtime
            options = query_options(dict(request.query_params), kind)
            function = runtime.events if kind == 'events' else runtime.list_runs
            args = (run_id, auth) if kind == 'events' else (auth,)
            data = await run_in_threadpool(function, *args, **options)
            return JSONResponse(workflow_service.envelope(request_reference.get() or f'req_{uuid4().hex}', 200, data))
        except RuntimeFailure as exc:
            return error(exc.code, str(exc), exc.status)
        except (ValueError, TypeError):
            return error('INVALID_REQUEST', 'Use valid history filters and cursors.', 400)

    @app.get('/runs/{run_id}')
    async def run(run_id: str, request: Request):
        return await dispatch(request, 'get_run', {'run_id': run_id})

    @app.get('/runs')
    async def runs(request: Request):
        return await runtime_history(request, 'runs')

    @app.get('/cases')
    async def cases(request: Request):
        manager = getattr(workflow_service, 'reply_cases', None)
        if manager is None:
            return error('SERVICE_UNAVAILABLE', 'Reply monitoring is not configured.', 503)
        if 'runs.view' not in auth['permissions']:
            return error('OPERATION_NOT_AUTHORIZED', 'Run access is required.', 403)
        try:
            items = await run_in_threadpool(manager.list_cases, auth['subject']['workspace_id'])
            return JSONResponse(workflow_service.envelope(f'req_{uuid4().hex}', 200,
                {'items': items, 'monitor': getattr(workflow_service, 'reply_monitor_health', {'state': 'unknown'})}))
        except Exception:
            return error('CASE_LIST_UNAVAILABLE', 'Case records are unavailable.', 503)

    @app.post('/cases/{case_id}/actions')
    async def case_action(case_id: str, request: Request):
        manager = getattr(workflow_service, 'reply_cases', None)
        if manager is None:
            return error('SERVICE_UNAVAILABLE', 'Reply monitoring is not configured.', 503)
        if 'workflow.approve' not in auth['permissions'] or not {'admin', 'approver'} & set(auth['roles']):
            return error('OPERATION_NOT_AUTHORIZED', 'Approval access is required.', 403)
        if not re.fullmatch(r'run_[A-Za-z0-9]+', case_id):
            return error('INVALID_REQUEST', 'Use a valid case ID.', 400)
        try:
            body = await request.json()
            if (not isinstance(body, dict) or set(body) != {'reply_id', 'kind'} or
                    not isinstance(body['reply_id'], str) or not isinstance(body['kind'], str)):
                return error('INVALID_REQUEST', 'Choose a case action and reply.', 400)
            result = await run_in_threadpool(manager.send_action, auth['subject']['workspace_id'], case_id,
                                             body['reply_id'], body['kind'])
            return JSONResponse(workflow_service.envelope(f'req_{uuid4().hex}', 200, result))
        except ValueError as exc:
            return error(str(exc), 'This case action is unavailable or already attempted.', 409)
        except Exception:
            return error('SMTP_DELIVERY_UNCERTAIN', 'Email submission was uncertain; do not retry automatically.', 503)

    @app.get('/approvals')
    async def approvals(request: Request):
        return await dispatch(request, 'list_approvals')

    @app.get('/runs/{run_id}/events')
    async def events(run_id: str, request: Request):
        return await runtime_history(request, 'events', run_id)

    @app.get('/monitoring')
    async def monitoring(request: Request):
        from runtime.service import RuntimeFailure
        try:
            if workflow_service.runtime_runner is None:
                return error('SERVICE_UNAVAILABLE', 'The runtime and monitoring service is not connected.', 503)
            workflow_service.runtime_runner.runtime.authorize(auth, 'runs.view', {'admin', 'builder', 'viewer', 'approver'})
            from runtime.history import query_options
            data = await run_in_threadpool(workflow_service.runtime_runner.runtime.monitoring, auth, **query_options(dict(request.query_params), 'monitoring'))
            return JSONResponse(workflow_service.envelope(request_reference.get() or f'req_{uuid4().hex}', 200, data))
        except RuntimeFailure as exc:
            return error(exc.code, str(exc), exc.status)
        except Exception:
            return error('SERVICE_UNAVAILABLE', 'Monitoring data is unavailable.', 503)

    @app.get('/worker-health')
    async def worker_health():
        if 'runs.view' not in auth['permissions']:
            return error('OPERATION_NOT_AUTHORIZED','Worker monitoring access is required.',403)
        from .worker_control import health
        data = await run_in_threadpool(health,workflow_service.store,auth['subject']['workspace_id'])
        return JSONResponse(workflow_service.envelope(request_reference.get(),200,data))

    @app.get('/workspace/{collection}')
    async def workspace_collection(collection: str, request: Request):
        if collection not in {'settings', 'knowledge', 'governance'}:
            return error('NOT_FOUND', 'The workspace collection was not found.', 404)
        if auth.get('decision')!='allow' or 'workflow.view' not in auth['permissions']:
            return error('OPERATION_NOT_AUTHORIZED','Workspace read permission is required.',403)
        table = {'settings': 'workspace_settings', 'knowledge': 'knowledge_sources', 'governance': 'governance_policies'}[collection]
        try:
            with workflow_service.store.transaction(write=False) as db:
                if collection == 'settings':
                    rows = db.execute('SELECT key, value, updated_at FROM workspace_settings WHERE workspace=? ORDER BY key', (auth['subject']['workspace_id'],)).fetchall()
                    items = [{'key': k, 'value': json.loads(v), 'updated_at': t} for k, v, t in rows]
                else:
                    rows = db.execute(f'SELECT document FROM {table} WHERE workspace=? ORDER BY updated_at DESC', (auth['subject']['workspace_id'],)).fetchall()
                    items = [json.loads(row[0]) for row in rows]
            return JSONResponse(workflow_service.envelope(f'req_{uuid4().hex}', 200, {'items': items, 'total': len(items), 'has_more': False, 'next_cursor': None}))
        except Exception:
            return error('INVALID_API_DATA', 'The workspace collection is unavailable.', 400)

    @app.put('/workspace/{collection}/{item_id}')
    async def save_workspace_item(collection: str, item_id: str, request: Request):
        if collection not in {'settings', 'knowledge', 'governance'}:
            return error('NOT_FOUND', 'The workspace collection was not found.', 404)
        if 'admin' not in auth['roles'] or auth.get('decision')!='allow' or 'workspace:write' not in auth['scopes']:
            return error('OPERATION_NOT_AUTHORIZED', 'Workspace administration is required.', 403)
        try:
            payload = await request.json()
            from registry.safety import reject_secrets
            reject_secrets(payload)
            if not isinstance(payload,dict) or not re.fullmatch(r'[a-zA-Z0-9_-]{1,64}',item_id):
                return error('INVALID_REQUEST','Use a valid workspace item identifier and JSON object.',400)
            if collection=='settings':
                if set(payload)!={'value'} or len(json.dumps(payload,allow_nan=False).encode())>16000:
                    return error('SETTING_INVALID','Use a value smaller than 16 KiB.',400)
                if item_id=='notifications' and (not isinstance(payload['value'],str) or len(payload['value'])>2000):
                    return error('SETTING_INVALID','Notification preference must be text of at most 2000 characters.',400)
            import datetime
            updated = datetime.datetime.now(datetime.timezone.utc).isoformat()
            workspace = auth['subject']['workspace_id']
            with workflow_service.store.transaction() as db:
                if collection == 'settings':
                    db.execute('INSERT INTO workspace_settings VALUES (?, ?, ?, ?) ON CONFLICT(workspace, key) DO UPDATE SET value=excluded.value, updated_at=excluded.updated_at', (workspace, item_id, json.dumps(payload.get('value')), updated))
                    document = {'key': item_id, 'value': payload.get('value'), 'updated_at': updated}
                else:
                    table = 'knowledge_sources' if collection == 'knowledge' else 'governance_policies'
                    document = {'id': item_id, **payload, 'updated_at': updated}
                    db.execute(f'INSERT INTO {table} VALUES (?, ?, ?, ?) ON CONFLICT({"source_id" if collection == "knowledge" else "policy_id"}) DO UPDATE SET document=excluded.document, updated_at=excluded.updated_at', (workspace, item_id, json.dumps(document), updated))
            return JSONResponse(workflow_service.envelope(f'req_{uuid4().hex}', 200, document))
        except Exception:
            return error('INVALID_API_DATA', 'The workspace item is invalid.', 400)

    @app.post('/workflows/{workflow_id}/submit-for-approval')
    async def submit_for_approval(workflow_id: str, request: Request):
        try:
            from .review_actions import submit
            body=await request.json()
            if not isinstance(body,dict) or not isinstance(body.get('payload'),dict) or body['payload'].get('workflow_id')!=workflow_id:
                return error('REFERENCE_MISMATCH','Route and workflow reference must match.',400)
            result=await run_in_threadpool(submit,workflow_service,body,auth)
            return JSONResponse(result,status_code=result['status'])
        except ApiFailure as exc:
            result=workflow_service.failure(request_reference.get() or f'req_{uuid4().hex}',exc)
            return JSONResponse(result,status_code=exc.status,headers={'Cache-Control':'no-store'})
        except Exception:return error('APPROVAL_SUBMISSION_FAILED','The approval submission could not be confirmed.',503)

    @app.post('/integrations/{provider}/test')
    async def integration_test(provider: str, request: Request):
        try:
            from .integration_checks import check
            payload=await request.json()
            if not isinstance(payload,dict) or set(payload)-{'mode'}:
                return error('INVALID_REQUEST','Only a check mode is accepted; credentials and destinations stay on the server.',400)
            result=await run_in_threadpool(check,workflow_service,provider,auth,payload.get('mode','configuration'))
            return JSONResponse(workflow_service.envelope(request_reference.get(),200,result))
        except ApiFailure as exc:return error(exc.code,str(exc),exc.status)
        except Exception:return error('INTEGRATION_CHECK_FAILED','The provider check could not be completed.',503)

    @app.post('/approvals/{approval_id}/decision')
    async def decision(approval_id: str, request: Request):
        return await dispatch(request, 'decide_approval', {'approval_id': approval_id})

    return app


app = create_app()
