"""One grounded preparation boundary; existing resolver, coverage and source authority."""
from copy import deepcopy
import json
import secrets
from pathlib import Path
from jsonschema import Draft202012Validator
from registry.safety import reject_secrets
from .business_coverage import coverage,FINGERPRINT
from .business_environments import case_coverage
from .business_knowledge_model import canonical,digest
from .investigation_graph import requirements,fail,CAPABILITIES
from .google_connections import now

SCHEMA_PATH=Path(__file__).parent/'schemas'/'business-preparation-v1.json'
SCHEMA=json.loads(SCHEMA_PATH.read_text())

def validate_preparation(document):
    if list(Draft202012Validator(SCHEMA).iter_errors(document)):
        fail('Preparation does not satisfy its typed result contract.','BUSINESS_PREPARATION_INVALID',422)

class SharedBusinessPreparation:
    def __init__(self,coverage_service,registry=None):
        self.coverage=coverage_service
        self.service=coverage_service.service
        self.store=coverage_service.store
        self.environments=coverage_service.environments
        self.registry=registry

    def prepare_package(self,packages,auth,package_id,revision,objective):
        """Alternate knowledge adapter; same downstream capability/Registry pipeline."""
        return packages.prepare(auth,package_id,revision,objective)

    def prepare(self,auth,body):
        from jsonschema import Draft202012Validator
        from .investigation_graph import CONTEXT_SCHEMA
        if not isinstance(body,dict) or list(Draft202012Validator(CONTEXT_SCHEMA).iter_errors(body.get('inputs',{'identifiers':{}}))):fail('Provide typed identifiers and optional assessment_date/policy_id inputs.')
        allowed={'objective','inputs','version_id','evidence_context','client_id','domain_id','workspace_id','tenant_id','request_key','planning_mode','analysis_mode','wait_for_information','preflight_id'}
        if set(body)-allowed:fail('Unknown business preparation input.','BUSINESS_PREPARATION_INPUT',422)
        if body.get('version_id') is not None and (not isinstance(body['version_id'],str) or not 1<=len(body['version_id'])<=128):fail('Supply a saved ontology version ID.')
        auth,scope=self.service.authorize(auth);reject_secrets(body);required=requirements(body.get('objective'));context=deepcopy(body.get('inputs',{'identifiers':{}}));selection=body.get('evidence_context');snapshot=None;case=None
        if body.get('tenant_id') not in (None,scope[0]) or body.get('workspace_id') not in (None,scope[0]):fail('Preparation scope must match authenticated workspace.','BUSINESS_PREPARATION_SCOPE',403)
        for key in ('client_id','domain_id'):
            if key in body and (not isinstance(body[key],str) or not 1<=len(body[key])<=128):fail('Client/domain labels must be bounded strings.')
        if context.get('assessment_date'):
            from datetime import date
            try:date.fromisoformat(context['assessment_date'])
            except ValueError:fail('Use an ISO calendar assessment date.')
        if selection:
            release,case=self.environments.selected(auth,selection)
            requested=context.get('identifiers',{})
            if requested and requested!=case['source_identifiers']:fail('Selected case and explicit identifiers disagree.','EVIDENCE_CASE_MISMATCH',422)
            # An explicit prompt identifier must agree as well.
            from .business_resolution import interpret
            v=self.service.ontology.version(auth,release['manifest']['ontology_version'])
            parsed=interpret(body['objective'],v)
            if parsed['identifiers'] and parsed['identifiers']!=case['source_identifiers']:fail('Prompt identifier is outside the selected case.','EVIDENCE_CASE_MISMATCH',422)
            context={'identifiers':case['source_identifiers'],**case['inputs'],**{k:v for k,v in context.items() if k!='identifiers'}}
            vid=release['manifest']['ontology_version'];snapshot=dict(**selection,sha256=release['sha256'])
        else:vid=body.get('version_id') or self.service.retrieval.latest(auth)
        if body.get('version_id') not in (None,vid):fail('Selected ontology and scenario version disagree.','EVIDENCE_PREFLIGHT_MISMATCH',422)
        version=self.service.ontology.version(auth,vid)
        from .business_resolution import interpret
        parsed=interpret(body['objective'],version,context.get('identifiers',{}));context['identifiers']=parsed['identifiers']
        if parsed['ambiguities'] and parsed['identifiers']:fail('Resolve ambiguous source identifiers before preflight.','EVIDENCE_INPUT_AMBIGUOUS',422)
        results={};observations={};reads=0;previews={};evidences={};tasks=['complaints']+[t for t in ('inspection','warranty','replacement','history','recurrence') if required.get(t)]
        for task in tasks:
            if case:
                mapped_inputs={**context['identifiers'],**{k:context[k] for k in ('assessment_date',) if k in context}}
                preview=self.service.retrieval.prepare(auth,version,self.service.question(task,context),mapped_inputs)
                result=case_coverage(case,task,context,self.environments.revoked(auth,selection['dataset_id']))
                evidence=self.coverage.scenario_evidence(auth,dict(workflow_id='preparation_'+digest(snapshot)[:24],inputs=context,evidence_context=snapshot),task)
            else:
                inputs={**context['identifiers'],**{k:context[k] for k in ('assessment_date','policy_id') if k in context}}
                preview=self.service.retrieval.preview(auth,dict(question=self.service.question(task,context),inputs=inputs,version_id=vid,request_key='coverage_'+secrets.token_hex(12)))
                evidence=self.service.retrieval.execute(auth,preview['request_id'],{}) if preview['ready'] and context['identifiers'] else dict(records=[],reference_edges=[],selected_mappings=preview['mappings'])
                if preview['ready'] and context['identifiers']:reads+=1
                result=coverage(task,evidence,context,policies=preview['policies'])
            if not context['identifiers']:
                result['state']='needs_input';result['conclusion_ready']=False
            if not preview['dependency_resolution']['complete']:
                result['state']='unsupported';result['conclusion_ready']=False
            previews[task]=preview;evidences[task]=evidence
            results[task]=result;observations[task]=dict(record_count=len(evidence.get('records',[])),read_at=[r.get('read_at') for r in evidence.get('records',[])],evidence_sha256=digest(evidence))
        doc=dict(preflight_id='preflight_'+secrets.token_hex(12),objective=body['objective'],inputs=context,version_id=vid,evidence_context=snapshot,coverage=results,observations=observations,created_at=now(),source_retrieval_calls=reads,company_writes=0)
        if len(canonical(evidences).encode())>4000000:fail('Required preparation evidence exceeds its storage bound.','BUSINESS_PREPARATION_LIMIT',422)
        doc.update(self.describe(auth,scope,body,version,previews,evidences,results))
        reject_secrets(doc)
        validate_preparation(doc)
        doc['sha256']=digest(doc)
        with self.store.transaction() as db:db.execute('INSERT INTO business_evidence_preflights VALUES (?,?,?,?)',(*scope,doc['preflight_id'],canonical(doc)))
        return doc
    def describe(self,auth,scope,body,version,previews,evidences,results):
        stamps={}
        for p in previews.values():
            for m in p['mappings']:
                b=self.service.retrieval.binding(auth,m['source_role'],m['collection'],[])
                stamps[(m['source_role'],m['collection'])]=dict(source_role=m['source_role'],collection=m['collection'],connection_id=b['connection_id'],stamp=b['stamp'],metadata_revision=b['metadata_revision'])
        tasks={t:{k:deepcopy(p[k]) for k in ('intent','concepts','relationships','dependency_resolution','fact_providers','mappings','steps','rules','missing','evidence_requirements')} for t,p in previews.items()}
        gaps=[];seen=set()
        for t,p in previews.items():
            for gap in results[t]['gaps']:
                key=digest([t,gap['fact_id'],gap['state']])
                if key not in seen:seen.add(key);gaps.append(deepcopy(gap))
            for item in p['missing']:
                gap=dict(task=t,kind='retrieval_requirement',**deepcopy(item))
                if digest(gap) not in seen:seen.add(digest(gap));gaps.append(gap)
        candidates=[]
        registry=getattr(self.registry,'service',self.registry)
        if registry:
            response=registry.list_tools(auth)
            if response['status']<400:
                for item in response['data']['items']:
                    d=item['definition']
                    if d['availability']=='enabled':candidates.append(dict(tool_id=item['tool_id'],capability=d['capability'],description=d['description'],provider_id=d['provider_id'],risk_level=d['risk_level'],version=item['version'],input_schema=d['input_schema'],output_schema=d['output_schema'],authorization_state='requires_assignment'))
        requested=set(previews)
        capabilities=[deepcopy(c) for c in CAPABILITIES if c.get('retrieval_task') in requested or c['id']=='prepare_summary' or c['id']=='compare_inspection' and 'inspection' in requested or c['id']=='warranty_readiness' and 'warranty' in requested]
        return dict(schema_version='business-preparation-v1',scope=dict(tenant_id=scope[0],workspace_id=scope[0],owner_id=scope[1]),domain_context={k:body[k] for k in ('client_id','domain_id') if k in body},
            goal=dict(objective=body['objective'],interpretation='existing_validated_resolver',requested_outcomes=list(previews)),tasks=tasks,
            available_evidence=deepcopy(evidences),gaps=gaps,capabilities=capabilities,tool_candidates=candidates,
            pins=dict(ontology_version=version['version_id'],knowledge_sha256=version['knowledge_sha256'],mapping_sha256=digest(version['knowledge']['source_mappings']),configuration_revision=version['knowledge']['manifest'].get('configuration_revision'),provider_fingerprint=FINGERPRINT,source_stamps=list(stamps.values())),
            provenance=dict(mode='scenario' if body.get('evidence_context') else 'company_sources',company_writes=0,generated_authority=False))

    def get(self,auth,preparation_id):
        doc=self.coverage.get(auth,preparation_id)
        if doc.get('schema_version')!='business-preparation-v1':fail('Historical preflight has no shared preparation.','BUSINESS_PREPARATION_REQUIRED',409)
        validate_preparation(doc)
        return doc

    def checked(self,auth,preparation_id):
        doc=self.get(auth,preparation_id)
        version=self.service.ontology.version(auth,doc['version_id'])
        if version['knowledge_sha256']!=doc['pins']['knowledge_sha256'] or digest(version['knowledge'])!=doc['pins']['knowledge_sha256'] or FINGERPRINT!=doc['pins']['provider_fingerprint']:fail('Pinned preparation knowledge/provider changed.','BUSINESS_PREPARATION_STALE',409)
        for stamp in doc['pins']['source_stamps']:
            current=self.service.retrieval.binding(auth,stamp['source_role'],stamp['collection'],[])
            if current['stamp']!=stamp['stamp'] or current['connection_id']!=stamp['connection_id']:fail('Prepared source metadata changed.','BUSINESS_SOURCE_STALE',409)
        if doc.get('evidence_context'):
            release,_=self.environments.selected(auth,{k:doc['evidence_context'][k] for k in ('dataset_id','case_id')})
            if release['sha256']!=doc['evidence_context']['sha256']:fail('Prepared scenario changed.','EVIDENCE_ENVIRONMENT_CHANGED',409)
        return doc

    @staticmethod
    def context(doc):
        # Deduplicate definitions; retain all mandatory dependencies by stable ID.
        result={k:deepcopy(doc[k]) for k in ('schema_version','preflight_id','sha256','scope','domain_context','goal','tool_candidates','pins','observations','evidence_context')}
        definitions={k:{} for k in ('concepts','relationships','mappings','rules')}
        tasks={}
        for task,p in doc['tasks'].items():
            t={k:deepcopy(p[k]) for k in ('intent','dependency_resolution','fact_providers','steps','missing')}
            for kind in definitions:
                for item in p[kind]:
                    identifier=item['id']
                    if identifier in definitions[kind] and definitions[kind][identifier]!=item:fail('Conflicting prepared definition.','BUSINESS_PREPARATION_INVALID',422)
                    definitions[kind][identifier]=deepcopy(item)
                t[kind]=[item['id'] for item in p[kind]]
            t['required_facts']=[{k:deepcopy(r[k]) for k in ('fact_id','business_meaning','requirement_level') if k in r} for r in doc['coverage'][task]['requirements']]
            tasks[task]=t
        result.update(tasks=tasks,definitions=definitions)
        result['coverage']={t:{k:deepcopy(c[k]) for k in ('state','conclusion_ready','business_outcomes','provenance','provider_fingerprint')} for t,c in doc['coverage'].items()}
        result['gaps']=deepcopy(doc['gaps'])
        result['capabilities']=[{k:deepcopy(c[k]) for k in ('id','purpose','kind','retrieval_task','required_ontology','implementation','read_only') if k in c} for c in doc['capabilities']]
        result['available_evidence']={t:[{k:deepcopy(r[k]) for k in ('record_id','collection','values','source_reference','read_at') if k in r} for r in e.get('records',[])] for t,e in doc['available_evidence'].items()}
        if len(canonical(result).encode())>500000:fail('Required preparation exceeds planner context; narrow the objective.','BUSINESS_PREPARATION_LIMIT',422)
        return result

    def general_context(self,auth,objective,requested=None):
        if requested is None:requested={}
        allowed={'inputs','version_id','evidence_context','client_id','domain_id','workspace_id','tenant_id'}
        if not isinstance(requested,dict) or set(requested)-allowed:fail('Invalid business preparation context.')
        # Unrelated generic workflows retain their existing planning path.
        try:requirements(objective)
        except Exception as exc:
            if getattr(exc,'code',None)!='INVESTIGATION_UNSUPPORTED':raise
            return dict(state='unsupported',reason='No supported business outcome; existing general planning remains available.',company_reads=0)
        try:
            vid=requested.get('version_id') or self.service.retrieval.latest(auth)
            if not self.service.ontology.version(auth,vid).get('knowledge'):fail('Phase 1 knowledge is required.','BUSINESS_RETRIEVAL_KNOWLEDGE_REQUIRED',409)
        except Exception as exc:
            if getattr(exc,'code',None) not in ('BUSINESS_VERSION_NOT_FOUND','BUSINESS_RETRIEVAL_KNOWLEDGE_REQUIRED'):raise
            if requested:raise
            return dict(state='not_configured',company_reads=0)
        doc=self.prepare(auth,dict(objective=objective,**requested))
        return self.context(doc)

