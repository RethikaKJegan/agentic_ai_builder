"""Bounded command client for BusinessCases. No agent loop or alternate stage scheduler."""
from copy import deepcopy
import json
import secrets
from pathlib import Path
from jsonschema import Draft202012Validator
from .business_cases import DONE, TERMINAL, fail
from .business_knowledge_model import digest, canonical
from .service import ApiFailure
from runtime.service import RuntimeFailure

CONTRACTS=Path(__file__).resolve().parents[1]/'shared/contracts'
REPORT_VALIDATOR=Draft202012Validator(json.loads((CONTRACTS/'business-lifecycle-report-v1.json').read_text()))
DRIVER_VALIDATOR=Draft202012Validator(json.loads((CONTRACTS/'business-case-driver-v1.json').read_text()))


def analytical_report(case):
    stages=[]
    for definition in case['process_definition']['stages']:
        stage=case['stages'][definition['stage_instance_id']]
        status=stage['execution_status']
        display='SKIPPED' if stage['business_outcome_status']=='SKIPPED' else 'WAITING' if status.startswith('WAITING_') or status in ('CREATED','READY') else status
        stages.append(dict(stage_instance_id=stage['stage_instance_id'],name=stage['definition']['name'],status=display,
            execution_status=status,business_outcome_status=stage['business_outcome_status'],real_world_status=stage['real_world_status'],
            capabilities=stage['definition']['required_capabilities'],run_id=stage.get('run_id'),composition_id=stage.get('composition_id'),
            inputs=deepcopy(stage['resolved_inputs']),outputs=deepcopy(stage['outputs']),errors=deepcopy(stage['errors']),
            tool_execution_records=deepcopy(stage.get('tool_execution_records',[]))))
    report=dict(schema_version='business-lifecycle-report-v1',case_id=case['case_id'],process_definition_id=case['process_definition_id'],
        process_definition_version=case['process_definition_version'],execution_status=case['execution_status'],
        business_outcome_status=case['business_outcome_status'],case_status=case['case_status'],observed_revision=case['revision'],
        ontology_version=case['ontology_version'],mapping_version=case['mapping_version'],stages=stages,
        pending_real_world_waits=[deepcopy(w) for w in case['waits'].values() if w['current_status'] in ('PENDING','TIMED_OUT')],
        evidence_references=deepcopy(case['evidence_references']),generated_assumptions=deepcopy(case['assumptions']),
        conflicts=deepcopy(case['conflicts']),timeline=deepcopy(case['execution_history']),
        qualification='Analytical execution only. Source reports, derived values, hypotheses and synthetic assumptions retain their provenance. '
        'Analytical artifacts do not grant business authority or prove physical activity or business effectiveness.')
    if case.get('reassessments'):report['reassessments']=deepcopy(case['reassessments'])
    return report


