"""Separate business ontology routes under the existing session transport."""
from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.concurrency import run_in_threadpool
from .business_ontology import BusinessOntology
from .service import ApiFailure


def install(app, service, auth, reference, env=None):
    ontology = BusinessOntology(service.store)
    app.state.business_ontology = ontology
    from .business_documents import BusinessDocuments
    from .business_generation import BusinessGeneration
    from .business_compiler import BusinessCompiler
    compiler=BusinessCompiler(ontology)
    app.state.business_compiler=compiler
    from .business_rules import BusinessRules
    rules=BusinessRules(ontology,compiler)
    app.state.business_rules=rules
    documents=BusinessDocuments(ontology)
    def current_authority(workspace,owner):
        current=getattr(app.state,'workflow_auth',auth)
        return current if current['subject']=={'workspace_id':workspace,'subject_id':owner} else None
    from .business_sources import BusinessSources
    sources=BusinessSources(ontology,app.state.data_sources,resolve=current_authority)
    app.state.business_sources=sources
    from .business_graph import BusinessGraph
    graph=BusinessGraph(ontology,compiler,app.state.data_sources,current_authority)
    app.state.business_graph=graph
    jobs=BusinessGeneration(ontology,current_authority,env=env)
    app.state.business_generation=jobs
    from .business_reference import BusinessReference
    from .business_intelligence import BusinessIntelligence
    reference_drafts=BusinessReference(ontology,current_authority)
    intelligence=BusinessIntelligence(ontology,graph)
    app.state.business_reference=reference_drafts
    app.state.business_intelligence=intelligence
    from .business_warranty import BusinessWarranty
    warranty=BusinessWarranty(ontology,graph)
    app.state.business_warranty=warranty
    from .business_policies import BusinessPolicies
    policies=BusinessPolicies(ontology,graph,current_authority)
    app.state.business_policies=policies
    from .business_identity import BusinessIdentity
    identity_service=BusinessIdentity(ontology,graph)
    app.state.business_identity=identity_service
    from .business_monitoring import BusinessMonitoring
    monitoring=BusinessMonitoring(ontology,graph)
    app.state.business_monitoring=monitoring
    from .business_rule_execution import BusinessRuleExecution
    rule_execution=BusinessRuleExecution(ontology,graph,current_authority)
    app.state.business_rule_execution=rule_execution
    from .business_knowledge import BusinessKnowledge
    knowledge=BusinessKnowledge(ontology,current_authority)
    app.state.business_knowledge=knowledge

    async def call(fn, *args):
        try:
            data = await run_in_threadpool(fn, getattr(app.state,'workflow_auth',auth), *args)
            return JSONResponse(service.envelope(reference(),200,data),headers={'Cache-Control':'no-store'})
        except ApiFailure as exc:
            return JSONResponse(service.failure(reference(),exc),status_code=exc.status,headers={'Cache-Control':'no-store'})
        except Exception:
            exc = ApiFailure('BUSINESS_ONTOLOGY_UNAVAILABLE','Business ontology is unavailable. Refresh before retrying.',503)
            return JSONResponse(service.failure(reference(),exc),status_code=503,headers={'Cache-Control':'no-store'})

    @app.get('/business-ontology/v1/sources')
    async def source_status():
        return await call(sources.get)

    @app.post('/business-ontology/v1/sources/{connection_id}/profile')
    async def profile_source(connection_id:str,request:Request):
        if await body(request)!={}:return await call(sources.profile,None)
        return await call(sources.profile,connection_id)

    @app.post('/business-ontology/v1/source-records')
    async def source_records(request:Request):
        return await call(sources.records,await body(request))

    @app.get('/business-ontology/v1')
    async def get():
        return await call(ontology.get)

    @app.post('/business-ontology/v1/initialize')
    async def initialize(request: Request):
        try:
            raw = await request.body()
            if len(raw) > 4096:
                raise ValueError()
            import json
            body = json.loads(raw)
        except Exception:
            body = None
        return await call(ontology.initialize, body)

    @app.get('/business-ontology/v1/versions/{version_id}')
    async def version(version_id: str):
        return await call(ontology.version, version_id)

    async def body(request):
        try:
            raw=await request.body()
            if len(raw)>100000:raise ValueError()
            import json
            return json.loads(raw)
        except Exception:return None

    @app.post('/business-ontology/v1/knowledge/import')
    async def import_knowledge(request:Request):
        return await call(knowledge.import_package,await body(request))

    @app.get('/business-ontology/v1/versions/{version_id}/knowledge')
    async def inspect_knowledge(version_id:str):
        return await call(knowledge.inspect,version_id)

    @app.get('/business-ontology/v1/versions/{version_id}/knowledge/concepts/{concept_id}')
    async def inspect_knowledge_concept(version_id:str,concept_id:str):
        return await call(knowledge.inspect,version_id,concept_id)

    @app.post('/business-ontology/v1/versions/{version_id}/knowledge/diagnose')
    async def diagnose_knowledge(version_id:str,request:Request):
        return await call(knowledge.diagnose,version_id,await body(request))

    @app.post('/business-ontology/v1/documents')
    async def add_document(request:Request):
        return await call(documents.add,await body(request))

    @app.post('/business-ontology/v1/import-reference')
    async def import_reference(request:Request):
        return await call(documents.import_reference,await body(request))

    @app.get('/business-ontology/v1/documents/{document_id}')
    async def document(document_id:str):
        return await call(documents.get,document_id)

    @app.get('/business-ontology/v1/jobs')
    async def list_jobs():
        return await call(jobs.list)

    @app.post('/business-ontology/v1/jobs')
    async def submit_job(request:Request):
        return await call(jobs.submit,await body(request))

    @app.get('/business-ontology/v1/jobs/{job_id}')
    async def get_job(job_id:str):
        return await call(jobs.get,job_id)

    @app.post('/business-ontology/v1/jobs/{job_id}/cancel')
    async def cancel_job(job_id:str,request:Request):
        data=await body(request)
        if data!={}:return await call(jobs.submit,None)
        return await call(jobs.cancel,job_id)

    @app.get('/business-ontology/v1/versions/{version_id}/compilation')
    async def compilation(version_id:str):
        return await call(compiler.get,version_id)

    @app.post('/business-ontology/v1/versions/{version_id}/compilation')
    async def compile_version(version_id:str,request:Request):
        return await call(compiler.compile,version_id,await body(request))

    @app.get('/business-ontology/v1/versions/{version_id}/rule-catalogue')
    async def rule_catalogue(version_id:str):
        return await call(rules.view,version_id)

    @app.post('/business-ontology/v1/versions/{version_id}/competency-queries/run')
    async def run_competency(version_id:str,request:Request):
        return await call(rules.run,version_id,await body(request))

    @app.get('/business-ontology/v1/versions/{version_id}/graph-plan')
    async def graph_plan(version_id:str):
        return await call(graph.plan,version_id)

    @app.post('/business-ontology/v1/versions/{version_id}/graphs')
    async def build_graph(version_id:str,request:Request):
        return await call(graph.build,version_id,await body(request))

    @app.get('/business-ontology/v1/versions/{version_id}/graphs/{graph_id}')
    async def graph_snapshot(version_id:str,graph_id:str):
        return await call(graph.get,version_id,graph_id)

    @app.get('/business-ontology/v1/versions/{version_id}/module-coverage')
    async def module_coverage(version_id:str):
        return await call(reference_drafts.coverage,version_id)

    @app.post('/business-ontology/v1/reference-modules')
    async def add_reference_modules(request:Request):
        return await call(reference_drafts.apply,await body(request))

    @app.get('/business-ontology/v1/versions/{version_id}/graphs/{graph_id}/intelligence')
    async def intelligence_catalogue(version_id:str,graph_id:str):
        return await call(intelligence.catalogue,version_id,graph_id)

    @app.post('/business-ontology/v1/versions/{version_id}/graphs/{graph_id}/intelligence/run')
    async def intelligence_report(version_id:str,graph_id:str,request:Request):
        return await call(intelligence.run,version_id,graph_id,await body(request))

    @app.post('/business-ontology/v1/versions/{version_id}/graphs/{graph_id}/warranty-readiness')
    async def warranty_readiness(version_id:str,graph_id:str,request:Request):
        return await call(warranty.run,version_id,graph_id,await body(request))

    @app.get('/business-ontology/v1/warranty-policies')
    async def policy_list():return await call(policies.list)

    @app.post('/business-ontology/v1/warranty-policies')
    async def policy_save(request:Request):return await call(policies.save,await body(request))

    @app.post('/business-ontology/v1/warranty-policies/import-implementation')
    async def import_warranty_implementation(request: Request):
        return await call(policies.import_implementation, await body(request))

    @app.get('/business-ontology/v1/warranty-policies/{policy_id}')
    async def policy_get(policy_id:str):return await call(policies.get,policy_id)

    @app.post('/business-ontology/v1/versions/{version_id}/graphs/{graph_id}/policy-comparison')
    async def policy_compare(version_id:str,graph_id:str,request:Request):
        return await call(policies.compare,version_id,graph_id,await body(request))

    @app.post('/business-ontology/v1/versions/{version_id}/graphs/{graph_id}/associations')
    async def associations(version_id:str,graph_id:str,request:Request):
        return await call(identity_service.run,version_id,graph_id,await body(request))

    @app.post('/business-ontology/v1/versions/{version_id}/graphs/{graph_id}/warranty-assessment')
    async def warranty_assessment(version_id:str,graph_id:str,request:Request):
        return await call(policies.assess,version_id,graph_id,await body(request))

    @app.post('/business-ontology/v1/versions/{version_id}/graphs/{graph_id}/monitoring-readiness')
    async def monitoring_readiness(version_id:str,graph_id:str,request:Request):
        return await call(monitoring.run,version_id,graph_id,await body(request))

    @app.get('/business-ontology/v1/versions/{version_id}/graphs/{graph_id}/rule-execution')
    async def execution_catalogue(version_id:str,graph_id:str):return await call(rule_execution.catalogue,version_id,graph_id)

    @app.post('/business-ontology/v1/versions/{version_id}/graphs/{graph_id}/rule-evidence')
    async def save_rule_evidence(version_id:str,graph_id:str,request:Request):return await call(rule_execution.save,version_id,graph_id,await body(request))

    @app.get('/business-ontology/v1/rule-evidence/{evidence_id}')
    async def get_rule_evidence(evidence_id:str):return await call(rule_execution.get,evidence_id)

    @app.post('/business-ontology/v1/versions/{version_id}/graphs/{graph_id}/rules/execute')
    async def execute_rule(version_id:str,graph_id:str,request:Request):return await call(rule_execution.run,version_id,graph_id,await body(request))
