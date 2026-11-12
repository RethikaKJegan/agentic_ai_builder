"""Draft-only call allowances derived from trusted capability contracts."""

def normalize_generated(action, contract, *, minimum_timeout_seconds=None):
    """Called only before review for generated actions, never at execution.

    Do not coerce malformed values or repair retry policies. Full schema, plan
    caps, Registry limits and approval checks remain authoritative afterwards.
    """
    budget = action.get('budget')
    if not isinstance(budget, dict):return
    names = ('max_llm_calls', 'max_tool_calls')
    if any(type(budget.get(key)) is not int or budget[key] < 0 for key in names):return
    if contract['kind'] == 'model':
        budget['max_llm_calls'] = max(1, budget['max_llm_calls'])
        budget['max_tool_calls'] = 0
    elif contract['kind'] == 'tool':
        budget['max_llm_calls'] = 0
        budget['max_tool_calls'] = 1 if contract['side_effect'] in ('write', 'draft') else max(1, budget['max_tool_calls'])
        if (type(minimum_timeout_seconds) is int and minimum_timeout_seconds > 0
                and type(budget.get('timeout_seconds')) is int and budget['timeout_seconds'] > 0):
            budget['timeout_seconds'] = max(budget['timeout_seconds'], minimum_timeout_seconds)


def validate_allowance(action, contract):
    budget = action['budget']
    kind = contract['kind']
    if not (kind == 'tool' and budget['max_tool_calls'] < 1 or
            kind == 'model' and (budget['max_llm_calls'] < 1 or budget['max_tool_calls'] != 0)):
        return
    from runtime.service import RuntimeFailure
    required = {'max_tool_calls_minimum': 1} if kind == 'tool' else {'max_llm_calls_minimum': 1, 'max_tool_calls': 0}
    description = 'at least one tool call' if kind == 'tool' else 'at least one model call and zero direct tool calls'
    error = RuntimeFailure('ACTION_BINDING_INVALID', f"Action {action['action_id']} ({action['capability_id']}) requires {description}.", 422)
    error.binding_issue = dict(field='budget', action_id=action['action_id'], capability_id=action['capability_id'],
        rule='capability_budget_mismatch', required=required,
        observed={key: budget[key] for key in ('max_llm_calls', 'max_tool_calls')},
        correction='Use the registered capability kind to allocate call allowances. Preserve requested actions, retry restrictions and plan/agent limits; never increase aggregate limits to evade validation.')
    raise error
