"""Composition guards for the existing DelegationSession; no scheduler or model loop."""
from copy import deepcopy
from jsonschema import Draft202012Validator
from .service import RuntimeFailure


def fail(code,message):raise RuntimeFailure(code,message,422)


def analysis_schema(context):
    """Constrain model citations to supplied observations without relaxing verification."""
    from workflow_api.investigation_graph import ANALYSIS_SCHEMA
    schema=deepcopy(ANALYSIS_SCHEMA)
    refs=schema['properties']['findings']['items']['properties']['references']
    by_record={}
    for record in context.get('records',[]):
        by_record.setdefault(record['record_id'],set()).update(record['values'])
    variants=[dict(type='object',additionalProperties=False,required=['record_id','mapping_id'],properties=dict(record_id=dict(type='string',const=rid),mapping_id=dict(type='string',enum=sorted(mids)))) for rid,mids in sorted(by_record.items()) if mids]
    if variants:refs['items']={'anyOf':variants}
    else:refs['maxItems']=0
    return schema


def verify_action(method,output,inputs=None):
    if not isinstance(output,dict):fail('CAPABILITY_RESULT_INVALID','Expected a typed tool receipt.')
    if output.get('status') in ('failed','error','rejected'):fail('CAPABILITY_RESULT_UNVERIFIED','The provider reported an unsuccessful action.')
    if method=='cancelled_event' and output.get('status')!='cancelled':fail('CAPABILITY_RESULT_UNVERIFIED','Cancellation was not confirmed.')
    if method in ('event_id','draft_id','spreadsheet_id') and not output.get(method):fail('CAPABILITY_RESULT_UNVERIFIED','The action returned no required provider identifier.')
    for key in ('event_id','spreadsheet_id'):
        if inputs and inputs.get(key) and output.get(key) and inputs[key]!=output[key]:fail('CAPABILITY_RESULT_UNVERIFIED','Provider receipt identifies a different resource.')
    if method=='event_id' and output.get('status') in ('cancelled','failed','error'):fail('CAPABILITY_RESULT_UNVERIFIED','The event was not created or updated successfully.')
    return output


