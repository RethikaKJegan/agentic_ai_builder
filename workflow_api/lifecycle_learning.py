"""Auditable lifecycle feedback over existing verified runtime records; no training."""
from copy import deepcopy
import json
from pathlib import Path
from jsonschema import Draft202012Validator
from .business_knowledge_model import canonical,digest

VALIDATOR=Draft202012Validator(json.loads((Path(__file__).resolve().parents[1]/'shared/contracts/lifecycle-feedback-v1.json').read_text()))


class LifecycleLearning:
    def __init__(self,cases):self.cases=cases

    def record(self,db,auth,case):
        scope=self.cases.scope(auth,True,True)
        runtime=getattr(getattr(self.cases.service,'runtime_runner',None),'runtime',None)
        count=db.execute('SELECT COUNT(*) FROM business_lifecycle_feedback WHERE workspace=? AND owner=? AND case_id=?',(*scope,case['case_id'])).fetchone()[0]
        for sid,stage in case['stages'].items():
            if not stage['attempts']:continue
            run=workflow=None
            if runtime and stage.get('run_id'):
                run=runtime.load(db,stage['run_id'],auth)
                if run['subject_id']!=scope[1]:continue
                workflow=self.cases.store.get(db,scope[0],run['workflow_id'],run['workflow_version'])
            values=list(stage['resolved_inputs'].values())+list(stage['outputs'].values())
            counts={p:sum(v['provenance_type']==p for v in values) for p in ('ACTUAL','DERIVED','INFERRED','SYNTHETIC')}
            evaluation=(run or {}).get('outcome_evaluation',{})
            completed=stage['execution_status'] in ('COMPLETED','COMPLETED_PROVISIONALLY')
            schema_valid=completed and stage['business_outcome_status']!='SKIPPED'
            tools=evaluation.get('tool_success_count',0)
            failures=evaluation.get('tool_failure_count',0)
            signals=dict(task_completed=completed,validated_output_schema=schema_valid,tool_successes=tools,tool_failures=failures,
                verified_receipts=sum(v['generation_method']=='connector_receipt' for v in stage['outputs'].values()),
                evidence_coverage=evaluation.get('evidence_validity'),provenance_counts=counts,
                retry_count=len(stage['retry_history']),recovery_success=evaluation.get('recovery_success',False),
                latency_seconds=evaluation.get('duration_seconds'),usage=deepcopy(evaluation.get('model_usage',{})),
                estimated_cost_usd=evaluation.get('estimated_cost_usd'),
                unnecessary_tool_calls=None,contradictions=sum(c.get('stage')==sid for c in case['conflicts']),
                rejected_actions=sum(e.get('category') in ('revoked_authorization','uncertain_external_write') for e in stage['errors']))
            # Completion with generated assumptions is not itself a positive reward.
            score=(int(schema_valid and counts['SYNTHETIC']==0 and counts['INFERRED']==0)+min(tools,4)
                   -failures-len(stage['retry_history'])-signals['contradictions']-signals['rejected_actions'])
            ref=dict(case_id=case['case_id'],stage_instance_id=sid,run_id=stage.get('run_id'),stage_sha256=digest(stage))
            eid='feedback_'+digest(ref)[:40]
            doc=dict(schema_version='lifecycle-feedback-v1',feedback_id=eid,case_id=case['case_id'],stage_instance_id=sid,
                run_id=stage.get('run_id'),pins={k:case.get(k) for k in ('ontology_version','mapping_version','capability_registry_version')},
                signals=signals,rewards=dict(execution_quality=score,independently_verified_business_outcome=None),
                categories=dict(operational_execution=bool(run and run['status']=='completed'),
                    source_evidence=sum(v['generation_method']=='authorized_mapped_source' for v in values),human_reported_outcomes=int(stage.get('event') is not None),
                    inferred_conclusions=counts['INFERRED'],synthetic_assumptions=counts['SYNTHETIC']),
                provenance=[ref],created_at=self.cases.timestamp(),
                authority='Offline feedback only. No source values or generated policies are promoted; no model weights or authority change.')
            VALIDATOR.validate(doc)
            if count<512:
                cursor=db.execute('INSERT INTO business_lifecycle_feedback VALUES (?,?,?,?,?) ON CONFLICT DO NOTHING',(*scope,case['case_id'],eid,canonical(doc)))
                count+=int(cursor.rowcount==1)
            if runtime and run and workflow:
                policy=case.get('memory_policy',{'enabled':True,'retention_seconds':2592000})
                if policy.get('enabled',True):runtime.experience_memory.observe_execution(db,auth,run,workflow,retention_seconds=policy.get('retention_seconds',2592000))

    def metrics(self,auth,case_id):
        scope=self.cases.scope(auth);self.cases.get(auth,case_id)
        with self.cases.store.transaction(write=False) as db:
            rows=db.execute('SELECT document FROM business_lifecycle_feedback WHERE workspace=? AND owner=? AND case_id=? ORDER BY feedback_id LIMIT 512',(*scope,case_id)).fetchall()
        return dict(items=[json.loads(r[0]) for r in rows],limit=512,training='offline_only')
