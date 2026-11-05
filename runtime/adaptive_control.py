"""Case-owned permission to advance existing GraphRunner; no action dispatch here."""
from .service import RuntimeFailure


def guard(db, runtime, run, workflow, node):
    control=workflow.get('metadata',{}).get('adaptive_control')
    if not control:return True
    row=db.execute('SELECT document FROM business_cases WHERE workspace=? AND owner=? AND case_id=?',
                   (run['workspace_id'],run['subject_id'],control['case_id'])).fetchone()
    import json
    case=json.loads(row[0]) if row else None
    adaptive=(case or {}).get('adaptive',{})
    if not case or case['case_status']=='CANCELLED' or adaptive.get('composition_id')!=workflow['metadata']['composition_id']:
        raise RuntimeFailure('ADAPTIVE_REVISION_SUPERSEDED','Adaptive case/revision is no longer executable.',409)
    if runtime.clock()>=adaptive.get('deadline',0):raise RuntimeFailure('ADAPTIVE_BUDGET_EXHAUSTED','Adaptive execution deadline expired.',409)
    if node['kind']=='trigger':return True
    if node['kind']=='output' and adaptive.get('status')=='completed':return True
    permission=adaptive.get('execution_permission') or {}
    if adaptive.get('phase')=='EXECUTE' and permission.get('run_id')==run['run_id'] and permission.get('action_id')==node['node_id']:
        return True
    if node['node_id'] in ('condition_'+str(permission.get('action_id')),'skip_'+str(permission.get('action_id'))) and adaptive.get('phase')=='EXECUTE' and permission.get('run_id')==run['run_id']:return True
    if node['kind']=='approval' and adaptive.get('phase')=='EXECUTE' and permission.get('run_id')==run['run_id'] and node['node_id']=='approve_'+str(permission.get('action_id')):
        return True
    # Case/driver owns continuation and completion. Workers cannot bypass evaluation.
    run['lease_until']=0
    runtime.save(db,run)
    return False


def reserve(run, workflow, amount):
    if not workflow.get('metadata',{}).get('adaptive_control'):return
    limits=run.get('adaptive_limits')
    if not limits:raise RuntimeFailure('ADAPTIVE_BUDGET_REQUIRED','Adaptive run must be attached by its case driver.',409)
    existing=run.get('usage',{}).get('workflow',{})
    external=run.get('adaptive_reasoning_usage',{})
    for key,ceiling in [('tokens','max_tokens'),('tool_calls','max_tool_calls'),('llm_calls','max_llm_calls')]:
        if existing.get(key,0)+external.get(key,0)+amount.get(key,0)>limits[ceiling]:
            raise RuntimeFailure('ADAPTIVE_BUDGET_EXHAUSTED','Case-wide execution/reasoning allowance is exhausted.',409)


def suspended(db,runtime,run,workflow):
    control=workflow.get('metadata',{}).get('adaptive_control')
    if not control:return False
    import json
    row=db.execute('SELECT document FROM business_cases WHERE workspace=? AND owner=? AND case_id=?',(run['workspace_id'],run['subject_id'],control['case_id'])).fetchone()
    if not row:return False
    case=json.loads(row[0]);adaptive=case.get('adaptive',{})
    if case['case_status']!='CANCELLED' and adaptive.get('suspended_at') is not None and adaptive.get('composition_id')==workflow['metadata']['composition_id']:
        run['lease_until']=0;runtime.save(db,run);return True
    return False
