## Why
Procurement automation needs to create its own tracking spreadsheet and tabs, rather than requiring manually prepared destinations. Existing Sheets tools only discover/read/upsert records.

## What Changes
Add extension-only opt-in create-spreadsheet and add-tabs tools, bounded literal-header setup, a six-tab procurement layout helper, private resource ownership receipts and operator reconciliation. Preserve current action gates, source data and canonical contracts.

## Impact
Only connector_extension files and this change. No original source or shared schema changes. No automatic procurement worker or case database. A live creation workflow is prepared only after offline verification and pauses before provider mutation.