class BusinessEvidenceAdapter:
    """Call from a server-bound tool after Registry checks; no caller query/field authority."""
    input_schema={'type':'object','additionalProperties':False,'required':['preparation_id','task'],'properties':{'preparation_id':{'type':'string'},'task':{'type':'string','enum':['complaints','inspection','warranty','replacement','history','recurrence']}}}
    output_schema={'type':'object','required':['version_id','knowledge_sha256','records','coverage'],'properties':{'version_id':{'type':'string'},'knowledge_sha256':{'type':'string'},'records':{'type':'array','items':{'type':'object'}},'coverage':{'type':'object','required':['state','conclusion_ready']}}}
    def __init__(self,preparation):self.preparation=preparation
    def invoke(self,auth,inputs):
        if list(Draft202012Validator(self.input_schema).iter_errors(inputs)):fail('Supply preparation_id and one prepared task.','BUSINESS_ADAPTER_INPUT',422)
        doc=self.preparation.checked(auth,inputs['preparation_id'])
        if inputs['task'] not in doc['tasks']:fail('Task was not prepared.','BUSINESS_ADAPTER_TASK',422)
        result=self.preparation.coverage.refresh(auth,dict(workflow_id=doc['preflight_id'],version_id=doc['version_id'],inputs=doc['inputs'],evidence_context=doc['evidence_context']),inputs['task'])
        if list(Draft202012Validator(self.output_schema).iter_errors(result)):fail('Retrieval adapter output violated its contract.','BUSINESS_ADAPTER_OUTPUT',422)
        return result


