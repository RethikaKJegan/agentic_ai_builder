"""Persistent five-state policy on BusinessCases and LifecycleDriver, not an executor.

Models propose; this module validates decisions/revisions and grants one action to
GraphRunner. Case CAS/command receipts and existing run journals own durability.
"""
from copy import deepcopy
import json
import secrets
from pathlib import Path
from jsonschema import Draft202012Validator
from registry.safety import reject_secrets
from runtime.memory import WorkingMemory, bounded_context
from runtime.service import RuntimeFailure
from .business_cases import fail, TERMINAL
from .service import ApiFailure
from .business_knowledge_model import canonical, digest
from .action_plans import prepare as prepare_actions

CONTRACT=json.loads((Path(__file__).resolve().parents[1]/'shared/contracts/evaluator-decision-v1.json').read_text())
DECISIONS=Draft202012Validator(CONTRACT)
STATES=('UNDERSTAND','PLAN','GATHER_AND_ASSESS','EXECUTE','EVALUATE')
from runtime.adaptive_context import DEFAULT_LIMITS, brief


class AdaptiveOrchestration:
    def __init__(self,cases):
        self.cases=cases
        self.service=cases.service
        self.store=cases.store
        self.composition=self.service.business_composition

    def _load(self,db,scope,case_id,expected=None):
        case=self.cases._load(db,scope,case_id)
        if expected is not None and case['revision']!=expected:fail('Case revision changed.','ADAPTIVE_STALE_REVISION',409)
        if case['case_status']=='CANCELLED':fail('Case is cancelled.','CASE_CANCELLED',409)
        return case

    def _stage(self,case):return case['stages'][case['adaptive']['stage_instance_id']]

    def _phase(self,case,phase):
        if phase not in STATES:fail('Unknown reasoning state.')
        old=case['adaptive']['phase'];case['adaptive']['phase']=phase
        self.cases.record(case,'adaptive.state',previous=old,target=phase,plan_revision=case['adaptive']['plan_revision'])

    def _status(self,case,status):
        stage=self._stage(case)
        if stage['execution_status']!=status:
            # Existing legal stage transitions stay authoritative.
            if stage['execution_status'] in ('WAITING_FOR_INPUT','WAITING_FOR_EVENT','WAITING_FOR_AUTHORIZATION','BLOCKED','FAILED'):
                self.cases.transition(case,stage,'READY')
            if status not in ('READY','CANCELLED') and stage['execution_status']=='READY':self.cases.transition(case,stage,'RUNNING')
            self.cases.transition(case,stage,status)

    def _claim_free(self,case):
        claim=case['adaptive'].get('claim')
        if claim and claim['until']>self.cases.clock():fail('A reasoning/continuation turn is active.','ADAPTIVE_BUSY',409)
        if claim and claim.get('provider_intent'):
            fail('The interrupted model result is unknown; explicit reconciliation is required.','ADAPTIVE_UNKNOWN_EVALUATION',409)

    def _limits(self,body):
        limits={**DEFAULT_LIMITS,**body}
        if set(limits)!=set(DEFAULT_LIMITS):fail('Unknown adaptive budget.')
        for name,ceiling in DEFAULT_LIMITS.items():
            if type(limits[name]) is not int or not 1<=limits[name]<=ceiling:fail('Adaptive budget is outside server bounds.','ADAPTIVE_BUDGET_INVALID')
        return limits

    def enable(self,auth,case_id,body):
        scope=self.cases.scope(auth,True,True)
        self.cases.body(body,('request_key','expected_revision','stage_instance_id','plan_request'),('limits',))
        fp=digest(['adaptive.enable',case_id,body])
        with self.store.transaction() as db:
            old=self.cases._receipt(db,scope,body,fp)
            if old:return old
            case=self._load(db,scope,case_id,body['expected_revision'])
            if case.get('adaptive') or not case.get('prepared_at') or case['active_stage_ids'] or case['case_status'] in TERMINAL:
                fail('Enable adaptive control on one idle prepared case.','ADAPTIVE_STATE',409)
            stage=case['stages'].get(body['stage_instance_id'])
            if not stage or stage['execution_status']!='READY' or stage.get('run_id') or stage.get('composition_id'):
                fail('Select a ready stage before its first composition.','ADAPTIVE_STATE',409)
            request=deepcopy(body['plan_request'])
            if not isinstance(request,dict):fail('Supply a typed plan request.')
            if request.get('client_id',case['client_id'])!=case['client_id']:fail('Client differs from the case.','ADAPTIVE_SCOPE',403)
            if request.get('objective',case['original_user_goal'])!=case['original_user_goal']:fail('Keep the original case goal.')
            limits=self._limits(body.get('limits',{}))
            request.update(objective=case['original_user_goal'],client_id=case['client_id'])
            request.pop('request_key',None)
            if case.get('preparation_id'):request['preparation_id']=case['preparation_id']
            if case.get('google_connection_id'):request['google_connection_id']=case['google_connection_id']
            stage['adaptive_controlled']=True
            case['adaptive']=dict(schema_version='adaptive-case-v1',stage_instance_id=stage['stage_instance_id'],phase='UNDERSTAND',
                status='active',plan_id='plan_'+secrets.token_hex(12),plan_revision=0,composition_id=None,run_id=None,
                limits=limits,started_at=self.cases.clock(),deadline=self.cases.clock()+limits['max_seconds'],
                reasoning_usage=dict(llm_calls=0,tokens=0),reasoning_turns=0,revision_history=[],decisions=[],observations=[],
                pending_wait=None,request=request,execution_permission=None)
            self.cases.record(case,'adaptive.enabled',stage_instance_id=stage['stage_instance_id'])
            self.cases._save(db,scope,case);self.cases._remember(db,scope,body,fp,case)
            return case

    def _run(self,auth,case):
        rid=case['adaptive'].get('run_id')
        if not rid:return None
        with self.store.transaction(write=False) as db:return deepcopy(self.service.runtime_runner.runtime.load(db,rid,auth))

    def _memory(self,case):
        stage=deepcopy(self._stage(case))
        stage['tool_execution_records']=[{k:deepcopy(v) for k,v in r.items() if k!='output'}|{'output_sha256':digest(r.get('output'))} for r in stage.get('tool_execution_records',[])]
        return WorkingMemory.case_view(case,stage)

    def _observations(self,case,doc,run):
        a=case['adaptive'];obs=[dict(observation_id='goal:'+digest([case['original_user_goal'],case['client_id']])[:24],kind='goal',value=case['original_user_goal']),
            dict(observation_id='plan:'+doc['action_plan']['fingerprint'],kind='plan',value=doc['action_plan']['completion_criteria'])]
        for aid,item in (run or {}).get('action_instances',{}).items():
            if item.get('output') is not None:
                obs.append(dict(observation_id='action:'+aid+':'+digest(item['output']),kind='action_result',action_id=aid,
                    provenance_type=item.get('provenance_type'),verified_receipt=item.get('verified_receipt',False),value=brief(item['output'])))
            if item.get('error_code'):obs.append(dict(observation_id='failure:'+aid+':'+item['error_code'],kind='failure',action_id=aid,value=item['error_code']))
        for key,entry in doc['binding_context'].get('evidence',{}).items():
            obs.append(dict(observation_id='evidence:'+digest([key,entry]),kind='mapped_evidence',reference=key,value=brief(entry)))
        if run and run['status'] in ('failed','blocked','rejected'):
            obs.append(dict(observation_id='run_failure:'+run['run_id']+':'+str(run.get('error_code')),kind='failure',value=dict(status=run['status'],error_code=run.get('error_code'))))
        obs.extend(deepcopy(a.get('input_observations',[])))
        return obs[:64]

    def context(self,auth,case,doc,run):
        a=case['adaptive'];stage=self._stage(case)
        observations=self._observations(case,doc,run)
        ontology={}
        if doc.get('preparation_id'):
            prepared=self.composition.preparation.checked(auth,doc['preparation_id'])
            ontology={task:{key:deepcopy(view[key]) for key in ('concepts','relationships','rules')} for task,view in prepared['tasks'].items()}
        elif doc.get('client_package_context'):
            ontology=deepcopy(doc['client_package_context']['tasks'])
        completed={k:v for k,v in (run or {}).get('action_instances',{}).items() if v.get('state')=='completed'}
        usage=(run or {}).get('usage',{}).get('workflow',{})
        remaining={key:max(0,a['limits'][ceiling]-usage.get(key,0)-a['reasoning_usage'].get(key,0)) for key,ceiling in [('tokens','max_tokens'),('tool_calls','max_tool_calls'),('llm_calls','max_llm_calls')]}
        ctx=dict(case_id=case['case_id'],scope=dict(workspace_id=case['workspace_id'],owner_id=case['owner_id'],client_id=case['client_id']),
            original_goal=case['original_user_goal'],ontology_context=ontology,constraints=doc['action_plan']['constraints'],plan_revision=a['plan_revision'],
            plan=dict(plan_id=a['plan_id'],actions=[{k:deepcopy(v) for k,v in action.items() if k!='expected_output_schema'} for action in doc['action_plan']['actions']],completion_criteria=doc['action_plan']['completion_criteria']),
            observations=observations,completed_actions={k:dict(provenance_type=v.get('provenance_type'),verified_receipt=v.get('verified_receipt'),output=brief(v['output']),output_fingerprint=v['output_fingerprint']) for k,v in completed.items()},
            skipped_actions=[k for k,v in (run or {}).get('action_instances',{}).items() if v.get('state')=='skipped'],missing_information=brief([o for o in observations if o['kind']=='failure']),pending_wait=deepcopy(a.get('pending_wait')),
            remaining_budgets={**remaining,**{k:a['limits'][k]-a.get(v,0) for k,v in [('max_reasoning_turns','reasoning_turns'),('max_plan_revisions','plan_revision')]}},
            working_memory=self._memory(case),experience_recommendations=deepcopy(doc.get('memory_recommendations',[])),
            allowed_capabilities={cid:{k:deepcopy(c[k]) for k in ('capability_id','kind','side_effect','input_schema','output_schema','retrieval_task')} for cid,c in case['capability_contracts'].items() if c['kind']=='model' or c['side_effect']=='read' or cid in doc['contracts']},qualification='Bounded untrusted evidence. Execution receipts are not business authority; no hidden source values are assumed.')
        return bounded_context(ctx,max_bytes=96000,max_tokens=96000)

    def _revision(self,auth,case,proposal,reason,observations,expected_plan,planning_budget=None):
        a=case['adaptive']
        if a['plan_revision']!=expected_plan:fail('Plan revision changed.','ADAPTIVE_STALE_REVISION',409)
        if a['plan_revision']>=a['limits']['max_plan_revisions']:fail('Plan revision budget exhausted.','ADAPTIVE_REVISION_LIMIT',409)
        previous=self.composition.get(auth,a['composition_id']) if a['composition_id'] else None
        run=self._run(auth,case)
        if run and (run.get('lease_until',0)>self.cases.clock() or any(v=='executing' for v in run['node_states'].values())):
            fail('Runtime invocation is active or uncertain.','ADAPTIVE_RECONCILIATION_REQUIRED',409)
        if run and any(v.get('external_effect_status') in ('requires_reconciliation','intent_persisted') for v in run.get('action_instances',{}).values()):
            fail('Reconcile uncertain external writes before revising.','ADAPTIVE_RECONCILIATION_REQUIRED',409)
        request=deepcopy(a['request']);request['action_plan']=deepcopy(proposal)
        request['request_key']='adaptive_plan_'+digest([case['case_id'],a['plan_revision']+1,proposal,a['request'].get('user_values',{})])[:40]
        control=dict(case_id=case['case_id'],stage_instance_id=a['stage_instance_id'])
        prev=None if previous is None else dict(plan_id=a['plan_id'],revision=a['plan_revision'],fingerprint=previous['action_plan']['fingerprint'],composition_id=previous['composition_id'])
        revision=dict(plan_id=a['plan_id'],revision=a['plan_revision']+1,previous_revision=prev,reason=reason,observations=observations,control=control,contracts=deepcopy(case['capability_contracts']),allowed_tools=deepcopy(self._stage(case)['definition']['allowed_tools']))
        if case.get('client_package_id'):revision['package']=dict(package_id=case['client_package_id'],revision=case['client_package_revision'])
        context=dict(case_id=case['case_id'],stage_instance_id=a['stage_instance_id'],inputs=deepcopy(self._stage(case)['resolved_inputs']),working_memory=self._memory(case),qualification='Adaptive reasoning grants no authority.')
        doc=prepare_actions(self.composition,auth,request,lifecycle_context=context,_revision=revision,_planning_budget=planning_budget)
        plan=doc['action_plan'];stage=self._stage(case);definition=stage['definition']
        if {t['tool_id'] for t in doc['selected_tools'].values()}-set(definition['allowed_tools']):fail('New actions exceed the pinned stage tool allowlist.','CASE_TOOL_DENIED',403)
        if any(t['side_effect'] in ('draft','write') for t in doc['tasks']) and definition['side_effect_classification'] not in ('draft','write'):fail('Revision exceeds the stage effect ceiling.','CASE_TOOL_DENIED',403)
        for cid,c in doc['contracts'].items():
            if cid not in case['capability_contracts'] or case['capability_contracts'][cid]!=c:fail('Revision changes pinned capability contracts.','CASE_CAPABILITY_STALE',409)
        if not set(definition['required_capabilities'])<={t['capability_id'] for t in doc['tasks']}:fail('Revision omits required pinned capabilities.')
        if previous:
            old={x['action_id']:x for x in previous['action_plan']['actions']};new={x['action_id']:x for x in plan['actions']}
            completed={k for k,v in (run or {}).get('action_instances',{}).items() if v.get('state')=='completed'}
            for aid in completed:
                if aid not in new or new[aid]!=old[aid]:fail('Completed actions are immutable.','ADAPTIVE_COMPLETED_ACTION',409)
            for field in ('scope','goal','constraints','account_reference','resource_references'):
                if plan[field]!=previous['action_plan'][field]:fail('A revision cannot broaden scope or reset constraints.','ADAPTIVE_PIN_CHANGED',409)
            if previous['preparation_id']!=doc['preparation_id']:
                old_prepared=self.composition.preparation.checked(auth,previous['preparation_id'])
                new_prepared=self.composition.preparation.checked(auth,doc['preparation_id'])
                if any(old_prepared['pins'].get(k)!=new_prepared['pins'].get(k) for k in ('ontology_version','knowledge_sha256','mapping_sha256','configuration_revision','provider_fingerprint')) or any(stamp not in new_prepared['pins']['source_stamps'] for stamp in old_prepared['pins']['source_stamps']) or old_prepared['inputs']!=new_prepared['inputs']:fail('Evidence expansion must preserve ontology, mappings and identifier pins.','ADAPTIVE_PIN_CHANGED',409)
        self.composition.workflow(auth,doc['composition_id'])
        return doc

    def _install(self,db,scope,case,doc,source_run,auth):
        a=case['adaptive'];stage=self._stage(case)
        if source_run:
            runtime=self.service.runtime_runner.runtime
            old=runtime.load(db,source_run['run_id'],auth)
            if old.get('lease_until',0)>self.cases.clock() or any(s=='executing' for s in old['node_states'].values()):fail('Runtime changed while revising.','ADAPTIVE_BUSY',409)
            if digest(old)!=digest(source_run):fail('Runtime changed while revising.','ADAPTIVE_STALE_REVISION',409)
            historical={ref for item in old.get('action_instances',{}).values() if item.get('state')=='completed' for ref in item.get('approval_references',[])}
            for approval in old['approvals']:
                if approval['status'] in ('pending','approved') and approval['approval_id'] not in historical:
                    approval.update(superseded_status=approval['status'],status='superseded',allowed_decisions=[],superseded_by=doc['composition_id'])
            old['adaptive_superseded_by']=doc['composition_id'];runtime.transition(db,old,'cancelled')
        a['revision_history'].append(dict(plan_id=doc['action_plan']['plan_id'],revision=doc['action_plan']['revision'],composition_id=doc['composition_id'],fingerprint=doc['action_plan']['fingerprint'],previous_revision=doc['action_plan']['previous_revision'],rationale=doc['action_plan']['revision_reason'],observations=doc['action_plan']['triggering_observations'],source_run_id=(source_run or {}).get('run_id')))
        a.update(plan_revision=doc['action_plan']['revision'],composition_id=doc['composition_id'],run_id=None,execution_permission=None,status='active')
        # Successor run initialization uses archived existing runtime records, not model receipts.
        if doc.get('preparation_id'):a['request']['preparation_id']=doc['preparation_id']
        a['carry_run_id']=(source_run or {}).get('run_id') or a.get('carry_run_id')
        from .action_plans import compile_workflow
        stage.update(composition_id=doc['composition_id'],run_id=None,workflow=compile_workflow(doc),action_plan_reference=dict(plan_id=a['plan_id'],revision=a['plan_revision'],fingerprint=doc['action_plan']['fingerprint']))
        self._status(case,'READY');self._phase(case,'GATHER_AND_ASSESS')

    def revise(self,auth,case_id,body):
        scope=self.cases.scope(auth,True,True)
        self.cases.body(body,('request_key','expected_revision','expected_plan_revision','proposal','rationale','observation_ids'))
        fp=digest(['adaptive.revise',case_id,body])
        with self.store.transaction(write=False) as db:
            old=self.cases._receipt(db,scope,body,fp)
            if old:return old
            case=deepcopy(self._load(db,scope,case_id,body['expected_revision']));self._claim_free(case)
        a=case['adaptive'];doc=self.composition.get(auth,a['composition_id']);run=self._run(auth,case)
        known={o['observation_id'] for o in self._observations(case,doc,run)}
        if not body['observation_ids'] or set(body['observation_ids'])-known:fail('Revision must cite actual current observations.','ADAPTIVE_OBSERVATION_INVALID')
        successor=self._revision(auth,case,body['proposal'],body['rationale'],body['observation_ids'],body['expected_plan_revision'])
        with self.store.transaction() as db:
            current=self._load(db,scope,case_id,case['revision']);self._claim_free(current)
            self._install(db,scope,current,successor,run,auth)
            self.cases._save(db,scope,current);self.cases._remember(db,scope,body,fp,current)
            return current

    def supply(self,auth,case_id,body,*,on_accept=None):
        scope=self.cases.scope(auth,True,True)
        self.cases.body(body,('request_key','expected_revision','wait_id'),('inputs','event'))
        reject_secrets(body);fp=digest(['adaptive.supply',case_id,body])
        with self.store.transaction() as db:
            old=self.cases._receipt(db,scope,body,fp)
            if old:return old
            case=self._load(db,scope,case_id,body['expected_revision']);self._claim_free(case)
            a=case['adaptive'];wait=a.get('pending_wait')
            if not wait or wait['wait_id']!=body['wait_id'] or wait['status']!='PENDING':fail('No matching pending wait.','ADAPTIVE_WAIT_INVALID',409)
            if self.cases.clock()>wait['deadline']:fail('The wait deadline expired.','ADAPTIVE_WAIT_EXPIRED',409)
            if wait['kind']=='input':
                if set(body)-{'request_key','expected_revision','wait_id','inputs'}:fail('Use typed inputs for this wait.')
                values=body.get('inputs')
                if not isinstance(values,dict) or set(values)!=set(wait['schemas']):fail('Supply exactly the requested input fields.')
                for key,value in values.items():
                    if list(Draft202012Validator(wait['schemas'][key]).iter_errors(value)):fail('Input violates requested schema.')
                    if key in a['request'].get('user_values',{}):fail('Existing input pins cannot be overwritten.','ADAPTIVE_PIN_CHANGED',409)
                a['request'].setdefault('user_values',{}).update(deepcopy(values))
                observation=dict(observation_id='input:'+digest([body['wait_id'],values]),kind='user_input',value=brief(values),provenance_type='ACTUAL',submitted_by=auth['subject']['subject_id'])
            else:
                event=body.get('event',{})
                if set(body)-{'request_key','expected_revision','wait_id','event'} or set(event)!={'source','event_type','payload'}:fail('Supply an explicit event report.')
                if 'events.ingest' not in auth.get('permissions',[]):fail('Event ingestion authority is required.','ADAPTIVE_EVENT_DENIED',403)
                if event['source']!=wait['expected_source'] or event['event_type']!=wait['event_type'] or list(Draft202012Validator(wait['schema']).iter_errors(event['payload'])):fail('Event does not match the saved wait.')
                observation=dict(observation_id='event:'+digest(event),kind='authenticated_event_report',value=brief(event['payload']),provenance_type='ACTUAL',submitted_by=auth['subject']['subject_id'])
            wait.update(status='SATISFIED',observation_id=observation['observation_id'])
            a.setdefault('wait_history',[]).append(deepcopy(wait));a.setdefault('input_observations',[]).append(observation);a['pending_wait']=None
            self._status(case,'READY');self._phase(case,'PLAN' if not a['composition_id'] else 'EVALUATE')
            automation=getattr(self.service,'automation',None)
            if automation:automation._unsuspend(db,auth,case)
            self.cases._save(db,scope,case);self.cases._remember(db,scope,body,fp,case)
            if on_accept:on_accept(db,case)
            elif automation:automation._enqueue(db,scope,case_id,'input:'+body['request_key'],'case')
            return case

    def _wait(self,case,kind,schemas=None,event=None,reason=None):
        a=case['adaptive'];wait=dict(wait_id='aw_'+secrets.token_hex(12),kind=kind,status='PENDING',reason=reason,deadline=min(a['deadline'],self.cases.clock()+(event or {}).get('deadline_seconds',600)))
        if kind=='input':wait['schemas']=schemas
        else:wait.update(deepcopy(event))
        a['pending_wait']=wait;a['status']='waiting';a['execution_permission']=None
        self._status(case,'WAITING_FOR_INPUT' if kind=='input' else 'WAITING_FOR_EVENT')
        self.cases.record(case,'adaptive.wait',wait_id=wait['wait_id'],wait_kind=kind)

    @staticmethod
    def _local_schema(schema):
        if len(canonical(schema))>4000:fail('Wait schema exceeds its bound.')
        def inspect(value):
            if isinstance(value,dict):
                if {'$ref','$dynamicRef'}&set(value):fail('Wait schemas must be local and self-contained.','ADAPTIVE_DECISION_INVALID')
                for item in value.values():inspect(item)
            elif isinstance(value,list):
                for item in value:inspect(item)
        inspect(schema);Draft202012Validator.check_schema(schema)

    def _validate_decision(self,decision,context,doc,run):
        reject_secrets(decision)
        if list(DECISIONS.iter_errors(decision)):fail('Evaluator decision violates evaluator-decision-v1.','ADAPTIVE_DECISION_INVALID')
        if decision['plan_revision']!=doc['action_plan']['revision']:fail('Evaluator referenced a stale revision.','ADAPTIVE_STALE_REVISION',409)
        known={o['observation_id'] for o in context['observations']}
        if set(decision['observation_ids'])-known:fail('Evaluator cited unknown observations.','ADAPTIVE_OBSERVATION_INVALID')
        ids={a['action_id'] for a in doc['action_plan']['actions']}
        if set(decision['action_ids'])-ids or set(decision['completion_criteria'])!=set(doc['action_plan']['completion_criteria']):fail('Evaluator referenced unknown actions or completion criteria.','ADAPTIVE_DECISION_INVALID')
        d=decision['decision']
        if (decision['proposal'] is not None)!=(d in ('revise_plan','gather_context')):fail('Only revision/gather decisions may propose actions.')
        if bool(decision['input_requests'])!=(d=='request_input') or (decision['event_request'] is not None)!=(d=='wait_for_event'):fail('Decision payload differs from decision kind.')
        if d=='continue' and len(decision['action_ids'])!=1:fail('Continuation selects one action.')
        if d=='complete':
            if any((run or {}).get('action_instances',{}).get(a['action_id'],{}).get('state') not in ('completed','skipped') for a in doc['action_plan']['actions']):fail('Completion criteria are not satisfied.','ADAPTIVE_INCOMPLETE')
        for item in decision['input_requests']:
            self._local_schema(item['schema'])
        if decision['event_request']:self._local_schema(decision['event_request']['schema'])
        if len({r['key'] for r in decision['input_requests']})!=len(decision['input_requests']):fail('Input request keys must be unique.')
        return decision

    def _ready(self,doc,run,aid):
        action=next((a for a in doc['action_plan']['actions'] if a['action_id']==aid),None)
        items=(run or {}).get('action_instances',{})
        if not action or items.get(aid,{}).get('state') in ('completed','skipped','failed','blocked','executing') or any(items.get(d,{}).get('state')!='completed' for d in action['depends_on']):fail('Selected action is not ready.','ADAPTIVE_ACTION_NOT_READY')

    def _ensure_run(self,auth,scope,case):
        a=case['adaptive'];stage=self._stage(case);runner=self.service.runtime_runner;runtime=runner.runtime
        workflow=self.composition.workflow(auth,a['composition_id'])
        # The existing review/save APIs remain responsible for approving the immutable revision.
        with self.store.transaction(write=False) as db:existing=self.store.get(db,case['workspace_id'],workflow['workflow_id'],1)
        if not existing:
            response=self.service.handle(dict(request_id='adaptive_save',operation='save_workflow_version',idempotency_key='adaptive_save_'+a['composition_id'],payload=dict(workflow_id=workflow['workflow_id'],workflow_version=1,base_version=0,workflow=workflow)),auth)
            if response['status']>=400:fail('Save the validated successor workflow before execution.','ADAPTIVE_WORKFLOW_INVALID',409)
        def seed(db,created):
            current=self._load(db,scope,case['case_id'],case['revision'])
            run=runtime.load(db,created['run_id'],auth)
            if run.get('adaptive_initialized'):return
            carry=None
            if a.get('carry_run_id'):carry=runtime.load(db,a['carry_run_id'],auth)
            if carry:
                completed={k:v for k,v in carry.get('action_instances',{}).items() if v.get('state')=='completed'}
                run['action_instances']=deepcopy(completed);run['outputs']={k:deepcopy(v['output']) for k,v in completed.items()}
                run['task_checkpoints']={k:deepcopy(v) for k,v in carry.get('task_checkpoints',{}).items() if k in completed}
                run['node_states']={k:'completed' for k in completed}
                # Gates for preserved effects are historical facts; they do not authorize any new action.
                for node in workflow['nodes']:
                    if node['node_id'].startswith('approve_') and node['node_id'][8:] in completed:run['node_states'][node['node_id']]='completed'
                for edge in workflow['edges']:
                    if edge['source'] in run['node_states']:run['edge_states'][edge['edge_id']]='selected'
                run['usage']=deepcopy(carry.get('usage',{}));run['created_at']=carry['created_at']
                run['preserved_from_run']=carry['run_id']
            run['created_at']=min(run['created_at'],a['started_at']+a.get('waited_seconds',0))
            run.update(adaptive_initialized=True,adaptive_limits=deepcopy(a['limits']),adaptive_reasoning_usage=deepcopy(a['reasoning_usage']))
            runtime.save(db,run)
            current['adaptive']['run_id']=created['run_id'];self._stage(current)['run_id']=created['run_id'];self.cases._save(db,scope,current)
        runtime.create_run(dict(request_id='adaptive_run',idempotency_key='adaptive_run_'+a['composition_id'],payload=dict(workflow_id=workflow['workflow_id'],workflow_version=1,inputs={})),auth,on_created=seed)
        return self.cases.get(auth,case['case_id'])

    def _step(self,auth,case_id):
        scope=self.cases.scope(auth,True,True)
        with self.store.transaction() as db:
            case=self._load(db,scope,case_id);a=case['adaptive'];self._claim_free(case)
            if self.cases.clock()>=a['deadline']:return 'budget_exhausted'
            if a['status']=='completed':return 'terminal'
            if a.get('pending_wait'):return 'external_or_input_wait'
            if a['status']=='blocked':return 'blocked_or_failed'
            phase=a['phase']
            if phase=='UNDERSTAND':
                a['understanding']=dict(goal=case['original_user_goal'],client_id=case['client_id'],constraints=a['request'].get('constraints',{}),completion_criteria=(a['request'].get('action_plan') or {}).get('completion_criteria',[]))
                self._phase(case,'PLAN');self.cases._save(db,scope,case);return 'progress'
            token=secrets.token_hex(12);a['claim']=dict(token=token,until=self.cases.clock()+300,provider_intent=phase in ('EVALUATE','GATHER_AND_ASSESS'))
            self.cases._save(db,scope,case)
        try:
            if phase=='PLAN':
                proposal=a['request'].get('action_plan')
                def plan_budget(context):
                    nonlocal case,a
                    from .action_bindings import SCHEMA
                    bounded_context(context,max_bytes=96000,max_tokens=96000)
                    reservation=16000+4000+len(canonical(dict(context=context,action_schema=SCHEMA)).encode())
                    if a['reasoning_turns']>=a['limits']['max_reasoning_turns'] or a['reasoning_usage']['tokens']+reservation>a['limits']['max_tokens'] or a['reasoning_usage']['llm_calls']>=a['limits']['max_llm_calls']:
                        fail('Initial planning allowance exhausted.','ADAPTIVE_BUDGET_EXHAUSTED',409)
                    with self.store.transaction() as db:
                        current=self._load(db,scope,case_id,case['revision']);ca=current['adaptive'];ca['claim']['provider_intent']=True
                        ca['reasoning_turns']+=1;ca['reasoning_usage']['tokens']+=reservation;ca['reasoning_usage']['llm_calls']+=1
                        self.cases._save(db,scope,current);case=current;a=case['adaptive']
                try:doc=self._revision(auth,case,proposal,'Initial plan after goal understanding.',['goal:'+digest([case['original_user_goal'],case['client_id']])[:24]],0,planning_budget=plan_budget)
                except (RuntimeFailure,ApiFailure) as exc:
                    if exc.code!='ACTION_INPUT_REQUIRED':raise
                    # Missing identity/content is persisted as input wait, never filled by a model.
                    requested=getattr(exc,'required_inputs',{})
                    if not requested:raise
                    with self.store.transaction() as db:
                        current=self._load(db,scope,case_id,case['revision']);current['adaptive'].pop('claim',None)
                        self._wait(current,'input',requested,reason='Required explicit plan inputs are missing.')
                        self.cases._save(db,scope,current)
                    return 'external_or_input_wait'
                with self.store.transaction() as db:
                    current=self._load(db,scope,case_id,case['revision']);current['adaptive'].pop('claim',None)
                    self._install(db,scope,current,doc,None,auth);self.cases._save(db,scope,current)
                return 'progress'
            doc=self.composition.get(auth,a['composition_id']);run=self._run(auth,case)
            if phase in ('GATHER_AND_ASSESS','EVALUATE'):
                ctx=self.context(auth,case,doc,run)
                turns=a['reasoning_turns'];limits=a['limits']
                reservation=len(canonical(dict(context=ctx,decision_schema=CONTRACT)).encode())+2000+limits['evaluator_output_tokens']
                usage=(run or {}).get('usage',{}).get('workflow',{})
                if turns>=limits['max_reasoning_turns'] or reservation+a['reasoning_usage']['tokens']+usage.get('tokens',0)>limits['max_tokens'] or a['reasoning_usage']['llm_calls']+usage.get('llm_calls',0)>=limits['max_llm_calls']:
                    fail('Reasoning budget exhausted.','ADAPTIVE_BUDGET_EXHAUSTED',409)
                with self.store.transaction() as db:
                    current=self._load(db,scope,case_id,case['revision']);ca=current['adaptive'];ca['reasoning_turns']+=1;ca['reasoning_usage']['llm_calls']+=1;ca['reasoning_usage']['tokens']+=reservation
                    self.cases._save(db,scope,current);case=current;a=case['adaptive']
                evaluator=getattr(self.service.planner.provider,'evaluate_actions',None)
                if not callable(evaluator):fail('Configure the existing OpenAI evaluator adapter.','ADAPTIVE_EVALUATOR_UNAVAILABLE',503)
                decision=evaluator(ctx,max_output_tokens=limits['evaluator_output_tokens'])
                self._validate_decision(decision,ctx,doc,run)
                successor=None
                if decision['decision'] in ('revise_plan','gather_context'):
                    successor=self._revision(auth,case,decision['proposal'],decision['rationale'],decision['observation_ids'],a['plan_revision'])
                    if decision['decision']=='gather_context':
                        before={x['action_id'] for x in doc['action_plan']['actions']}
                        added=[x for x in successor['action_plan']['actions'] if x['action_id'] not in before]
                        if any(x!=next((old for old in doc['action_plan']['actions'] if old['action_id']==x['action_id']),x) for x in successor['action_plan']['actions'] if x['action_id'] in before and successor['contracts'][x['capability_id']]['side_effect'] in ('write','draft')):fail('Gather decisions cannot change pending writes.','ADAPTIVE_GATHER_INVALID')
                        if not added or any(successor['contracts'][x['capability_id']]['side_effect'] in ('draft','write') for x in added):fail('Gather decisions may add registered read/reasoning actions only.','ADAPTIVE_GATHER_INVALID')
                with self.store.transaction() as db:
                    current=self._load(db,scope,case_id,case['revision']);ca=current['adaptive'];ca.pop('claim',None)
                    ca['decisions'].append(dict(turn=ca['reasoning_turns'],decision=deepcopy(decision),context_sha256=digest(ctx),timestamp=self.cases.timestamp()))
                    ca['observations']=deepcopy(ctx['observations'])
                    d=decision['decision']
                    if successor:self._install(db,scope,current,successor,run,auth)
                    elif d=='continue':
                        self._ready(doc,run,decision['action_ids'][0]);ca['next_action_id']=decision['action_ids'][0];self._status(current,'READY');self._phase(current,'EXECUTE')
                    elif d=='request_input':self._wait(current,'input',{r['key']:r['schema'] for r in decision['input_requests']},reason=decision['rationale'])
                    elif d=='wait_for_event':self._wait(current,'event',event=decision['event_request'],reason=decision['rationale'])
                    elif d=='complete':
                        ca['status']='completed';ca['execution_permission']=None
                        stage=self._stage(current);stage['action_instances']=deepcopy((run or {}).get('action_instances',{}));stage['runtime_result']=deepcopy((run or {}).get('outputs',{}));stage['business_outcome_status']='PROVISIONAL'
                        previous_status=stage['execution_status'];self.cases.resolve_outputs(current,stage,scope);stage['execution_status']=previous_status
                        stage['business_outcome_status']='PROVISIONAL'
                        self._status(current,'COMPLETED_PROVISIONALLY');self.cases.record(current,'adaptive.completed',qualification='Analytical execution complete; no physical/business outcome is inferred.')
                    self.cases._save(db,scope,current)
                if decision['decision']=='complete' and run:self.service.runtime_runner.advance(run['run_id'],auth)
                return 'terminal' if decision['decision']=='complete' else 'external_or_input_wait' if decision['decision'] in ('request_input','wait_for_event') else 'progress'
            if phase=='EXECUTE':
                # Release case claim before create_run's atomic attachment; GraphRunner retains its own lease.
                with self.store.transaction() as db:
                    current=self._load(db,scope,case_id,case['revision']);current['adaptive'].pop('claim',None);self.cases._save(db,scope,current);case=current
                if not case['adaptive'].get('run_id'):
                    try:case=self._ensure_run(auth,scope,case)
                    except (RuntimeFailure,ApiFailure) as exc:
                        if exc.code not in ('REVISION_NOT_APPROVED','WORKFLOW_NOT_FOUND'):raise
                        with self.store.transaction() as db:
                            current=self._load(db,scope,case_id);self._status(current,'WAITING_FOR_AUTHORIZATION');self.cases._save(db,scope,current)
                        return 'approval_wait'
                a=case['adaptive'];rid=a['run_id']
                with self.store.transaction() as db:
                    current=self._load(db,scope,case_id,case['revision']);ca=current['adaptive'];ca['execution_permission']=dict(run_id=rid,action_id=ca['next_action_id'])
                    runtime=self.service.runtime_runner.runtime;rr=runtime.load(db,rid,auth);rr['adaptive_reasoning_usage']=deepcopy(ca['reasoning_usage']);rr['adaptive_next_action']=ca['next_action_id'];runtime.save(db,rr)
                    self.cases._save(db,scope,current)
                result=self.service.runtime_runner.advance(rid,auth)
                with self.store.transaction() as db:
                    current=self._load(db,scope,case_id);ca=current['adaptive'];rr=self.service.runtime_runner.runtime.load(db,rid,auth)
                    stage=self._stage(current);stage['action_instances']=deepcopy(rr.get('action_instances',{}));stage['runtime_checkpoints']=deepcopy(rr.get('task_checkpoints',{}));stage['tool_execution_records']=[dict(node_id=k,output=deepcopy(v['output']),run_id=rid) for k,v in rr.get('action_instances',{}).items() if v.get('verified_receipt')]
                    if result['status']=='paused_for_approval':self._status(current,'WAITING_FOR_AUTHORIZATION');reason='approval_wait'
                    elif result['status'] in ('failed','blocked'):
                        ca['execution_permission']=None;ca['failure']=rr.get('error_code')
                        uncertain=any(i.get('external_effect_status') in ('requires_reconciliation','intent_persisted') for i in rr.get('action_instances',{}).values())
                        if uncertain:
                            ca['status']='blocked';self._status(current,'BLOCKED');reason='blocked_or_failed'
                        else:
                            self._status(current,'READY');self._phase(current,'EVALUATE');reason='progress'
                    elif rr.get('action_instances',{}).get(ca['next_action_id'],{}).get('state') in ('completed','skipped'):
                        ca['execution_permission']=None;self._status(current,'READY');self._phase(current,'EVALUATE');reason='progress'
                    else:reason='execution_in_progress'
                    self.cases._save(db,scope,current)
                return reason
            fail('Unknown adaptive phase.')
        except BaseException as exc:
            # Known validation/provider failures are persisted. Abrupt interruption keeps the intent/claim.
            if isinstance(exc,Exception):
                with self.store.transaction() as db:
                    current=self.cases._load(db,scope,case_id)
                    if current['adaptive'].get('claim',{}).get('token')==token:
                        current['adaptive'].pop('claim',None);current['adaptive']['failure']=getattr(exc,'code','ADAPTIVE_PROVIDER_FAILED');current['adaptive']['status']='blocked'
                        self._status(current,'BLOCKED');self.cases._save(db,scope,current)
            raise

    def drive(self,auth,case_id,body):
        scope=self.cases.scope(auth,True,True)
        from .lifecycle_driver import DRIVER_VALIDATOR,analytical_report
        if list(DRIVER_VALIDATOR.iter_errors(body)):fail('Driver request violates its budget contract.')
        fp=digest(['adaptive.drive',case_id,body])
        with self.store.transaction() as db:
            old=self.cases._receipt(db,scope,body,fp)
            if old:
                if old['state']=='finished':return old['result']
                if old['until']>self.cases.clock():return dict(case_id=case_id,stop_reason='driver_in_progress')
            case=self._load(db,scope,case_id);self._claim_free(case)
            doc=old or dict(state='running',started=self.cases.clock(),steps=0)
            doc['until']=self.cases.clock()+600
            if old:db.execute('UPDATE business_case_commands SET document=? WHERE workspace=? AND owner=? AND request_key=?',(canonical(doc),*scope,body['request_key']))
            else:self.cases._remember(db,scope,body,fp,doc)
        reason='budget_exhausted';maximum=min(body.get('max_commands',32),body.get('max_stage_executions',64))
        try:
            while doc['steps']<maximum and self.cases.clock()-doc['started']<body.get('max_seconds',120):
                reason=self._step(auth,case_id);doc['steps']+=1
                with self.store.transaction() as db:db.execute('UPDATE business_case_commands SET document=? WHERE workspace=? AND owner=? AND request_key=?',(canonical(doc),*scope,body['request_key']))
                if reason!='progress':break
            else:reason='budget_exhausted'
        except Exception as exc:
            # Stable errors remain inspectable; do not retry model or connector effects here.
            reason='command_rejected';doc['error_code']=getattr(exc,'code','ADAPTIVE_PROVIDER_FAILED')
        case=self.cases.get(auth,case_id)
        if case['adaptive']['status']=='completed' and case['adaptive'].get('run_id'):
            self.service.runtime_runner.advance(case['adaptive']['run_id'],auth)
        result=dict(case_id=case_id,revision=case['revision'],stop_reason=reason,commands_used=doc['steps'],stage_executions_reserved=doc['steps'],report=analytical_report(case),adaptive=deepcopy(case['adaptive']))
        if doc.get('error_code'):result['error_code']=doc['error_code']
        doc.update(state='finished',result=result)
        with self.store.transaction() as db:db.execute('UPDATE business_case_commands SET document=? WHERE workspace=? AND owner=? AND request_key=?',(canonical(doc),*scope,body['request_key']))
        return result
