"""Agent definitions and an adapter for the accepted planner handoff."""
from copy import deepcopy
from .contracts import RegistryError, validate, validate_json_schema
from .safety import reject_secrets

PLANNER_CAPABILITIES = frozenset({
    'classify_text', 'retrieve_records', 'generate_report', 'read_spreadsheet',
    'send_email', 'send_notification',
})


def validate_agent(agent, policy, capabilities):
    reject_secrets(agent)
    validate(agent, 'agent')
    for name in ('input_schema', 'output_schema'):
        validate_json_schema(agent[name])
    if set(agent['permissions']) - policy.agent_permissions or any('*' in p for p in agent['permissions']):
        raise RegistryError('AGENT_NOT_AUTHORIZED', 'Agent permissions exceed workspace policy.', 'permissions', status=403)
    if set(agent['capabilities']) - set(capabilities):
        raise RegistryError('UNKNOWN_CAPABILITY', 'Agent requests an unknown capability.', 'capabilities')
    # Registration does not accept caller-created tool grants.
    if agent['allowed_tool_ids']:
        raise RegistryError('UNASSIGNED_TOOL', 'Tools must be assigned through registry authorization.', 'allowed_tool_ids', status=403)
    for name, maximum in policy.agent_limits.items():
        if name == 'max_estimated_cost_usd' and name not in agent['limits']:
            continue
        if name not in agent['limits'] or agent['limits'][name] > maximum:
            raise RegistryError('AGENT_LIMIT_EXCEEDED', 'Agent limits exceed workspace policy.', f'limits.{name}', status=403)
    if agent['retry_policy']['max_retries'] > agent['limits']['max_retries']:
        raise RegistryError('AGENT_LIMIT_EXCEEDED', 'Agent retry policy exceeds its limits.', 'retry_policy', status=403)
    if not all(agent['guardrails'].values()):
        raise RegistryError('AGENT_NOT_AUTHORIZED', 'All workspace agent guardrails are required.', 'guardrails', status=403)
    return deepcopy(agent)


def planner_requirements(response, known_tools):
    """Normalize workflow agent references without granting any authority."""
    reject_secrets(response)
    if not isinstance(response, dict) or response.get('status') != 200:
        raise RegistryError('INVALID_PLANNER_HANDOFF', 'A successful planner response is required.')
    data = response.get('data', {})
    if not isinstance(data, dict):
        raise RegistryError('INVALID_PLANNER_HANDOFF', 'Planner response data must be an object.')
    workflow = data.get('workflow')
    validate(workflow, 'workflow')
    agents = []
    for ref in workflow['agents']:
        if ref['allowed_tool_ids']:
            raise RegistryError('INVALID_PLANNER_HANDOFF', 'Planner drafts cannot assign executable tools.')
        definition = deepcopy(ref)
        definition['name'] = ref['agent_id'].replace('_', ' ').title()
        definition['retry_policy'] = {'max_retries': ref['limits']['max_retries'], 'backoff_seconds': 1}
        definition['guardrails'] = dict(pii_redaction=True, prompt_injection_detection=True, output_validation=True)
        agents.append(definition)
    accepted, unresolved = [], deepcopy(workflow['metadata'].get('unresolved_requirements', []))
    if not isinstance(unresolved, list):
        raise RegistryError('INVALID_PLANNER_HANDOFF', 'Unresolved requirements must be a list.')
    for tool in workflow['tools']:
        known = known_tools.get(tool['tool_id'])
        if known and known['capability'] == tool['capability']:
            accepted.append(deepcopy(tool))
        else:
            unresolved.append({'tool_id': tool['tool_id'], 'capability': tool['capability'], 'reason': 'REGISTRY_ENTRY_REQUIRED'})
    return dict(workflow_id=workflow['workflow_id'], workflow_version=workflow['version'],
                agents=agents, tool_requirements=accepted, unresolved_requirements=unresolved,
                approval_gates=deepcopy(workflow['approval_gates']),
                execution_policy=deepcopy(workflow['execution_policy']))
