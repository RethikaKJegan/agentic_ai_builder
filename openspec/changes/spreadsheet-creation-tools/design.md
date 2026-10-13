## Operations
Create a new spreadsheet with explicitly reviewed tabs and literal headers. Add missing tabs through one atomic Sheets batchUpdate; matching existing headers are reused and conflicting tabs are never overwritten. Inputs carry project_id and a stable creation_key. Bounds: twenty tabs, one hundred unique headers per tab, ten thousand rows per tab and one million requested cells overall.

## Authorization
Feature flag sheet_creation_enabled defaults false. Google Sheets edit consent, exact current Registry binding and a dedicated action gate are required. New setup nodes accept complete literal reviewed inputs, not model-selected dynamic writes. Existing nonempty write ceilings block provisioning; creation never silently bypasses optional operator restrictions.

## Recovery and ownership
Use a stable workspace/project/creation-key journal identity across runs. Reject changed inputs under that key. Retain uncertain write intents without replay. Stamp a private creation marker in Google developer metadata and persist confirmed resource IDs, project ownership and header manifests separately from future case state. Replays verify actual resources/headers. A read-only operator reconciliation command can adopt an uncertain result only when provider markers and complete manifests match the original intent.

## Write targets
Return proposed stable-identity row-write targets from the initialized headers. They are review data, not a new Registry grant. Later workflows must save and review their exact sheet_write_targets before writing rows. No creation result widens an existing workflow's permissions.

## Procurement layout
Provide BOQ, Vendors, RFQs, Quotations, Orders and Activity headers derived from the Step 1 record definitions. This helper initializes tables only; Sheets are projections, not authoritative case state. SQLite procurement persistence and agent orchestration remain later steps.

## Verification
Offline actual adapters and canonical runtime approval flows, repeated/restarted calls, conflicting existing headers, limits, ceilings, missing grant and uncertain/reconciled outcomes. Validate original contracts and file hashes. Prepare one approved live test after reload of only the extension backend.