class CompositionGuard:
    def __init__(self,session):
        self.session=session;self.tasks=session.workflow['metadata'].get('composition_tasks',{})
        self.by_task={t['task_id']:a for a,t in self.tasks.items()}
    @property
    def active(self):return bool(self.tasks)
    def completed(self,results):return {self.tasks[r['agent_id']]['task_id']:r['result'] for r in results if r['agent_id'] in self.tasks}
    def ready(self,results,pending):
        completed=self.completed(results);scheduled={r['agent_id'] for r in results}|{t['agent_id'] for t,_ in pending}
        return {a for a,t in self.tasks.items() if a not in scheduled and set(t['depends_on'])<=set(completed)}
    def proposal_schema(self,agent_id):
        """The master chooses a task ID; context is supplied only by the runtime."""
        return dict(type='object',additionalProperties=False,required=['task_id'],properties={'task_id':{'type':'string','const':self.tasks[agent_id]['task_id']}})

    def inputs(self,agent_id,proposed,results):
        task=self.tasks[agent_id]
        if not isinstance(proposed,dict) or proposed.get('task_id')!=task['task_id'] or set(proposed)-{'task_id'}:fail('CAPABILITY_TASK_INPUT','Delegate only the assigned task_id; task context is application-owned.')
        completed=self.completed(results)
        if not set(task['depends_on'])<=set(completed):fail('CAPABILITY_DEPENDENCY','Required task dependencies have not completed.')
        evidence=[];analyses=[]
        for dep in task['depends_on']:
            output=completed[dep];evidence.extend(output.get('source_evidence',[]))
            if output.get('classification')=='agent_interpretation':analyses.append({k:output[k] for k in ('summary','findings','missing_information')})
        from workflow_api.investigation_agents import packet
        context=dict(task=deepcopy(task),dependency_results={d:{k:deepcopy(v) for k,v in completed[d].items() if k not in ('source_evidence','tool_results')} for d in task['depends_on']},evidence=packet(evidence,analyses) if evidence else {},operation_inputs=deepcopy(task['operation_inputs']))
        preparation=getattr(self.session.runtime.workflows,'business_preparation',None)
        preparation_id=self.session.workflow['metadata'].get('composition_preparation_id')
        if preparation and preparation_id:
            doc=preparation.get(self.session.auth,preparation_id)
            names={task.get('retrieval_task')}|{self.tasks[self.by_task[d]].get('retrieval_task') for d in task['depends_on']}
            context['ontology_context']={name:{key:deepcopy(doc['tasks'][name][key]) for key in ('concepts','relationships','mappings','rules','dependency_resolution')} for name in names if name in doc['tasks']}
            context['knowledge_version']=doc['pins']
        from .memory import bounded_context, knowledge_pin
        with self.session.runtime.store.transaction(write=False) as db:
            memory_run=self.session.current(db)
        memory=self.session.runtime.working_memory.view(memory_run,self.session.workflow,task=task,dependencies=context['dependency_results'],permitted_tools=[task['selected_tool_id']] if task['selected_tool_id'] else [])
        memory.pop('dependency_outputs',None)  # Already supplied exactly once above.
        context['working_memory']=bounded_context(memory)
        failures=[f for f in memory_run.get('classified_failures',[]) if f.get('affected_task')==task['task_id']]
        context['previous_failure_feedback']=[deepcopy(f) for f in memory_run.get('previous_failure_feedback',[]) if f.get('affected_task')==task['task_id']]
        context['validated_strategy_hints']=self.session.runtime.experience_memory.relevant(self.session.auth,domain=self.session.workflow['metadata'].get('client_domain','configured_business_ontology'),capability=task['capability_id'],category=failures[-1]['category'] if failures else None,pins=knowledge_pin(self.session.workflow),agent_id=agent_id)
        package_context=self.session.workflow['metadata'].get('client_package_context',{})
        if package_context:
            context['ontology_context']={cid:deepcopy(v) for cid,v in package_context.items() if cid==task['capability_id'] or cid in {self.tasks[self.by_task[d]]['capability_id'] for d in task['depends_on']}}
            context['knowledge_version']=self.session.workflow['metadata']['client_package_pin']
        context['_source_evidence']=deepcopy(evidence)
        return dict(task_id=task['task_id'],context=context)
    def blocked(self,task,inputs):
        if task['condition']!='required_facts_available':return None
        results=inputs['context']['dependency_results'];bad=[v.get('coverage') for v in results.values() if v.get('coverage') and not v['coverage'].get('conclusion_ready')]
        if not bad:return None
        return dict(summary='Required evidence is unavailable or conflicting; dependent interpretation was not invoked.',findings=[],missing_information=sorted({g['fact_id'] for c in bad for g in c.get('blocking_requirements',[])}),state='conflicting_evidence' if any(c['state']=='conflicting_evidence' for c in bad) else 'needs_input',classification='backend_evidence_requirement',source_evidence=[])
    def verify(self,agent_id,output,inputs,tool_results=()):
        from workflow_api.capability_contracts import RESULT_SCHEMA
        if list(Draft202012Validator(RESULT_SCHEMA).iter_errors(output)):fail('CAPABILITY_RESULT_INVALID','Specialist result does not satisfy its contract.')
        task=self.tasks[agent_id];result=deepcopy(output)
        # The model cannot inject backend evidence or verification fields.
        result={k:result[k] for k in ('summary','findings','missing_information')}
        if task['selected_tool_id']:
            matches=[r for r in tool_results if r['tool_id']==task['selected_tool_id'] and r['inputs']==task['operation_inputs']]
            if not matches:fail('CAPABILITY_RESULT_UNVERIFIED','The required tool operation was not executed.')
            actual=matches[-1]['output'];verify_action(task['verification_method'],actual,task['operation_inputs'])
            if task.get('retrieval_task') or task.get('mapped_evidence'):
                from workflow_api.investigation_agents import validate_analysis,packet
                result=validate_analysis(result,packet([actual]))
            result.update(state='completed',classification='agent_interpretation',tool_results=deepcopy(matches))
            if task.get('retrieval_task') or task.get('mapped_evidence'):
                result['source_evidence']=[deepcopy(actual)];result['coverage']=deepcopy(actual['coverage'])
        else:
            from workflow_api.investigation_agents import validate_analysis
            packet=inputs['context'].get('evidence',{})
            if packet:
                result=validate_analysis(result,packet)
            else:
                if result['findings']:fail('CAPABILITY_RESULT_UNVERIFIED','No source observations were supplied for these findings.')
                result['classification']='agent_interpretation'
            result['state']='completed'
            result['source_evidence']=[deepcopy(e) for d in inputs['context']['dependency_results'].values() for e in d.get('source_evidence',[])]
        # Transitive source packets are supplied separately by the application.
        if not task['selected_tool_id']:
            result['source_evidence']=deepcopy(inputs['context'].get('_source_evidence',[]))
        return result
    def tool_inputs(self,agent_id,decision):
        task=self.tasks[agent_id]
        if decision['tool_id']!=task['selected_tool_id'] or decision['inputs']!=task['operation_inputs']:fail('CAPABILITY_TOOL_SCOPE','Tool operation differs from the exact prepared task/resource inputs.')
    def finish(self,output,results):
        if set(self.completed(results))!=set(self.by_task):fail('CAPABILITY_INCOMPLETE','All required tasks must return before final synthesis.')
        return dict(summary=output['summary'],narrative_classification='agent_interpretation',task_results=[dict(task_id=self.tasks[r['agent_id']]['task_id'],result=deepcopy(r['result'])) for r in results])
    def master_view(self,results):
        return [{**r,'result':{k:deepcopy(v) for k,v in r['result'].items() if k not in ('source_evidence','tool_results')}} for r in results]
