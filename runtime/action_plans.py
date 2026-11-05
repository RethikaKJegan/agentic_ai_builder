"""Connected-plan hooks for GraphRunner; execution and effect ownership stay there."""
from copy import deepcopy
from jsonschema import Draft202012Validator,FormatChecker
from workflow_api.action_bindings import resolve_inputs,binding_value,deny
from .service import digest


def action_for(workflow,node_id):
    return next((a for a in workflow.get('metadata',{}).get('connected_action_plan',{}).get('actions',[]) if a['action_id']==node_id),None)


def params(workflow,node,run):
    metadata=workflow.get('metadata',{});plan=metadata.get('connected_action_plan')
    if not plan:return None
    if plan['constraints'].get('deadline'):
        from datetime import datetime,timezone
        if datetime.now(timezone.utc)>=datetime.fromisoformat(plan['constraints']['deadline'].replace('Z','+00:00')):deny('Plan deadline has expired.','ACTION_DEADLINE_EXCEEDED')
    context=metadata['action_binding_context'];actions={a['action_id']:a for a in plan['actions']}
    if node['node_id']=='workflow_output':
        for aid in plan['completion_criteria']:
            if run.get('action_instances',{}).get(aid,{}).get('state')!='completed':deny('Plan completion criteria are not satisfied.','ACTION_INCOMPLETE')
        return {'actions':deepcopy(run.get('action_instances',{}))}
    if node['node_id'].startswith('condition_'):
        action=actions.get(node['node_id'].removeprefix('condition_'))
        if action:
            return {'condition':binding_value(action['when']['binding'],context,actions,run)==action['when']['equals']}
    action=actions.get(node['node_id'])
    if not action:return None
    result=resolve_inputs(action,context,actions,run)
    if action['capability_id']=='content.prepare':
        result['instructions']=action['instructions']
        result['source_references']=deepcopy(action['evidence_references'])
    if node['kind']=='agent' and action['capability_id']!='content.prepare':
        from workflow_api.investigation_agents import packet
        sources=[e for dep in action['depends_on'] for e in run.get('task_checkpoints',{}).get(dep,{}).get('result',{}).get('source_evidence',[])]
        result.setdefault('context',{})['evidence']=packet(sources)
    agent=next(a for a in workflow['agents'] if a['agent_id']==node['agent_id'])
    if node['kind']=='tool':
        # Exact Registry schema will be checked again by prepare_tool immediately before dispatch.
        c=metadata['connected_contracts'][action['capability_id']];schema=c['input_schema']
    else:schema=agent['input_schema']
    if list(Draft202012Validator(schema,format_checker=FormatChecker()).iter_errors(result)):deny('Resolved payload violates the registered input schema.','ACTION_INPUT_INVALID')
    return result


def verify(workflow,node,output,inputs):
    action=action_for(workflow,node['node_id'])
    if not action:return
    if action['capability_id']=='content.prepare':
        refs=output.get('source_references',[])
        if not set(refs)<=set(inputs['source_references']) or inputs['source_references'] and not refs:
            deny('Content citations must identify supplied evidence.','ACTION_CONTENT_UNVERIFIED')
        # Artifact URLs are copied from verified inputs, never invented during generation.
        url=inputs.get('artifact_url')
        if url and (url not in output.get('body','') and url not in output.get('summary','')):
            deny('Generated content omitted the verified artifact URL.','ACTION_CONTENT_UNVERIFIED')
        import re,json
        allowed=set(re.findall(r'https?://[^\s<>"\)]+',json.dumps(inputs)))
        for text in (output.get('body',''),output.get('summary','')):
            if set(re.findall(r'https?://[^\s<>"\)]+',text))-allowed:deny('Generated content invented an artifact/source URL.','ACTION_CONTENT_UNVERIFIED')
    if node['kind']=='agent' and action['capability_id']!='content.prepare':
        from workflow_api.investigation_agents import validate_analysis
        from workflow_api.service import ApiFailure
        try:checked=validate_analysis(output,inputs['context']['evidence'])
        except ApiFailure as exc:deny('Specialist findings cite unprovided evidence.',exc.code)
        output.clear();output.update(checked)
    if node['kind']=='tool':
        if output.get('status') in ('failed','error','rejected'):deny('Connector did not confirm the operation.','ACTION_RECEIPT_INVALID')
        if 'spreadsheet_id' in output and 'spreadsheet_url' in output:
            from urllib.parse import urlsplit
            url=urlsplit(output['spreadsheet_url'])
            if url.scheme!='https' or url.netloc!='docs.google.com' or url.path.rstrip('/') not in ('/spreadsheets/d/'+output['spreadsheet_id'],'/spreadsheets/d/'+output['spreadsheet_id']+'/edit'):
                deny('Spreadsheet receipt URL does not identify the created artifact.','ACTION_RECEIPT_INVALID')


