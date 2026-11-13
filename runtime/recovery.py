"""Failure attribution and dependency invalidation on the existing durable run."""
from copy import deepcopy
import json
from .service import RuntimeFailure, digest

# Exact codes take precedence; unknown errors fail closed, never imply retry safety.
CATEGORIES = {
 'storage_contention': ('retry_read', True, False),
 'internal_execution_failure': ('inspect_service', False, True),
 'model_service_failure': ('inspect_model_service', False, True),
 'invalid_model_output': ('correct_structured_output', True, False),
 'missing_evidence': ('request_input', False, True),
 'invalid_source_values': ('refresh_evidence', False, True),
 'stale_metadata': ('refresh_evidence', False, True),
 'incorrect_source_mapping': ('review_mapping', False, True),
 'connector_timeout': ('retry_read', True, False),
 'connector_authentication': ('renew_authorization', False, True),
 'revoked_authorization': ('renew_authorization', False, True),
 'conflicting_business_evidence': ('review_conflict', False, True),
 'unsupported_capability': ('request_input', False, True),
 'tool_execution_failure': ('retry_read', False, True),
 'uncertain_external_write': ('reconcile_effect', False, True),
 'workflow_dependency': ('recompute_dependencies', False, True),
 'interrupted_read': ('retry_read', True, False),
}
CODES = {
 'DATABASE_BUSY':'storage_contention','INVOCATION_FAILED':'internal_execution_failure','INVALID_USAGE':'internal_execution_failure',
 'MODEL_INVOCATION_FAILED':'model_service_failure','MODEL_PROVIDER_TIMEOUT':'model_service_failure',
 'MODEL_PROVIDER_CONNECTION':'model_service_failure','MODEL_PROVIDER_AUTH':'model_service_failure',
 'MODEL_PROVIDER_RATE_LIMIT':'model_service_failure','MODEL_PROVIDER_UNAVAILABLE':'model_service_failure',
 'MODEL_REQUEST_REJECTED':'model_service_failure',
 'ACTION_CONTENT_UNVERIFIED':'invalid_model_output',
 'SUBWAY_ASSESSMENT_INVALID':'incorrect_source_mapping','SUBWAY_QUERY_INVALID':'incorrect_source_mapping',
 'SUBWAY_ASSESSMENT_DENIED':'revoked_authorization','SUBWAY_QUERY_DENIED':'revoked_authorization',
 'SUBWAY_QUERY_STALE':'stale_metadata','SUBWAY_KNOWLEDGE_STALE':'stale_metadata',
 'SUBWAY_ASSESSMENT_LIMIT':'unsupported_capability','SUBWAY_QUERY_TIMEOUT':'connector_timeout',
 'DATA_QUERY_STALE':'stale_metadata','DATA_QUERY_RESULT_EXPIRED':'stale_metadata',
 'DATA_QUERY_INVALID':'invalid_model_output','DATA_QUERY_INCOMPLETE':'missing_evidence',
 'DATA_QUERY_SCOPE_REQUIRED':'revoked_authorization','ACTION_INPUT_REQUIRED':'missing_evidence',
 'INVESTIGATION_AGENT_REFERENCE':'invalid_model_output','INVESTIGATION_AGENT_OUTPUT':'invalid_model_output',
 'AGENT_OUTPUT_INVALID':'invalid_model_output','MODEL_OUTPUT_SCHEMA_INVALID':'invalid_model_output',
 'MODEL_OUTPUT_TRUNCATED':'invalid_model_output','CAPABILITY_RESULT_INVALID':'invalid_model_output',
 'PUBLIC_QUERY_PRIVATE_DATA':'missing_evidence',
 'BUSINESS_RETRIEVAL_NOT_READY':'missing_evidence','EVIDENCE_MISSING':'missing_evidence','INVALID_INPUT':'missing_evidence',
 'EVIDENCE_VALUE_INVALID':'invalid_source_values','BUSINESS_VALUE_INVALID':'invalid_source_values',
 'BUSINESS_SOURCE_STALE':'stale_metadata','SOURCE_METADATA_STALE':'stale_metadata','BUSINESS_PREPARATION_STALE':'stale_metadata','ONTOLOGY_SELECTION_STALE':'stale_metadata',
 'MAPPING_INVALID':'incorrect_source_mapping','CONNECTOR_TIMEOUT':'connector_timeout','RETRYABLE_INVOCATION_FAILED':'connector_timeout',
 'CONNECTOR_AUTH_FAILED':'connector_authentication','OPERATION_NOT_AUTHORIZED':'revoked_authorization',
 'ASSIGNMENT_MISMATCH':'revoked_authorization','TOOL_ISOLATION_DENIED':'revoked_authorization',
 'EVIDENCE_CONFLICT':'conflicting_business_evidence','CAPABILITY_UNSUPPORTED':'unsupported_capability',
 'CAPABILITY_DEPENDENCY':'workflow_dependency','UNMATCHED_BRANCH':'workflow_dependency',
 'ACTION_EFFECT_UNVERIFIED':'uncertain_external_write','UNKNOWN_INVOCATION_RESULT':'uncertain_external_write','SMTP_DELIVERY_UNCERTAIN':'uncertain_external_write',
 'DELEGATION_INTERRUPTED':'interrupted_read',
 'ACCOUNT_GRAPH_STALE':'stale_metadata','ACCOUNT_GRAPH_VERSION':'stale_metadata','ACCOUNT_GRAPH_INTEGRITY':'stale_metadata','ACCOUNT_GRAPH_SOURCE':'revoked_authorization',
}



