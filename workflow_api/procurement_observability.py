"""Read-only aggregation of project-owned exact canonical run revisions."""
from connector_extension.procurement.store import require,ProcurementError


def communication_actions(actions, limit=100):
    """Keep real agent work visible when frequent inbox polls dominate history."""
    history=list(actions.items())
    if len(history)<=limit:return history
    substantive=[item for item in history if not item[0].startswith(('ful_read_','read_quotes_'))]
    protected=[item for item in substantive if item[0]=='ingestion']
    fulfilment=[item for item in substantive if item[0].startswith('ful_extract_')]
    if fulfilment:protected.append(fulfilment[-1])
    selected={key:action for key,action in protected}
    polls=[item for item in history if item[0].startswith(('ful_read_','read_quotes_'))][-min(10,limit//4):]
    remaining=limit-len(selected)-len(polls)
    for key,action in [item for item in substantive if item[0] not in selected][-max(0,remaining):]:
        if len(selected)<limit:selected[key]=action
    for key,action in polls:
        if len(selected)<limit:selected[key]=action
    return list(selected.items())


def project_communication(service,procurement,workflow_id,version,auth):
    workspace=procurement.authorize(auth)
    result=service.handle({'request_id':'req_project_graph','operation':'get_workflow',
                          'payload':{'workflow_id':workflow_id,'workflow_version':version}},auth)
    require(result['status']==200,'WORKFLOW_NOT_FOUND')
    parent=result['data']['workflow'];plan=parent.get('metadata',{}).get('procurement_plan')
    require(plan is not None,'PROCUREMENT_SETUP_INVALID')
    try:job=procurement.job(workspace,plan['project_id'])
    except ProcurementError as exc:
        if exc.code!='PROCUREMENT_PROJECT_NOT_FOUND':raise
        from .procurement import communication_workflow
        return {'project_id':plan['project_id'],'phase':'NOT_STARTED','root_workflow':parent,'actions':[],
                'configured_workflow':procurement.discovery_ingestion(plan,communication_workflow(
                    procurement.effective_plan(plan),workflow_id+'_preview',procurement.model)), 'truncated':False}
    require(all(job.get('owner_workflow',{}).get(k)==v for k,v in {'workflow_id':workflow_id,'version':version}.items()),'PROCUREMENT_PROJECT_BOUND')
    actions=[];truncated=False
    root_run=None;root_events=[]
    if job.get('root_run_id'):
        root_run=service.runtime_runner.runtime.get_run(job['root_run_id'],auth)
        require(root_run['workflow_id']==workflow_id and root_run['workflow_version']==version,'PROCUREMENT_RUN_MISMATCH')
        root_events=service.runtime_runner.runtime.events(job['root_run_id'],auth)['items'][:300]
    history=list(job['actions'].items())
    selected=communication_actions(job['actions'])
    for name,action in selected:
        if not action.get('run_id'):continue
        run=service.runtime_runner.runtime.get_run(action['run_id'],auth)
        require(run['workflow_id']==action['workflow_id'] and run['workflow_version']==action['workflow_version'],'PROCUREMENT_RUN_MISMATCH')
        response=service.handle({'request_id':'req_project_action','operation':'get_workflow','payload':{
            'workflow_id':action['workflow_id'],'workflow_version':action['workflow_version']}},auth)
        require(response['status']==200,'WORKFLOW_NOT_FOUND')
        workflow=response['data']['workflow']
        require(workflow['metadata'].get('procurement_project_id')==plan['project_id'],'PROCUREMENT_SCOPE_MISMATCH')
        events=service.runtime_runner.runtime.events(action['run_id'],auth)['items']
        truncated=truncated or len(events)>300
        actions.append({'key':name,'workflow':workflow,'run':run,'events':events[:300]})
    return {'project_id':plan['project_id'],'phase':job['phase'],'root_workflow':parent,'actions':actions,
            'root_run':root_run,'root_events':root_events,'configured_workflow':None,'truncated':truncated or len(job['actions'])>100}
