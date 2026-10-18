"""Published manual assignments survive a fresh service without stored authority."""
from copy import deepcopy
import json
import pytest
from registry.contracts import RegistryError
from runtime.service import digest
from workflow_api.database_workflows import bind_generated
from workflow_api.inventory_report_planner import compile_inventory_report
from tests.test_inventory_report_planner import PROMPT, proposal, source_catalog


def test_fresh_manual_worker_recovers_only_current_original_approver():
    from tests.test_integrated_procurement import IntegratedTests
    case=IntegratedTests(methodName='test_native_prompt_to_approved_sends_and_tracking');case.setUp()
    try:
        config=json.loads((case.path/'config.json').read_text());config['enabled_providers'].append('google_calendar')
        (case.path/'config.json').write_text(json.dumps(config));case.start()
        s=case.service
        defs=[t['definition'] for t in s.registry.list_tools(case.auth)['data']['items']]
        catalog=source_catalog()
        context={'google_connection_id':'gc_'+'a'*32,'database_catalog':catalog,'database_workflow_tools':defs,'workflow_google_tools':defs}
        workflow=compile_inventory_report(proposal(),PROMPT,context);workflow['workflow_id']='fresh_worker_report'
        bind_generated(workflow,context)
        s.database_workflows.scope=lambda *args:(workflow['metadata']['database_scope'],catalog)
        s.database_workflows.queries.context=lambda actor:({}, {}, {}, {})
        s.database_workflows.queries.validate=lambda plan,ctx:({'products':set(),'categories':set(),'suppliers':set()},None,None)
        ref={'workflow_id':workflow['workflow_id'],'workflow_version':1}
        case.call('save_workflow_version',{**ref,'base_version':0,'workflow':workflow})
        case.call('validate_workflow',ref)
        case.call('approve_workflow',{**ref,'action':'approve'})
        published=case.call('approve_workflow',{**ref,'action':'publish'})['workflow']
        expected=digest(published)
        for mode in ('different_subject','no_approval_permission','no_approval_role','missing_scopes','draft','good'):
            case.start()  # Independent Registry/approval memory, same persisted revision.
            service=case.service;adapter=service.registry_adapter;actor=deepcopy(case.auth);document=deepcopy(published)
            if mode=='different_subject':actor['subject']['subject_id']='another_executor'
            if mode=='no_approval_permission':actor['permissions'].remove('workflow.approve')
            if mode=='no_approval_role':actor['roles']=['builder']
            if mode=='missing_scopes':actor['scopes']=[]
            if mode=='draft':document['status']='draft'
            review=adapter.review(document,actor)
            assert not review['ready'],(mode,review)
            if mode!='good':
                with pytest.raises(RegistryError):adapter.execution_assignments(document,actor)
                continue
            with service.store.transaction(write=False) as db:
                loaded,grants=service.runtime_runner.runtime.revision(db,ref['workflow_id'],1,actor)
            assert grants and digest(loaded)==expected
            assert all(g['authorization_state']=='authorized' and g['subject_id']==actor['subject']['subject_id'] for g in grants)
            assert len(loaded['approval_gates'])==3
    finally:case.doCleanups()
