"""Read-only setup discovery: resolve real tables before generating a workflow."""
from copy import deepcopy
import re

from planner.errors import PlannerFailure
from runtime.connectors import google_spreadsheet_id


def spreadsheet_references(objective):
    ids = re.findall(r'https://docs\.google\.com/spreadsheets/d/([A-Za-z0-9_-]+)', objective)
    ids += re.findall(r'\bspreadsheet(?:\s+ID)?\s*[:=]?\s+([A-Za-z0-9_-]{20,})\b', objective, re.I)
    ids = list(dict.fromkeys(ids))
    if len(ids) > 8:
        raise PlannerFailure('SHEETS_DISCOVERY_LIMIT', 'Use at most eight spreadsheet links in one setup.')
    return ids


def validate_discovered_setup(workflow, catalogs):
    if not catalogs:
        return
    tables = {(c['spreadsheet_id'], t['range']): t for c in catalogs for t in c['tables']}
    for c in catalogs:
        for t in c['tables']:
            if re.fullmatch(r'[A-Za-z0-9_]+', t['title']):
                tables[(c['spreadsheet_id'], t['title'] + '!' + t['range'].split('!')[-1])] = t
    sources = workflow.get('metadata', {}).get('trigger_templates', [])
    for source in sources:
        if source.get('provider_id') != 'google_sheets':
            continue
        table = tables.get((google_spreadsheet_id(source['resource_id']), source.get('poll_input', {}).get('range')))
        if table is None:
            raise PlannerFailure('SHEETS_DISCOVERED_SOURCE_REQUIRED', 'Choose a source tab and range from the discovered spreadsheet.')
        poll = source['poll_input']
        if poll.get('identity_field') not in table['headers'] or any(f not in table['headers'] for f in poll.get('required_fields', [])):
            raise PlannerFailure('SHEETS_DISCOVERED_COLUMNS_REQUIRED', 'Choose identity and required columns from the actual source headers.')
        policy = workflow['metadata'].get('email_recipient_policy')
        if policy and policy.get('field') not in table['headers']:
            raise PlannerFailure('SHEETS_CUSTOMER_EMAIL_REQUIRED', 'Choose the customer email column from the actual source headers.')
        fields = workflow['metadata'].get('customer_automation', {}).get('case_fields', {})
        if any(field not in table['headers'] for field in fields.values()):
            raise PlannerFailure('SHEETS_CASE_FIELDS_REQUIRED', 'Case fields must refer to actual source headers.')
        if policy and fields:
            required = {policy['field'], fields['identity'], fields['complaint']}
            candidates = [t for c in catalogs for t in c['tables'] if required <= set(t['headers'])]
            objective = workflow['metadata']['customer_automation'].get('instructions', '').casefold()
            if len(candidates) > 1 and not any(t['title'].casefold() in objective for t in candidates):
                raise PlannerFailure('SHEETS_SOURCE_AMBIGUOUS', 'Which tab contains incoming customer cases? Choose ' +
                    ' or '.join(t['title'] for t in candidates) + ' and mention its name in your prompt.')
    for target in workflow.get('metadata', {}).get('sheet_read_targets', []):
        if (google_spreadsheet_id(target['spreadsheet_id']), target['range']) not in tables:
            raise PlannerFailure('SHEETS_DISCOVERED_TARGET_REQUIRED', 'Use supporting tabs and ranges from discovery.')


def catalog_snapshot(catalogs):
    return [{**deepcopy(c), 'tables': [{k: deepcopy(v) for k, v in t.items() if k != 'sample_rows'}
                                      for t in c['tables']]} for c in catalogs]