def node_external_write(workflow, node):
    """Use the reviewed per-node contract; unknown legacy tools fail closed."""
    if node.get('kind')!='tool':return False
    metadata=workflow.get('metadata',{})
    plan=metadata.get('connected_action_plan')
    contracts=metadata.get('connected_contracts')
    actions=plan.get('actions',[]) if isinstance(plan,dict) else []
    if not isinstance(actions,list):actions=[]
    action=next((a for a in actions if isinstance(a,dict) and a.get('action_id')==node.get('node_id')),None)
    contract=contracts.get(action.get('capability_id')) if action and isinstance(contracts,dict) else None
    if isinstance(contract,dict):
        effect=contract.get('side_effect')
        if effect in ('read','none'):return False
        if effect in ('write','draft'):return True
    return bool(workflow.get('execution_policy',{}).get('allow_external_writes',False))


def classify(code, *, task=None, source=None, external_write=False):
    category=CODES.get(code,'tool_execution_failure')
    if external_write and (category in ('connector_timeout','interrupted_read','storage_contention') or code=='UNKNOWN_INVOCATION_RESULT'):
        category='uncertain_external_write'
    strategy,retry,human=CATEGORIES[category]
    return dict(error_code=code,category=category,affected_task=task,source_or_tool=source,
                retry_eligible=retry and not external_write,recovery_strategy=strategy,human_intervention=human)


def failure_feedback(run):
    """Diagnostic hints, not validated experience, business facts or permissions."""
    from shared.llm_feedback import feedback, OUTPUT_ERRORS
    result=[]
    for item in run.get('classified_failures',[]):
        code=item.get('error_code')
        if code not in OUTPUT_ERRORS:continue
        result.append(dict(affected_task=item.get('affected_task'),**feedback(code)))
        if len(result)==8:break
    return result


def affected_tasks(tasks, changes):
    """Each task declares typed upstream refs; close the task-output dependency DAG."""
    changed=set(changes)
    affected={t['task_id'] for t in tasks if t['task_id'] in changed or set(t.get('dependency_refs',[])) & changed}
    while True:
        expanded=affected | {t['task_id'] for t in tasks if set(t['depends_on']) & affected}
        if expanded==affected:return affected
        affected=expanded