def observed(workflow,node,run,inputs):
    plan=workflow.get('metadata',{}).get('connected_action_plan')
    if not plan:return
    run.setdefault('action_instances',{a['action_id']:dict(state='pending',capability_id=a['capability_id'],depends_on=deepcopy(a['depends_on']),external_effect_status='not_started') for a in plan['actions']})
    action=action_for(workflow,node['node_id'])
    if not action:return
    plan=workflow['metadata']['connected_action_plan']
    run['action_plan_reference']={'plan_id':plan['plan_id'],'revision':plan['revision'],'fingerprint':plan['fingerprint'],'scope':deepcopy(plan['scope'])}
    run.setdefault('action_instances',{}).setdefault(action['action_id'],{}).update(state='executing',capability_id=action['capability_id'],
        depends_on=deepcopy(action['depends_on']),resolved_inputs=deepcopy(inputs),input_fingerprint=digest(inputs),
        approval_references=[a['approval_id'] for a in run['approvals'] if a['status']=='approved' and a.get('action_digest')==digest({'node_id':node['node_id'],'kind':node['kind'],'tool_id':node.get('tool_id'),'agent_id':node.get('agent_id'),'params':inputs})],
        external_effect_status='intent_persisted' if action['required_approvals'] else 'not_applicable')
    from workflow_api.action_bindings import content_target
    run['action_instances'][action['action_id']]['input_provenance']=[dict(field=b['target'],binding_kind=b['kind'],
        provenance_type='SYNTHETIC' if b['kind']=='evidence' and workflow.get('metadata',{}).get('business_preparation',{}).get('evidence_context') else 'INFERRED' if b['kind']=='generated' else run.get('action_instances',{}).get(b.get('action_id'),{}).get('provenance_type','DERIVED') if b['kind']=='output' else 'ACTUAL',
        authority_classification='generated_content' if action['capability_id']=='content.prepare' or content_target(b['target']) else 'execution_input',
        source_reference=dict(action_id=b['action_id'],path=b['path']) if 'action_id' in b else dict(key=b['key'],path=b['path'])) for b in action['bindings']]


def completed(workflow,node,run,output):
    action=action_for(workflow,node['node_id'])
    if not action:return
    item=run.setdefault('action_instances',{}).setdefault(action['action_id'],{})
    scenario=bool(workflow.get('metadata',{}).get('business_preparation',{}).get('evidence_context'))
    source_read=workflow['metadata']['connected_contracts'][action['capability_id']].get('retrieval_task')
    item.update(state='completed',output=deepcopy(output),output_fingerprint=digest(output),
        verified_receipt=node['kind']=='tool',provenance_type='SYNTHETIC' if scenario and source_read else 'ACTUAL' if node['kind']=='tool' else 'INFERRED',
        source_references=deepcopy(action['evidence_references']),assumptions=[dict(value=v,provenance_type='SYNTHETIC',permitted_uses=['analytical_continuation']) for v in (output or {}).get('assumptions',[])],external_effect_status='connector_confirmed' if action['required_approvals'] else 'not_applicable')
    # Existing checkpoint/recovery storage is reused with stable action-specific keys.
    checkpoint_result=deepcopy(output)
    checkpoint_result['state']='completed'
    sources=[e for dep in action['depends_on'] for e in run.get('task_checkpoints',{}).get(dep,{}).get('result',{}).get('source_evidence',[])]
    if node['kind']=='tool' and 'records' in output and 'coverage' in output:sources.append(deepcopy(output))
    if sources:checkpoint_result['source_evidence']=list({digest(e):deepcopy(e) for e in sources}.values())
    run.setdefault('task_checkpoints',{})[action['action_id']]={'state':'completed','result':checkpoint_result,'action_plan_id':workflow['metadata']['connected_action_plan']['plan_id']}


def preflight(connector,inputs):
    # Only local validation here: never contact a provider before approval.
    recipient=getattr(connector,'recipient',None)
    if callable(recipient) and 'to' in inputs:recipient(inputs['to'])
    if getattr(connector,'definition',{}).get('provider_id')=='google_calendar' and 'event' in inputs:
        from connector_extension.calendar import validate_event
        validate_event(inputs['event'])
    calendars=getattr(connector,'calendars',None)
    if calendars and inputs.get('calendar_id') not in calendars:deny('Calendar is outside current connector restrictions.','DESTINATION_NOT_AUTHORIZED')
