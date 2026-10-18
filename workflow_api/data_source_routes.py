"""Session-protected data-source routes using the existing safe API envelope."""
from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.concurrency import run_in_threadpool

from .data_sources import DataSources, DataSourceWorker
from .service import ApiFailure
from .data_queries import DataQueries
from .data_query_jobs import DataQueryJobs
from .data_operations import DataOperations


def install(app,service,auth,env,reference):
    manager=DataSources(service.store,env)
    app.state.data_sources=manager
    queries=DataQueries(manager)
    app.state.data_queries=queries
    from .kg_records import KnowledgeRecords
    records=KnowledgeRecords(manager.semantic,queries)
    def current_authority(workspace, owner):
        current=getattr(app.state,'workflow_auth',auth)
        return current if current['subject']=={'workspace_id':workspace,'subject_id':owner} else None
    manager.semantic.authenticate=current_authority
    jobs=DataQueryJobs(queries,current_authority)
    app.state.data_query_jobs=jobs
    app.state.data_source_worker=DataSourceWorker(manager)
    operations = DataOperations(manager, current_authority)
    app.state.data_operations = operations
    from .database_workflows import DatabaseWorkflows
    database_workflows = DatabaseWorkflows(service, operations, queries, current_authority)
    app.state.database_workflows = service.database_workflows = database_workflows
    database_workflows.register(auth)
    if getattr(service, 'runtime_runner', None) is not None:
        service.runtime_runner.connectors.update(database_workflows.connectors())

    async def call(fn,*args,status=200):
        try:
            data=await run_in_threadpool(fn,getattr(app.state,'workflow_auth',auth),*args)
            return JSONResponse(service.envelope(reference(),status,data),status_code=status,headers={'Cache-Control':'no-store'})
        except ApiFailure as exc:
            return JSONResponse(service.failure(reference(),exc),status_code=exc.status,headers={'Cache-Control':'no-store'})
        except Exception:
            exc=ApiFailure('DATA_SOURCE_UNAVAILABLE','The database connection service is unavailable. Refresh status before repeating a mutation.',503)
            return JSONResponse(service.failure(reference(),exc),status_code=503,headers={'Cache-Control':'no-store'})

    @app.get('/knowledge-graph')
    async def semantic_graph():return await call(manager.semantic.get)

    @app.post('/knowledge-graph/records')
    async def semantic_records(request:Request):
        try:data=await body(request)
        except Exception:return await call(bad_input)
        return await call(records.explore,data)

    @app.post('/knowledge-graph/infer')
    async def semantic_inference():return await call(manager.semantic.request)

    @app.post('/knowledge-graph/review/{relationship_id}')
    async def semantic_review(relationship_id:str,request:Request):
        try:data=await body(request)
        except Exception:return await call(bad_input)
        return await call(manager.semantic.review,relationship_id,data)

    @app.post('/knowledge-graph/preview')
    async def knowledge_preview(request:Request):
        try:data=await body(request)
        except Exception:return await call(bad_input)
        return await call(database_workflows.preview,data)

    @app.get('/data-operations')
    async def operation_status():return await call(operations.status)

    @app.get('/data-operations/{operation_id}')
    async def operation_detail(operation_id:str):return await call(operations.get,operation_id)

    @app.post('/data-operations/read')
    async def operation_read(request:Request):
        try:data=await body(request)
        except Exception:return await call(bad_input)
        return await call(operations.read,data)

    @app.post('/data-operations/prepare')
    async def operation_prepare(request:Request):
        try:data=await body(request)
        except Exception:return await call(bad_input)
        return await call(operations.prepare,data,request.headers.get('Idempotency-Key'))

    @app.post('/data-operations/{operation_id}/execute')
    async def operation_execute(operation_id:str,request:Request):
        try:data=await body(request)
        except Exception:return await call(bad_input)
        return await call(operations.execute,operation_id,data)

    @app.post('/data-operations/{operation_id}/recover')
    async def operation_recover(operation_id:str,request:Request):
        try:
            data=await body(request)
            if data != {}:raise ValueError()
        except Exception:return await call(bad_input)
        return await call(operations.recover,operation_id,request.headers.get('Idempotency-Key'))

    @app.get('/data-queries')
    async def query_status():return await call(queries.status)

    @app.get('/data-queries/jobs')
    async def query_jobs():return await call(jobs.list)

    @app.post('/data-queries/jobs')
    async def submit_query_job(request:Request):
        try:data=await body(request)
        except Exception:return await call(bad_input)
        return await call(jobs.submit,data,request.headers.get('Idempotency-Key'),status=202)

    @app.get('/data-queries/jobs/{job_id}')
    async def query_job(job_id:str):return await call(jobs.get,job_id)

    @app.get('/data-queries/jobs/{job_id}/result')
    async def query_job_result(job_id:str):return await call(jobs.result,job_id)

    @app.post('/data-queries/jobs/{job_id}/cancel')
    async def cancel_query_job(job_id:str):return await call(jobs.cancel,job_id)

    @app.post('/data-queries/{action}')
    async def query_action(action:str,request:Request):
        if action not in {'plan','execute'}:return await call(bad_input)
        try:data=await body(request)
        except Exception:return await call(bad_input)
        return await call(queries.plan if action=='plan' else queries.execute,data)

    @app.get('/data-sources')
    async def connections():return await call(manager.list)

    @app.get('/data-refresh')
    async def refresh_status():return await call(manager.refresh.get)

    @app.post('/data-refresh/{connection_id}')
    async def refresh_settings(connection_id:str,request:Request):
        try:data=await body(request)
        except Exception:return await call(bad_input)
        return await call(manager.refresh.edit,connection_id,data)

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

    @app.get('/data-relationships/v2')
    async def detailed_relationships():return await call(manager.relationships.detailed.get)

    @app.get('/data-ontology')
    async def ontology():return await call(manager.relationships.ontology.get)

    @app.post('/data-ontology/{relationship_id}')
    async def ontology_review(relationship_id:str,request:Request):
        try:data=await body(request)
        except Exception:return await call(bad_input)
        return await call(manager.relationships.ontology.edit,relationship_id,data)

    @app.post('/data-relationships/v2/mapping/{node_id}')
    async def entity_mapping(node_id:str,request:Request):
        try:data=await body(request)
        except Exception:return await call(bad_input)
        return await call(manager.relationships.detailed.edit,node_id,data)

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
