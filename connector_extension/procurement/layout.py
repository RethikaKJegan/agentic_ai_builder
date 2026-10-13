"""Procurement table projections and a canonical approved creation workflow."""
from copy import deepcopy
from connector_extension.examples import connector_workflow

TABLE_HEADERS = {
    'BOQ': ['item_id', 'section', 'description', 'quantity', 'unit', 'specifications', 'delivery_location',
            'delivery_deadline', 'status', 'source_reference', 'project_id', 'revision'],
    'Vendors': ['vendor_id', 'vendor_name', 'email', 'item_categories', 'status', 'contact_evidence'],
    'RFQs': ['rfq_id', 'vendor_id', 'item_ids', 'scope_digest', 'quote_deadline', 'currency', 'status',
             'gmail_message_id', 'gmail_thread_ids', 'revision'],
    'Quotations': ['quotation_id', 'rfq_id', 'vendor_id', 'item_ids', 'currency', 'subtotal', 'discount', 'tax',
                   'shipping', 'other_charges', 'total_delivered_cost', 'delivery_date', 'valid_until',
                   'compliance_state', 'status', 'source_message_id', 'revision'],
    'Orders': ['po_id', 'po_number', 'award_id', 'quotation_id', 'vendor_id', 'item_ids', 'currency',
               'total_delivered_cost', 'required_delivery_date', 'expected_delivery_date', 'status',
               'tracking_references', 'buyer_receipt_confirmed', 'buyer_acceptance_confirmed',
               'resolution_confirmed', 'unresolved_exception_ids', 'gmail_thread_ids', 'revision'],
    'Activity': ['event_id', 'project_id', 'po_id', 'event_kind', 'actor_role', 'authority_state',
                 'source_message_id', 'observed_at', 'evidence_reference'],
}


def tracking_inputs(project_id, title, creation_key='tracking_book_v1', row_count=1000):
    return {'project_id': project_id, 'creation_key': creation_key, 'title': title, 'row_count': row_count,
            'tabs': [{'title': name, 'headers': deepcopy(headers)} for name, headers in TABLE_HEADERS.items()]}


def tracking_workflow(project_id, title, creation_key='tracking_book_v1', row_count=1000,
                      workflow_id='procurement_tracking_setup'):
    workflow = connector_workflow('extension_sheets_create', tracking_inputs(project_id, title, creation_key, row_count),
                                  workflow_id)
    workflow['name'] = 'Procurement tracking spreadsheet setup'
    workflow['description'] = 'After action approval create one new tracking spreadsheet with six empty header-initialized tabs.'
    workflow['metadata']['procurement_project_id'] = project_id
    workflow['approval_gates'][0]['timeout_seconds'] = 1800
    workflow['execution_policy']['limits']['timeout_seconds'] = 3600
    return workflow


def main():
    import argparse
    import json
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project-id', required=True)
    parser.add_argument('--title', required=True)
    parser.add_argument('--creation-key', default='tracking_book_v1')
    parser.add_argument('--row-count', type=int, default=1000)
    args = parser.parse_args()
    print(json.dumps(tracking_inputs(args.project_id, args.title, args.creation_key, args.row_count), indent=2))


if __name__ == '__main__': main()
