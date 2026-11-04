"""Preparation and runtime coverage integration for existing investigations."""
from copy import deepcopy
import secrets
from .business_coverage import coverage,TASKS
from .business_environments import BusinessEnvironments,case_coverage
from .business_knowledge_model import canonical,digest
from .investigation_graph import requirements,fail
from .google_connections import now


class InvestigationCoverage:
    def __init__(self,service):
        self.service,self.store=service,service.store
        self.environments=BusinessEnvironments(service)
        with self.store.transaction() as db:db.execute('CREATE TABLE IF NOT EXISTS business_evidence_preflights (workspace TEXT NOT NULL,owner TEXT NOT NULL,preflight_id TEXT NOT NULL,document TEXT NOT NULL,PRIMARY KEY(workspace,owner,preflight_id))')
    def preflight(self,auth,body):
        from jsonschema import Draft202012Validator
        from .investigation_graph import CONTEXT_SCHEMA
        if not isinstance(body,dict) or list(Draft202012Validator(CONTEXT_SCHEMA).iter_errors(body.get('inputs',{'identifiers':{}}))):fail('Provide typed identifiers and optional assessment_date/policy_id inputs.')
        auth,scope=self.service.authorize(auth);required=requirements(body.get('objective'));context=deepcopy(body.get('inputs',{'identifiers':{}}));selection=body.get('evidence_context');snapshot=None;case=None
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
        version=self.service.ontology.version(auth,vid)
        from .business_resolution import interpret
        parsed=interpret(body['objective'],version,context.get('identifiers',{}));context['identifiers']=parsed['identifiers']
        if parsed['ambiguities']:fail('Resolve ambiguous source identifiers before preflight.','EVIDENCE_INPUT_AMBIGUOUS',422)
        results={};observations={};reads=0;tasks=['complaints']+[t for t in ('inspection','warranty','replacement','history','recurrence') if required.get(t)]
        for task in tasks:
            if case:
                result=case_coverage(case,task,context,self.environments.revoked(auth,selection['dataset_id']));evidence=deepcopy(case['evidence'])
            else:
                inputs={**context['identifiers'],**{k:context[k] for k in ('assessment_date','policy_id') if k in context}}
                preview=self.service.retrieval.preview(auth,dict(question=self.service.question(task,context),inputs=inputs,version_id=vid,request_key='coverage_'+secrets.token_hex(12)))
                evidence=self.service.retrieval.execute(auth,preview['request_id'],{}) if preview['ready'] and context['identifiers'] else dict(records=[],reference_edges=[],selected_mappings=preview['mappings'])
                if preview['ready'] and context['identifiers']:reads+=1
                result=coverage(task,evidence,context,policies=preview['policies'])
            results[task]=result;observations[task]=dict(record_count=len(evidence.get('records',[])),read_at=[r.get('read_at') for r in evidence.get('records',[])],evidence_sha256=digest(evidence))
        doc=dict(preflight_id='preflight_'+secrets.token_hex(12),objective=body['objective'],inputs=context,version_id=vid,evidence_context=snapshot,coverage=results,observations=observations,created_at=now(),source_retrieval_calls=reads,company_writes=0)
        doc['sha256']=digest(doc)
        with self.store.transaction() as db:db.execute('INSERT INTO business_evidence_preflights VALUES (?,?,?,?)',(*scope,doc['preflight_id'],canonical(doc)))
        return doc
    def get(self,auth,pid):
        _,scope=self.service.authorize(auth)
        with self.store.transaction(write=False) as db:row=db.execute('SELECT document FROM business_evidence_preflights WHERE workspace=? AND owner=? AND preflight_id=?',(*scope,pid)).fetchone()
        if not row:fail('Coverage preflight not found.','EVIDENCE_PREFLIGHT_NOT_FOUND',404)
        doc=__import__('json').loads(row[0]);sha=doc.pop('sha256')
        if digest(doc)!=sha:fail('Preflight integrity failed.','EVIDENCE_PREFLIGHT_CHANGED',409)
        doc['sha256']=sha;return doc
    def prepare_plan(self,auth,body):
        if not isinstance(body,dict):fail('Provide a planning request.')
        _,scope=self.service.authorize(auth)
        if body.get('request_key'):
            with self.store.transaction(write=False) as db:row=db.execute('SELECT document FROM business_investigation_plans WHERE workspace=? AND owner=? AND request_key=?',(*scope,body['request_key'])).fetchone()
            if row:
                old=__import__('json').loads(row[0])
                if old.get('preparation_fingerprint')!=digest(body):fail('Request key belongs to another preparation.','INVESTIGATION_CONFLICT',409)
                self.service.check_plan(auth,old);return old
        updated=deepcopy(body)
        if not updated.get('preflight_id'):
            result=self.preflight(auth,updated);updated['preflight_id']=result['preflight_id']
        return self.service.plan(auth,updated)
    def scenario_evidence(self,auth,plan,task):
        pin=plan.get('evidence_context')
        if not pin:return None
        release,case=self.environments.selected(auth,{k:pin[k] for k in ('dataset_id','case_id')})
        if release['sha256']!=pin['sha256']:fail('Selected evidence environment changed.','EVIDENCE_ENVIRONMENT_CHANGED',409)
        revoked=self.environments.revoked(auth,pin['dataset_id'])
        result=case_coverage(case,task,plan['inputs'],revoked)
        evidence=deepcopy(case['evidence']);evidence['intent']={'task':task};evidence['request_id']='scenario_'+digest([plan['workflow_id'],task])[:24]
        evidence['coverage']=result;evidence['requirement_results']=result;evidence['evidence_requirements']=result['requirements'];evidence['normalized_gaps']=result['gaps']
        evidence['missing']=[dict(fact=g['fact_id'],reason=g['state']) for g in result['gaps']];evidence['rule_results']=[]
        evidence['scenario_context']=dict(**pin,provenance='mixed_source_and_generated_scenario',observed_at=now(),snapshot_source_times_retained=True)
        for record in case['business_records']:
            values={'mapping:business:'+record['kind']+':'+k:dict(state='value',value=deepcopy(v)) for k,v in record['data'].items()}
            evidence['records'].append(dict(record_id=record['record_id'],collection='business_'+record['kind'],fields=deepcopy(record['data']),values=values,states=[],source_reference=dict(dataset_id=pin['dataset_id'],case_id=case['case_id'],record_kind=record['kind'],provenance=record['provenance'],withdrawn=record['record_id'] in revoked,checked_at=now()),read_at=record['observed_at']))
        return evidence
    def runtime_coverage(self,auth,plan,task,evidence):
        if plan.get('evidence_context'):
            refreshed=self.scenario_evidence(auth,plan,task)
            return refreshed['coverage']
        return coverage(task,evidence,plan['inputs'],policies=self.service.ontology.version(auth,plan['version_id'])['knowledge']['manifest']['policy_snapshots'])

    def refresh(self,auth,plan,task):
        if plan.get('evidence_context'):return self.scenario_evidence(auth,plan,task)
        inputs={**plan['inputs']['identifiers'],**{k:plan['inputs'][k] for k in ('assessment_date','policy_id') if k in plan['inputs']}}
        preview=self.service.retrieval.preview(auth,dict(question=self.service.question(task,plan['inputs']),inputs=inputs,version_id=plan['version_id'],request_key='revalidate_'+secrets.token_hex(12)))
        evidence=self.service.retrieval.execute(auth,preview['request_id'],{})
        evidence['coverage']=self.runtime_coverage(auth,plan,task,evidence);evidence['requirement_results']=evidence['coverage'];evidence['coverage_checked_at']=now()
        return evidence