def bind_workflow(workflow,context):
    """Server-produced context only; provider-authored pins have no authority."""
    metadata=workflow.setdefault('metadata',{})
    metadata.pop('business_preparation',None)
    doc=context.get('business_preparation',{}) if isinstance(context,dict) else {}
    if doc.get('schema_version')=='business-preparation-v1':
        metadata['business_preparation']={k:deepcopy(doc[k]) for k in ('preflight_id','sha256','scope','pins','evidence_context','observations')}


def verify_workflow_pin(db,auth,workflow):
    pin=workflow.get('metadata',{}).get('business_preparation')
    scope=(auth['subject']['workspace_id'],auth['subject']['subject_id'])
    registered=db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='business_prepared_workflows'").fetchone()
    expected_pin=db.execute('SELECT document FROM business_prepared_workflows WHERE workspace=? AND owner=? AND workflow_id=?',(*scope,workflow['workflow_id'])).fetchone() if registered else None
    if expected_pin and pin!=json.loads(expected_pin[0]):fail('Keep the original workflow preparation pin.','BUSINESS_PREPARATION_PIN_INVALID',422)
    if pin is None:return
    exists=db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='business_evidence_preflights'").fetchone()
    row=db.execute('SELECT document FROM business_evidence_preflights WHERE workspace=? AND owner=? AND preflight_id=?',(*scope,pin.get('preflight_id'))).fetchone() if exists and isinstance(pin,dict) else None
    if not row:fail('Use an owned server-generated preparation.','BUSINESS_PREPARATION_PIN_INVALID',422)
    doc=json.loads(row[0]);sha=doc.pop('sha256')
    if digest(doc)!=sha:fail('Saved preparation changed.','BUSINESS_PREPARATION_PIN_INVALID',422)
    doc['sha256']=sha;expected={k:doc[k] for k in ('preflight_id','sha256','scope','pins','evidence_context','observations')}
    if pin!=expected:fail('Prepared source context was modified.','BUSINESS_PREPARATION_PIN_INVALID',422)


