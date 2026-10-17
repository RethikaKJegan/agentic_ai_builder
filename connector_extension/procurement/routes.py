"""Procurement-only routes protected by the existing extension session middleware."""
from uuid import uuid4
from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.concurrency import run_in_threadpool
from registry.safety import reject_secrets
from registry.contracts import RegistryError
from runtime.service import RuntimeFailure
from workflow_api.service import ApiFailure
from .store import ProcurementError


def register_routes(app, service, auth):
    workflows=service.workflows
    def failure(code,status):
        return JSONResponse(workflows.failure('req_'+uuid4().hex,
            ApiFailure(code,'Procurement request was stopped; check setup, scope and action status.',status)),status_code=status)

    @app.get('/procurement/projects/{project_id}')
    async def status(project_id:str):
        try:
            workspace=service.authorize(auth)
            data=await run_in_threadpool(service.status,workspace,project_id)
            return JSONResponse(workflows.envelope('req_'+uuid4().hex,200,data))
        except (ProcurementError,RuntimeFailure) as exc:return failure(exc.code,403 if isinstance(exc,RuntimeFailure) else 404)

    async def mutate(request:Request, advance=False):
        try:
            body=await request.body()
            if len(body)>65536:return failure('REQUEST_TOO_LARGE',413)
            doc=await request.json();reject_secrets(doc)
            operation='procurement_advance' if advance else 'procurement_setup'
            if (not isinstance(doc,dict) or set(doc)!={'request_id','operation','idempotency_key','payload'} or
                doc['operation']!=operation or not isinstance(doc['idempotency_key'],str) or not doc['idempotency_key'] or
                not isinstance(doc['payload'],dict)):return failure('INVALID_REQUEST',400)
            if advance:
                project=request.path_params['project_id']
                if doc['payload']!={'project_id':project}:return failure('REFERENCE_MISMATCH',400)
                data=await run_in_threadpool(service.advance,project,auth)
            else:data=await run_in_threadpool(service.setup,doc['payload'],auth)
            return JSONResponse(workflows.envelope('req_'+uuid4().hex,200,data))
        except (ProcurementError,RuntimeFailure) as exc:return failure(exc.code,403 if isinstance(exc,RuntimeFailure) else 409)
        except RegistryError as exc:return failure(exc.code,400)
        except (ValueError,TypeError,KeyError):return failure('INVALID_REQUEST',400)
        except Exception:return failure('PROCUREMENT_UNAVAILABLE',503)

    @app.post('/procurement/projects')
    async def setup(request:Request):return await mutate(request)

    @app.post('/procurement/projects/{project_id}/advance')
    async def advance(request:Request):return await mutate(request,True)

    @app.post('/procurement/projects/{project_id}/retry-tracking')
    async def retry_tracking(request:Request):
        try:
            if len(await request.body())>4096:return failure('REQUEST_TOO_LARGE',413)
            doc=await request.json();reject_secrets(doc);payload=doc.get('payload',{})
            if (doc.get('operation')!='procurement_retry_tracking' or not isinstance(doc.get('idempotency_key'),str) or
                not doc['idempotency_key'] or set(payload)!={'project_id','expected_run_id','absence_confirmed'} or
                payload['project_id']!=request.path_params['project_id']):return failure('INVALID_REQUEST',400)
            data=await run_in_threadpool(service.retry_tracking,payload['project_id'],payload['expected_run_id'],payload['absence_confirmed'],auth)
            return JSONResponse(workflows.envelope('req_'+uuid4().hex,200,data))
        except (ProcurementError,RuntimeFailure) as exc:return failure(exc.code,403 if isinstance(exc,RuntimeFailure) else 409)
        except (ValueError,TypeError,KeyError,RegistryError):return failure('INVALID_REQUEST',400)
        except Exception:return failure('PROCUREMENT_UNAVAILABLE',503)


class ProcurementWorker:
    def __init__(self, service):
        import threading
        self.service=service;self.stop_event=threading.Event();self.thread=None
        self.health={'state':'starting','last_success':None,'last_error':None}
    def start(self):
        import threading,time
        if self.thread and self.thread.is_alive():return
        self.stop_event.clear()
        def run():
            while not self.stop_event.wait(3):
                try:
                    self.service.tick()
                    self.health={'state':'ready','last_success':time.time(),'last_error':None}
                except Exception:
                    self.health['state'],self.health['last_error']='error','PROCUREMENT_WORKER_FAILED'
                    import logging
                    logging.getLogger(__name__).warning('Procurement worker tick failed; durable state retained.')
        self.thread=threading.Thread(target=run,daemon=True,name='extension-procurement');self.thread.start()
    def stop(self):
        self.stop_event.set()
        if self.thread:self.thread.join(timeout=5)
