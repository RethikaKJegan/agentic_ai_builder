"""Owner-scoped UI projection of composition and existing durable runtime state."""
from copy import deepcopy
import json
from uuid import uuid4
from .investigation_graph import fail
from .google_connections import now


def tool_receipt(output):
    receipt={k:deepcopy(output[k]) for k in ('draft_id','message_id','thread_id','event_id','spreadsheet_id','spreadsheet_url','status','request_id','version_id','row_count','has_more') if k in output}
    for field in ('messages','events','rows'):
        if isinstance(output.get(field),list):
            receipt['returned_'+field]=len(output[field])
            if field!='rows':receipt[field+'_identifiers']=[{k:item[k] for k in ('id','message_id','thread_id','event_id') if k in item} for item in output[field][:10] if isinstance(item,dict)]
    if isinstance(output.get('records'),list):
        receipt['returned_records']=len(output['records'])
        receipt['collections']=sorted({r['collection'] for r in output['records'] if isinstance(r,dict) and isinstance(r.get('collection'),str)})
    return receipt or {'returned_fields':sorted(output)}


def result_view(result):
    view={k:deepcopy(result[k]) for k in ('summary','findings','missing_information','state','classification','coverage') if k in result}
    records=[];seen=set();rules=[]
    for evidence in result.get('source_evidence',[]):
        rules.extend(deepcopy(evidence.get('rule_results',[])))
        for record in evidence.get('records',[]):
            compatible=next((r for r in records if all(r.get(k)==record.get(k) for k in ('record_id','collection','source_reference')) and all(r['values'][k]==v for k,v in record['values'].items() if k in r['values'])),None)
            if compatible is not None:
                compatible['values'].update(deepcopy(record['values']))
                continue
            identity=(record['record_id'],json.dumps(record['values'],sort_keys=True,default=str))
            if identity in seen:continue
            seen.add(identity)
            records.append({k:deepcopy(record[k]) for k in ('record_id','collection','source_reference','read_at','values') if k in record})
    view['records']=records;view['rule_results']=rules
    view['tool_receipts']=[dict(tool_id=r['tool_id'],receipt=tool_receipt(r.get('output',{}))) for r in result.get('tool_results',[])]
    return view


