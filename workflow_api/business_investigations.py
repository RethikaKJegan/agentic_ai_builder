"""Durable read-only Simpson investigation composition over Phase 2 and CrewAI.

Company reads stay inside BusinessRetrieval. This domain executor does not submit
or bypass approved production workflow releases and cannot execute write tools.
"""
from concurrent.futures import ThreadPoolExecutor,as_completed
from copy import deepcopy
import json
import re
import secrets
import time
from jsonschema import Draft202012Validator
from registry.safety import reject_secrets
from runtime.graph import ready_frontier
from .business_knowledge_model import canonical,digest
from .business_ontology import identity
from .business_resolution import interpret
from .investigation_graph import VERSION,CAPABILITIES,CATALOGUE,CATALOGUE_HASH,LIMITS,CONTEXT_SCHEMA,requirements,validate_graph,predicate,fail
from .investigation_planning import InvestigationPlanner
from .investigation_agents import InvestigationAgents,packet,MODEL_USAGE_POLICY
from .google_connections import now

TERMINAL={'completed','canceled'}
NODE_TRANSITIONS={
 'pending':{'ready','skipped'},'ready':{'running','failed'},'running':{'succeeded','failed','waiting_for_input','pending'},
 'waiting_for_input':{'pending'},'failed':{'pending'},'succeeded':set(),'skipped':set(),
}
QUESTIONS={'complaints':'Show complaints','inspection':'Show inspection findings','warranty':'Check warranty evidence','replacement':'Show replacement evidence','history':'Show history','recurrence':'Check recurrence evidence'}