def record_workflow_pin(store,auth,workflow):
    pin=workflow.get('metadata',{}).get('business_preparation')
    if not pin:return
    scope=(auth['subject']['workspace_id'],auth['subject']['subject_id'])
    with store.transaction() as db:
        db.execute('CREATE TABLE IF NOT EXISTS business_prepared_workflows (workspace TEXT NOT NULL,owner TEXT NOT NULL,workflow_id TEXT NOT NULL,document TEXT NOT NULL,PRIMARY KEY(workspace,owner,workflow_id))')
        db.execute('INSERT INTO business_prepared_workflows VALUES (?,?,?,?) ON CONFLICT DO NOTHING',(*scope,workflow['workflow_id'],canonical(pin)))


def retrieval_tool_definition():
    """Operator-registerable tool; this definition creates no grants or credentials."""
    return dict(tool_id='business_retrieve_evidence',provider_id='builder_business',capability='business.retrieve_evidence',description='Retrieve one prepared business task through pinned ontology mappings, current source authority and evidence coverage. No arbitrary queries or company writes.',input_schema=deepcopy(BusinessEvidenceAdapter.input_schema),output_schema=deepcopy(BusinessEvidenceAdapter.output_schema),authentication=dict(mode='none',credential_reference_required=False,scopes=['workspace:read']),permission_scopes=['tools.read'],availability='enabled',risk_level='low',rate_limits=dict(requests_per_minute=20),estimated_cost=dict(currency='USD',per_call=0),retry_policy=dict(max_retries=0,retryable_errors=[]),timeout_seconds=45,approval_required=False,allowed_destinations=[])


