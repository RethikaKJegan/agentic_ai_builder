"""Publication-reviewed customer automation policy, independent of business domain."""
import re

from planner.errors import PlannerFailure

EMAIL = re.compile(r"[A-Za-z0-9.!#$%&'*+/=?^_`{|}~-]+@[A-Za-z0-9](?:[A-Za-z0-9.-]*[A-Za-z0-9])?\.[A-Za-z]{2,}")


def automatic_policy(workflow, *, enabled=None, managers=None):
    policy = workflow.get('metadata', {}).get('customer_automation')
    if policy is None:
        return None
    fields = policy.get('case_fields', {}) if isinstance(policy, dict) else {}
    if (not isinstance(policy, dict) or policy.get('mode') != 'automatic' or
            not isinstance(policy.get('manager_email'), str) or not EMAIL.fullmatch(policy['manager_email']) or
            not isinstance(fields, dict) or set(fields) - {'identity', 'reference', 'name', 'complaint'} or
            not {'identity', 'complaint'} <= set(fields) or
            any(not isinstance(value, str) or not value.strip() for value in fields.values()) or
            policy.get('close_on_customer_confirmation') is not True or
            not isinstance(policy.get('instructions', ''), str) or len(policy.get('instructions', '')) > 12000):
        raise PlannerFailure('CUSTOMER_AUTOMATION_POLICY_INVALID', 'Choose a manager, case fields, and closure only on customer confirmation.')
    if enabled is False:
        raise PlannerFailure('CUSTOMER_AUTOMATION_DISABLED', 'Enable automatic email actions in the backend before publishing this workflow.')
    if managers is not None and policy['manager_email'].lower() not in {m.lower() for m in managers}:
        raise PlannerFailure('CUSTOMER_MANAGER_NOT_AUTHORIZED', 'The manager address must be an approved notification destination.')
    if workflow.get('error_policy', {}).get('max_retries', 0) != 0:
        raise PlannerFailure('EMAIL_ZERO_RETRIES_REQUIRED', 'Email submission requires zero automatic retries.')
    if (any(n.get('tool_id') == 'google_sheets_upsert_record' for n in workflow.get('nodes', [])) or
            any(t.get('capability') == 'update_spreadsheet' for t in workflow.get('tools', [])) or
            any('update_spreadsheet' in a.get('capabilities', []) for a in workflow.get('agents', []))):
        raise PlannerFailure('CUSTOMER_SHEETS_READ_ONLY', 'Customer email automation keeps spreadsheets read-only.')
    return policy


def routine_email_allowed(body):
    """Routine agents may acknowledge requests, but not commit compensation."""
    return not re.search(r'\b(?:we|i)\s+(?:will|have|shall)\s+(?:issue|provide|process|send|give|approve)\s+'
        r'(?:you\s+)?(?:a\s+|the\s+|your\s+)?(?:refund|replacement|compensation)\b|'
        r'\b(?:your\s+)?(?:refund|replacement|compensation)\s+(?:has\s+been|is|was)\s+(?:approved|issued|processed)\b', body, re.I)


def source_email_policy(workflow):
    policy = workflow.get('metadata', {}).get('email_recipient_policy')
    return isinstance(policy, dict) and policy.get('mode') == 'source_row' and isinstance(policy.get('field'), str)
