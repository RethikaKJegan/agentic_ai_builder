"""Create one explicit tool-check DRAFT through the ordinary workflow save API."""
from uuid import uuid4
from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.concurrency import run_in_threadpool
from jsonschema import Draft202012Validator
from registry.safety import reject_secrets
from .service import ApiFailure

ALLOWED = {'google_sheets_read_rows','google_sheets_upsert_record','extension_sheets_create','extension_sheets_add_tabs',
           'extension_sheets_discover','extension_mail_search','extension_mail_message','extension_mail_thread',
           'extension_mail_draft','extension_mail_send','extension_mail_reply','extension_mail_attachment',
           'extension_calendar_list','extension_calendar_create','extension_calendar_update','extension_calendar_cancel'}


def install(app,service,auth,reference):
    def fail(exc):return JSONResponse(service.failure(reference(),exc),status_code=exc.status)

    @app.post('/integrations/google/tool-check-draft')
    async def draft(request:Request):
        try:
            service.authorize(auth,'save_workflow_version')
            body=await request.json()
            if not isinstance(body,dict) or set(body)-{'connection_id','tool_id','inputs','sheet_targets'}:
                raise ApiFailure('INVALID_REQUEST','Provide a connection, supported tool and explicit inputs.',400)
            identifier=body.get('connection_id');tool_id=body.get('tool_id')
            if not isinstance(identifier,str) or not identifier:
                raise ApiFailure('GOOGLE_CONNECTION_REQUIRED','Select a Google account for this tool-check draft.',400)
            if tool_id not in ALLOWED:raise ApiFailure('GOOGLE_TOOL_UNSUPPORTED','Choose a supported Google tool.',400)
            from connector_extension.catalog import CATALOG
            from connector_extension.examples import connector_workflow
            tool=CATALOG[tool_id]
            inputs=body.get('inputs')
            if not isinstance(inputs,dict) or list(Draft202012Validator(tool['input_schema']).iter_errors(inputs)):
                raise ApiFailure('CONNECTOR_INPUT_INVALID','Inputs do not match the selected tool schema.',400)
            reject_secrets(inputs)
            if service.runtime_runner is None or tool_id not in service.runtime_runner.connectors:
                raise ApiFailure('GOOGLE_TOOL_UNAVAILABLE','This Google tool is not registered in this deployment.',503)
            w=connector_workflow(tool_id,inputs,'google_check_'+uuid4().hex,body.get('sheet_targets'))
            w['metadata']['google_connection_id']=identifier
            w['name']='Google check · '+tool['capability']
            request_id=reference()
            result=await run_in_threadpool(service.handle,{'request_id':request_id,'operation':'save_workflow_version','idempotency_key':request_id,
                'payload':{'workflow_id':w['workflow_id'],'workflow_version':1,'base_version':0,'workflow':w}},auth)
            return JSONResponse(result,status_code=result['status'])
        except ApiFailure as exc:return fail(exc)
        except Exception:return fail(ApiFailure('GOOGLE_TOOL_DRAFT_FAILED','The tool-check draft could not be saved. Check its inputs and connection.',400))
