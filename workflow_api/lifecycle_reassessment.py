"""Reviewed dependency reassessment on BusinessCases; preserves historical runs/effects."""
from copy import deepcopy
import json
from pathlib import Path
from jsonschema import Draft202012Validator
from .business_cases import DONE,definition_write,fail
from .business_knowledge_model import canonical,digest
from .evidence_completion import at,MISSING,artifact,conforms

VALIDATOR=Draft202012Validator(json.loads((Path(__file__).resolve().parents[1]/'shared/contracts/business-case-reassessment-v1.json').read_text()))


class LifecycleReassessment:
    def __init__(self,cases):self.cases=cases

    def history(self,auth,case_id):
        cases=self.cases;scope=cases.scope(auth);cases.get(auth,case_id)
        with cases.store.transaction(write=False) as db:
            rows=db.execute('SELECT revision,document FROM business_case_revisions WHERE workspace=? AND owner=? AND case_id=? ORDER BY revision LIMIT 16',(*scope,case_id)).fetchall()
        return {'items':[dict(revision=r[0],case_status=json.loads(r[1])['case_status']) for r in rows]}

    def revision(self,auth,case_id,revision):
        cases=self.cases;scope=cases.scope(auth);cases.get(auth,case_id)
        with cases.store.transaction(write=False) as db:
            row=db.execute('SELECT document FROM business_case_revisions WHERE workspace=? AND owner=? AND case_id=? AND revision=?',(*scope,case_id,revision)).fetchone()
        if not row:fail('Archived case revision not found.','CASE_NOT_FOUND',404)
        return json.loads(row[0])

    def reassess(self,auth,case_id,body):
        cases=self.cases;scope=cases.scope(auth,True,True)
        cases.body(body,('request_key','expected_revision','source','event_id','input_bindings'))
        if list(VALIDATOR.iter_errors(body)):fail('Reassessment request violates its versioned contract.')
        if type(body['expected_revision']) is not int or not isinstance(body['source'],str) or not isinstance(body['event_id'],str):fail('Supply an exact revision and saved event identity.')
        bindings=body['input_bindings']
        if not isinstance(bindings,dict) or not 1<=len(bindings)<=32 or any(not isinstance(k,str) or not isinstance(v,str) or len(v)>512 for k,v in bindings.items()):fail('Supply bounded event-payload paths for affected stage input names.')
        fingerprint=digest([case_id,'reassess',body])
        with cases.store.transaction() as db:
            old=cases._receipt(db,scope,body,fingerprint)
            if old:return cases._load(db,scope,case_id)
            case=cases._load(db,scope,case_id)
            if case['revision']!=body['expected_revision']:fail('Case changed; reload its revision.','CASE_CONFLICT',409)
            if case['case_status']=='CANCELLED' or case['active_stage_ids']:fail('Reassessment requires an idle, uncancelled case.','CASE_REASSESSMENT_BUSY',409)
            if len(case.get('reassessments',[]))>=16:fail('Reassessment history bound reached; create a reviewed successor case.','CASE_REASSESSMENT_LIMIT',409)
            conflicts=[c for c in case['conflicts'] if c.get('reason')=='late_event_requires_downstream_reassessment' and not c.get('resolved_by')
                       and c.get('event',{}).get('event_id')==body['event_id'] and c['event'].get('source')==body['source']]
            if len(conflicts)!=1:fail('Choose one unresolved saved late event.','CASE_REASSESSMENT_EVENT',409)
            conflict=conflicts[0];sid=conflict['stage'];stage=case['stages'][sid];event=stage.get('event',{})
            if event.get('event_id')!=body['event_id'] or event.get('source')!=body['source'] or not event.get('submitted_by'):fail('Event provenance is unavailable.','CASE_REASSESSMENT_EVENT',409)
            specs={**stage['definition']['required_inputs'],**stage['definition']['optional_inputs']};overrides={}
            for name,path in bindings.items():
                value=at(event['payload'],path)
                if name not in specs or value is MISSING or not conforms(value,specs[name]['schema']):fail('Event binding violates the pinned input schema.','CASE_REASSESSMENT_BINDING')
                overrides[name]=artifact(value,'ACTUAL',[dict(event_id=event['event_id'],source=event['source'],submitted_by=event['submitted_by'],path=path)],
                    'authenticated_event_assertion',cases.timestamp(),case_id)
            affected={sid}
            while True:
                expanded=affected|{k for k,s in case['stages'].items() if set(s['definition']['dependency_definitions'])&affected}
                if expanded==affected:break
                affected=expanded
            # Block a changed analytical dependency from leaking into an existing live composition.
            if any(s['execution_status'] not in DONE|{'CREATED','BLOCKED','FAILED'} for k,s in case['stages'].items() if k in affected):
                fail('Finish or cancel existing affected compositions before reassessment.','CASE_REASSESSMENT_BUSY',409)
            writes={k for k in affected if definition_write(case['stages'][k])}
            uncertain=[k for k in writes if case['stages'][k]['execution_status'] not in DONE or case['stages'][k].get('error',{}).get('category')=='uncertain_external_write']
            if uncertain:fail('Reconcile uncertain or incomplete effects before reassessment.','CASE_UNCERTAIN_EFFECT',409)
            if sid in writes:fail('A write stage cannot be reassessed or replayed.','CASE_UNCERTAIN_EFFECT',409)
            eligible=affected-writes
            original=deepcopy(case);rid='reassessment_'+digest([case_id,body])[:24]
            db.execute('INSERT INTO business_case_revisions VALUES (?,?,?,?,?)',(*scope,case_id,case['revision'],canonical(original)))
            comparisons=[]
            for name,entry in overrides.items():
                previous=stage['resolved_inputs'].get(name)
                comparisons.append(dict(input=name,previous=deepcopy(previous),actual=deepcopy(entry),changed=not previous or previous['value']!=entry['value']))
            for target in eligible:
                current=case['stages'][target]
                current['reassessment_generation']=current.get('reassessment_generation',0)+1
                current['reassessment_id']=rid
                for key in ('run_id','composition_id','workflow','claim','runtime_result','runtime_checkpoints','runtime_error_code','analytical_runtime_result','error','retry_after','event_timeout_provisional','deadline_exceeded','pending_real_world_event'):
                    current.pop(key,None)
                current.update(run_id=None,composition_id=None,execution_status='CREATED',business_outcome_status='PENDING',inputs={},resolved_inputs={},outputs={},
                    agent_configurations=[],tool_execution_records=[],errors=[],retry_history=[])
                current['runtime_source_evidence']={}
                # Old inferred/derived assumptions must be recomputed from current upstream facts.
                for key in list(case['assumptions']):
                    if key.startswith(target+':'):del case['assumptions'][key]
            case['stages'][sid].setdefault('reassessment_inputs',{}).update(overrides)
            conflict['resolved_by']=rid
            item=dict(reassessment_id=rid,event_id=event['event_id'],source=event['source'],original_revision=original['revision'],
                affected_stage_ids=sorted(affected),reexecute_stage_ids=sorted(eligible),preserved_write_stage_ids=sorted(writes),
                comparisons=comparisons,status='PENDING',created_at=cases.timestamp())
            case.setdefault('reassessments',[]).append(item)
            case.update(case_status='CREATED',execution_status='CREATED',completed_at=None)
            case.pop('analytical_report',None)
            cases.record(case,'case.reassessment_created',reassessment_id=rid,affected_stage_ids=sorted(affected))
            cases.refresh(case,scope);cases._save(db,scope,case);cases._remember(db,scope,body,fingerprint,case)
        return case