class CompositionPresentation:
    def __init__(self,composition):self.composition,self.service,self.store=composition,composition.service,composition.store

    def listing(self,auth):
        _,scope=self.composition.authorize(auth)
        with self.store.transaction(write=False) as db:
            rows=db.execute('SELECT document FROM business_compositions WHERE workspace=? AND owner=? ORDER BY rowid DESC LIMIT 50',scope).fetchall()
            metadata={r[0]:dict(name=r[1],deleted=r[2]) for r in db.execute('SELECT workflow_id,display_name,deleted_at FROM business_investigation_metadata WHERE workspace=? AND owner=?',scope).fetchall()}
            runs=[]
            if db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='runtime_runs'").fetchone():
                runs=[json.loads(r[0]) for r in db.execute('SELECT document FROM runtime_runs WHERE workspace=? AND subject=? ORDER BY rowid DESC LIMIT 200',scope).fetchall()]
            deleted={r[0] for r in db.execute('SELECT workflow_id FROM lifecycle_tombstones WHERE workspace=?',(scope[0],)).fetchall()}
        items=[]
        for row in rows:
            doc=json.loads(row[0]);wid='cw_'+doc['composition_id'].removeprefix('composition_');meta=metadata.get(wid,{})
            if wid in deleted or meta.get('deleted'):continue
            run=next((r for r in runs if r['workflow_id']==wid),None)
            items.append(dict(workflow_id=wid,composition_id=doc['composition_id'],display_name=meta.get('name') or doc['objective'],objective=doc['objective'],created_at=doc['created_at'],node_count=len(doc['tasks']),run_id=run['run_id'] if run else None,status=run['status'] if run else doc['state'],kind='composition'))
        return items

    def view(self,auth,cid,run_id=None):
        doc=self.composition.get(auth,cid,revalidate=False);wid='cw_'+cid.removeprefix('composition_');scope=(doc['scope']['workspace'],doc['scope']['owner'])
        with self.store.transaction(write=False) as db:
            if db.execute('SELECT 1 FROM lifecycle_tombstones WHERE workspace=? AND workflow_id=?',(scope[0],wid)).fetchone():fail('Workflow was deleted.','WORKFLOW_DELETED',410)
            meta=db.execute('SELECT display_name,deleted_at FROM business_investigation_metadata WHERE workspace=? AND owner=? AND workflow_id=?',(*scope,wid)).fetchone()
            if meta and meta[1]:fail('Workflow was deleted.','WORKFLOW_DELETED',410)
            workflow=self.store.get(db,scope[0],wid)
            run=None
            runtime=getattr(getattr(self.service,'runtime_runner',None),'runtime',None)
            if run_id is None and runtime is not None:
                latest=db.execute('SELECT run_id FROM runtime_runs WHERE workspace=? AND subject=? AND workflow_id=? ORDER BY rowid DESC LIMIT 1',(*scope,wid)).fetchone()
                if latest:run_id=latest[0]
            if run_id:
                if runtime is None:fail('The runtime is unavailable.','SERVICE_UNAVAILABLE',503)
                run=runtime.load(db,run_id,auth)
                if run['subject_id']!=scope[1] or run['workflow_id']!=wid:fail('Run is outside this composition.','RUN_NOT_FOUND',404)
                if run.get('adaptive'):
                    from .workflow_adaptive import effective, presentation_document
                    workflow=effective(run,workflow)
                    doc=presentation_document(doc,workflow)
            events=[]
            if run:
                events=[json.loads(r[0]) for r in db.execute('SELECT document FROM runtime_events WHERE workspace=? AND run_id=? ORDER BY sequence DESC LIMIT 1000',(scope[0],run_id)).fetchall()][::-1]
        tasks=[];checkpoints=(run or {}).get('task_checkpoints',{});failures=deepcopy((run or {}).get('classified_failures',[]))
        # Historical records retain their original diagnostics. Present citation
        # validation with its current classification without rewriting the run.
        from runtime.recovery import classify
        for failure in failures:
            if failure.get('error_code') in ('INVESTIGATION_AGENT_REFERENCE','INVESTIGATION_AGENT_OUTPUT','ACTION_CONTENT_UNVERIFIED'):
                failure.update(classify(failure['error_code'],task=failure.get('affected_task'),source=failure.get('source_or_tool')))

        from .workflow_queries import query_clarifications
        clarifications=query_clarifications(run,workflow)
        spawned={e['details']['agent_id']:e['details']['node_id'] for e in events if e['event_type']=='agent.spawned' and e['details'].get('agent_id')}
        for task in doc['tasks']:
            config=next((c for c in doc['configurations'] if c['assigned_task']==task['task_id']),None)
            checkpoint=checkpoints.get(task['task_id']);state=task['state'] if task['state']!='ready' else 'pending';output=None
            if checkpoint:
                output=result_view(checkpoint['result']);state='needs_input' if output.get('state') in ('needs_input','insufficient_evidence','conflicting_evidence') else 'completed'
            elif run and config:
                node_id=spawned.get(config['configuration_id'])
                execution=run.get('delegation_states',{}).get(node_id)
                state={'executing':'running','failed':'failed'}.get(execution,state)
                if run['status'] in ('failed','blocked','cancelled') and state=='running':state='interrupted'
            contract=doc['contracts'][task['capability_id']]
            action_node=next((n for n in (workflow or {}).get('nodes',[]) if n['node_id']==(task['task_id'] if doc.get('action_plan') else 'action_'+task['task_id'])),None)
            gate=next((n for n in (workflow or {}).get('nodes',[]) if n['node_id']=='approve_'+task['task_id']),None)
            if run and action_node:
                state=run['node_states'].get(action_node['node_id'],'pending')
                receipt=run['outputs'].get(action_node['node_id'])
                if receipt is not None and task['capability_id']=='content.prepare':
                    output=dict(summary=receipt.get('summary') or receipt.get('body') or '',findings=[],missing_information=deepcopy(receipt.get('questions',[])),records=[],rule_results=[],tool_receipts=[])
                    if run.get('adaptive'):
                        output['summary']='Generated interpretation; consult the evidence assessment for verified findings and completion. '+output['summary']
                        output['classification']='agent_interpretation'
                elif receipt is not None and contract['kind']=='model':output=result_view(receipt)
                elif receipt is not None:
                    tool_id=doc['selected_tools'].get(task['task_id'],{}).get('tool_id') or action_node.get('tool_id')
                    mapped=receipt.get('records')
                    if isinstance(mapped,list) and all(isinstance(r,dict) and 'record_id' in r and isinstance(r.get('values'),dict) for r in mapped):
                        output=result_view(dict(source_evidence=[receipt]))
                        output['summary']='Database read completed: '+str(len(mapped))+' record(s) retrieved.' if mapped else 'Database read completed. No matching records.'
                    else:
                        output=dict(summary='Tool execution completed; recorded result details follow.',findings=[],missing_information=[],records=[],rule_results=[])
                    output['tool_receipts']=[dict(tool_id=tool_id,receipt=tool_receipt(receipt))]
            if task['task_id'] in clarifications:
                state='needs_input'
                output=dict(summary='This query needs a business definition before it can run.',
                    classification='query_clarification',state='needs_input',
                    missing_information=[clarifications[task['task_id']]],records=[],rule_results=[],tool_receipts=[])
            tasks.append(dict(id=task['task_id'],label=contract['business_purpose'],kind='action' if contract['side_effect'] in ('write','draft') else 'retrieval' if contract['kind']=='tool' else 'agent',state=state,depends_on=task['depends_on'],capability_id=task['capability_id'],agent_id=config['configuration_id'] if config else None,tools=[doc['selected_tools'][task['task_id']]['tool_id']] if task['task_id'] in doc['selected_tools'] else [],condition=task['condition'],result=output,errors=[f for f in failures if f.get('affected_task')==task['task_id']],required_evidence=config.get('required_evidence_facts',[]) if config else contract['required_evidence'],completion_criteria=contract['completion_criteria'],approval_gate=dict(id=gate['node_id'],label=gate['label'],state=(run or {}).get('node_states',{}).get(gate['node_id'],'pending')) if gate else None))
        knowledge={}
        if doc.get('preparation_id'):
            prepared=self.composition.preparation.get(auth,doc['preparation_id'])
            knowledge=dict(pins=prepared['pins'],tasks=prepared['tasks'],coverage=prepared['coverage'],provenance=prepared['provenance'])
        elif doc.get('client_package_context'):knowledge=deepcopy(doc['client_package_context'])
        memory=runtime.working_memory.view(run,workflow) if run and workflow else None
        recovery=self.recovery_view(run,workflow,runtime.clock() if runtime else 0)
        public_run=None
        if run:
            public_run={k:deepcopy(run[k]) for k in ('run_id','status','approvals','created_at','usage')}
            if run.get('adaptive'):
                public_run['adaptive']=runtime.public(run)['adaptive']
                public_run['action_plan']=deepcopy(workflow['metadata']['connected_action_plan'])
            if doc.get('action_plan'):
                public_run['action_plan_reference']=deepcopy(run.get('action_plan_reference'))
                public_run['action_instances']=deepcopy(run.get('action_instances',{}))
            public_run['error_code']=run.get('error_code');public_run['failures']=deepcopy(failures)
            public_run['diagnostic_reference']=run.get('trace_reference')
            public_run['previous_failure_feedback']=deepcopy(run.get('previous_failure_feedback',[]))
            public_run['recovery_history']=[{k:deepcopy(h[k]) for k in ('attempt','timestamp','category','strategy','affected_tasks','verified_success','source_revalidations') if k in h} for h in run.get('recovery_history',[])]
            public_run['outcome']=deepcopy(run.get('outcome_evaluation'))
            public_run['approvals']=runtime.get_run(run_id,auth)['approvals']
            public_run['actions']=[dict(node_id=n['node_id'],label=n.get('label',n['node_id']),state=run['node_states'].get(n['node_id'],'pending'),inputs=deepcopy(run.get('action_instances',{}).get(n['node_id'],{}).get('resolved_inputs',n.get('configuration',{}).get('input',{}))),receipt=tool_receipt(run['outputs'][n['node_id']]) if n['node_id'] in run.get('outputs',{}) else {}) for n in workflow['nodes'] if n['kind']=='tool']
        request_context=dict(google_connection_id=doc.get('google_connection_id'),resources=deepcopy(doc['resources']))
        if doc.get('preparation_id'):
            request_context['business_request']=dict(inputs=deepcopy(prepared['inputs']))
            if prepared.get('evidence_context'):request_context['business_request']['evidence_context']={k:prepared['evidence_context'][k] for k in ('dataset_id','case_id')}
        if doc.get('client_package_context'):
            package=doc['client_package_context']['package'];request_context.update(client_package_id=package['package_id'],client_package_revision=package['revision'])
        return dict(composition_id=cid,workflow_id=wid,display_name=meta[0] if meta and meta[0] else 'Business investigation',objective=doc['objective'],state=doc['state'],gaps=doc['gaps'],created_at=doc['created_at'],tasks=tasks,master=doc['master'],workflow_status=workflow['status'] if workflow else None,workflow_version=workflow['version'] if workflow else None,run=public_run,knowledge=knowledge,memory=memory,recovery=recovery,planning=doc['planning'],resources=doc['resources'],request_context=request_context)

    @staticmethod
    def recovery_view(run,workflow,clock):
        from runtime.recovery import classify,node_external_write
        if not run or not workflow or run['status'] not in ('failed','blocked'):return dict(eligible=False,reason='No failed execution requires recovery.')
        failure=classify(run.get('error_code','UNKNOWN_INVOCATION_RESULT'))
        if run.get('error_code')=='INVESTIGATION_AGENT_REFERENCE':
            return dict(eligible=False,reason='The agent summary contained an unsupported or missing source citation. Review the retrieved records and evidence gaps, then start a new run with the corrected result schema. Source reads may already have completed; this error does not mean an agent ID is missing.',failure=failure)
        writes=[n for n in workflow['nodes'] if node_external_write(workflow,n)]
        if any(run['node_states'].get(n['node_id']) in ('executing','completed','blocked','failed') for n in writes):return dict(eligible=False,can_clarify=False,reason='Reconcile the external action before preparing another attempt.',failure=failure)
        from .workflow_queries import query_clarifications
        questions=query_clarifications(run,workflow)
        if questions:return dict(eligible=False,can_clarify=True,reason='Clarification needed: '+' '.join(questions.values())+' Supply the intended definition to generate a new reviewable workflow. This query has not executed.',failure=failure)
        if run.get('error_code')=='DATA_QUERY_INVALID' and workflow.get('metadata',{}).get('overview_intent',{}).get('route',{}).get('intent_type')=='knowledge':
            return dict(eligible=False,reason='This knowledge question was incorrectly prepared as a record query. Generate a new workflow from the original prompt to use the workspace knowledge. The failed run is preserved.',failure=failure)
        if run.get('error_code')=='UNKNOWN_INVOCATION_RESULT' and workflow['metadata'].get('composition_tasks'):failure=classify('DELEGATION_INTERRUPTED')
        if not failure['retry_eligible']:return dict(eligible=False,reason='The service could not identify a recoverable failure. Inspect its diagnostic reference before retrying.' if failure['category']=='internal_execution_failure' else 'Resolve the evidence, knowledge or authorization issue and prepare a new workflow.',failure=failure)
        if run.get('lease_until',0)>clock:return dict(eligible=False,reason='Waiting for the previous worker lease to expire.',failure=failure)
        if clock-run['created_at']>=workflow['execution_policy']['limits']['timeout_seconds']:return dict(eligible=False,reason='The original execution deadline has expired. Start a new run.',failure=failure)
        if len(run.get('recovery_history',[]))>=workflow['error_policy']['max_retries']:return dict(eligible=False,reason='The approved recovery allowance is exhausted. Start a new run.',failure=failure)
        return dict(eligible=True,reason='The application database was busy. Resume affected tasks after current source, permission and budget checks.' if failure['category']=='storage_contention' else 'Resume affected tasks after current source, permission and budget checks.',failure=failure)

    def rename(self,auth,cid,body):
        doc=self.composition.get(auth,cid,revalidate=False)
        from runtime.service import RuntimeService
        RuntimeService.authorize(auth,'workflow.edit',{'admin','builder'})
        if not isinstance(body,dict) or set(body)!={'display_name'} or not isinstance(body['display_name'],str) or not 1<=len(body['display_name'].strip())<=160:fail('Enter a workflow name between 1 and 160 characters.')
        from registry.safety import reject_secrets
        reject_secrets(body);wid='cw_'+cid.removeprefix('composition_');scope=(doc['scope']['workspace'],doc['scope']['owner'])
        with self.store.transaction() as db:
            db.execute('INSERT INTO business_investigation_metadata VALUES (?,?,?,?,?,?) ON CONFLICT(workspace,owner,workflow_id) DO UPDATE SET display_name=excluded.display_name,updated_at=excluded.updated_at',(*scope,wid,body['display_name'].strip(),None,now()))
        return dict(workflow_id=wid,display_name=body['display_name'].strip())

    def delete(self,auth,cid,body):
        doc=self.composition.get(auth,cid,revalidate=False)
        if body!={'confirmed':True}:fail('Confirm workflow deletion.','DELETE_CONFIRMATION_REQUIRED',400)
        from runtime.service import RuntimeService
        RuntimeService.authorize(auth,'workflow.delete',{'admin','builder'})
        scope=(doc['scope']['workspace'],doc['scope']['owner']);wid='cw_'+cid.removeprefix('composition_')
        with self.store.transaction(write=False) as db:
            if db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='runtime_runs'").fetchone():
                active=db.execute("SELECT 1 FROM runtime_runs WHERE workspace=? AND workflow_id=? AND json_extract(document,'$.status') IN ('queued','running','paused_for_approval')",(scope[0],wid)).fetchone()
                if active:fail('Wait for active work to finish before deleting.','INVESTIGATION_ACTIVE',409)
            release=db.execute('SELECT release_id FROM lifecycle_active WHERE workspace=? AND workflow_id=?',(scope[0],wid)).fetchone()
            existing=self.store.get(db,scope[0],wid)
        if existing:
            response=self.service.handle_lifecycle('delete_workflow',dict(request_id='delete_'+uuid4().hex,idempotency_key='delete_'+cid,payload=dict(workflow_id=wid,expected_release_id=release[0] if release else None,confirmed=True)),auth)
            if response['status']>=400:
                e=response['data']['error'];fail(e['message'],e['error_code'],response['status'])
        with self.store.transaction() as db:
            db.execute('INSERT INTO business_investigation_metadata VALUES (?,?,?,?,?,?) ON CONFLICT(workspace,owner,workflow_id) DO UPDATE SET deleted_at=excluded.deleted_at,updated_at=excluded.updated_at',(*scope,wid,None,now(),now()))
        return dict(workflow_id=wid,deleted=True)

    def cancel(self,auth,cid,run_id,body):
        if body!={}:fail('Cancellation does not accept replacement inputs.')
        doc=self.composition.get(auth,cid,revalidate=False);wid='cw_'+cid.removeprefix('composition_')
        runtime=getattr(getattr(self.service,'runtime_runner',None),'runtime',None)
        if runtime is None:fail('Runtime is unavailable.','SERVICE_UNAVAILABLE',503)
        with self.store.transaction() as db:
            run=runtime.load(db,run_id,auth,'workflow.execute')
            if run['subject_id']!=doc['scope']['owner'] or run['workflow_id']!=wid:fail('Run is outside this composition.','RUN_NOT_FOUND',404)
            if run['status'] in ('queued','running','paused_for_approval'):runtime.transition(db,run,'cancelled')
        return runtime.public(run)
