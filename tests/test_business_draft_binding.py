"""Standalone draft matching uses runtime-bound effects, not automatic procurement defaults."""
from copy import copy,deepcopy
import pytest
from tests.test_business_composition import (composition,investigation,retrieval,knowledge,reference,
    generation,foundation,install_external,prepare,approve,DiagnosticAgents)
from workflow_api.procurement import ScopedConnector
from runtime import RuntimeService
from runtime.graph import GraphRunner


def deployment_draft(f):
    tool,transport=install_external(f,'extension_mail_draft',automatic=True)
    transport.definition=deepcopy(tool)
    transport.bind_workflow=lambda workflow:copy(transport)
    connector=ScopedConnector(transport,None)
    f.connectors[tool['tool_id']]=connector
    return connector,transport


def request(inputs):
    return dict(operations=[dict(capability_id='tool.extension_mail_draft',inputs=inputs)],
                resources=dict(destination='extension_recipients'))


INPUTS=dict(to='explicit@example.test',subject='Investigation review',body='Review the cited observations; no confirmed physical action.')


def test_automatic_default_is_classified_using_standalone_binding(composition):
    f=composition;connector,transport=deployment_draft(f)
    assert connector.external_write is False
    workflow=dict(workflow_id='checked_binding',version=1,metadata=dict(workspace_id='one'))
    assert connector.external_write_for_workflow(workflow) is True
    assert connector.bind_workflow(workflow).external_write is True
    procurement={**workflow,'metadata':{**workflow['metadata'],'procurement_project_id':'owned_project'}}
    assert connector.external_write_for_workflow(procurement) is False
    assert connector.bind_workflow(procurement).external_write is False
    assert transport.external_write is False and transport.calls==[]
    doc=prepare(f,'Prepare the explicitly addressed investigation draft.',**request(INPUTS))
    assert doc['state']=='ready',doc['gaps']
    assert transport.calls==[]


@pytest.mark.parametrize('missing',['destination','body'])
def test_matching_still_requires_explicit_destination_and_schema(composition,missing):
    f=composition;_,transport=deployment_draft(f);body=request(deepcopy(INPUTS))
    if missing=='destination':body['resources']={}
    else:body['operations'][0]['inputs'].pop('body')
    doc=prepare(f,'Prepare an investigation draft.',**body)
    assert doc['state']!='ready'
    assert any(('DESTINATION_NOT_AUTHORIZED' if missing=='destination' else 'REQUIRED_RESOURCE_INPUT') in gap.get('reasons',[]) for gap in doc['gaps'])
    assert transport.calls==[]


def test_workflow_bound_draft_still_waits_for_exact_action_approval(composition):
    f=composition;_,transport=deployment_draft(f)
    doc=prepare(f,'Prepare the explicitly addressed investigation draft.',**request(INPUTS))
    assert doc['state']=='ready',doc['gaps']
    workflow=f.c.workflow(f.x.a,doc['composition_id'])
    assert workflow['approval_gates'] and workflow['execution_policy']['allow_external_writes']
    f.adapter.auto_resolve_planner=True
    assert f.adapter.approve_pending(workflow,f.x.a)['ready']
    workflow=approve(f,workflow);runtime=RuntimeService(f.general)
    created=runtime.create_run(dict(request_id='bound_draft_run',operation='execute_workflow',idempotency_key='bound_draft_run_001',
        payload=dict(workflow_id=workflow['workflow_id'],workflow_version=1,inputs={})),f.x.a)
    runner=GraphRunner(runtime,agents=DiagnosticAgents(),connectors=f.connectors)
    result=runner.advance(created['run_id'],f.x.a)
    assert result['status']=='paused_for_approval',runtime.events(created['run_id'],f.x.a)
    assert transport.calls==[]
    with f.general.store.transaction(write=False) as db:stored=runtime.load(db,created['run_id'],f.x.a)
    runner.decide(dict(request_id='bound_draft_approval',operation='decide_approval',idempotency_key='bound_draft_approval_001',
        payload=dict(approval_id=stored['approvals'][-1]['approval_id'],workflow_id=workflow['workflow_id'],workflow_version=1,decision='approved')),f.x.a)
    result=runner.advance(created['run_id'],f.x.a)
    assert result['status']=='completed',runtime.events(created['run_id'],f.x.a)
    assert transport.calls==[INPUTS]


def test_existing_procurement_binding_does_not_require_extension_definition():
    class RowConnector:
        external_write=True
        def bind_workflow(self, workflow):return self
    connector=ScopedConnector(RowConnector(),None)
    workflow=dict(workflow_id='row_sync',version=1,metadata=dict(workspace_id='one',procurement_project_id='owned_project'))
    assert connector.external_write_for_workflow(workflow) is True
    assert connector.bind_workflow(workflow).external_write is True
