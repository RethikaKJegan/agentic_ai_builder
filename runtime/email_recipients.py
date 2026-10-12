"""Reviewed source-row recipient policy; email addresses bypass model output."""
import re
import ast

from planner.errors import PlannerFailure
from .service import RuntimeFailure
from .customer_automation import automatic_policy, source_email_policy


def normalize_generated_email_approvals(workflow):
    """Align a newly generated customer's sender with its direct approval gate."""
    if not source_email_policy(workflow):
        return
    nodes = {node['node_id']: node for node in workflow.get('nodes', [])}
    gates_by_agent = {}
    for node in workflow.get('nodes', []):
        if node.get('tool_id') != 'smtp_send_email' or not node.get('agent_id'):
            continue
        incoming = [edge for edge in workflow.get('edges', []) if edge['target'] == node['node_id']]
        if len(incoming) != 1 or incoming[0].get('outcome') != 'approved':
            continue
        parent = nodes.get(incoming[0]['source'], {})
        if parent.get('kind') == 'approval' and parent.get('approval_gate_id'):
            gates_by_agent.setdefault(node['agent_id'], set()).add(parent['approval_gate_id'])
    for agent in workflow.get('agents', []):
        gates = gates_by_agent.get(agent['agent_id'], set())
        if len(gates) == 1:
            agent['approval_requirements'] = list(gates)


def validate_email_workflow(workflow, *, allow_automatic=None, managers=None):
    automatic = automatic_policy(workflow, enabled=allow_automatic, managers=managers)
    policy = workflow.get('metadata', {}).get('email_recipient_policy')
    if policy is None:
        if automatic:
            raise PlannerFailure('EMAIL_SOURCE_ROW_REQUIRED', 'Automatic customer workflows require a source-row recipient.')
        return
    if (not source_email_policy(workflow) or set(policy) != {'mode', 'field'} or
            not policy['field'].strip() or len(policy['field']) > 128 or any(c in policy['field'] for c in '\r\n')):
        raise PlannerFailure('EMAIL_RECIPIENT_POLICY_INVALID', 'Use source_row mode with an actual customer email column.')
    templates = workflow.get('metadata', {}).get('trigger_templates', [])
    if not templates or any(t.get('provider_id') != 'google_sheets' or
                            t.get('input_mapping', {}).get('row') != 'row' for t in templates):
        raise PlannerFailure('EMAIL_SOURCE_ROW_REQUIRED', 'Map the original Sheets event row to inputs.row.')
    for node in workflow.get('nodes', []):
        if node.get('tool_id') != 'smtp_send_email':
            continue
        expression = node.get('configuration', {}).get('input_mapping', {}).get('to', '')
        expected = [f'inputs.row[{policy["field"]!r}]']
        if policy['field'].isidentifier():
            expected.append('inputs.row.' + policy['field'])
        try:
            matches = any(ast.dump(ast.parse(expression, mode='eval')) == ast.dump(ast.parse(e, mode='eval')) for e in expected)
        except (ValueError, SyntaxError, TypeError):
            matches = False
        if not matches:
            raise PlannerFailure('EMAIL_SOURCE_MAPPING_REQUIRED', 'Map the recipient directly from the configured source-row email column.')
        incoming = [e for e in workflow['edges'] if e['target'] == node['node_id']]
        agent = next((a for a in workflow.get('agents', []) if a['agent_id'] == node.get('agent_id')), None)
        if automatic and (agent is None or agent.get('limits', {}).get('max_llm_calls', 0) != 0):
            raise PlannerFailure('EMAIL_DETERMINISTIC_SENDER_REQUIRED', 'Automatic emails require a deterministic sender tool step.')
        if automatic and agent is not None and not agent.get('approval_requirements') and incoming and all(
                not any(n['node_id'] == e['source'] and n['kind'] == 'approval' for n in workflow['nodes']) for e in incoming):
            continue
        if not incoming or any(e.get('outcome') != 'approved' or not any(
                n['node_id'] == e['source'] and n['kind'] == 'approval' for n in workflow['nodes']) for e in incoming):
            raise PlannerFailure('EMAIL_APPROVAL_REQUIRED', 'Customer email sends must directly follow approval.')
        gates = {n['approval_gate_id'] for n in workflow['nodes'] if n['kind'] == 'approval' and
                 any(e['source'] == n['node_id'] and e['target'] == node['node_id'] and e.get('outcome') == 'approved'
                     for e in incoming)}
        if (len(gates) != 1 or agent is None or set(agent.get('approval_requirements', [])) != gates or
                not gates <= {g['approval_gate_id'] for g in workflow.get('approval_gates', [])}):
            raise PlannerFailure('EMAIL_APPROVAL_GATE_MISMATCH', 'The sender agent must require its direct approval gate.')
        if workflow.get('error_policy', {}).get('max_retries', 0) != 0:
            raise PlannerFailure('EMAIL_ZERO_RETRIES_REQUIRED', 'Customer email submission requires zero retries.')
    if automatic and any('send_email' in a.get('capabilities', []) and a.get('hierarchy_role') in {'master','sub_agent'} for a in workflow.get('agents', [])):
        raise PlannerFailure('EMAIL_DETERMINISTIC_SENDER_REQUIRED', 'Delegate drafting; keep submission in the deterministic sender step.')


def source_recipient(workflow, inputs):
    validate_email_workflow(workflow)
    if workflow.get('metadata', {}).get('email_recipient_policy') is None:
        return None
    row = inputs.get('row')
    value = row.get(workflow['metadata']['email_recipient_policy']['field']) if isinstance(row, dict) else None
    if (not isinstance(value, str) or len(value) > 254 or
            not re.fullmatch(r'[A-Za-z0-9.!#$%&\'*+/=?^_`{|}~-]+@[A-Za-z0-9](?:[A-Za-z0-9.-]*[A-Za-z0-9])?\.[A-Za-z]{2,}', value)):
        raise RuntimeFailure('CUSTOMER_EMAIL_INVALID', 'The source row must contain one valid customer email address.', 400)
    return value
