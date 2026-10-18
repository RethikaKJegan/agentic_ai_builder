"""HTTP boundary for owned Google connections and the single external callback."""
import re
import secrets
from fastapi import Request
from fastapi.responses import JSONResponse, RedirectResponse
from starlette.concurrency import run_in_threadpool
from .google_connections import GoogleConnections, BROWSER_COOKIE, CALLBACK
from .service import ApiFailure


def install(app, service, auth, env, reference):
    manager=GoogleConnections(service.store,env)
    app.state.google_connections=manager

    def response(data):
        return JSONResponse(service.envelope(reference(),200,data),headers={'Cache-Control':'no-store'})

    def failure(exc):
        result=service.failure(reference(),exc)
        return JSONResponse(result,status_code=exc.status,headers={'Cache-Control':'no-store'})

    @app.get('/integrations/google/connections')
    async def connections():
        try:return response(await run_in_threadpool(manager.list,auth))
        except ApiFailure as exc:return failure(exc)
        except Exception:return failure(ApiFailure('GOOGLE_CONNECTIONS_UNAVAILABLE','Google connections could not be loaded.',503))

    @app.put('/integrations/google/workflow-default')
    async def workflow_default(request: Request):
        try:
            body = await request.json()
            if not isinstance(body, dict) or set(body) != {'connection_id'} or not isinstance(body['connection_id'], str):
                raise ApiFailure('INVALID_REQUEST', 'Select one owned Google account.', 400)
            return response(await run_in_threadpool(manager.set_workflow_default, auth, body['connection_id']))
        except ApiFailure as exc:
            return failure(exc)

    async def authorize(request, connection_id=None):
        try:
            body=await request.json()
            if not isinstance(body,dict) or set(body)-{'capabilities'}:raise ApiFailure('INVALID_REQUEST','Choose Google capabilities only.',400)
            browser=request.cookies.get(BROWSER_COOKIE,'')
            if not re.fullmatch(r'[A-Za-z0-9_-]{43}',browser):browser=secrets.token_urlsafe(32)
            data=await run_in_threadpool(manager.authorize,auth,browser,body.get('capabilities',[]),connection_id)
            result=response(data)
            # Lax is essential for Google's top-level redirect; application sessions remain Strict.
            result.set_cookie(BROWSER_COOKIE,browser,httponly=True,samesite='lax',secure=manager.redirect_uri.startswith('https:'),path='/api/backend/integrations/google',max_age=600)
            return result
        except ApiFailure as exc:return failure(exc)
        except Exception:return failure(ApiFailure('GOOGLE_AUTHORIZE_FAILED','Google authorization could not be started.',503))

    @app.post('/integrations/google/authorize')
    async def start(request:Request):return await authorize(request)

    @app.post('/integrations/google/connections/{connection_id}/authorize')
    async def manage(connection_id:str,request:Request):return await authorize(request,connection_id)

    @app.get(CALLBACK)
    async def callback(request:Request):
        # Session belongs to its initiating subject. No shared app-session cookie is needed on the cross-site return.
        query=getattr(request.state,'google_oauth_query',{})
        try:
            result=await run_in_threadpool(manager.complete,query.get('state',''),request.cookies.get(BROWSER_COOKIE,''),query.get('code'),bool(query.get('error')))
        except ApiFailure as exc:
            result='expired' if exc.code=='OAUTH_SESSION_INVALID' else 'account_mismatch' if exc.code=='GOOGLE_ACCOUNT_MISMATCH' else 'failed'
        except Exception:result='failed'
        if not manager.return_origin:return failure(ApiFailure('GOOGLE_SETUP_REQUIRED','Google callback configuration is unavailable.',503))
        # Fixed server-owned destination. No provider text, codes, tokens or user redirect values are reflected.
        output=RedirectResponse(manager.return_origin+'/app/integrations?google='+result,status_code=303)
        output.headers['Referrer-Policy']='no-referrer'
        output.delete_cookie(BROWSER_COOKIE,path='/api/backend/integrations/google',secure=manager.redirect_uri.startswith('https:'),httponly=True,samesite='lax')
        return output

    @app.post('/integrations/google/connections/{connection_id}/verify')
    async def verify(connection_id:str):
        try:return response(await run_in_threadpool(manager.verify,auth,connection_id))
        except ApiFailure as exc:return failure(exc)
        except Exception:return failure(ApiFailure('GOOGLE_VERIFY_FAILED','Google verification could not be completed.',503))

    @app.post('/integrations/google/connections/{connection_id}/disconnect')
    async def disconnect(connection_id:str):
        try:return response(await run_in_threadpool(manager.disconnect,auth,connection_id))
        except ApiFailure as exc:return failure(exc)
        except Exception:return failure(ApiFailure('GOOGLE_DISCONNECT_FAILED','Disconnection could not be confirmed. Refresh connection status.',503))
