"""Scoped working views and validated strategy hints; never a source of authority."""
from copy import deepcopy
import json
import math
from uuid import uuid4
from registry.safety import reject_secrets
from .service import RuntimeFailure, digest

STRATEGIES = {'refresh_evidence', 'correct_structured_output', 'retry_read',
              'request_input', 'review_mapping', 'renew_authorization',
              'reconcile_effect', 'review_conflict', 'recompute_dependencies'}
PIN_KEYS = ('ontology_version', 'knowledge_sha256', 'mapping_sha256',
            'configuration_revision', 'provider_fingerprint', 'package_sha256')


def knowledge_pin(workflow):
    metadata = workflow.get('metadata', {})
    return deepcopy(metadata.get('client_package_pin') or metadata.get('business_preparation', {}).get('pins') or
                    metadata.get('business_knowledge_pin') or {})


def bounded_context(value, *, max_bytes=48000, max_tokens=16000):
    """UTF-8 byte count is a conservative token upper bound, not a tokenizer claim."""
    reject_secrets(value)
    size = len(json.dumps(value, ensure_ascii=False, allow_nan=False).encode('utf-8'))
    if size > min(max_bytes, max_tokens):
        raise RuntimeFailure('WORKING_CONTEXT_LIMIT', 'Required context exceeds the reviewed memory allowance; decompose the task.', 422)
    return deepcopy(value)


class WorkingMemory:
    def __init__(self, runtime):
        self.runtime = runtime

    @staticmethod
    def case_view(case,stage=None):
        """Durable case state is the store; this is its bounded task-specific projection."""
        sid=stage['stage_instance_id'] if stage else None
        dependencies=stage['definition']['dependency_definitions'] if stage else []
        def brief(value):
            if isinstance(value,str):return value[:512]
            if isinstance(value,dict):return {k:brief(v) for k,v in list(value.items())[:12]}
            if isinstance(value,list):return [brief(v) for v in value[:8]]
            return value
        selected={k:v for k,v in case['stages'].items() if k in dependencies}
        view=dict(case_id=case['case_id'],goal=case['original_user_goal'],stage_instance_id=sid,
            pins={k:case.get(k) for k in ('ontology_version','mapping_version','capability_registry_version','configuration_version')},
            resolved_evidence=brief(stage.get('resolved_inputs',{})) if stage else {},
            prior_conclusions={k:brief(v['outputs']) for k,v in list(selected.items())[:8]},
            pending_waits=[{k:w[k] for k in ('wait_id','stage_instance_id','event_type','current_status')} for w in case['waits'].values() if (not sid or w['stage_instance_id'] in [sid,*dependencies]) and w['current_status'] in ('PENDING','TIMED_OUT')][:16],
            failures=brief(stage.get('errors',[])[-4:]) if stage else [],
            recovery_history=brief(stage.get('retry_history',[])[-4:]) if stage else [],
            assignments=brief(stage.get('agent_configurations',[])) if stage else [],
            tool_receipts=brief(stage.get('tool_execution_records',[])[-4:]) if stage else [],
            budgets={'execution_deadline':stage.get('deadline'),'retry_limit':stage['definition']['retry_policy']['max_retries']} if stage else {},
            qualification='Bounded projection; complete evidence, outputs, receipts and history remain in scoped case/run storage. Memory grants no authority.')
        # Avoid duplicating full agent definitions in model context.
        view['assignments']=[{k:a.get(k) for k in ('configuration_id','assigned_task','permitted_tools')} for a in (stage or {}).get('agent_configurations',[])][:8]
        return bounded_context(view)

    def view(self, run, workflow, *, task=None, dependencies=None, permitted_tools=()):
        checkpoints = run.get('task_checkpoints', {})
        graph = workflow.get('metadata', {}).get('composition_tasks', {})
        failures = run.get('classified_failures', [])
        common = dict(knowledge_pin=knowledge_pin(workflow),
                      authority='Reference context only; current source and Registry checks remain mandatory.')
        common['verified_execution_recommendations']=[deepcopy(h) for h in workflow.get('metadata',{}).get('memory_recommendations',[])
                                                      if task is None or h['capability_id']==task['capability_id']][:8]
        if workflow.get('metadata',{}).get('lifecycle_context',{}).get('working_memory'):
            common['business_lifecycle']=deepcopy(workflow['metadata']['lifecycle_context']['working_memory'])
        if task is None:
            common.update(objective=workflow.get('description', ''),
                          task_graph={t['task_id']:dict(capability_id=t['capability_id'], depends_on=t['depends_on']) for t in graph.values()},
                          completed_tasks=sorted(checkpoints),
                          pending_tasks=sorted(t['task_id'] for t in graph.values() if t['task_id'] not in checkpoints),
                          verified_results={k:dict(state=v['result'].get('state'), classification=v['result'].get('classification')) for k,v in checkpoints.items()},
                          errors=deepcopy(failures[-8:]), recovery_attempts=[{k:deepcopy(a[k]) for k in ('attempt','category','strategy','affected_tasks','verified_success')} for a in run.get('recovery_history', [])[-4:]])
        else:
            tid=task['task_id']
            common.update(assigned_task=deepcopy(task), dependency_outputs=deepcopy(dependencies or {}),
                          permitted_tools=list(permitted_tools),
                          completion_criteria=['Schema-valid output', 'Actual evidence or tool receipt', 'No inferred authority'],
                          previous_attempts=[deepcopy(f) for f in failures if f.get('affected_task') == tid][-4:])
        return common