class RecoveryService:
    def __init__(self, runtime):self.runtime=runtime

    def inspect(self, run_id, auth):
        """Read-only operator evidence; never certify a remote outcome from flags."""
        rt = self.runtime
        with rt.store.transaction(write=False) as db:
            run = rt.load(db, run_id, auth)
            workflow = rt.store.get(db, run['workspace_id'], run['workflow_id'], run['workflow_version']) or {'nodes': []}
            nodes = {n['node_id']: n for n in workflow['nodes']}
            uncertain = []
            completed = []
            not_invoked = []
            for nid, state in run.get('node_states', {}).items():
                node = nodes.get(nid, {})
                identity = dict(node_id=nid, invocation_id=run.get('node_invocations', {}).get(nid))
                if state == 'completed':
                    completed.append({**identity, 'output_sha256': digest(run['outputs'][nid]) if nid in run.get('outputs', {}) else None})
                elif node.get('kind') == 'tool' and node_external_write(workflow,node) and state in ('executing', 'blocked', 'failed'):
                    started = db.execute("SELECT 1 FROM runtime_events WHERE workspace=? AND run_id=? AND json_extract(document,'$.event_type')='node.started' AND json_extract(document,'$.details.node_id')=? AND json_extract(document,'$.details.invocation_id')=? LIMIT 1",
                                         (run['workspace_id'], run_id, nid, identity['invocation_id'])).fetchone()
                    if not started:
                        not_invoked.append({**identity, 'tool_id': node.get('tool_id'), 'outcome': 'not_invoked'})
                        continue
                    # An intent or a failed local checkpoint cannot prove whether
                    # a provider accepted the call. Keep it explicitly uncertain.
                    uncertain.append({**identity, 'tool_id': node.get('tool_id'),
                        'effect_reference': run_id + ':' + nid, 'outcome': 'unknown',
                        'required_action': 'verify_provider_and_connector_journal'})
            for nid, state in run.get('delegation_states', {}).items():
                if nid.startswith('delegated_tool_') and state in ('executing', 'failed'):
                    # Delegated effect references use the recorded invocation UUID,
                    # not the dynamically generated tool node ID.
                    row = db.execute("SELECT document FROM runtime_events WHERE workspace=? AND run_id=? AND json_extract(document,'$.event_type')='node.started' AND json_extract(document,'$.details.node_id')=? ORDER BY sequence DESC LIMIT 1",
                                     (run['workspace_id'], run_id, nid)).fetchone()
                    invocation = json.loads(row[0])['details'].get('invocation_id') if row else None
                    uncertain.append(dict(node_id=nid, invocation_id=invocation,
                        effect_reference=run_id + ':' + invocation if invocation else None,
                        outcome='unknown', required_action='verify_provider_and_connector_journal'))
            lease_active = run.get('lease_until', 0) > rt.clock() and run['status'] == 'running'
            return dict(run_id=run_id, workflow_id=run['workflow_id'], workflow_version=run['workflow_version'],
                        status=run['status'], error_code=run.get('error_code'), lease_active=lease_active,
                        required_action='wait_for_worker' if lease_active else 'operator_reconciliation' if uncertain else 'review_failure' if run['status'] in ('failed', 'blocked') else 'none',
                        automatic_replay_allowed=False, uncertain_invocations=uncertain,
                        not_invoked=not_invoked, failure=deepcopy(run.get('classified_failures', [])[-1]) if run.get('classified_failures') else None,
                        completed_checkpoints=completed, consumed_usage=deepcopy(run.get('usage', {})),
                        guidance='Preserve the original effect reference and reviewed inputs. Use connector read-back reconciliation where supported; otherwise independently verify the provider outcome. A timeout or missing receipt does not prove failure. This view does not authorize replay or resume.')

    @staticmethod
    def observation_signature(evidence):
        # Read timestamps/request IDs are provenance, not changed business facts.
        def stable(value):
            if isinstance(value,list):return [stable(v) for v in value]
            if isinstance(value,dict):return {k:stable(v) for k,v in value.items() if k not in ('read_at','request_id','evidence_id','context_id','coverage_checked_at')}
            return value
        coverage=evidence.get('coverage',{})
        coverage_view={k:coverage[k] for k in ('state','conclusion_ready','business_outcomes') if k in coverage}
        for key in ('requirements','blocking_requirements'):
            coverage_view[key]=[{k:r[k] for k in ('fact_id','state','requirement_level') if k in r} for r in coverage.get(key,[])]
        return digest(dict(records=sorted([dict(record_id=r['record_id'],values=r['values']) for r in evidence.get('records',[])],key=lambda r:r['record_id']),
                           rule_results=stable(evidence.get('rule_results',[])),coverage=coverage_view))

    def revalidate_sources(self, run, workflow, auth):
        """Read outside write transactions; source checks are not agent re-execution."""
        preparation_id=workflow['metadata'].get('composition_preparation_id')
        preparation=None
        if preparation_id:preparation=self.runtime.workflows.business_preparation.checked(auth,preparation_id)
        package_pin=workflow['metadata'].get('client_package_pin')
        changed=[];receipts=[]
        tasks={t['task_id']:t for t in (workflow['metadata'].get('connected_tasks') or workflow['metadata'].get('composition_tasks',{})).values()}
        for tid,checkpoint in run.get('task_checkpoints',{}).items():
            task=tasks.get(tid,{})
            previous=checkpoint['result'].get('source_evidence',[])
            if not previous or not task.get('selected_tool_id'):continue
            if task.get('retrieval_task') and preparation:
                plan=dict(workflow_id=preparation_id,version_id=preparation['version_id'],inputs=preparation['inputs'],evidence_context=preparation['evidence_context'])
                current=self.runtime.workflows.business_preparation.coverage.refresh(auth,plan,task['retrieval_task'])
            elif package_pin and task.get('mapped_evidence'):
                current=self.runtime.workflows.business_composition.packages.read(auth,task['operation_inputs'])
            else:
                # Unknown read protocols are not silently certified fresh.
                changed.append(tid);continue
            fingerprint=self.observation_signature(current)
            same=fingerprint==self.observation_signature(previous[-1])
            if not same:changed.append(tid)
            receipts.append(dict(task_id=tid,evidence_sha256=fingerprint,unchanged=same,checked_at=self.runtime.clock()))
        return changed,receipts

    def resume(self, run_id, auth, *, changed_dependencies=()):
        """Explicit operator resume, same run, same approved revision and budget.

        No model-supplied correction, permission, new input or replacement version
        is accepted here. Changes requiring a new pin need a new preparation.
        """
        rt=self.runtime
        if not isinstance(changed_dependencies,(list,tuple)) or any(not isinstance(v,str) for v in changed_dependencies):
            raise RuntimeFailure('RECOVERY_INPUT_INVALID','Supply typed dependency reference identifiers.',422)
        with rt.store.transaction(write=False) as db:
            snapshot=rt.load(db,run_id,auth,'workflow.execute')
            if snapshot['subject_id']!=auth['subject']['subject_id']:raise RuntimeFailure('SUBJECT_MISMATCH','Resume requires the execution owner.',403)
            if snapshot['status'] not in ('failed','blocked'):raise RuntimeFailure('RECOVERY_STATE','Only failed or blocked runs can be resumed.')
            if snapshot.get('lease_until',0)>rt.clock():raise RuntimeFailure('RECOVERY_LEASE','Wait for the previous execution lease to expire.')
            snapshot_workflow,_=rt.revision(db,snapshot['workflow_id'],snapshot['workflow_version'],auth,snapshot.get('release_bound',False))
        rt.check_deadlines(snapshot, snapshot_workflow)
        with rt.store.transaction(write=False) as db:
            rt.governance.check_run(db, snapshot, snapshot_workflow)
        observed_changes,source_receipts=self.revalidate_sources(snapshot,snapshot_workflow,auth)
        requested_changes=list(changed_dependencies)
        changed_dependencies=list(dict.fromkeys([*requested_changes,*observed_changes]))
        with rt.store.transaction() as db:
            run=rt.load(db,run_id,auth,'workflow.execute')
            if digest(run)!=digest(snapshot):raise RuntimeFailure('RECOVERY_CONFLICT','Run state changed during source revalidation.')
            if run['subject_id']!=auth['subject']['subject_id']:raise RuntimeFailure('SUBJECT_MISMATCH','Resume requires the execution owner.',403)
            if run['status'] not in ('failed','blocked'):raise RuntimeFailure('RECOVERY_STATE','Only failed or blocked runs can be resumed.')
            if run.get('lease_until',0)>rt.clock():raise RuntimeFailure('RECOVERY_LEASE','Wait for the previous execution lease to expire.')
            workflow,_=rt.revision(db,run['workflow_id'],run['workflow_version'],auth,run.get('release_bound',False))
            if digest(workflow)!=run['workflow_digest']:raise RuntimeFailure('REVISION_CHANGED','Recovery cannot change the approved revision.')
            if rt.clock()-run['created_at']>=workflow['execution_policy']['limits']['timeout_seconds']:
                raise RuntimeFailure('RUN_TIMEOUT','Recovery cannot reset the workflow deadline.')
            tasks=list((workflow.get('metadata',{}).get('connected_tasks') or workflow.get('metadata',{}).get('composition_tasks',{})).values())
            if not tasks:raise RuntimeFailure('RECOVERY_UNSUPPORTED','Targeted resumption requires a prepared task composition.')
            preparation_id=workflow['metadata'].get('composition_preparation_id')
            package_pin=workflow['metadata'].get('client_package_pin')
            if package_pin:
                package=rt.workflows.business_composition.packages.get(auth,package_pin['package_id'],package_pin['revision'])
                if package['sha256']!=package_pin['package_sha256']:raise RuntimeFailure('CLIENT_PACKAGE_CHANGED','Recovery must preserve the package revision.')
            known={t['task_id'] for t in tasks}|{ref for t in tasks for ref in t.get('dependency_refs',[])}
            if set(changed_dependencies)-known:raise RuntimeFailure('RECOVERY_INPUT_INVALID','Unknown dependency references cannot select recovery targets.',422)
            nid=run.get('current_node_id')
            node=next((n for n in workflow['nodes'] if n['node_id']==nid),None)
            # Node-level external effects, including downstream completed writes,
            # must never be repeated or silently left inconsistent after recompute.
            connected=bool(workflow['metadata'].get('connected_action_plan'))
            writes=({a['action_id'] for a in workflow['metadata']['connected_action_plan']['actions'] if a['required_approvals']} if connected else
                    {n['node_id'] for n in workflow['nodes'] if n['kind']=='tool'} if workflow['execution_policy'].get('allow_external_writes') else set())
            affected=affected_tasks(tasks,changed_dependencies)
            if not affected:
                affected=affected_tasks(tasks,{t['task_id'] for t in tasks if t['task_id'] not in run.get('task_checkpoints',{})})
            if nid in writes or any(run['node_states'].get(w) in ('executing','completed') for w in (writes & affected if connected else writes)):
                raise RuntimeFailure('RECOVERY_RECONCILIATION_REQUIRED','Reconcile external effects before preparing an explicit new action.')
            failure=classify(run.get('error_code','UNKNOWN_INVOCATION_RESULT'),task=nid)
            # An expired master read lease has an uncertain model/read result, but
            # no external action; never extrapolate this to write-capable children.
            read_only=bool(tasks) and all(t['side_effect'] not in ('write','draft') for t in tasks)
            if run.get('error_code')=='UNKNOWN_INVOCATION_RESULT' and read_only:
                failure=classify('DELEGATION_INTERRUPTED',task=nid)
            if not failure['retry_eligible']:
                raise RuntimeFailure('RECOVERY_REVIEW_REQUIRED','Resolve the classified cause through current evidence, knowledge or authorization review before a new preparation.')
            attempts=run.get('recovery_history',[])
            agent=next((a for a in workflow['agents'] if node and a['agent_id']==node.get('agent_id')),None)
            ceiling=min(workflow['error_policy']['max_retries'], agent['limits']['max_retries'] if agent else 0)
            if len(attempts)>=ceiling:raise RuntimeFailure('RETRY_EXHAUSTED','The approved recovery allowance is exhausted.')
            # Use the same runtime reservation code; prior model/tool consumption stays charged.
            from .graph import GraphRunner
            GraphRunner(rt).reserve(db,run,workflow,agent,{'retries':1})
            affected=affected_tasks(tasks,changed_dependencies)
            if not affected:
                affected={t['task_id'] for t in tasks if t['task_id'] not in run.get('task_checkpoints',{})}
                affected=affected_tasks(tasks,affected)
            archived={k:run['task_checkpoints'].pop(k) for k in list(run.get('task_checkpoints',{})) if k in affected}
            attempt=dict(attempt=len(attempts)+1,timestamp=rt.clock(),category=failure['category'],strategy=failure['recovery_strategy'],
                         changed_dependencies=list(changed_dependencies),source_revalidations=source_receipts,affected_tasks=sorted(affected),
                         invalidated_results=archived,verified_success=False)
            run.setdefault('recovery_history',[]).append(attempt)
            # Invalidate the coordinator and graph descendants, retaining the trigger
            # and all independently completed graph branches and specialist checkpoints.
            graph_tasks=[dict(task_id=n['node_id'],depends_on=[e['source'] for e in workflow['edges'] if e['target']==n['node_id']]) for n in workflow['nodes']]
            downstream=affected_tasks(graph_tasks,affected if connected else [nid]) if nid else set()
            for key in downstream:
                if connected and key in run.get('action_instances',{}):run['action_instances'][key]=dict(state='pending',retry_decision='explicit_safe_retry',recovery_attempt=attempt['attempt'])
                run['node_states'].pop(key,None);run['outputs'].pop(key,None)
            for edge in workflow['edges']:
                if edge['source'] in downstream:run['edge_states'].pop(edge['edge_id'],None)
            run.pop('worker',None);run.pop('lease_until',None);run.pop('error_code',None)
            run['status']='queued'
            rt.event(db,run,'run.recovery_requested',{'attempt':attempt['attempt'],'affected_tasks':sorted(affected),'error_code':failure['error_code']})
            rt.save(db,run)
            return rt.public(run)


