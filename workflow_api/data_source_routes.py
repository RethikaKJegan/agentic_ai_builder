"""Session-protected data-source routes using the existing safe API envelope."""
from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.concurrency import run_in_threadpool

from .data_sources import DataSources, DataSourceWorker
from .service import ApiFailure


def install(app,service,auth,env,reference):
    manager=DataSources(service.store,env)
    app.state.data_sources=manager
    app.state.data_source_worker=DataSourceWorker(manager)

    async def call(fn,*args):
        try:
            data=await run_in_threadpool(fn,auth,*args)
            return JSONResponse(service.envelope(reference(),200,data),headers={'Cache-Control':'no-store'})
        except ApiFailure as exc:
            return JSONResponse(service.failure(reference(),exc),status_code=exc.status,headers={'Cache-Control':'no-store'})
        except Exception:
            exc=ApiFailure('DATA_SOURCE_UNAVAILABLE','The database connection service is unavailable. Refresh status before repeating a mutation.',503)
            return JSONResponse(service.failure(reference(),exc),status_code=503,headers={'Cache-Control':'no-store'})

    @app.get('/data-sources')
    async def connections():return await call(manager.list)

    async def body(request):
        # Never echo credential-bearing request validation failures.
        raw=await request.body()
        if len(raw)>16384:raise ValueError()
        return await request.json()

    @app.post('/data-sources/test')
    async def test(request:Request):
        try:data=await body(request)
        except Exception:return await call(bad_input)
        return await call(manager.test,data)

    @app.post('/data-sources')
    async def connect(request:Request):
        try:data=await body(request)
        except Exception:return await call(bad_input)
        return await call(manager.connect,data)

    @app.get('/data-relationships')
    async def relationships():return await call(manager.relationships.get)

    @app.post('/data-relationships/build')
    async def build_relationships():return await call(manager.relationships.request)

    @app.post('/data-relationships/{kind}/{item_id}')
    async def edit_relationship(kind:str,item_id:str,request:Request):
        if kind not in {'review','annotation'}:return await call(bad_input)
        try:data=await body(request)
        except Exception:return await call(bad_input)
        return await call(manager.relationships.edit,kind,item_id,data)

    @app.get('/data-sources/{connection_id}')
    async def get(connection_id:str):return await call(manager.metadata,connection_id)

    @app.get('/data-sources/{connection_id}/metadata')
    async def metadata(connection_id:str):return await call(manager.metadata,connection_id)

    @app.post('/data-sources/{connection_id}/credentials')
    async def credentials(connection_id:str,request:Request):
        try:data=await body(request)
        except Exception:return await call(bad_input)
        return await call(manager.credentials,connection_id,data)

    @app.post('/data-sources/{connection_id}/{action}')
    async def action(connection_id:str,action:str):
        if action not in {'verify','refresh-metadata','disconnect'}:return await call(bad_input)
        return await call(manager.action,connection_id,action)


def bad_input(auth):
    raise ApiFailure('DATA_SOURCE_INPUT_INVALID','Supply a valid database connection request.',400)