class ExperienceMemory:
    """Same workflow database, separate immutable provenance plus validation lifecycle."""
    def __init__(self, runtime):
        self.runtime, self.store = runtime, runtime.store
        with self.store.transaction() as db:
            db.execute('CREATE TABLE IF NOT EXISTS runtime_experiences (workspace TEXT NOT NULL, owner TEXT NOT NULL, experience_id TEXT NOT NULL, document TEXT NOT NULL, PRIMARY KEY(workspace,owner,experience_id))')

    def scope(self, auth, *, write=False, validate=False):
        permission = 'workflow.approve' if validate else 'workflow.execute' if write else 'runs.view'
        self.runtime.authorize(auth, permission, {'admin', 'approver'} if validate else {'admin', 'builder'} if write else {'admin','builder','viewer','approver'})
        return auth['subject']['workspace_id'], auth['subject']['subject_id']

    def observe_execution(self,db,auth,run,workflow,*,retention_seconds=2592000):
        """Trusted lifecycle hook: learn execution metadata, never model/business facts."""
        scope=self.scope(auth,write=True)
        if (run['workspace_id'],run['subject_id'])!=scope or run['status']!='completed':return
        if run.get('workflow_digest')!=digest(workflow):return
        existing=db.execute('SELECT experience_id,document FROM runtime_experiences WHERE workspace=? AND owner=? ORDER BY experience_id LIMIT 2049',scope).fetchall()
        active=len(existing)
        for row in existing:
            entry=json.loads(row[1])
            if entry.get('schema_version')!='operational-experience-v1':continue
            if entry['expires_at']<=self.runtime.clock():
                db.execute('DELETE FROM runtime_experiences WHERE workspace=? AND owner=? AND experience_id=?',(*scope,row[0]))
                active-=1
        metadata=workflow.get('metadata',{});pins=knowledge_pin(workflow)
        for task in metadata.get('composition_tasks',{}).values():
            checkpoint=run.get('task_checkpoints',{}).get(task['task_id'],{})
            result=checkpoint.get('result',{})
            if result.get('state')!='completed':continue
            tool=task.get('selected_tool_id')
            if tool and not any(t.get('tool_id')==tool and t.get('inputs')==task['operation_inputs'] for t in result.get('tool_results',[])):continue
            cid=task['capability_id'];contract=metadata.get('composition_contracts',{}).get(cid)
            # Older workflows without explicit contracts are not compatibility-ranked.
            if not contract:continue
            if active>=2048:break
            eid='op_'+digest([run['run_id'],task['task_id']])[:40]
            entry=dict(experience_id=eid,schema_version='operational-experience-v1',workspace=scope[0],owner=scope[1],
                domain=metadata.get('client_domain','configured_business_ontology'),capability=cid,tool_id=tool,
                contract_sha256=digest(contract),tool_reference_sha256=metadata.get('composition_tool_fingerprints',{}).get(tool),pins=pins,
                category='verified_operational_execution',strategy='reuse_verified_configuration',
                validation_status='validated',created_at=self.runtime.clock(),expires_at=self.runtime.clock()+retention_seconds,
                evidence_references=[{'run_id':run['run_id'],'task_id':task['task_id'],'checkpoint_sha256':digest(checkpoint)}],
                verified_outcome={'execution_completed':True,'business_outcome_verified':False},
                recovered=bool(run.get('outcome_evaluation',{}).get('recovery_success')),
                retry_count=len(run.get('recovery_history',[])),
                authority='Execution metadata only; excludes source values, human outcomes, inferred conclusions and synthetic assumptions.')
            cursor=db.execute('INSERT INTO runtime_experiences VALUES (?,?,?,?) ON CONFLICT DO NOTHING',(*scope,eid,json.dumps(entry)))
            active+=int(cursor.rowcount==1)

    def ranked(self,auth,*,domain,pins,contracts,tool_references=(),limit=8):
        """Deterministic compatible verified successes; no mutation of historical pins."""
        scope=self.scope(auth);groups={}
        tool_hashes={t['tool_id']:digest(t) for t in tool_references}
        with self.store.transaction(write=False) as db:
            rows=db.execute('SELECT document FROM runtime_experiences WHERE workspace=? AND owner=? ORDER BY experience_id LIMIT 2048',scope).fetchall()
        for row in rows:
            e=json.loads(row[0]);cid=e.get('capability');tool=e.get('tool_id')
            if (e.get('schema_version')!='operational-experience-v1' or e.get('validation_status')!='validated'
                or e['expires_at']<=self.runtime.clock() or e['domain']!=domain or cid not in contracts
                or e['contract_sha256']!=digest(contracts[cid]) or any(e['pins'].get(k)!=pins.get(k) for k in PIN_KEYS)
                or tool and tool_hashes.get(tool)!=e['tool_reference_sha256']):continue
            key=(cid,tool or '');g=groups.setdefault(key,dict(capability_id=cid,tool_id=tool,verified_successes=0,recovery_successes=0,retries=0,experience_references=[]))
            g['verified_successes']+=1;g['recovery_successes']+=int(e.get('recovered',False));g['retries']+=e.get('retry_count',0)
            if len(g['experience_references'])<4:g['experience_references'].append(e['experience_id'])
        for g in groups.values():g['score']=g['verified_successes']*10+g['recovery_successes']*2-g['retries']
        return sorted(groups.values(),key=lambda g:(-g['score'],g['capability_id'],g['tool_id'] or ''))[:min(8,limit)]

    def candidate(self, auth, *, domain, capability, category, strategy, evidence_references, pins, expires_at, agent_id=None):
        scope=self.scope(auth,write=True)
        from .recovery import CATEGORIES
        if category not in CATEGORIES:raise RuntimeFailure('EXPERIENCE_INVALID','Use a registered failure category.',422)
        if (strategy not in STRATEGIES or not all(isinstance(s,str) and 0<len(s)<=160 for s in (domain,capability,category))
                or type(expires_at) not in (int,float) or not math.isfinite(expires_at) or expires_at<=self.runtime.clock()
                or not isinstance(pins,dict) or not isinstance(evidence_references,list) or not evidence_references):
            raise RuntimeFailure('EXPERIENCE_INVALID','A bounded strategy, provenance, versions and future expiry are required.',422)
        entry=dict(experience_id='exp_'+uuid4().hex,workspace=scope[0],owner=scope[1],domain=domain,capability=capability,
                   category=category,strategy=strategy,evidence_references=deepcopy(evidence_references),pins=deepcopy(pins),
                   validation_status='candidate',created_at=self.runtime.clock(),expires_at=expires_at,
                   invalidation_conditions=['expiry','knowledge_version_changed','contradicted_outcome'],agent_id=agent_id,verified_outcome=None)
        reject_secrets(entry)
        if len(json.dumps(entry).encode())>12000:raise RuntimeFailure('EXPERIENCE_INVALID','Experience is too large.',422)
        with self.store.transaction() as db:
            if db.execute('SELECT COUNT(*) FROM runtime_experiences WHERE workspace=? AND owner=?',scope).fetchone()[0]>=2048:
                raise RuntimeFailure('EXPERIENCE_LIMIT','Scoped experience capacity reached; invalidate or archive expired entries.',422)
            db.execute('INSERT INTO runtime_experiences VALUES (?,?,?,?)',(*scope,entry['experience_id'],json.dumps(entry)))
        return entry

    def validate(self, auth, experience_id, *, run_id):
        workspace,_=self.scope(auth,validate=True)
        with self.store.transaction() as db:
            run=self.runtime.load(db,run_id,auth)
            row=db.execute('SELECT owner,document FROM runtime_experiences WHERE workspace=? AND experience_id=?',(workspace,experience_id)).fetchone()
            if not row:raise RuntimeFailure('EXPERIENCE_NOT_FOUND','Experience not found.',404)
            entry=json.loads(row[1]);evaluation=run.get('outcome_evaluation',{})
            workflow=self.store.get(db,workspace,run['workflow_id'],run['workflow_version'])
            expected={k:entry['pins'].get(k) for k in PIN_KEYS}
            actual={k:knowledge_pin(workflow).get(k) for k in PIN_KEYS}
            successful=[h for h in run.get('recovery_history',[]) if h.get('verified_success') and h.get('category')==entry['category'] and h.get('strategy')==entry['strategy']]
            capabilities={t['capability_id'] for t in workflow.get('metadata',{}).get('composition_tasks',{}).values()}
            provenance_matches=any(isinstance(ref,dict) and ref.get('run_id')==run_id for ref in entry['evidence_references'])
            if (run['subject_id']!=entry['owner'] or run['status']!='completed' or not evaluation.get('recovery_success')
                    or entry['domain']!=workflow.get('metadata',{}).get('client_domain','configured_business_ontology') or not successful or not provenance_matches or entry['capability'] not in capabilities or expected!=actual or entry['expires_at']<=self.runtime.clock()
                    or entry['validation_status']!='candidate'):
                raise RuntimeFailure('EXPERIENCE_NOT_VERIFIED','A completed, matching recovered outcome is required.',422)
            entry.update(validation_status='validated',validated_by=auth['subject']['subject_id'],validated_at=self.runtime.clock(),
                         verified_outcome=dict(run_id=run_id,evaluation_sha256=digest(evaluation)))
            db.execute('UPDATE runtime_experiences SET document=? WHERE workspace=? AND owner=? AND experience_id=?',(json.dumps(entry),workspace,row[0],experience_id))
            return entry

    def relevant(self, auth, *, domain, capability, category, pins, agent_id=None):
        scope=self.scope(auth);result=[]
        with self.store.transaction() as db:
            rows=db.execute('SELECT document FROM runtime_experiences WHERE workspace=? AND owner=? ORDER BY experience_id LIMIT 2048',scope).fetchall()
            for row in rows:
                entry=json.loads(row[0])
                if entry.get('schema_version')=='operational-experience-v1':continue
                if entry['validation_status']!='validated':continue
                stale=entry['expires_at']<=self.runtime.clock()
                # Invalidate only entries in the requested domain, never unrelated client versions.
                same=entry['domain']==domain and entry['pins'].get('package_id')==pins.get('package_id')
                changed=same and any(entry['pins'].get(k)!=pins.get(k) for k in PIN_KEYS)
                if stale or changed:
                    entry.update(validation_status='invalidated',invalidated_at=self.runtime.clock(),invalidation_reason='expiry' if stale else 'knowledge_version_changed')
                    db.execute('UPDATE runtime_experiences SET document=? WHERE workspace=? AND owner=? AND experience_id=?',(json.dumps(entry),*scope,entry['experience_id']))
                    continue
                if (same and entry['capability']==capability and (category is None or entry['category']==category)
                        and entry.get('agent_id') in (None,agent_id)):
                    result.append({k:deepcopy(entry[k]) for k in ('experience_id','strategy','evidence_references','verified_outcome')})
        return result[:4]

    def invalidate(self,auth,experience_id,reason):
        scope=self.scope(auth,write=True)
        if reason not in ('contradicted_outcome','source_withdrawn','operator_correction'):raise RuntimeFailure('EXPERIENCE_INVALID','Use a supported invalidation reason.',422)
        with self.store.transaction() as db:
            row=db.execute('SELECT document FROM runtime_experiences WHERE workspace=? AND owner=? AND experience_id=?',(*scope,experience_id)).fetchone()
            if not row:raise RuntimeFailure('EXPERIENCE_NOT_FOUND','Experience not found.',404)
            entry=json.loads(row[0]);entry.update(validation_status='invalidated',invalidation_reason=reason,invalidated_at=self.runtime.clock())
            db.execute('UPDATE runtime_experiences SET document=? WHERE workspace=? AND owner=? AND experience_id=?',(json.dumps(entry),*scope,experience_id))
            return entry