def evaluate_run(run, workflow, now):
    checkpoints=run.get('task_checkpoints',{})
    records=[c['result'] for c in checkpoints.values()]
    coverage=[r['coverage'] for r in records if r.get('coverage')]
    status=run['status']
    rules=[rule for r in records for e in r.get('source_evidence',[]) for rule in e.get('rule_results',[])]
    # Successful execution is separate from a supported business conclusion.
    evidence_valid=all(c.get('conclusion_ready',False) for c in coverage) if coverage else None
    for attempt in run.get('recovery_history',[]):
        needed=set(attempt['affected_tasks'])
        attempt['verified_success']=bool(status=='completed' and needed<=set(checkpoints) and
                                        all(checkpoints[t]['result'].get('state')=='completed' for t in needed))
    return dict(requested_outcome=workflow.get('description',''),achieved_outcome=status,
                evidence_validity=evidence_valid,business_rule_validity=('evaluated_with_gaps' if evidence_valid is False else 'evaluated') if rules else 'not_evaluated',
                tool_success_count=sum(len(r.get('tool_results',[])) for r in records)+sum(n['kind']=='tool' and run.get('node_states',{}).get(n['node_id'])=='completed' for n in workflow['nodes']),
                tool_failure_count=sum(bool(f.get('source_or_tool')) for f in run.get('classified_failures',[])),
                failure_count=len(run.get('classified_failures',[])),recovery_attempts=len(run.get('recovery_history',[])),
                recovery_success=bool(run.get('recovery_history')) and all(a['verified_success'] for a in run['recovery_history']),
                duration_seconds=max(0,now-run['created_at']),model_usage=deepcopy(run.get('usage',{}).get('workflow',{})),
                estimated_cost_usd=run.get('usage',{}).get('workflow',{}).get('estimated_cost_usd',0),
                human_corrections=deepcopy(run.get('human_corrections',[])))
