"""Display titles are independent of immutable executable workflow revisions."""
from copy import deepcopy
from datetime import datetime, timezone
import json


def project(db, workspace, workflow):
    row=db.execute('SELECT value FROM workspace_settings WHERE workspace=? AND key=?',
                   (workspace,'workflow_title:'+workflow['workflow_id'])).fetchone()
    if not row:return workflow
    title=json.loads(row[0])
    if not isinstance(title,str) or not 1<=len(title.strip())<=200 or any(ord(c)<32 for c in title):return workflow
    result=deepcopy(workflow)
    result['name']=title
    return result


def rename(service,auth,workflow_id,body):
    from .service import ApiFailure
    from registry.safety import reject_secrets
    service.authorize(auth,'save_workflow_version')
    reject_secrets(body)
    if (not isinstance(body,dict) or set(body)!={'name','expected_name'} or
            not isinstance(body['name'],str) or not 1<=len(body['name'].strip())<=200 or
            any(ord(c)<32 for c in body['name']) or not isinstance(body['expected_name'],str)):
        raise ApiFailure('WORKFLOW_NAME_INVALID','Enter a workflow name of 1–200 characters without line breaks.',400)
    workspace=auth['subject']['workspace_id'];name=body['name'].strip()
    with service.store.transaction() as db:
        if db.execute('SELECT 1 FROM lifecycle_tombstones WHERE workspace=? AND workflow_id=?',(workspace,workflow_id)).fetchone():
            raise ApiFailure('WORKFLOW_NOT_FOUND','Workflow not found.',404)
        workflow=service.store.get(db,workspace,workflow_id)
        if not workflow:raise ApiFailure('WORKFLOW_NOT_FOUND','Workflow not found.',404)
        current=project(db,workspace,workflow)['name']
        # Repeating a confirmed title is harmless, including a transport retry.
        if current!=name and current!=body['expected_name']:
            raise ApiFailure('WORKFLOW_NAME_CONFLICT','The workflow name changed. Refresh and try again.',409)
        db.execute('INSERT INTO workspace_settings VALUES (?,?,?,?) ON CONFLICT(workspace,key) DO UPDATE SET value=excluded.value,updated_at=excluded.updated_at',
                   (workspace,'workflow_title:'+workflow_id,json.dumps(name),datetime.now(timezone.utc).isoformat()))
        service.lifecycle.emit(db,workspace,workflow_id,'workflow.renamed')
    return {'workflow_id':workflow_id,'name':name}


def install(app,service,auth):
    from registry.contracts import RegistryError
    from fastapi import Request
    from fastapi.responses import JSONResponse
    from starlette.concurrency import run_in_threadpool
    from uuid import uuid4
    from .service import ApiFailure
    @app.post('/workflows/{workflow_id}/rename')
    async def rename_workflow(workflow_id:str,request:Request):
        reference=request.headers.get('X-Request-ID') or 'req_'+uuid4().hex
        try:
            result=await run_in_threadpool(rename,service,auth,workflow_id,await request.json())
            return JSONResponse(service.envelope(reference,200,result),headers={'Cache-Control':'no-store'})
        except ApiFailure as exc:
            return JSONResponse(service.failure(reference,exc),status_code=exc.status)
        except RegistryError as exc:
            failure=ApiFailure(exc.code,'Choose a workflow name without sensitive information.',400)
            return JSONResponse(service.failure(reference,failure),status_code=400)
        except ValueError:
            exc=ApiFailure('WORKFLOW_NAME_INVALID','Enter a valid workflow name.',400)
            return JSONResponse(service.failure(reference,exc),status_code=400)
