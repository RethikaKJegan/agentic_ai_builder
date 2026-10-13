"""Canonical single-tool smoke workflows; no procurement business decisions."""
from copy import deepcopy
import json
from .catalog import CATALOG, ROOT


def connector_workflow(tool_id, inputs, workflow_id='extension_connector_check', sheet_targets=None):
    tool = CATALOG[tool_id]
    workflow = json.loads((ROOT / 'shared/contracts/examples/workflows/support-triage.json').read_text())
    agent = json.loads((ROOT / 'shared/contracts/examples/agents/valid-classifier.json').read_text())
    agent.update(agent_id=workflow_id + '_connector', capabilities=[tool['capability']],
                 permissions=['workflow.read_input'], input_schema={'type': 'object'}, output_schema={'type': 'object'})
    agent['limits'].update(max_llm_calls=1, max_tool_calls=3, max_retries=0, timeout_seconds=120)
    embedded = {key: value for key, value in agent.items() if key not in {'name', 'retry_policy', 'guardrails'}}
    workflow.update(workflow_id=workflow_id, version=1, status='draft', name='Extension connector check',
        description='Run one connector with supplied settings and inspect its actual result in the runtime trace.',
        inputs=[], outputs=[], stakeholders=[], agents=[embedded],
        tools=[{'tool_id': tool_id, 'capability': tool['capability']}], conditions=[], approval_gates=[], metadata={},
        nodes=[{'node_id': 'start', 'kind': 'trigger', 'label': 'Manual check'},
               {'node_id': 'action', 'kind': 'tool', 'label': tool['description'], 'tool_id': tool_id,
                'agent_id': agent['agent_id'], 'configuration': {'input': deepcopy(inputs)}},
               {'node_id': 'finish', 'kind': 'output', 'label': 'Finished', 'configuration': {'input': {}}}],
        edges=[{'edge_id': 'start_action', 'source': 'start', 'target': 'action'},
               {'edge_id': 'action_finish', 'source': 'action', 'target': 'finish'}])
    workflow['execution_policy']['allow_external_writes'] = tool['approval_required']
    workflow['execution_policy']['limits'].update(max_llm_calls=3, max_tool_calls=5, max_retries=0,
                                                 timeout_seconds=300, max_estimated_cost_usd=1)
    workflow['error_policy'].update(on_runtime_error='stop', max_retries=0)
    if sheet_targets: workflow['metadata']['sheet_write_targets'] = deepcopy(sheet_targets)
    if tool['approval_required']:
        workflow['approval_gates'] = [{'approval_gate_id': 'review_action', 'approver_roles': ['approver'],
                                       'on_reject': 'stop', 'timeout_seconds': 120}]
        workflow['nodes'].insert(1, {'node_id': 'review', 'kind': 'approval', 'label': 'Review connector action', 'approval_gate_id': 'review_action'})
        workflow['edges'][0] = {'edge_id': 'start_review', 'source': 'start', 'target': 'review'}
        workflow['edges'].append({'edge_id': 'review_action', 'source': 'review', 'target': 'action', 'outcome': 'approved'})
    return workflow
