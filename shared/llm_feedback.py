"""Small, data-free rule feedback; never include rejected model text or secrets."""
from copy import deepcopy

OUTPUT_ERRORS = frozenset({'MODEL_OUTPUT_INVALID_JSON', 'MODEL_OUTPUT_SCHEMA_INVALID', 'AGENT_OUTPUT_INVALID'})
HINTS = {
    'PLANNER_OUTPUT_INVALID_JSON': 'Return one complete JSON object matching canonical_workflow_schema, without prose or Markdown.',
    'CONNECTOR_INPUT_INVALID': 'Correct the proposed tool inputs to match that available tool input_schema. Do not change tool permissions or claim execution.',
    'AGENT_INPUT_INVALID': 'Correct each delegated task input to match the selected specialist input_schema. Preserve the original request.',
    'EMAIL_RECIPIENT_POLICY_INVALID': 'email_recipient_policy supports only {mode:source_row,field:actual_email_column}. For the connected account own inbox, omit this policy and use the registered mail profile output as recipient.',
    'WORKFLOW_COST_BUDGET_REQUIRED': 'Set execution_policy.limits.max_estimated_cost_usd to at least the sum of model-node and delegated specialist cost allowances. This is draft consistency, not provider billing.',
    'MODEL_OUTPUT_INVALID_JSON': 'Return one complete JSON object only, matching the required output schema.',
    'MODEL_OUTPUT_SCHEMA_INVALID': 'Return one schema-valid object. For control turns use the supplied decision envelope, exact action fields and final_output_schema; use only registered agent/tool IDs.',
    'AGENT_OUTPUT_INVALID': 'Return the exact business output object required by the output schema. Do not add wrappers or omit required fields.',
}


def feedback(code, field=None):
    item = {'code': code, 'hint': HINTS.get(code, 'Correct this validation rule using the supplied schema and allowed configuration. Preserve the user objective and approvals.')}
    if isinstance(field, str):
        item['field'] = field[:200]
    return item


def with_feedback(inputs, item):
    return {**deepcopy(inputs), 'validation_feedback': [item]}


def correct_once(invoke, before_correction):
    """Retry pure model generation once; caller owns reservation and authority."""
    try:
        return invoke(None)
    except Exception as error:
        code = getattr(error, 'code', None)
        if code not in OUTPUT_ERRORS and not (
            code in {'CONNECTOR_INPUT_INVALID', 'AGENT_INPUT_INVALID'} and
            getattr(error, 'invalid_model_output', False)
        ):
            raise
        item = feedback(code, getattr(error, 'validation_field', None))
        if before_correction(item) is False:
            raise
        return invoke(item)