class BusinessInvestigations:
    def __init__(self,retrieval,env=None,planner=None,agents=None,clock=time.time):
        self.retrieval,self.ontology,self.store=retrieval,retrieval.ontology,retrieval.store
        self.env=env or {};self.planner=planner or InvestigationPlanner(self.env);self.agents=agents or InvestigationAgents(self.env);self.clock=clock
        with self.store.transaction() as db:
            db.execute('CREATE TABLE IF NOT EXISTS business_investigation_metadata (workspace TEXT NOT NULL,owner TEXT NOT NULL,workflow_id TEXT NOT NULL,display_name TEXT,deleted_at TEXT,updated_at TEXT NOT NULL,PRIMARY KEY(workspace,owner,workflow_id))')
            db.execute('CREATE TABLE IF NOT EXISTS business_investigation_plans (workspace TEXT NOT NULL,owner TEXT NOT NULL,workflow_id TEXT NOT NULL,request_key TEXT NOT NULL,fingerprint TEXT NOT NULL,document TEXT NOT NULL,PRIMARY KEY(workspace,owner,workflow_id),UNIQUE(workspace,owner,request_key))')
            db.execute('CREATE TABLE IF NOT EXISTS business_investigation_runs (workspace TEXT NOT NULL,owner TEXT NOT NULL,run_id TEXT NOT NULL,request_key TEXT NOT NULL,fingerprint TEXT NOT NULL,lease_owner TEXT,lease_until REAL NOT NULL,document TEXT NOT NULL,PRIMARY KEY(workspace,owner,run_id),UNIQUE(workspace,owner,request_key))')
        from .investigation_coverage import InvestigationCoverage
        self.coverage=InvestigationCoverage(self)

    def authorize(self,auth,execute=False):
        current,scope=self.retrieval.sources.authorize(auth)
        permission='workflow.execute' if execute else 'tools.read'
        if permission not in current.get('permissions',[]):fail('Current investigation execution is not authorized.','INVESTIGATION_DENIED',403)
        return current,scope

    @staticmethod
    def key(body):
        key=body.get('request_key')
        if not isinstance(key,str) or not 8<=len(key)<=128:fail('Provide a request_key of 8–128 characters.')
        return key

    def row(self,db,table,scope,key,value,lock=False):
        # Table/column identifiers are server literals, never client-provided.
        suffix=' FOR UPDATE' if lock and self.store.database is not None else ''
        row=db.execute('SELECT document FROM '+table+' WHERE workspace=? AND owner=? AND '+key+'=?'+suffix,(*scope,value)).fetchone()
        if not row:fail('Investigation artifact not found.','INVESTIGATION_NOT_FOUND',404)
        return json.loads(row[0])

    def get_plan(self,auth,workflow_id):
        auth,scope=self.authorize(auth)
        with self.store.transaction(write=False) as db:
            meta=db.execute('SELECT deleted_at FROM business_investigation_metadata WHERE workspace=? AND owner=? AND workflow_id=?',(*scope,workflow_id)).fetchone()
            if meta and meta[0]:fail('Investigation artifact not found.','INVESTIGATION_NOT_FOUND',404)
            p=self.row(db,'business_investigation_plans',scope,'workflow_id',workflow_id)
        self.check_plan(auth,p)
        return p

    def manage(self,auth,workflow_id,body,delete=False):
        auth,scope=self.authorize(auth)
        permission='workflow.delete' if delete else 'workflow.edit'
        if permission not in auth.get('permissions',[]) or 'workspace:write' not in auth.get('scopes',[]):fail('Workflow management permission is required.','INVESTIGATION_DENIED',403)
        if not isinstance(body,dict) or set(body)!=(set() if delete else {'display_name'}):fail('Supply a display name only, or an empty delete request.')
        name=None if delete else body['display_name']
        if not delete:
            if not isinstance(name,str) or not 1<=len(name.strip())<=160 or any(ord(c)<32 for c in name):fail('Use a name of 1–160 characters without control characters.')
            name=name.strip();reject_secrets(name)
        with self.store.transaction() as db:
            self.row(db,'business_investigation_plans',scope,'workflow_id',workflow_id)
            meta=db.execute('SELECT display_name,deleted_at FROM business_investigation_metadata WHERE workspace=? AND owner=? AND workflow_id=?',(*scope,workflow_id)).fetchone()
            if meta and meta[1]:
                if delete:return dict(workflow_id=workflow_id,deleted=True)
                fail('Investigation artifact not found.','INVESTIGATION_NOT_FOUND',404)
            if delete:
                runs=[json.loads(r[0]) for r in db.execute('SELECT document FROM business_investigation_runs WHERE workspace=? AND owner=?',scope).fetchall()]
                if any(r['workflow_id']==workflow_id and r['status'] in ('queued','running') for r in runs):fail('Wait for the investigation to stop before deleting it.','INVESTIGATION_BUSY',409)
                ids={r['run_id'] for r in runs if r['workflow_id']==workflow_id}
                # Jobs exist whenever the API/worker is installed; direct service
                # diagnostics need not create that table.
                if db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='business_investigation_jobs'").fetchone():
                    jobs=[json.loads(r[0]) for r in db.execute("SELECT document FROM business_investigation_jobs WHERE workspace=? AND owner=? AND state IN ('queued','running')",scope).fetchall()]
                    if any(j.get('workflow_id')==workflow_id or j.get('run_id') in ids for j in jobs):fail('Wait for queued investigation work to stop before deleting it.','INVESTIGATION_BUSY',409)
            db.execute('INSERT INTO business_investigation_metadata VALUES (?,?,?,?,?,?) ON CONFLICT(workspace,owner,workflow_id) DO UPDATE SET display_name=excluded.display_name,deleted_at=excluded.deleted_at,updated_at=excluded.updated_at',(*scope,workflow_id,meta[0] if delete and meta else name,now() if delete else None,now()))
        return dict(workflow_id=workflow_id,deleted=True) if delete else dict(workflow_id=workflow_id,display_name=name)

    def check_plan(self,auth,p):
        self.authorize(auth)
        if p.get('evidence_context'):
            pin=p['evidence_context'];release,_=self.coverage.environments.selected(auth,{k:pin[k] for k in ('dataset_id','case_id')})
            if release['sha256']!=pin['sha256']:fail('Evidence environment changed.','EVIDENCE_ENVIRONMENT_CHANGED',409)
        if digest({k:v for k,v in p.items() if k!='plan_sha256'})!=p['plan_sha256']:fail('Saved workflow plan was modified.','INVESTIGATION_PLAN_CHANGED',409)
        if p['catalogue_sha256']!=CATALOGUE_HASH or p['limits']!=LIMITS:fail('Capability catalogue or limits changed; create a new plan.','INVESTIGATION_CATALOGUE_CHANGED',409)
        validation=validate_graph(p['graph'],p['requirements'])
        if not validation['valid']:fail('Saved workflow graph is invalid.','INVESTIGATION_GRAPH_REJECTED')
        v=self.ontology.version(auth,p['version_id'])
        if digest(v['knowledge'])!=p['knowledge_sha256'] or v['knowledge_sha256']!=p['knowledge_sha256']:fail('Pinned knowledge changed.','INVESTIGATION_KNOWLEDGE_CHANGED',409)
        for s in p['source_stamps']:
            b=self.retrieval.binding(auth,s['source_role'],s['collection'],[])
            if b['stamp']!=s['stamp'] or b['connection_id']!=s['connection_id']:fail('Source bindings or metadata changed; create a fresh plan.','BUSINESS_SOURCE_STALE',409)
        return v

    def catalogue(self,auth):
        self.authorize(auth)
        from .business_evidence import definitions,REGISTRY,REGISTRY_SHA256
        return dict(schema_version=VERSION,sha256=CATALOGUE_HASH,capabilities=deepcopy(CAPABILITIES),limits=deepcopy(LIMITS),
                    model_usage_policy=deepcopy(MODEL_USAGE_POLICY),evidence_requirements={t:definitions(t) for t in REGISTRY},requirement_registry_sha256=REGISTRY_SHA256)

    @staticmethod
    def question(task,context):
        ids=context['identifiers']
        anchor='complaint '+ids['complaint_id'] if ids.get('complaint_id') else 'engine '+ids['serial'] if ids.get('serial') else 'complaint'
        return QUESTIONS[task]+' for '+anchor+'.'

    def plan(self,auth,body):
        auth,scope=self.authorize(auth)
        if not isinstance(body,dict) or set(body)-{'objective','request_key','version_id','inputs','planning_mode','analysis_mode','wait_for_information','evidence_context','preflight_id','client_id','domain_id','workspace_id','tenant_id'} or not {'objective','request_key'}<=set(body):fail('Provide objective and request_key; executable graph payloads are not accepted.')
        key=self.key(body);required=requirements(body['objective']);reject_secrets(body)
        preflight=self.coverage.get(auth,body['preflight_id']) if body.get('preflight_id') else None
        if body.get('evidence_context') and not preflight:fail('Select scenario context through preflight preparation.','EVIDENCE_PREFLIGHT_REQUIRED',422)
        if preflight and preflight['objective']!=body['objective']:fail('Preflight objective differs from the request.','EVIDENCE_PREFLIGHT_MISMATCH',422)
        if preflight and body.get('evidence_context'):
            pin=preflight.get('evidence_context') or {}
            if body['evidence_context']!={k:pin.get(k) for k in ('dataset_id','case_id')}:fail('Preflight case differs from the request.','EVIDENCE_PREFLIGHT_MISMATCH',422)
        context=body.get('inputs',{'identifiers':{}})
        if preflight and any(value and value!=preflight['inputs'].get(key) for key,value in context.items()):fail('Preflight inputs differ from the request.','EVIDENCE_PREFLIGHT_MISMATCH',422)
        if preflight:context=deepcopy(preflight['inputs'])
        if list(Draft202012Validator(CONTEXT_SCHEMA).iter_errors(context)):fail('Inputs must contain typed identifiers and optional ISO assessment date/pinned policy ID.')
        if context.get('assessment_date'):
            from datetime import date
            try:date.fromisoformat(context['assessment_date'])
            except ValueError:fail('assessment_date must be an ISO calendar date.')
        mode=body.get('analysis_mode','crewai')
        if mode not in ('crewai','offline') or type(body.get('wait_for_information',False)) is not bool:fail('Invalid analysis mode or waiting option.')
        if body.get('version_id') is not None and not isinstance(body['version_id'],str):fail('Invalid version ID.')
        fingerprint=digest(body)
        with self.store.transaction(write=False) as db:
            old=db.execute('SELECT fingerprint,document FROM business_investigation_plans WHERE workspace=? AND owner=? AND request_key=?',(*scope,key)).fetchone()
        if old:
            if old[0]!=fingerprint:fail('Request key already belongs to another objective.','INVESTIGATION_CONFLICT',409)
            p=json.loads(old[1]);self.check_plan(auth,p);return p
        vid=(preflight['version_id'] if preflight else None) or body.get('version_id') or self.retrieval.latest(auth);v=self.ontology.version(auth,vid)
        if preflight and body.get('version_id') not in (None,vid):fail('Preflight knowledge differs from the request.','EVIDENCE_PREFLIGHT_MISMATCH',422)
        if not v.get('knowledge'):fail('This version has no Phase 1 knowledge.','INVESTIGATION_KNOWLEDGE_REQUIRED',409)
        parsed=interpret(body['objective'],v,context['identifiers'])
        context=deepcopy(context);context['identifiers']=parsed['identifiers']
        if parsed['ambiguities'] and parsed['identifiers']:fail('Conflicting identifiers: '+str(parsed['ambiguities']))
        previews={};stamps={}
        tasks=['complaints']+[t for t in ('inspection','warranty','replacement','history','recurrence') if required.get(t)]
        for task in tasks:
            prepared_inputs=dict(context['identifiers'],**{k:context[k] for k in ('assessment_date','policy_id') if k in context and not (preflight and preflight.get('evidence_context') and k=='policy_id')})
            preview=self.retrieval.prepare(auth,v,self.question(task,context),prepared_inputs)
            previews[task]=preview
            for m in preview['mappings']:
                b=self.retrieval.binding(auth,m['source_role'],m['collection'],[])
                stamps[(m['source_role'],m['collection'])]=dict(source_role=m['source_role'],collection=m['collection'],connection_id=b['connection_id'],stamp=b['stamp'])
        knowledge=dict(version_id=vid,knowledge_sha256=v['knowledge_sha256'],tasks={name:dict(intent=p['intent'],concepts=p['concepts'],dependencies=p['dependency_resolution'],mappings=p['mappings'],rules=p['rules'],missing=p['missing'],evidence_requirements=p['evidence_requirements']) for name,p in previews.items()})
        if preflight:
            for task,result in preflight['coverage'].items():
                if task in knowledge['tasks']:knowledge['tasks'][task]['coverage']=dict(state=result['state'],required_facts=[r['fact_id'] for r in result['requirements']],available_facts=[r['fact_id'] for r in result['available_evidence']],available_evidence=[dict(fact_id=r['fact_id'],source_record_ids=[ref.get('record_id',ref.get('policy_id')) for ref in r['source_references']]) for r in result['available_evidence']],provider_fingerprint=result['provider_fingerprint'],blocking_requirements=[dict(fact_id=g['fact_id'],state=g['state'],impact=g['impact']) for g in result['blocking_requirements']],optional_limitations=[g['fact_id'] for g in result['optional_limitations']],business_outcomes=result['business_outcomes'],provenance=result['provenance'])
        if preflight and preflight.get('schema_version')=='business-preparation-v1':
            knowledge['business_preparation']=self.coverage.preparation.context(preflight)
        planning_knowledge=(dict(version_id=vid,knowledge_sha256=v['knowledge_sha256'],business_preparation=knowledge['business_preparation']) if 'business_preparation' in knowledge else knowledge)
        from .workflow_display import title_before_planning
        display_name=title_before_planning(body['objective'],env=self.env if body.get('planning_mode','model')=='model' else None)
        graph,planning=self.planner.plan(body['objective'],required,planning_knowledge,body.get('planning_mode','model'))
        if not validate_graph(graph,required)['valid']:fail('The proposed graph is invalid.','INVESTIGATION_GRAPH_REJECTED')
        p=dict(schema_version=VERSION,workflow_id='investigation_'+secrets.token_hex(12),revision=1,objective=body['objective'],requirements=required,
               version_id=vid,knowledge_sha256=v['knowledge_sha256'],catalogue_sha256=CATALOGUE_HASH,graph=graph,planning=planning,
               inputs=context,analysis_mode=mode,wait_for_information=body.get('wait_for_information',False),
               ontology_context=knowledge,source_stamps=list(stamps.values()),limits=deepcopy(LIMITS),created_at=now(),read_only=True,company_reads=0)
        if preflight:p.update(preflight=preflight,evidence_context=preflight.get('evidence_context'),company_reads=preflight.get('source_retrieval_calls',0),preparation_fingerprint=digest({k:v for k,v in body.items() if k!='preflight_id'}))
        p['display_name']=display_name
        p['plan_sha256']=digest(p)
        self.check_plan(auth,p)
        with self.store.transaction() as db:
            db.execute('INSERT INTO business_investigation_plans VALUES (?,?,?,?,?,?) ON CONFLICT(workspace,owner,request_key) DO NOTHING',(*scope,p['workflow_id'],key,fingerprint,canonical(p)))
            row=db.execute('SELECT fingerprint,document FROM business_investigation_plans WHERE workspace=? AND owner=? AND request_key=?',(*scope,key)).fetchone()
        if row[0]!=fingerprint:fail('Concurrent plan request conflict.','INVESTIGATION_CONFLICT',409)
        return json.loads(row[1])

    def validate(self,auth,workflow_id):
        p=self.get_plan(auth,workflow_id)
        return dict(workflow_id=workflow_id,validation=validate_graph(p['graph'],p['requirements']),version_id=p['version_id'],knowledge_sha256=p['knowledge_sha256'])

    def create_run(self,auth,workflow_id,body):
        auth,scope=self.authorize(auth,True)
        if not isinstance(body,dict) or set(body)!={'request_key'}:fail('Run creation accepts request_key only.')
        key=self.key(body);p=self.get_plan(auth,workflow_id);fingerprint=digest([workflow_id,p['plan_sha256']])
        run=dict(run_id='investigation_run_'+secrets.token_hex(12),workflow_id=workflow_id,workflow_revision=p['revision'],plan_sha256=p['plan_sha256'],
                 version_id=p['version_id'],knowledge_sha256=p['knowledge_sha256'],status='queued',node_states={n['id']:'pending' for n in p['graph']['nodes']},
                 edge_states={},outputs={},attempts={},node_inputs={},node_errors={},node_times={},invocations={},branches={},inputs=deepcopy(p['inputs']),assertions={},
                 pending_inputs=[],input_history=[],usage=dict(model_calls=0,model_calls_reserved=0,tokens=0,estimated_cost_usd=0,retrieval_calls=0,active_seconds=0),
                 events=[],created_at=now(),updated_at=now(),company_writes=0)
        self.event(run,'run.created')
        with self.store.transaction() as db:
            deleted=db.execute('SELECT deleted_at FROM business_investigation_metadata WHERE workspace=? AND owner=? AND workflow_id=?',(*scope,workflow_id)).fetchone()
            if deleted and deleted[0]:fail('Investigation artifact not found.','INVESTIGATION_NOT_FOUND',404)
            db.execute('INSERT INTO business_investigation_runs VALUES (?,?,?,?,?,?,?,?) ON CONFLICT(workspace,owner,request_key) DO NOTHING',(*scope,run['run_id'],key,fingerprint,None,0,canonical(run)))
            row=db.execute('SELECT fingerprint,document FROM business_investigation_runs WHERE workspace=? AND owner=? AND request_key=?',(*scope,key)).fetchone()
        if row[0]!=fingerprint:fail('Run request key conflict.','INVESTIGATION_CONFLICT',409)
        return json.loads(row[1])

    def get_run(self,auth,run_id):
        auth,scope=self.authorize(auth)
        with self.store.transaction(write=False) as db:r=self.row(db,'business_investigation_runs',scope,'run_id',run_id)
        p=self.get_plan(auth,r['workflow_id'])
        if r['plan_sha256']!=p['plan_sha256'] or r['version_id']!=p['version_id']:fail('Run binding is inconsistent.')
        return r

    def save(self,db,scope,run):
        run['updated_at']=now();reject_secrets(run)
        if len(canonical(run).encode())>LIMITS['max_run_bytes']:fail('Investigation state exceeds its byte budget.','INVESTIGATION_STATE_LIMIT')
        db.execute('UPDATE business_investigation_runs SET document=? WHERE workspace=? AND owner=? AND run_id=?',(canonical(run),*scope,run['run_id']))

    @staticmethod
    def event(run,name,**details):
        run['events'].append(dict(sequence=len(run['events'])+1,type=name,at=now(),**details))

    def transition(self,run,nid,target):
        current=run['node_states'][nid]
        if target not in NODE_TRANSITIONS[current]:fail('Invalid node transition '+current+' -> '+target)
        run['node_states'][nid]=target;self.event(run,'node.'+target,node_id=nid)

    def claim(self,auth,run_id,resume):
        auth,scope=self.authorize(auth,True);r=self.get_run(auth,run_id);p=self.get_plan(auth,r['workflow_id'])
        owner=secrets.token_hex(16)
        with self.store.transaction() as db:
            run=self.row(db,'business_investigation_runs',scope,'run_id',run_id,True)
            lease=db.execute('SELECT lease_owner,lease_until FROM business_investigation_runs WHERE workspace=? AND owner=? AND run_id=?',(*scope,run_id)).fetchone()
            if lease[0] and lease[1]>self.clock():fail('Another executor owns this run.','INVESTIGATION_BUSY',409)
            if run['status'] in TERMINAL:return auth,scope,p,run,None
            if run['status']=='failed' and not resume:fail('Inspect failure and explicitly resume eligible work.','INVESTIGATION_RESUME_REQUIRED',409)
            if run['status']=='waiting_for_input':return auth,scope,p,run,None
            for n in p['graph']['nodes']:
                nid=n['id'];state=run['node_states'][nid]
                if state in ('running','failed','ready'):
                    if state=='running' and not resume:fail('Interrupted work requires explicit resume.','INVESTIGATION_RESUME_REQUIRED',409)
                    if run['attempts'].get(nid,0)>=n['constraints']['max_attempts'] and state!='ready':
                        fail('Node retry budget exhausted; inspect or create a new run.','INVESTIGATION_RETRY_EXHAUSTED',409)
                    if state=='failed' and run['node_errors'].get(nid,{}).get('retryable') is not True:
                        fail('This failure is not retryable; create a corrected plan.','INVESTIGATION_NONRETRYABLE',409)
                    if state=='ready':run['node_states'][nid]='pending'
                    else:self.transition(run,nid,'pending')
            run['status']='running';self.event(run,'run.resumed' if resume else 'run.started')
            db.execute('UPDATE business_investigation_runs SET lease_owner=?,lease_until=? WHERE workspace=? AND owner=? AND run_id=?',(owner,self.clock()+90,*scope,run_id))
            self.save(db,scope,run)
        return auth,scope,p,run,owner

    def renew(self,scope,run_id,owner):
        with self.store.transaction() as db:
            cur=db.execute('UPDATE business_investigation_runs SET lease_until=? WHERE workspace=? AND owner=? AND run_id=? AND lease_owner=? AND lease_until>?',(self.clock()+90,*scope,run_id,owner,self.clock()))
        return cur.rowcount==1

    def owned(self,db,scope,run_id,owner):
        run=self.row(db,'business_investigation_runs',scope,'run_id',run_id,True)
        row=db.execute('SELECT lease_owner,lease_until FROM business_investigation_runs WHERE workspace=? AND owner=? AND run_id=?',(*scope,run_id)).fetchone()
        if row[0]!=owner or row[1]<=self.clock():fail('Executor lease was lost.','INVESTIGATION_LEASE_LOST',409)
        return run

    @staticmethod
    def evidence(run):
        result=[]
        for output in run['outputs'].values():
            if not isinstance(output,dict):continue
            for o in (output,output.get('fresh_source_evidence')):
                if isinstance(o,dict) and isinstance(o.get('records'),list) and 'request_id' in o:result.append(o)
        return result

    def analysis_context(self,run,node):
        if node['capability']!='prepare_summary':
            e=run['outputs'][next(b['source'] for b in node['inputs'] if b['name']=='evidence')]
            return packet([e],assertions=run['assertions'])
        analyses=[{k:v for k,v in o.items() if k!='fresh_source_evidence'} for o in run['outputs'].values() if o.get('classification')=='agent_interpretation']
        return packet(self.evidence(run),analyses,run['assertions'])

    def report(self,p,run):
        evidence=self.evidence(run);analyses=[deepcopy({k:v for k,v in o.items() if k!='fresh_source_evidence'}) for o in run['outputs'].values() if o.get('classification')=='agent_interpretation']
        previous=[]
        if p.get('preflight'):
            latest={}
            for e in evidence:
                task=e['intent']['task']
                if task in latest:previous.append(latest[task])
                latest[task]=e
            evidence=list(latest.values())
        def observed_values(e):return digest([(r['record_id'],r['fields'],r['values']) for r in e.get('records',[])])
        source_changes=[dict(task=e['intent']['task'],previous_request=e['request_id'],current_request=current['request_id']) for e in previous for current in evidence if e['intent']['task']==current['intent']['task'] and observed_values(e)!=observed_values(current)]
        if source_changes:
            for analysis in analyses:
                for finding in analysis.get('findings',[]):finding['qualification']='Sources changed during execution. This interpretation may refer to a prior observation; inspect retained observation history.'
        records=[];seen=set()
        for e in evidence:
            for r in e['records']:
                key=(e['request_id'],r['record_id'])
                if key not in seen:records.append(dict(evidence_id=e['request_id'],**r));seen.add(key)
        from .business_evidence import evaluate,normalize_gaps,reconcile_suggestions,REGISTRY_SHA256
        requested=set(p['ontology_context']['tasks'])-{'complaints'}
        if not requested:requested={'complaints'}
        task_results=[]
        for task in sorted(requested):
            selected=[e for e in evidence if e['intent']['task']==task]
            if selected:
                task_results.extend(e.get('requirement_results') or evaluate(task,e,p['inputs']) for e in selected)
            else:
                task_results.append(evaluate(task,dict(records=[],selected_mappings=p['ontology_context']['tasks'][task]['mappings']),p['inputs']))
        all_gaps=normalize_gaps([g for result in task_results for g in result['gaps']])
        missing=[g for g in all_gaps if g['requirement_level']!='downstream']
        # Original model outputs remain in run.outputs. Report copies remove
        # repeated model prose; only registered task facts create requirements.
        suggestions=reconcile_suggestions(analyses,task_results)
        analyses=[dict(a,missing_information=[]) for a in analyses]
        candidates=[c for e in evidence for c in e.get('ambiguous_associations',[])]
        recovery=next((o for o in run['outputs'].values() if o.get('classification')=='backend_evidence_compilation'),None)
        coverage_results=[e['coverage'] for e in evidence if 'coverage' in e and e['intent']['task'] in requested]
        mandatory=[g for g in missing if g['impact']!='optional_supporting_evidence']
        incomplete=bool(mandatory or run['node_errors']) or (not p.get('preflight') and any(not e.get('record_reads_complete',False) for e in evidence))
        return dict(objective=p['objective'],workflow_id=p['workflow_id'],workflow_revision=p['revision'],run_id=run['run_id'],version_id=p['version_id'],knowledge_sha256=p['knowledge_sha256'],
                    completion_status='completed_with_gaps' if incomplete else 'completed',source_records=records,
                    execution_status='completed',decision_readiness={r['task']:dict(state=r['state'],business_outcomes=r['business_outcomes'],provenance=r['provenance'],official_approval=False) for r in coverage_results},scenario_context=p.get('evidence_context'),
                    model_usage_policy=deepcopy(MODEL_USAGE_POLICY),report_generation=dict(mode='evidence_only' if recovery else 'standard',narrative_status='unavailable' if recovery else 'available',reason_code=recovery.get('reason_code') if recovery else None),
                    retrieved_facts=[dict(evidence_id=e['request_id'],**f) for e in evidence for f in e['findings']],
                    prior_source_observations=[dict(request_id=e['request_id'],records=e['records']) for e in previous],
                    source_changes=source_changes,
                    configured_rule_outcomes=[r for e in evidence for r in e.get('rule_results',[])],agent_interpretations=analyses,
                    missing_information=missing,normalized_gaps=missing,task_evidence=task_results,
                    requirement_registry_sha256=REGISTRY_SHA256,
                    gap_sections={impact:[g for g in missing if g['impact']==impact] for impact in ('blocking_current_task','blocking_requested_conclusion','optional_supporting_evidence')},
                    downstream_requirements=[g for g in all_gaps if g['requirement_level']=='downstream'],
                    recovery_actions=[dict(gap_id=g['gap_id'],**g['recovery_action']) for g in missing],
                    gap_reconciliation=dict(agent_suggestion_count=len(suggestions),mandatory_requirements_created_by_agents=0,original_suggestions_location='run.outputs'),
                    resolved_references=[v for e in evidence for v in e.get('resolved_references',[])],
                    confirmed_findings=[],unverified_findings=[dict(f,classification='agent_interpretation') for a in analyses for f in a.get('findings',[])],
                    ambiguous_associations=candidates,conversion_issues=[i for e in evidence for i in e.get('conversion_issues',[])],
                    executed_nodes={k:v for k,v in run['node_states'].items() if v!='pending'},branch_decisions=run['branches'],execution_errors=run['node_errors'],
                    user_assertions=dict(values=run['assertions'],verification='unverified_user_input'),
                    physical_engine_identity='unresolved',warranty_approval='not_performed',company_writes=0,
                    qualification=('Sources changed during execution; prior interpretations may describe earlier observations. ' if source_changes else '')+('Model-written final narrative was unavailable; the report was compiled from retrieved evidence, prior validated interpretations and registered gaps without another model call. ' if recovery else '')+'Source observations, configured rule outcomes and agent interpretations remain separate. No official eligibility, confirmed diagnosis or operational authorization is inferred.')

    def invoke(self,auth,p,run,node):
        self.authorize(auth,True);nid=node['id'];kind=node['type'];cap=CATALOGUE.get(node['capability'])
        # Recheck immediately before dispatch: canceled/lost invocations cannot
        # start a later source/model call from an older thread snapshot.
        with self.store.transaction(write=False) as db:
            current=self.row(db,'business_investigation_runs',identity(auth),'run_id',run['run_id'])
            lease=db.execute('SELECT lease_until FROM business_investigation_runs WHERE workspace=? AND owner=? AND run_id=?',(*identity(auth),run['run_id'])).fetchone()
        if current['status']!='running' or current['invocations'].get(nid)!=run['invocations'].get(nid) or lease[0]<=self.clock():
            fail('This node no longer owns an active execution.','INVESTIGATION_CANCELED',409)
        bound={b['name']:deepcopy(run['outputs'][b['source']]) for b in node['inputs']}
        if cap and list(Draft202012Validator(cap['input_schema']).iter_errors(bound)):fail('Capability inputs do not match their schema.')
        if kind=='start':return deepcopy(run['inputs']),None,{}
        if kind=='human_input':
            if not run['inputs']['identifiers']:return dict(waiting=True,requested=['complaint_id or serial'],reason='A concrete source identifier is required.'),None,{}
            return deepcopy(run['inputs']),None,{}
        if kind=='retrieval':
            task=cap['retrieval_task'];context=bound['context'];inputs=dict(context['identifiers'],**{k:context[k] for k in ('assessment_date','policy_id') if k in context})
            if p.get('evidence_context'):
                result=self.coverage.scenario_evidence(auth,p,task)
                return result,None,dict(retrieval_calls=1)
            preview=self.retrieval.preview(auth,dict(question=self.question(task,context),inputs=inputs,version_id=p['version_id'],request_key=run['run_id']+'_'+nid))
            result=self.retrieval.execute(auth,preview['request_id'],{})
            if p.get('preflight'):
                result['coverage']=self.coverage.runtime_coverage(auth,p,task,result);result['requirement_results']=result['coverage'];result['normalized_gaps']=result['coverage']['gaps']
            if result['version_id']!=p['version_id'] or result['knowledge_sha256']!=p['knowledge_sha256']:fail('Retrieval returned foreign knowledge.')
            return result,None,dict(retrieval_calls=1)
        if kind=='agent':
            fresh=None
            if p.get('preflight') and node['capability']!='prepare_summary':
                selected=bound.get('evidence',{});task='inspection' if node['capability']=='compare_inspection' else 'warranty'
                fresh=self.coverage.refresh(auth,p,task);selected=fresh
                checked=self.coverage.runtime_coverage(auth,p,task,selected)
                if not checked['task_executable'] or node['capability']=='warranty_readiness' and not checked['conclusion_ready']:
                    return dict(summary='This requested assessment needs the registered supporting evidence or inputs. Other investigation activities can continue.',findings=[],missing_information=[],classification='backend_coverage_check',coverage=checked,mode='deterministic',fresh_source_evidence=fresh),None,dict(coverage_retrieval_calls=0 if p.get('evidence_context') else 1)
                run=deepcopy(run)
                binding=next(b['source'] for b in node['inputs'] if b['name']=='evidence');run['outputs'][binding]=fresh
            result,usage=self.agents.run(node['capability'],self.analysis_context(run,node),p['analysis_mode'])
            if fresh:result['fresh_source_evidence']=fresh
            return result,None,dict(model_calls=usage['llm_calls'],tokens=usage['tokens'],estimated_cost_usd=usage['estimated_cost_usd'],coverage_retrieval_calls=1 if fresh and not p.get('evidence_context') else 0)
        if kind=='condition':
            outcome=predicate(node['predicate'],bound['evidence'])
            return dict(predicate=node['predicate'],outcome=outcome,classification='deterministic_backend_check'),outcome,{}
        if kind=='parallel':return dict(split=True),None,{}
        if kind=='join':return dict(joined_nodes=[e['source'] for e in p['graph']['edges'] if e['target']==nid and run['edge_states'].get(e['id'])=='selected']),None,{}
        if kind=='deterministic':
            msg='No matching complaint record was retrieved.' if nid=='not_found' else 'Inspection evidence is missing.' if nid=='no_inspection' else 'The branch condition could not be established.' if nid in ('uncertain_complaint','unknown_inspection') else 'Required facts remain listed in retrieved evidence.'
            return dict(missing_information=[msg],classification='deterministic_gap'),None,{}
        if kind=='end':
            if p.get('preflight'):
                run=deepcopy(run)
                for task in p['ontology_context']['tasks']:run['outputs']['coverage_refresh_'+task]=self.coverage.refresh(auth,p,task)
            report=self.report(p,run)
            if p['wait_for_information'] and report['missing_information'] and not run.get('information_acknowledged'):
                report['execution_status']='waiting_for_input'
                return dict(waiting=True,requested=['acknowledge_gaps','notes'],reason='Review the explicit evidence gaps before finalizing the report.',partial_report=report),None,{}
            return report,None,dict(coverage_retrieval_calls=len(p['ontology_context']['tasks']) if p.get('preflight') and not p.get('evidence_context') else 0)
        fail('Unsupported node implementation.')

    def invoke_timed(self,auth,p,run,node):
        started=time.monotonic()
        result=self.invoke(auth,p,run,node)
        if time.monotonic()-started>node['constraints']['timeout_seconds']:
            fail('Node duration exceeded its declared bound.','INVESTIGATION_NODE_TIMEOUT',408)
        return result

    def execute(self,auth,run_id,body=None,resume=False):
        self._execute(auth,run_id,body,resume)
        # Return the committed checkpoint including finally-accounted duration,
        # after a final current-authority/source check.
        return self.get_run(auth,run_id)

    def _execute(self,auth,run_id,body=None,resume=False):
        if body not in ({},None):fail('Execution accepts only a saved run ID and empty body.')
        auth,scope,p,run,owner=self.claim(auth,run_id,resume)
        if owner is None:return run
        from .worker_control import LeaseHeartbeat
        started=time.monotonic()
        try:
            with LeaseHeartbeat(lambda:self.renew(scope,run_id,owner),interval=15):
                with ThreadPoolExecutor(max_workers=LIMITS['max_parallel'],thread_name_prefix='simpson-investigation') as pool:
                    while True:
                        self.authorize(auth,True);self.check_plan(auth,p)
                        with self.store.transaction() as db:
                            run=self.owned(db,scope,run_id,owner)
                            if run['status']!='running':return run
                            if run['usage']['active_seconds']+time.monotonic()-started>LIMITS['max_seconds']:fail('Workflow time budget exhausted.','INVESTIGATION_TIMEOUT',408)
                            # Shared scheduler receives only unresolved/scheduled states.
                            scheduled={nid:state for nid,state in run['node_states'].items() if state!='pending'}
                            ns=[dict(node_id=n['id']) for n in p['graph']['nodes']]
                            es=[dict(edge_id=e['id'],source=e['source'],target=e['target']) for e in p['graph']['edges']]
                            ready,skipped=ready_frontier(ns,es,scheduled,run['edge_states'])
                            for item in skipped:
                                nid=item['node_id'];self.transition(run,nid,'skipped')
                                for e in p['graph']['edges']:
                                    if e['source']==nid:run['edge_states'][e['id']]='skipped'
                            if skipped:self.save(db,scope,run);continue
                            ids={n['node_id'] for n in ready};frontier=[n for n in p['graph']['nodes'] if n['id'] in ids][:LIMITS['max_parallel']]
                            if not frontier:
                                stopped=any(run['node_states'][n['id']]=='failed' and n['on_error']=='stop' for n in p['graph']['nodes'])
                                if stopped:run['status']='failed'
                                elif all(v in ('succeeded','skipped','failed') for v in run['node_states'].values()):run['status']='completed'
                                else:fail('No eligible nodes remain in a nonterminal graph.','INVESTIGATION_DEADLOCK')
                                self.event(run,'run.'+run['status']);self.save(db,scope,run);return run
                            for node in frontier:
                                nid=node['id'];self.transition(run,nid,'ready');self.transition(run,nid,'running')
                                run['attempts'][nid]=run['attempts'].get(nid,0)+1
                                run['node_inputs'][nid]=deepcopy(node['inputs'])
                                run['node_times'][nid]=dict(started_at=now())
                                run['invocations'][nid]=run['run_id']+':'+nid+':'+str(run['attempts'][nid])
                                if node['type']=='agent' and p['analysis_mode']=='crewai':
                                    if run['usage']['model_calls_reserved']>=LIMITS['max_model_calls']:fail('Workflow model-call budget exhausted.','INVESTIGATION_BUDGET')
                                    run['usage']['model_calls_reserved']+=1
                            self.save(db,scope,run)
                        futures={pool.submit(self.invoke_timed,auth,p,deepcopy(run),n):n for n in frontier}
                        batch_failed=False
                        for future in as_completed(futures):
                            node=futures[future];nid=node['id'];error=None
                            try:
                                output,outcome,usage=future.result();reject_secrets(output)
                                self.authorize(auth,True);self.check_plan(auth,p)
                                if node['capability'] and list(Draft202012Validator(CATALOGUE[node['capability']]['output_schema']).iter_errors(output)) and node['type']!='agent':fail('Capability output schema failed.')
                            except Exception as exc:
                                output,outcome,usage=None,None,{}
                                error=dict(code=getattr(exc,'code','INVESTIGATION_NODE_FAILED'),retryable=getattr(exc,'code',None) in ('BUSINESS_SOURCE_UNAVAILABLE','INVESTIGATION_MODEL_REQUIRED'),message='Node execution failed; inspect code and evidence gaps.')
                                observed=getattr(exc,'usage',None)
                                if isinstance(observed,dict) and all(type(observed.get(k)) in (int,float) and 0<=observed[k]<float('inf') for k in ('llm_calls','tokens','estimated_cost_usd')):
                                    error['model_usage']=observed
                                if error['code']=='MODEL_OUTPUT_SCHEMA_INVALID':
                                    path=getattr(exc,'validation_field',None)
                                    if isinstance(path,str) and re.fullmatch(r'[A-Za-z0-9_/-]{1,300}',path):error['validation_field']=path
                            with self.store.transaction() as db:
                                current=self.owned(db,scope,run_id,owner)
                                if current['status']=='canceled':continue
                                current['node_times'][nid]['finished_at']=now()
                                if error:
                                    observed=error.get('model_usage',{})
                                    for source,target in [('llm_calls','model_calls'),('tokens','tokens'),('estimated_cost_usd','estimated_cost_usd')]:
                                        current['usage'][target]+=observed.get(source,0)
                                    self.transition(current,nid,'failed');current['node_errors'][nid]=error;self.event(current,'node.error',node_id=nid,**error)
                                    if node['on_error']=='stop':batch_failed=True
                                    else:
                                        current['outputs'][nid]=dict(error=error,missing_information=['Node '+nid+' failed.'])
                                        for e in p['graph']['edges']:
                                            if e['source']==nid:current['edge_states'][e['id']]='selected'
                                elif output.get('waiting'):
                                    self.transition(current,nid,'waiting_for_input');current['status']='waiting_for_input'
                                    current['pending_inputs']=[dict(node_id=nid,**output)];self.event(current,'run.waiting_for_input',node_id=nid)
                                else:
                                    self.transition(current,nid,'succeeded');current['outputs'][nid]=output;current['node_errors'].pop(nid,None)
                                    for counter,value in usage.items():current['usage'][counter]=current['usage'].get(counter,0)+value
                                    if outcome is not None:current['branches'][nid]=outcome
                                    for e in p['graph']['edges']:
                                        if e['source']==nid:current['edge_states'][e['id']]='selected' if outcome is None or e['outcome']==outcome else 'skipped'
                                self.save(db,scope,current)
                        with self.store.transaction() as db:
                            current=self.owned(db,scope,run_id,owner)
                            if batch_failed and current['status']=='running':current['status']='failed';self.event(current,'run.failed')
                            self.save(db,scope,current)
                            if current['status']!='running':
                                self.authorize(auth,True);self.check_plan(auth,p)
                                return current
        except Exception as exc:
            with self.store.transaction() as db:
                current=self.owned(db,scope,run_id,owner)
                if current['status']=='running':
                    current['status']='failed';self.event(current,'run.error',code=getattr(exc,'code','INVESTIGATION_EXECUTION_FAILED'));self.save(db,scope,current)
            raise
        finally:
            with self.store.transaction() as db:
                row=db.execute('SELECT lease_owner,document FROM business_investigation_runs WHERE workspace=? AND owner=? AND run_id=?',(*scope,run_id)).fetchone()
                if row and row[0]==owner:
                    current=json.loads(row[1]);current['usage']['active_seconds']+=time.monotonic()-started;self.save(db,scope,current)
                    db.execute('UPDATE business_investigation_runs SET lease_owner=NULL,lease_until=0 WHERE workspace=? AND owner=? AND run_id=? AND lease_owner=?',(*scope,run_id,owner))

    def supply_input(self,auth,run_id,body):
        auth,scope=self.authorize(auth,True);r=self.get_run(auth,run_id)
        if not isinstance(body,dict) or set(body)-{'request_key','identifiers','assessment_date','policy_id','acknowledge_gaps','notes'} or 'request_key' not in body:fail('Supply only typed requested inputs.')
        key=self.key(body);reject_secrets(body)
        if 'notes' in body and (not isinstance(body['notes'],str) or len(body['notes'])>2000):fail('Notes must be at most 2000 characters.')
        if 'acknowledge_gaps' in body and type(body['acknowledge_gaps']) is not bool:fail('acknowledge_gaps must be boolean.')
        with self.store.transaction() as db:
            run=self.row(db,'business_investigation_runs',scope,'run_id',run_id,True)
            old=next((i for i in run['input_history'] if i['request_key']==key),None)
            if old:
                if old['sha256']!=digest(body):fail('Input request key conflict.','INVESTIGATION_CONFLICT',409)
                return run
            if run['status']!='waiting_for_input':fail('This run is not waiting for input.','INVESTIGATION_NOT_WAITING',409)
            nid=run['pending_inputs'][0]['node_id'];updated=deepcopy(run['inputs'])
            if nid=='anchor':
                if not body.get('identifiers'):fail('Supply one complaint_id or serial.')
                updated.update({k:body[k] for k in ('identifiers','assessment_date','policy_id') if k in body})
                if list(Draft202012Validator(CONTEXT_SCHEMA).iter_errors(updated)) or len(updated['identifiers'])!=1:fail('Supply exactly one typed identifier.')
                snapshot=self.ontology.version(auth,run['version_id'])
                if updated.get('assessment_date'):
                    from datetime import date
                    try:date.fromisoformat(updated['assessment_date'])
                    except ValueError:fail('assessment_date must be an ISO calendar date.')
                if updated.get('policy_id') and not any(p['policy_id']==updated['policy_id'] for p in snapshot['knowledge']['manifest']['policy_snapshots']):
                    fail('policy_id must name a revision pinned in this ontology version.')
                parsed=interpret('Show complaints.',snapshot,updated['identifiers'])
                if parsed['ambiguities'] or parsed['identifiers']!=updated['identifiers']:fail('Invalid identifier.')
            elif nid=='end':
                if body.get('acknowledge_gaps') is not True:fail('Explicitly acknowledge unresolved gaps; user input does not verify the evidence.')
                if any(k in body for k in ('identifiers','assessment_date','policy_id')):fail('Pinned retrieval inputs cannot change after source execution.')
                run['information_acknowledged']=True
            else:fail('Unsupported pending input node.')
            run['inputs']=updated;run['assertions'][key]={k:v for k,v in body.items() if k!='request_key'}
            run['input_history'].append(dict(request_key=key,sha256=digest(body),at=now(),verification='unverified_user_input'))
            self.transition(run,nid,'pending');run['pending_inputs']=[];run['status']='queued';self.event(run,'input.supplied',node_id=nid,verification='unverified_user_input');self.save(db,scope,run)
        return run

    def cancel(self,auth,run_id,body):
        if body!={}:fail('Cancel accepts an empty object.')
        auth,scope=self.authorize(auth,True);self.get_run(auth,run_id)
        with self.store.transaction() as db:
            run=self.row(db,'business_investigation_runs',scope,'run_id',run_id,True)
            if run['status']=='completed':fail('A completed run cannot be canceled.','INVESTIGATION_TERMINAL',409)
            if run['status']!='canceled':run['status']='canceled';self.event(run,'run.canceled');self.save(db,scope,run)
        return run
