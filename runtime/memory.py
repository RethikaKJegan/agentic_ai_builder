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

    def view(self, run, workflow, *, task=None, dependencies=None, permitted_tools=()):
        checkpoints = run.get('task_checkpoints', {})
        graph = workflow.get('metadata', {}).get('composition_tasks', {})
        failures = run.get('classified_failures', [])
        common = dict(knowledge_pin=knowledge_pin(workflow),
                      authority='Reference context only; current source and Registry checks remain mandatory.')
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
        with self.store.transaction() as db:db.execute('INSERT INTO runtime_experiences VALUES (?,?,?,?)',(*scope,entry['experience_id'],json.dumps(entry)))
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
            rows=db.execute('SELECT document FROM runtime_experiences WHERE workspace=? AND owner=?',scope).fetchall()
            for row in rows:
                entry=json.loads(row[0])
                if entry['validation_status']!='validated':continue
                stale=entry['expires_at']<=self.runtime.clock()
                # Invalidate only entries in the requested domain, never unrelated client versions.
                same=entry['domain']==domain
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