class BusinessEvidenceConnector:
    """Existing GraphRunner/DelegationSession connector protocol; server-bound scope."""
    external_write=False
    retry_safe=True
    timeout=45
    def __init__(self,preparation,auth=None,pin=None):
        self.preparation,self.auth,self.pin=preparation,deepcopy(auth),deepcopy(pin)
    def bind_context(self,workflow,run,auth,node):
        from runtime.service import RuntimeFailure
        pin=workflow.get('metadata',{}).get('business_preparation')
        if not isinstance(pin,dict):raise RuntimeFailure('BUSINESS_PREPARATION_REQUIRED','Workflow has no prepared business context.',409)
        try:doc=self.preparation.checked(auth,pin['preflight_id'])
        except Exception as exc:
            if getattr(exc,'code',None):raise RuntimeFailure(exc.code,str(exc),getattr(exc,'status',409)) from None
            raise
        if pin['sha256']!=doc['sha256']:raise RuntimeFailure('BUSINESS_PREPARATION_PIN_INVALID','Workflow preparation changed.',422)
        return BusinessEvidenceConnector(self.preparation,auth,pin)
    def reservation(self,grant):return dict(tool_calls=1,tokens=0,llm_calls=0,estimated_cost_usd=0)
    def invoke(self,grant,inputs,effect_id):
        from runtime.service import RuntimeFailure
        if not self.auth or not self.pin or grant.get('tool_id')!='business_retrieve_evidence' or not isinstance(inputs,dict) or inputs.get('preparation_id')!=self.pin['preflight_id']:
            raise RuntimeFailure('TOOL_ISOLATION_DENIED','Use the workflow-bound business preparation.',403)
        try:return BusinessEvidenceAdapter(self.preparation).invoke(self.auth,inputs)
        except Exception as exc:
            if getattr(exc,'code',None):raise RuntimeFailure(exc.code,str(exc),getattr(exc,'status',409)) from None
            raise
