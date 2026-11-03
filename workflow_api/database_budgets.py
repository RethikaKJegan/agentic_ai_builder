"""Finite proposal budgets based on registered database adapter reservations."""
from copy import deepcopy

# These are the reservation units of DatabaseConnector, not guessed API counts.
TOOL_UNITS = {'database_read_record': 1, 'database_read_query': 4,
              'database_prepare_operation': 4, 'database_execute_operation': 4}
CAPABILITY_TO_TOOL = {'database.read_record':'database_read_record', 'database.read_query':'database_read_query',
                      'database.prepare':'database_prepare_operation', 'database.execute':'database_execute_operation'}


def requirements(workflow):
    agents = {a['agent_id']:a for a in workflow.get('agents', [])}
    needed = {aid:0 for aid in agents}
    for node in workflow.get('nodes', []):
        if node.get('tool_id') in TOOL_UNITS and node.get('agent_id') in needed:
            needed[node['agent_id']] += TOOL_UNITS[node['tool_id']]
    for aid, agent in agents.items():
        if agent.get('hierarchy_role') != 'sub_agent' or agent['limits']['max_llm_calls'] == 0:
            continue
        units = [TOOL_UNITS[CAPABILITY_TO_TOOL[c]] for c in agent['capabilities'] if c in CAPABILITY_TO_TOOL]
        if units:
            needed[aid] = max(needed[aid], max(units))
    return agents, needed


def normalize(workflow):
    """Adjust editable proposals only; runtime reviewed limits stay authoritative."""
    agents, needed = requirements(workflow)
    if not any(needed.values()):
        return
    audit = workflow.setdefault('metadata', {}).setdefault('execution_budget_adjustments', [])
    for aid, agent in agents.items():
        limits = agent['limits']
        before = deepcopy(limits)
        if needed[aid]:
            limits['max_tool_calls'] = max(limits['max_tool_calls'], needed[aid])
        if agent.get('hierarchy_role') == 'sub_agent' and needed[aid] and limits['max_llm_calls']:
            limits['max_llm_calls'] = max(limits['max_llm_calls'], 4)
            # Query decision and result consumption each retain one bounded schema correction.
            # Both stages share a cumulative token cap.
            limits['max_tokens'] = max(limits['max_tokens'], 20000)
        if agent.get('hierarchy_role') == 'master' and limits['max_llm_calls']:
            limits['max_tokens'] = max(limits['max_tokens'], 20000)
        if before != limits:
            audit.append({'agent_id':aid, 'before':before, 'after':deepcopy(limits),
                          'reason':'database_adapter_reservation_and_result_turn'})
    limits = workflow['execution_policy']['limits']
    before = deepcopy(limits)
    for key in ('max_tool_calls', 'max_llm_calls', 'max_tokens'):
        limits[key] = max(limits[key], sum(a['limits'][key] for a in agents.values()))
    if before != limits:
        audit.append({'workflow':True, 'before':before, 'after':deepcopy(limits), 'reason':'cover_declared_agent_budgets'})
    if not audit:
        workflow['metadata'].pop('execution_budget_adjustments', None)


def validate(workflow):
    from .service import ApiFailure
    agents, needed = requirements(workflow)
    for aid, amount in needed.items():
        if amount > agents[aid]['limits']['max_tool_calls']:
            raise ApiFailure('DATABASE_EXECUTION_BUDGET_INVALID',
                'A database agent needs at least the connector reservation units before this workflow can run.',422,
                details={'agent_id':aid,'required_tool_units':amount})
        if amount and agents[aid].get('hierarchy_role')=='sub_agent' and 0 < agents[aid]['limits']['max_llm_calls'] < 2:
            raise ApiFailure('DATABASE_EXECUTION_BUDGET_INVALID','A delegated database reader needs a model turn to select the read and another to consume its result.',422)
    if workflow['execution_policy']['limits']['max_tool_calls'] < sum(needed.values()):
        raise ApiFailure('DATABASE_EXECUTION_BUDGET_INVALID','Workflow tool allowance cannot cover its required database adapter reservations.',422)
