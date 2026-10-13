# Spreadsheet provisioning — Step 2

Two general tools are available in the extension catalog: `extension_sheets_create` and `extension_sheets_add_tabs`. They work with reviewed titles and header manifests, independently of procurement. They are disabled unless `sheet_creation_enabled: true` is explicitly set in the separate extension configuration and Google Sheets is enabled and connected. Restart only the extension backend after changing this flag. The existing full Sheets edit OAuth scope is sufficient; no Drive scope is added.

Both tools require a complete literal `configuration.input`, publication review and a dedicated human action approval. They do not accept mapped setup parameters. Inputs include a `project_id`, a stable `creation_key`, `tabs` (titles and headers), and optional `row_count` (default 1000). Creation additionally requires `title`; adding tabs requires exactly one `spreadsheet_url` or `spreadsheet_id`.

The bounds are 20 requested tabs, 100 headers per tab, 10,000 rows per tab and one million requested cells in total. Titles and headers must be nonblank, trimmed and unique; tab titles are compared without case. Existing tabs larger than 100 columns cannot be reused by this bounded helper. Existing headers must match exactly. A conflict stops the operation before adding any tabs. Adding missing tabs uses one atomic batch and never updates rows of an existing tab. Headers beginning with `=` are literal strings.

New spreadsheets are created in the authorized account's default Drive location. Folder selection, sharing, moving, deleting spreadsheets and deleting tabs are not implemented. Nonempty operator `sheet_writes` ceilings block provisioning; a read ceiling must permit verification of the destination, and blocks creating unknown destinations.

## Procurement layout

`tracking_inputs()` and `tracking_workflow()` in `layout.py` prepare six empty tables: **BOQ, Vendors, RFQs, Quotations, Orders and Activity**. These are spreadsheet projections of the Step 1 definitions, not a database or an autonomous procurement workflow. They do not populate records, send RFQs or schedule events.

Print a reviewable input manifest without creating anything:

```sh
.venv-integrations/bin/python -m connector_extension.procurement.layout \
  --project-id procurement_demo --title 'Procurement tracking demo'
```

Build a canonical gated workflow:

```python
from connector_extension.procurement.layout import tracking_workflow
workflow = tracking_workflow('procurement_demo', 'Procurement tracking demo',
                             workflow_id='procurement_tracking_setup')
```

Save, validate, review, publish and execute it using the existing canonical workflow API. Execution pauses before the action. Approve the exact action in the isolated UI to create the spreadsheet. Successful output contains the verified link, actual tab IDs and `proposed_write_targets`. Those targets are suggestions only: review them into a separate row-write workflow's `metadata.sheet_write_targets` before using the existing upsert tool. A tool result cannot grant itself permission.

## Retry and recovery

Within one extension state directory, the workspace/tool/project/creation-key combination identifies a durable setup intent across workflows and process restarts. Reusing that key with identical normalized inputs verifies and returns the existing resource; changed inputs are rejected. Keep the original key when retrying. A different key intentionally requests a new setup. Every runtime invocation still passes through its action gate.

The private effect journal records intent before mutation. The separate `sheet-resources.sqlite3` records ownership receipts and any returned spreadsheet ID before header verification. It is not the future procurement case database. Unknown provider results block automatic retries; markers and exact titles/headers allow an operator to reconcile an identified candidate using read-only provider calls:

```sh
.venv-integrations/bin/python -m connector_extension.reconcile_sheet_setup \
  --config .local/connector-extension/config.json \
  --tool extension_sheets_create --input-file /path/to/exact-reviewed-inputs.json \
  --spreadsheet YOUR_CANDIDATE_ID --workflow-id procurement_tracking_setup --version 1
```

For tab setup, use `--tool extension_sheets_add_tabs` and the exact original destination. Reconciliation requires a previously recorded intent and refuses changed manifests. New spreadsheet recovery requires the exact creation markers. Tab recovery verifies the exact destination and compatible headers, and records tabs without matching markers as unowned. It does not create resources or erase journal entries. After reconciliation, retry the original workflow under its normal approval gate. Do not change the key to escape an unknown outcome: that can create duplicates.

Ownership is recorded for future cleanup decisions; this step implements no automatic cleanup. Google permissions still apply. External edits and other applications can race verification, and no distributed transaction is claimed.
