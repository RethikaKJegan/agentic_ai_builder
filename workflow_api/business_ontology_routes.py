"""Separate business ontology routes under the existing session transport."""
from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.concurrency import run_in_threadpool
from .business_ontology import BusinessOntology
from .service import ApiFailure
from runtime.service import RuntimeFailure


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
    from .business_retrieval import BusinessRetrieval
    retrieval=BusinessRetrieval(ontology,app.state.data_sources,current_authority,env=env)
    app.state.business_retrieval=retrieval
    from .business_investigations import BusinessInvestigations
    investigations=BusinessInvestigations(retrieval,env=env)
    app.state.business_investigations=investigations
    service.business_preparation=investigations.coverage.preparation
    service.business_preparation.registry=service.registry_adapter
    from .business_preparation import BusinessEvidenceAdapter
    service.business_evidence_adapter=BusinessEvidenceAdapter(service.business_preparation)
    if service.runtime_runner is not None:
        from .business_preparation import BusinessEvidenceConnector
        service.runtime_runner.connectors['business_retrieve_evidence']=BusinessEvidenceConnector(service.business_preparation)
    from .business_composition import BusinessComposition
    service.business_composition=BusinessComposition(service,service.business_preparation,model_id=(env or {}).get('OPENAI_MODEL','configured-model'))
    app.state.business_composition=service.business_composition
    app.state.client_packages=service.business_composition.packages
    if service.runtime_runner is not None:
        from .client_packages import PackageEvidenceConnector
        service.runtime_runner.connectors['client_package_read']=PackageEvidenceConnector(service.business_composition.packages)
    from .investigation_jobs import InvestigationJobs
    investigation_jobs=InvestigationJobs(investigations,current_authority,composition=service.business_composition)
    app.state.investigation_jobs=investigation_jobs
    from .composition_presentation import CompositionPresentation
    presentation=CompositionPresentation(service.business_composition)
    app.state.composition_presentation=presentation
    from .business_cases import BusinessCases
    service.business_cases=BusinessCases(service)
    app.state.business_cases=service.business_cases
    from .simpson_lifecycle import SimpsonLifecycle, definition as simpson_process
    from .lifecycle_driver import LifecycleDriver
    simpson_lifecycle=SimpsonLifecycle(service.business_cases)
    lifecycle_driver=LifecycleDriver(service.business_cases)

    async def call(fn, *args):
        try:
            data = await run_in_threadpool(fn, getattr(app.state,'workflow_auth',auth), *args)
            return JSONResponse(service.envelope(reference(),200,data),headers={'Cache-Control':'no-store'})
        except (ApiFailure, RuntimeFailure) as exc:
            if isinstance(exc,RuntimeFailure):exc=ApiFailure(exc.code,str(exc),exc.status)
            return JSONResponse(service.failure(reference(),exc),status_code=exc.status,headers={'Cache-Control':'no-store'})
        except Exception:
            exc = ApiFailure('BUSINESS_ONTOLOGY_UNAVAILABLE','Business ontology is unavailable. Refresh before retrying.',503)
            return JSONResponse(service.failure(reference(),exc),status_code=503,headers={'Cache-Control':'no-store'})

    @app.post('/business-ontology/v1/action-plans')
    async def prepare_action_plan(request:Request):
        return await call(service.business_composition.prepare_actions,await body(request))

    @app.get('/business-ontology/v1/action-plans/{composition_id}')
    async def get_action_plan(composition_id:str):
        return await call(service.business_composition.get,composition_id,False)

    @app.get('/business-ontology/v1/action-plans/{composition_id}/runs/{run_id}')
    async def action_plan_run(composition_id:str,run_id:str):
        return await call(presentation.view,composition_id,run_id)

    @app.post('/business-ontology/v1/cases/{case_id}/action-plan')
    async def attach_action_plan(case_id:str,request:Request):
        return await call(service.business_cases.attach_action_plan,case_id,await body(request))

    @app.post('/business-ontology/v1/process-definitions')
    async def publish_process_definition(request:Request):
        return await call(service.business_cases.publish,await body(request))

    @app.get('/business-ontology/v1/process-definitions')
    async def list_business_processes():
        return await call(service.business_cases.process_listing)

    @app.get('/business-ontology/v1/cases')
    async def list_business_cases(before:int|None=None):
        return await call(service.business_cases.listing,before)

    @app.get('/business-ontology/v1/process-definitions/{process_id}/{version}')
    async def get_process_definition(process_id:str,version:int):
        return await call(service.business_cases.process,process_id,version)

    @app.post('/business-ontology/v1/cases')
    async def create_business_case(request:Request):
        return await call(service.business_cases.create,await body(request))

    @app.get('/business-ontology/v1/simpson-lifecycle/process')
    async def get_simpson_process():
        def read(current):
            service.business_cases.scope(current)
            return simpson_process()
        return await call(read)

    @app.post('/business-ontology/v1/simpson-lifecycle/cases')
    async def create_simpson_case(request:Request):
        return await call(simpson_lifecycle.create,await body(request))

    @app.post('/business-ontology/v1/cases/{case_id}/drive')
    async def drive_business_case(case_id:str,request:Request):
        return await call(lifecycle_driver.drive,case_id,await body(request))

    @app.post('/business-ontology/v1/cases/{case_id}/reassess')
    async def reassess_business_case(case_id:str,request:Request):
        from .lifecycle_reassessment import LifecycleReassessment
        return await call(LifecycleReassessment(service.business_cases).reassess,case_id,await body(request))

    @app.get('/business-ontology/v1/cases/{case_id}/revisions/{revision}')
    async def archived_business_case(case_id:str,revision:int):
        from .lifecycle_reassessment import LifecycleReassessment
        return await call(LifecycleReassessment(service.business_cases).revision,case_id,revision)

    @app.get('/business-ontology/v1/cases/{case_id}')
    async def get_business_case(case_id:str):
        return await call(service.business_cases.get,case_id)

    @app.get('/business-ontology/v1/cases/{case_id}/sections/{section}')
    async def business_case_section(case_id:str,section:str):
        return await call(service.business_cases.section,case_id,section)

    @app.post('/business-ontology/v1/cases/{case_id}/events')
    async def business_case_event(case_id:str,request:Request):
        return await call(service.business_cases.event,case_id,await body(request))

    @app.post('/business-ontology/v1/cases/{case_id}/{operation}')
    async def business_case_command(case_id:str,operation:str,request:Request):
        return await call(service.business_cases.command,case_id,operation,await body(request))

    @app.get('/business-ontology/v1/client-packages')
    async def list_client_packages():return await call(service.business_composition.packages.listing)

    @app.post('/business-ontology/v1/client-packages')
    async def publish_client_package(request:Request):
        return await call(service.business_composition.packages.publish,await body(request))

    @app.get('/business-ontology/v1/client-packages/{package_id}/{revision}')
    async def get_client_package(package_id:str,revision:int):
        return await call(service.business_composition.packages.get,package_id,revision)

    def memory_operation(current,operation,payload):
        from runtime.service import RuntimeFailure
        if service.runtime_runner is None:raise RuntimeFailure('RUNTIME_NOT_CONFIGURED','Configure the existing runtime.',503)
        if not isinstance(payload,dict):raise RuntimeFailure('INVALID_INPUT','Supply a typed operation body.',422)
        runtime=service.runtime_runner.runtime
        fields={
            'candidate':({'domain','capability','category','strategy','evidence_references','pins','expires_at'},{'agent_id'}),
            'relevant':({'domain','capability','category','pins'},{'agent_id'}),
            'validate':({'experience_id','run_id'},set()),
            'invalidate':({'experience_id','reason'},set()),
            'resume':({'run_id'},{'changed_dependencies'}),
            'working':({'run_id'},set()),'outcome':({'run_id'},set())}
        if operation not in fields:raise RuntimeFailure('INVALID_INPUT','Unknown memory operation.',422)
        required,optional=fields[operation]
        if not required<=set(payload) or set(payload)-(required|optional):raise RuntimeFailure('INVALID_INPUT','Missing or unsupported memory-operation fields.',422)
        if operation=='candidate':return runtime.experience_memory.candidate(current,**payload)
        if operation=='relevant':return runtime.experience_memory.relevant(current,**payload)
        if operation=='validate':return runtime.experience_memory.validate(current,**payload)
        if operation=='invalidate':return runtime.experience_memory.invalidate(current,**payload)
        if operation=='resume':return runtime.recovery.resume(payload.pop('run_id'),current,**payload)
        if operation in ('working','outcome'):
            with runtime.store.transaction(write=False) as db:
                run=runtime.load(db,payload['run_id'],current)
                if run['subject_id']!=current['subject']['subject_id']:raise RuntimeFailure('SUBJECT_MISMATCH','Run context is owner-scoped.',403)
                if operation=='outcome':return run.get('outcome_evaluation',{})
                workflow=runtime.store.get(db,run['workspace_id'],run['workflow_id'],run['workflow_version'])
                from runtime.memory import bounded_context
                return bounded_context(runtime.working_memory.view(run,workflow))
        raise RuntimeFailure('INVALID_INPUT','Unknown memory operation.',422)

    @app.get('/business-ontology/v1/run-memory/{run_id}')
    async def run_working_memory(run_id:str):
        return await call(memory_operation,'working',{'run_id':run_id})

    @app.get('/business-ontology/v1/run-outcomes/{run_id}')
    async def run_outcomes(run_id:str):
        return await call(memory_operation,'outcome',{'run_id':run_id})

    @app.post('/business-ontology/v1/experiences/{operation}')
    async def experience_operation(operation:str,request:Request):
        if operation not in ('candidate','relevant','validate','invalidate'):
            return await call(memory_operation,'invalid',{})
        return await call(memory_operation,operation,await body(request))

    @app.post('/business-ontology/v1/recovery/{run_id}/resume')
    async def resume_composition(run_id:str,request:Request):
        payload=await body(request)
        if not isinstance(payload,dict) or set(payload)-{'changed_dependencies'}:
            return await call(memory_operation,'resume',None)
        return await call(memory_operation,'resume',dict(run_id=run_id,**payload))

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

    @app.post('/business-ontology/v1/retrieval/preview')
    async def retrieval_preview(request:Request):
        return await call(retrieval.preview,await body(request))

    @app.get('/business-ontology/v1/investigations/capabilities')
    async def investigation_capabilities():return await call(investigations.catalogue)

    @app.get('/business-ontology/v1/investigations')
    async def investigation_list():return await call(investigation_jobs.list)

    @app.post('/business-ontology/v1/investigations/jobs')
    async def investigation_job_submit(request:Request):return await call(investigation_jobs.submit,await body(request))

    @app.get('/business-ontology/v1/investigations/jobs/{job_id}')
    async def investigation_job_status(job_id:str):return await call(investigation_jobs.get,job_id)

    @app.post('/business-ontology/v1/investigations/plan')
    async def investigation_plan(request:Request):return await call(investigations.coverage.prepare_plan,await body(request))

    @app.post('/business-ontology/v1/investigations/preflight')
    async def investigation_preflight(request:Request):return await call(investigations.coverage.preflight,await body(request))

    @app.post('/business-ontology/v1/compositions')
    async def business_compose(request:Request):return await call(service.business_composition.prepare,await body(request))

    @app.get('/business-ontology/v1/compositions')
    async def list_compositions():return await call(lambda current:dict(items=presentation.listing(current)))

    @app.get('/business-ontology/v1/compositions/{composition_id}/view')
    async def composition_view(composition_id:str,run_id:str|None=None):return await call(presentation.view,composition_id,run_id)

    @app.put('/business-ontology/v1/compositions/{composition_id}/display-name')
    async def composition_rename(composition_id:str,request:Request):return await call(presentation.rename,composition_id,await body(request))

    @app.delete('/business-ontology/v1/compositions/{composition_id}')
    async def composition_delete(composition_id:str,request:Request):return await call(presentation.delete,composition_id,await body(request))

    @app.post('/business-ontology/v1/compositions/{composition_id}/runs/{run_id}/cancel')
    async def composition_cancel(composition_id:str,run_id:str,request:Request):return await call(presentation.cancel,composition_id,run_id,await body(request))

    @app.get('/business-ontology/v1/compositions/{composition_id}')
    async def business_composition_get(composition_id:str):return await call(service.business_composition.get,composition_id)

    @app.post('/business-ontology/v1/compositions/{composition_id}/workflow')
    async def business_composition_workflow(composition_id:str):return await call(service.business_composition.workflow,composition_id)

    @app.get('/business-ontology/v1/preparations/{preparation_id}')
    async def business_preparation_get(preparation_id:str):return await call(service.business_preparation.checked,preparation_id)

    @app.post('/business-ontology/v1/preparations/retrieve')
    async def business_preparation_retrieve(request:Request):return await call(service.business_evidence_adapter.invoke,await body(request))

    @app.get('/business-ontology/v1/investigations/environments')
    async def evidence_environments():return await call(investigations.coverage.environments.list)

    @app.get('/business-ontology/v1/investigations/plans/{workflow_id}')
    async def investigation_get_plan(workflow_id:str):return await call(investigations.get_plan,workflow_id)

    @app.put('/business-ontology/v1/investigations/plans/{workflow_id}')
    async def investigation_rename(workflow_id:str,request:Request):return await call(investigations.manage,workflow_id,await body(request))

    @app.delete('/business-ontology/v1/investigations/plans/{workflow_id}')
    async def investigation_delete(workflow_id:str):return await call(investigations.manage,workflow_id,{},True)

    @app.post('/business-ontology/v1/investigations/plans/{workflow_id}/validate')
    async def investigation_validate(workflow_id:str,request:Request):
        if await body(request)!={}:return await call(investigations.plan,None)
        return await call(investigations.validate,workflow_id)

    @app.post('/business-ontology/v1/investigations/plans/{workflow_id}/runs')
    async def investigation_run(workflow_id:str,request:Request):return await call(investigations.create_run,workflow_id,await body(request))

    @app.get('/business-ontology/v1/investigations/runs/{run_id}')
    async def investigation_get_run(run_id:str):return await call(investigations.get_run,run_id)

    @app.post('/business-ontology/v1/investigations/runs/{run_id}/execute')
    async def investigation_execute(run_id:str,request:Request):return await call(investigations.execute,run_id,await body(request))

    @app.post('/business-ontology/v1/investigations/runs/{run_id}/resume')
    async def investigation_resume(run_id:str,request:Request):return await call(investigations.execute,run_id,await body(request),True)

    @app.post('/business-ontology/v1/investigations/runs/{run_id}/input')
    async def investigation_input(run_id:str,request:Request):return await call(investigations.supply_input,run_id,await body(request))

    @app.post('/business-ontology/v1/investigations/runs/{run_id}/cancel')
    async def investigation_cancel(run_id:str,request:Request):return await call(investigations.cancel,run_id,await body(request))

    @app.get('/business-ontology/v1/retrieval/{request_id}')
    async def retrieval_inspect(request_id:str):
        return await call(retrieval.inspect,request_id)

    @app.post('/business-ontology/v1/retrieval/{request_id}/execute')
    async def retrieval_execute(request_id:str,request:Request):
        return await call(retrieval.execute,request_id,await body(request))

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
