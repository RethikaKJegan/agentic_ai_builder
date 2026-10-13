"""Offline definition/fixture checks. Never imports the app or calls providers."""
from copy import deepcopy
import json
from pathlib import Path
from decimal import Decimal
from datetime import datetime
import re
from jsonschema import Draft202012Validator, FormatChecker, ValidationError

ROOT = Path(__file__).resolve().parent / 'contracts/v1'


def main():
    schema = json.loads((ROOT / 'records.schema.json').read_text())
    policy_schema = json.loads((ROOT / 'policy.schema.json').read_text())
    for definition in (schema, policy_schema):
        Draft202012Validator.check_schema(definition)
    formats = FormatChecker()
    @formats.checks('date-time', raises=(ValueError, TypeError))
    def aware_timestamp(value):
        if not isinstance(value, str):
            return True
        if not re.fullmatch(r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})', value):
            return False
        return datetime.fromisoformat(value.replace('Z', '+00:00')).tzinfo is not None
    validator = Draft202012Validator(schema, format_checker=formats)
    policy_validator = Draft202012Validator(policy_schema, format_checker=FormatChecker())
    records = json.loads((ROOT / 'examples.json').read_text())
    policy = json.loads((ROOT / 'policy.default.json').read_text())
    policy_validator.validate(policy)
    for record in records:
        validator.validate(record)
    by_id = {record['record_id']: record for record in records}
    assert len(by_id) == len(records), 'Duplicate fixture IDs.'
    relation_types = {'vendor_id': 'vendor', 'rfq_id': 'rfq', 'quotation_id': 'quotation',
                      'award_id': 'award', 'purchase_order_id': 'purchase_order',
                      'approval_id': 'approval', 'release_approval_id': 'approval'}
    for record in records:
        assert by_id[record['project_id']]['record_type'] == 'project'
        for key, kind in relation_types.items():
            target = record['data'].get(key)
            if target is None:
                continue
            assert by_id[target]['record_type'] == kind
            assert by_id[target]['workspace_id'] == record['workspace_id']
            assert by_id[target]['project_id'] == record['project_id']
        data = record['data']
        if record['record_type'] in ('quotation', 'purchase_order') and record['data'].get('status') != 'NEEDS_CLARIFICATION':
            finance = data['financials']
            assert sum(Decimal(line['line_total']) for line in data['items']) == Decimal(finance['subtotal'])
            assert (Decimal(finance['subtotal']) - Decimal(finance['discount']) + Decimal(finance['tax'])
                    + Decimal(finance['shipping']) + Decimal(finance['other_charges'])) == Decimal(finance['total_delivered_cost'])
        if record['record_type'] == 'purchase_order':
            for line in data['items']:
                values = [Decimal(line[key]) for key in ('buyer_accepted_quantity', 'delivered_quantity',
                          'dispatched_quantity', 'packed_quantity', 'ordered_quantity')]
                assert values == sorted(values)
    states = json.loads((ROOT / 'states.json').read_text())
    edge_count = 0
    for kind, definition in states.items():
        field = definition.get('state_field', 'status')
        available = schema['$defs'][kind]['properties']['data']['properties'][field]['enum']
        assert definition['initial'] in available
        assert set(definition['terminal']) <= set(available)
        assert len({tuple(edge) for edge in definition['edges']}) == len(definition['edges'])
        for first, last in definition['edges']:
            assert first in available and last in available and first not in definition['terminal']
        for key in ('hold_from', 'same_state_updates', 'cancel_from'):
            assert set(definition.get(key, [])) <= set(available)
        edge_count += len(definition['edges'])
    samples = {r['record_type']: r for r in reversed(records)}
    invalid = []
    def bad(kind, mutate):
        value = deepcopy(samples[kind]); mutate(value); invalid.append((validator, value))
    bad('project', lambda r: r['data']['context'].update(quote_deadline=None))
    bad('boq_item', lambda r: r['data'].update(quantity=None))
    bad('quotation', lambda r: r['data']['financials'].update(subtotal=None))
    bad('boq_item', lambda r: r['data'].update(quantity='0'))
    bad('boq_item', lambda r: r['data'].update(quantity=2.0))
    bad('vendor', lambda r: r['data'].update(email='REPLACE_WITH_APPROVED_TEST_EMAIL'))
    bad('rfq', lambda r: r['data'].update(quote_deadline='2026-10-14T17:00:00'))
    bad('project', lambda r: r['data']['context'].update(delivery_deadline='2026-02-30'))
    bad('evidence', lambda r: r.update(access_token='must_never_be_a_record_field'))
    bad('purchase_order', lambda r: r['data'].update(status='CLOSED'))
    bad('approval', lambda r: r['data']['approver'].update(kind='AGENT'))
    bad('approval', lambda r: r['data'].update(approver=None))
    bad('quotation', lambda r: r['data'].update(compliance_state='CLAIMED'))
    bad('quotation', lambda r: r['data']['financials'].update(shipping='-1'))
    bad('project', lambda r: r['data'].update(status='COMPLETED', unresolved_issue_ids=['issue_demo']))
    closed = deepcopy(samples['purchase_order'])
    closed['data'].update(status='CLOSED', buyer_receipt_confirmed=True, buyer_acceptance_confirmed=True,
                          resolution_confirmed=True, buyer_confirmation_evidence_ids=['evidence_demo'])
    closed['data']['items'][0]['buyer_accepted_quantity'] = '2'
    validator.validate(closed)
    exception = deepcopy(closed); exception['data']['unresolved_exception_ids'] = ['issue_demo']
    invalid.append((validator, exception))
    for mutate in (lambda p: p.update(agents_may_approve=True),
                   lambda p: p['actions'].update(send_rfq='AUTOMATIC_AFTER_VALIDATION')):
        changed = deepcopy(policy); mutate(changed); invalid.append((policy_validator, changed))
    for index, (check, value) in enumerate(invalid, 1):
        try:
            check.validate(value)
        except ValidationError:
            continue
        raise AssertionError(f'Invalid fixture {index} ({value.get("record_type", "policy")}) was accepted.')
    print(f'PASS: {len(records)} example records, closed-order fixture, {len(invalid)} invalid cases, '
          f'{edge_count} transition edges and reviewed default policy. No runtime/provider actions.')


if __name__ == '__main__':
    main()
