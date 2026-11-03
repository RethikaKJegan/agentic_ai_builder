"""Durable read-only Simpson investigation composition over Phase 2 and CrewAI.

Company reads stay inside BusinessRetrieval. This domain executor does not submit
or bypass approved production workflow releases and cannot execute write tools.
"""
from concurrent.futures import ThreadPoolExecutor,as_completed
from copy import deepcopy
import json
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
from .investigation_agents import InvestigationAgents,packet
from .google_connections import now

TERMINAL={'completed','canceled'}
NODE_TRANSITIONS={
 'pending':{'ready','skipped'},'ready':{'running','failed'},'running':{'succeeded','failed','waiting_for_input','pending'},
 'waiting_for_input':{'pending'},'failed':{'pending'},'succeeded':set(),'skipped':set(),
}
QUESTIONS={'complaints':'Show complaints','inspection':'Show inspection findings','warranty':'Check warranty evidence','replacement':'Show replacement evidence','history':'Show history'}


class BusinessInvestigations:
    def __init__(self,retrieval,env=None,planner=None,agents=None,clock=time.time):
        self.retrieval,self.ontology,self.store=retrieval,retrieval.ontology,retrieval.store
        self.env=env or {};self.planner=planner or InvestigationPlanner(self.env);self.agents=agents or InvestigationAgents(self.env);self.clock=clock
        with self.store.transaction() as db:
            db.execute('CREATE TABLE IF NOT EXISTS business_investigation_plans (workspace TEXT NOT NULL,owner TEXT NOT NULL,workflow_id TEXT NOT NULL,request_key TEXT NOT NULL,fingerprint TEXT NOT NULL,document TEXT NOT NULL,PRIMARY KEY(workspace,owner,workflow_id),UNIQUE(workspace,owner,request_key))')
            db.execute('CREATE TABLE IF NOT EXISTS business_investigation_runs (workspace TEXT NOT NULL,owner TEXT NOT NULL,run_id TEXT NOT NULL,request_key TEXT NOT NULL,fingerprint TEXT NOT NULL,lease_owner TEXT,lease_until REAL NOT NULL,document TEXT NOT NULL,PRIMARY KEY(workspace,owner,run_id),UNIQUE(workspace,owner,request_key))')

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
        with self.store.transaction(write=False) as db:p=self.row(db,'business_investigation_plans',scope,'workflow_id',workflow_id)
        self.check_plan(auth,p)
        return p

    def check_plan(self,auth,p):
        self.authorize(auth)
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
        return dict(schema_version=VERSION,sha256=CATALOGUE_HASH,capabilities=deepcopy(CAPABILITIES),limits=deepcopy(LIMITS))

    @staticmethod
    def question(task,context):
        ids=context['identifiers']
        anchor='complaint '+ids['complaint_id'] if ids.get('complaint_id') else 'engine '+ids['serial'] if ids.get('serial') else 'complaint'
        return QUESTIONS[task]+' for '+anchor+'.'

    def plan(self,auth,body):
        auth,scope=self.authorize(auth)
        if not isinstance(body,dict) or set(body)-{'objective','request_key','version_id','inputs','planning_mode','analysis_mode','wait_for_information'} or not {'objective','request_key'}<=set(body):fail('Provide objective and request_key; executable graph payloads are not accepted.')
        key=self.key(body);required=requirements(body['objective']);reject_secrets(body)
        context=body.get('inputs',{'identifiers':{}})
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
        vid=body.get('version_id') or self.retrieval.latest(auth);v=self.ontology.version(auth,vid)
        if not v.get('knowledge'):fail('This version has no Phase 1 knowledge.','INVESTIGATION_KNOWLEDGE_REQUIRED',409)
        parsed=interpret(body['objective'],v,context['identifiers'])
        context=deepcopy(context);context['identifiers']=parsed['identifiers']
        if parsed['ambiguities'] and parsed['identifiers']:fail('Conflicting identifiers: '+str(parsed['ambiguities']))
        previews={};stamps={}
        tasks=['complaints']+[t for t in ('inspection','warranty','replacement','history') if required[t]]
        for task in tasks:
            preview=self.retrieval.prepare(auth,v,self.question(task,context),dict(context['identifiers'],**{k:context[k] for k in ('assessment_date','policy_id') if k in context}))
            previews[task]=preview
            for m in preview['mappings']:
                b=self.retrieval.binding(auth,m['source_role'],m['collection'],[])
                stamps[(m['source_role'],m['collection'])]=dict(source_role=m['source_role'],collection=m['collection'],connection_id=b['connection_id'],stamp=b['stamp'])
        knowledge=dict(version_id=vid,knowledge_sha256=v['knowledge_sha256'],tasks={name:dict(intent=p['intent'],concepts=p['concepts'],dependencies=p['dependency_resolution'],mappings=p['mappings'],rules=p['rules'],missing=p['missing']) for name,p in previews.items()})
        graph,planning=self.planner.plan(body['objective'],required,knowledge,body.get('planning_mode','model'))
        if not validate_graph(graph,required)['valid']:fail('The proposed graph is invalid.','INVESTIGATION_GRAPH_REJECTED')
        p=dict(schema_version=VERSION,workflow_id='investigation_'+secrets.token_hex(12),revision=1,objective=body['objective'],requirements=required,
               version_id=vid,knowledge_sha256=v['knowledge_sha256'],catalogue_sha256=CATALOGUE_HASH,graph=graph,planning=planning,
               inputs=context,analysis_mode=mode,wait_for_information=body.get('wait_for_information',False),
               ontology_context=knowledge,source_stamps=list(stamps.values()),limits=deepcopy(LIMITS),created_at=now(),read_only=True,company_reads=0)
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
        return [o for o in run['outputs'].values() if isinstance(o,dict) and isinstance(o.get('records'),list) and 'request_id' in o]

    def analysis_context(self,run,node):
        if node['capability']!='prepare_summary':
            e=run['outputs'][next(b['source'] for b in node['inputs'] if b['name']=='evidence')]
            return packet([e],assertions=run['assertions'])
        analyses=[o for o in run['outputs'].values() if o.get('classification')=='agent_interpretation']
        return packet(self.evidence(run),analyses,run['assertions'])

    def report(self,p,run):
        evidence=self.evidence(run);analyses=[o for o in run['outputs'].values() if o.get('classification')=='agent_interpretation']
        records=[];seen=set()
        for e in evidence:
            for r in e['records']:
                key=(e['request_id'],r['record_id'])
                if key not in seen:records.append(dict(evidence_id=e['request_id'],**r));seen.add(key)
        missing=[m for e in evidence for m in e['missing']]
        missing.extend(dict(reason=msg) for o in run['outputs'].values() for msg in o.get('missing_information',[]))
        candidates=[c for e in evidence for c in e.get('ambiguous_associations',[])]
        incomplete=bool(missing or candidates or run['node_errors']) or any(e['completeness']!='complete_for_scoped_reads' for e in evidence)
        return dict(objective=p['objective'],workflow_id=p['workflow_id'],workflow_revision=p['revision'],run_id=run['run_id'],version_id=p['version_id'],knowledge_sha256=p['knowledge_sha256'],
                    completion_status='completed_with_gaps' if incomplete else 'completed',source_records=records,
                    retrieved_facts=[dict(evidence_id=e['request_id'],**f) for e in evidence for f in e['findings']],
                    configured_rule_outcomes=[r for e in evidence for r in e.get('rule_results',[])],agent_interpretations=analyses,
                    missing_information=missing,ambiguous_associations=candidates,conversion_issues=[i for e in evidence for i in e.get('conversion_issues',[])],
                    executed_nodes={k:v for k,v in run['node_states'].items() if v!='pending'},branch_decisions=run['branches'],execution_errors=run['node_errors'],
                    user_assertions=dict(values=run['assertions'],verification='unverified_user_input'),
                    physical_engine_identity='unresolved',warranty_approval='not_performed',company_writes=0,
                    qualification='Source observations, configured rule outcomes and agent interpretations remain separate. No official eligibility, confirmed diagnosis or operational authorization is inferred.')

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
            preview=self.retrieval.preview(auth,dict(question=self.question(task,context),inputs=inputs,version_id=p['version_id'],request_key=run['run_id']+'_'+nid))
            result=self.retrieval.execute(auth,preview['request_id'],{})
            if result['version_id']!=p['version_id'] or result['knowledge_sha256']!=p['knowledge_sha256']:fail('Retrieval returned foreign knowledge.')
            return result,None,dict(retrieval_calls=1)
        if kind=='agent':
            result,usage=self.agents.run(node['capability'],self.analysis_context(run,node),p['analysis_mode'])
            return result,None,dict(model_calls=usage['llm_calls'],tokens=usage['tokens'],estimated_cost_usd=usage['estimated_cost_usd'])
        if kind=='condition':
            outcome=predicate(node['predicate'],bound['evidence'])
            return dict(predicate=node['predicate'],outcome=outcome,classification='deterministic_backend_check'),outcome,{}
        if kind=='parallel':return dict(split=True),None,{}
        if kind=='join':return dict(joined_nodes=[e['source'] for e in p['graph']['edges'] if e['target']==nid and run['edge_states'].get(e['id'])=='selected']),None,{}
        if kind=='deterministic':
            msg='No matching complaint record was retrieved.' if nid=='not_found' else 'Inspection evidence is missing.' if nid=='no_inspection' else 'The branch condition could not be established.' if nid in ('uncertain_complaint','unknown_inspection') else 'Required facts remain listed in retrieved evidence.'
            return dict(missing_information=[msg],classification='deterministic_gap'),None,{}
        if kind=='end':
            report=self.report(p,run)
            if p['wait_for_information'] and report['missing_information'] and not run.get('information_acknowledged'):
                return dict(waiting=True,requested=['acknowledge_gaps','notes'],reason='Review the explicit evidence gaps before finalizing the report.',partial_report=report),None,{}
            return report,None,{}
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
                            with self.store.transaction() as db:
                                current=self.owned(db,scope,run_id,owner)
                                if current['status']=='canceled':continue
                                current['node_times'][nid]['finished_at']=now()
                                if error:
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
                                    for counter,value in usage.items():current['usage'][counter]+=value
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