class LifecycleDriver:
    def __init__(self,cases):
        self.cases,self.store=cases,cases.store

    def _write(self,db,scope,doc):
        cursor=db.execute('UPDATE business_case_commands SET document=? WHERE workspace=? AND owner=? AND request_key=? AND fingerprint=?',
                          (canonical(doc),*scope,doc['request_key'],doc['fingerprint']))
        if cursor.rowcount!=1:fail('Driver request changed.', 'CASE_DRIVER_CONFLICT',409)

    def _owned(self,db,scope,key,token):
        row=db.execute('SELECT document FROM business_case_commands WHERE workspace=? AND owner=? AND request_key=?',(*scope,key)).fetchone()
        doc=json.loads(row[0]) if row else None
        if not doc or doc.get('token')!=token:fail('Driver claim changed.', 'CASE_DRIVER_CONFLICT',409)
        return doc

    def _authorized_work_available(self,case,auth):
        for stage in case['stages'].values():
            if stage['execution_status']!='WAITING_FOR_AUTHORIZATION' or not stage.get('composition_id'):continue
            with self.store.transaction(write=False) as db:
                if stage.get('run_id'):
                    runtime=self.cases.service.runtime_runner
                    if runtime and runtime.runtime.load(db,stage['run_id'],auth)['status'] in ('queued','running','completed'):return True
                else:
                    workflow=stage['workflow']
                    current=self.store.get(db,case['workspace_id'],workflow['workflow_id'],workflow['version'])
                    if current and current['status'] in ('approved','published'):return True
        return False

    def _operation(self,case,auth,resume):
        if case['case_status'] in TERMINAL:return None,'terminal'
        if not case.get('prepared_at'):return 'prepare',None
        if case['active_stage_ids']:
            expired=any(s['execution_status']=='RUNNING' and s.get('lease_until',float('inf'))<=self.cases.clock() for s in case['stages'].values())
            return ('resume',None) if resume and expired else (None,'execution_in_progress')
        if any(s['execution_status']=='READY' for s in case['stages'].values()):
            return ('advance' if case['started_at'] else 'start'),None
        if self._authorized_work_available(case,auth):return 'advance',None
        if case['blocked_stage_ids']:
            return ('resume',None) if resume else (None,'blocked_or_failed')
        return None,'external_or_input_wait'

    def _finish(self,auth,scope,key,token,reason,error=None):
        with self.store.transaction() as db:
            doc=self._owned(db,scope,key,token)
            case=self.cases._load(db,scope,doc['case_id'])
            from .lifecycle_learning import LifecycleLearning
            LifecycleLearning(self.cases).record(db,auth,case)
            report=analytical_report(case)
            REPORT_VALIDATOR.validate(report)
            case['analytical_report']=report
            self.cases._save(db,scope,case)
            result=dict(case_id=case['case_id'],revision=case['revision'],stop_reason=reason,
                commands_used=doc['commands_used'],stage_executions_reserved=doc['stage_executions_reserved'],report=report)
            if error:result['error_code']=error
            doc.update(state='finished',result=result,finished_at=self.cases.timestamp())
            self._write(db,scope,doc)
        return result

    def drive(self,auth,case_id,body):
        cases=self.cases;scope=cases.scope(auth,True,True)
        cases.body(body,('request_key',),('max_commands','max_seconds','max_stage_executions','resume'))
        if list(DRIVER_VALIDATOR.iter_errors(body)):fail('Driver request violates its budget contract.')
        key=cases.key(body)
        limits={k:body.get(k,d) for k,d in [('max_commands',32),('max_seconds',120),('max_stage_executions',64)]}
        for name,maximum in [('max_commands',64),('max_seconds',600),('max_stage_executions',256)]:
            if type(limits[name]) is not int or not 1<=limits[name]<=maximum:fail('Driver budget is outside its bound.')
        if type(body.get('resume',False)) is not bool:fail('Resume must be an explicit boolean.')
        fingerprint=digest(['case_driver_v1',case_id,body]);token=secrets.token_hex(16)
        with self.store.transaction() as db:
            cases._load(db,scope,case_id)
            old=cases._receipt(db,scope,body,fingerprint)
            if old:
                if old.get('kind')!='case_driver_v1':fail('Driver request key conflict.','CASE_COMMAND_CONFLICT',409)
                if old['state']=='finished':return old['result']
                if old['lease_until']>cases.clock():
                    return dict(case_id=case_id,stop_reason='driver_in_progress',commands_used=old['commands_used'])
                doc=old;doc['token']=token
                doc['lease_until']=max(cases.clock(),doc['deadline'])+600
                self._write(db,scope,doc)
            else:
                doc=dict(kind='case_driver_v1',request_key=key,fingerprint=fingerprint,case_id=case_id,token=token,
                    state='running',commands_used=0,stage_executions_reserved=0,limits=limits,steps=[],
                    deadline=cases.clock()+limits['max_seconds'],lease_until=cases.clock()+limits['max_seconds']+600)
                cases._remember(db,scope,body,fingerprint,doc)
        while True:
            case=cases.get(auth,case_id)
            if cases.clock()>=doc['deadline']:
                return self._finish(auth,scope,key,token,'budget_exhausted')
            pending=doc['steps'][-1] if doc['steps'] and not doc['steps'][-1].get('finished') else None
            if pending:
                # Reissue the exact persisted command after a crash; Phase 4 receipts prevent dispatch replay.
                operation,command=pending['operation'],pending['command']
            else:
                if case['case_status'] in TERMINAL:return self._finish(auth,scope,key,token,'terminal')
                if cases.clock()>=doc['deadline'] or doc['commands_used']>=limits['max_commands']:
                    return self._finish(auth,scope,key,token,'budget_exhausted')
                operation,reason=self._operation(case,auth,body.get('resume',False))
                if operation is None:return self._finish(auth,scope,key,token,reason)
                remaining=limits['max_stage_executions']-doc['stage_executions_reserved']
                if operation!='prepare' and remaining<1:return self._finish(auth,scope,key,token,'budget_exhausted')
                command=dict(request_key='drivecmd_'+digest([case_id,key,doc['commands_used'],operation])[:40],expected_revision=case['revision'])
                if operation!='prepare':command['max_stage_executions']=min(4,remaining)
                with self.store.transaction() as db:
                    doc=self._owned(db,scope,key,token)
                    doc['steps'].append(dict(operation=operation,command=command,finished=False))
                    doc['commands_used']+=1;doc['stage_executions_reserved']+=command.get('max_stage_executions',0)
                    self._write(db,scope,doc)
            before_progress=sum(s['attempts'] for s in case['stages'].values())+len(case['completed_stage_ids'])
            try:
                after=cases.command(auth,case_id,operation,command)
            except (ApiFailure,RuntimeFailure) as exc:
                return self._finish(auth,scope,key,token,'command_rejected',exc.code)
            with self.store.transaction() as db:
                doc=self._owned(db,scope,key,token);doc['steps'][-1]['finished']=True
                self._write(db,scope,doc)
            after_progress=sum(s['attempts'] for s in after['stages'].values())+len(after['completed_stage_ids'])
            if operation!='prepare' and after_progress==before_progress:
                return self._finish(auth,scope,key,token,'no_eligible_progress')
