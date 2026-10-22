- [x] Generate interconnected synthetic CSVs, schema, atomic import, SQL editor alternative, validation and reversible cleanup.
- [x] Test imports, relationship discovery, original-table preservation and cleanup against an isolated PostgreSQL instance.
- [x] Provide detailed steps, workflow baseline checklist, source-selection limitation and downloadable ZIP/CSVs.

Evidence: exports/northwind-graph-enrichment/VERIFICATION.json and START_HERE.md. Both installers, validation, rerun refusal and removal passed against an isolated PostgreSQL 16 instance. Actual CloudAdapters.postgres/build_graph discovered 17 datasets/31 declared relationships. Mock original inventory rows unchanged before/after; no live source connected. Download ZIP integrity and CSV totals checked. Strict scoped OpenSpec passes. No app code/deployment/configuration changes for this package.

## Owner-authorized Supabase create-only operation — 22 October 2026
The owner narrowed scope to creating PostgreSQL tables in Supabase only. Create the prepared dedicated schema and its 17 EMPTY tables with declared keys/indexes in one transaction, only if the namespace does not already exist. No CSV/row imports, app credential/schema-list changes, profiling, semantic inference, workflow runs, Google actions or source-table DDL/DML. Existing sources remain configured as-is. Use the saved encrypted owned Supabase connection without logging secrets; check CREATE authority and verify table/FK counts before commit.
- [x] Create empty demo schema/tables in the connected Supabase database and verify no rows imported.

Create-only live result: committed northwind_graph_demo with 17 empty tables and 31 validated foreign keys in the existing connected Supabase database. Zero rows imported; original configured source column metadata fingerprint unchanged. No connection configuration, graph refresh, workflow run or Google action. Evidence: .local/graph-enrichment-live/create-only-verification.json.

## Owner-authorized import-only operation — 22 October 2026
Import the 17 prepared CSVs into existing northwind_graph_demo tables in dependency order, in one transaction. Preserve already imported rows when all values match; refuse conflicting or unexpected existing rows rather than overwriting/deleting. Keep all foreign keys enabled. No application configuration, source profiling, graph regeneration, workflow execution or Google actions.
- [x] Load missing demo rows and validate all 928 rows/31 foreign keys after commit.

Import-only result: 920 new rows inserted, 8 existing matching manually imported business_regions rows preserved; 928 total rows across 17 tables. Exact CSV content and all 31 foreign keys verified inside the transaction and validation repeated after commit. No original tables written, application configuration/profile/graph changes, workflow execution or Google actions. Evidence: .local/graph-enrichment-live/import-only-verification.json.
