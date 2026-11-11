"""Connected-plan hooks for GraphRunner; execution and effect ownership stay there."""
from copy import deepcopy
import logging
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
    overview=metadata.get('overview_intent',{})
    if action['capability_id']=='tool.workflow_data_query' and overview.get('query'):
        if result.get('query')!=overview['query']:deny('Query differs from the reviewed automation template.','AUTOMATION_SCOPE_DENIED')
        if overview.get('temporal_pin'):
            from workflow_api.temporal_queries import resolve
            reference=run.get('automation_reference')
            due=reference.get('scheduled_due') if reference else overview['prepared_at']
            if due is None:deny('Logical occurrence time is missing.','AUTOMATION_SCOPE_DENIED')
            result['query']=resolve(overview['query'],overview['temporal_pin'],due)
    if action['capability_id']=='content.prepare':
        if metadata.get('goal_planning'):
            upstream={aid:deepcopy(run['action_instances'][aid]['output']) for aid in action['depends_on'] if run['action_instances'][aid]['output']!=result.get('data')}
            if upstream:result['data']={'primary':result['data'],'upstream_results':upstream}
        result['instructions']=action['instructions']
        result['source_references']=deepcopy(action['evidence_references'])
        from .aggregate_math import percentages,GUIDANCE
        derived=percentages([run['action_instances'][aid] for aid in action['depends_on']],
            dict(workspace_id=run['workspace_id'],subject_id=run['subject_id']))
        if derived:
            result['data']={'primary':result['data'],'verified_aggregate_math':derived}
            result['instructions']+=' '+GUIDANCE
        from .report_tables import context as table_context,GUIDANCE as TABLE_GUIDANCE
        tables=table_context(plan,action,run.get('action_instances',{}),metadata['connected_contracts'])
        if tables:
            data=result['data']
            result['data']={**data,'report_table_context':tables} if isinstance(data,dict) else {'primary':data,'report_table_context':tables}
            result['instructions']+=' '+TABLE_GUIDANCE
    if node['kind']=='agent' and action['capability_id'] not in {'content.prepare','subway.plan_query','data.plan_query'}:
        from workflow_api.investigation_agents import packet
        sources=[e for dep in action['depends_on'] for e in run.get('task_checkpoints',{}).get(dep,{}).get('result',{}).get('source_evidence',[])]
        result.setdefault('context',{})['evidence']=packet(sources)
        result['context']['task']={'task_id':action['action_id'],'capability_id':action['capability_id']}
    agent=next(a for a in workflow['agents'] if a['agent_id']==node['agent_id'])
    if node['kind']=='tool':
        # Exact Registry schema will be checked again by prepare_tool immediately before dispatch.
        c=metadata['connected_contracts'][action['capability_id']];schema=c['input_schema']
    else:schema=agent['input_schema']
    if list(Draft202012Validator(schema,format_checker=FormatChecker()).iter_errors(result)):deny('Resolved payload violates the registered input schema.','ACTION_INPUT_INVALID')
    return result


def validate_content_tables(workflow,node,output):
    action=action_for(workflow,node['node_id'])
    if not action or action['capability_id']!='content.prepare':return
    for tab in output.get('tabs',[]):
        if any(len(row)!=len(tab['headers']) for row in tab['rows']):
            from .service import RuntimeFailure
            error=RuntimeFailure('AGENT_OUTPUT_INVALID','Generated report rows must match their headers.')
            error.invalid_model_output=True
            error.validation_field='tabs/rows'
            error.validation_hint='Every report row must contain exactly one cell for each header, in the same order. Use null for unavailable values, including missing middle columns. Preserve all source citations and evidence qualifications. Never drop a column or shift values.'
            raise error


def content_urls(value):
    """Read native string values, not JSON-escaped text; trim prose punctuation."""
    import re
    if isinstance(value,str):return {u.rstrip('.,;:!?') for u in re.findall(r'https?://[^\s<>"\)\]]+',value)}
    if isinstance(value,dict):return set().union(*(content_urls(v) for v in value.values())) if value else set()
    if isinstance(value,list):return set().union(*(content_urls(v) for v in value)) if value else set()
    return set()


def validate_content(workflow,node,output,inputs):
    action=action_for(workflow,node['node_id'])
    if action and action['capability_id']=='data.plan_query' and isinstance(output,dict) and 'query' in output:
        from workflow_api.data_queries import canonical_model_projection,DataQueries
        from workflow_api.service import ApiFailure
        output['query']=canonical_model_projection(output['query'])
        catalog=inputs.get('context',{}).get('data_query_catalog',{})
        datasets={d['dataset_id']:d for d in catalog.get('datasets',[])}
        fields={f['field_id']:{**f,'dataset_id':d['dataset_id']} for d in datasets.values() for f in d['fields']}
        relationships={r['relationship_id']:r for r in catalog.get('relationships',[])}
        try:DataQueries.validate(None,output['query'],({},datasets,fields,relationships))
        except ApiFailure as exc:
            from .service import RuntimeFailure
            error=RuntimeFailure('AGENT_OUTPUT_INVALID','Generated query does not match the reviewed catalogue.',422)
            error.invalid_model_output=True;error.validation_field='query'
            error.validation_hint=('Typed-query validation: '+str(exc)+
                ' Correct that rule using the supplied catalogue. Fields must belong to the base or authorized join target. '
                'Preserve requested scope; never invent IDs, joins or filters. Use clarification for unsupported requirements.')[:400]
            raise error
        return
    if not action or action['capability_id']!='content.prepare':return
    from .report_tables import normalize,validate
    data=inputs.get('data',{})
    tables=data.get('report_table_context') if isinstance(data,dict) else None
    normalize(output,tables)
    validate(output,tables)
    validate_content_tables(workflow,node,output)
    def invalid(field,hint):
        from .service import RuntimeFailure
        error=RuntimeFailure('ACTION_CONTENT_UNVERIFIED','Generated content must use only supplied source references and verified URLs.',422)
        error.invalid_model_output=True;error.validation_field=field;error.validation_hint=hint
        raise error
    refs=output.get('source_references',[])
    if not set(refs)<=set(inputs['source_references']) or inputs['source_references'] and not refs:
        invalid('source_references','Copy the exact supplied source reference tokens. Do not invent references or omit all required citations.')
    url=inputs.get('artifact_url')
    if url and url not in output.get('body','') and url not in output.get('summary',''):
        invalid('body','Include the exact supplied artifact_url in body or summary. Do not shorten, rewrite, replace or invent an artifact URL.')
    if content_urls(output)-content_urls(inputs):
        logging.getLogger(__name__).warning('Connected content rejected: unprovided_url')
        invalid('content_urls','Use only exact URLs present in the supplied inputs or verified upstream receipts. Preserve their host, path and query. Do not invent links or append sharing parameters.')


def verify(workflow,node,output,inputs):
    action=action_for(workflow,node['node_id'])
    if not action:return
    validate_content(workflow,node,output,inputs)
    if node['kind']=='agent' and action['capability_id'] not in {'content.prepare','subway.plan_query','data.plan_query'}:
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
    for action in plan['actions']:
        run.setdefault('action_instances',{}).setdefault(action['action_id'],dict(state='pending',capability_id=action['capability_id'],depends_on=deepcopy(action['depends_on']),external_effect_status='not_started'))
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
    from workflow_api.workflow_knowledge import completed_usage
    item['ontology_usage']=completed_usage(workflow,action,run)
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
