# Northwind graph enrichment — detailed import guide

This download contains 17 related tables, 928 synthetic rows and 31 declared PostgreSQL foreign keys. One new table normally adds only one main dataset/entity; the interconnected tables create a much richer, inspectable schema graph. Row count is not graph node count: the application principally draws entity types and relationships, not 928 individual records.

## 1. Understand what is preserved

All new objects are inside `northwind_graph_demo`. The installer creates no objects in `public`, `northwind`, or your existing application schema. It does not update, delete, truncate, rename or add constraints to original tables; change search_path or roles; add triggers; or touch MongoDB, Google credentials or saved workflows. There are no stock balances, incoming quantities, purchase orders, lead-time scores, prices, sourced risks or ranking inputs. Every table has `is_demo = true` and explicit synthetic provenance. Any certification or approval is labelled `illustrative_only`, not an actual business claim.

There are deliberately NO foreign keys into live Northwind products/suppliers/categories. This avoids assuming where those records live and avoids fabricating business relationships. The new tables form their own connected cluster alongside the existing graph, not verified extensions of Northwind operational entities. They model regions, facility types, handling, packaging, transport, supplier sites, warehouses, lanes, inspections and illustrative associations.

**Important application limitation:** the current app uses discovered metadata in automatic source selection. A separate schema, demo table names, comments or `is_demo` flags are NOT an enforced graph-only exclusion. They prevent writes to original tables, but cannot guarantee identical future planning if you expose these sources in the same workflow workspace. Filtering a graph to one connection is not a planner exclusion rule. No such exclusion code has been added.

For the strongest workflow isolation, keep these demo sources in a separate test app instance/workspace that the production workflow cannot discover. That instance can use a new read-only account for this same PostgreSQL database/schema. This does not require another database engine. If the current installation only exposes the shared workspace, do not assume a workspace switch exists: use a test instance or the conditional same-workspace checks in step 8. Showing all new sources inside the original workspace while guaranteeing identical source selection would require an explicitly enforced graph-only feature, which is outside this data package.

## 2. Save the baseline before importing

1. Leave the current PostgreSQL and MongoDB connections connected. Record their connection IDs, configured schemas and successful metadata revision. Do not delete/reconnect existing sources just to add a schema.
2. Keep the original prompt below exactly as-is. Save a screenshot/export of the current five priorities, quantities, incoming-stock calculation, categories, suppliers, source paths and ranking reasons from the same fixed data snapshot. Use existing read-only results where available.
3. Record existing pending approvals. Do not approve/create a Sheet, send mail or book a meeting just to test this import.
4. If a saved approved/published workflow exists, keep its ID/version and source bindings. Do not regenerate or overwrite it during graph setup.
5. This package cannot freeze source databases or external websites. A later run can differ because actual stock, incoming stock or web information changes; compare against the same snapshot and settings.

### Original prompt — unchanged

> Review Northwind’s top five restocking priorities, accounting for incoming stock; include categories, suppliers and ranking reasons.
> Add sourced web supply risks separately in a new Google Sheet.
> Email the briefing and Sheet link to my connected Google inbox and include both in a review on 23 October 2026, 3:00–3:30 PM IST; get separate approval before creating the Sheet, sending email and booking the meeting.

The date remains 23 October 2026 and the meeting remains 3:00–3:30 PM IST (09:30–10:00 UTC). Synthetic records in this package must never be described as sourced web supply risks.

## 3. Download, extract and inspect

Extract the complete import kit. Keep its `csv` subfolder beside the numbered scripts. Do not mix the two installation methods below: choose A or B.

Files:

- `manifest.json`: exact table names, columns, row counts and declared FK counts.
- `csv/`: 17 UTF-8 CSV files with headers, one file per table.
- `01_create_schema.sql`: schema/table/constraint creation, no data; use inside a transaction.
- `02_setup_and_load_sql_editor.sql`: complete, atomic SQL-editor installation. The CSV data is embedded as INSERT statements for clients without CSV import support.
- `03_import_all.psql`: complete atomic CSV installation using psql; automatically creates the schema, loads the CSVs in dependency order and validates the result.
- `04_validate.sql`: read-only validation and counts; raises an error for missing/wrong rows or FK coverage.
- `06_readonly_access_template.sql`: optional grants to a role you already manage; edit the placeholder first. Not executed by either installer.
- `90_remove_demo_schema.sql`: optional removal of only the 17 demo tables/schema, in dependency order, without CASCADE.
- `relationship_guide.csv`: human-readable FK-to-business-label suggestions, not an extra database table. Do not import it.
- `VERIFICATION.json`: isolated PostgreSQL 16 and actual project metadata/relationship discovery test results.
- `generate_package.py`: optional deterministic regeneration; no DB connection.

## 4. Check the target database (read-only)

Use the PostgreSQL database where you want the demo schema. A database-owner/import account must be able to create schemas and tables. The app should continue using a read-only account.

Run in your SQL client:

```sql
SELECT current_database(), current_user, version();
SELECT schema_name
FROM information_schema.schemata
WHERE schema_name IN ('northwind_graph_demo', 'northwind', 'public');
```

If `northwind_graph_demo` already exists, stop and inspect it. The installers intentionally fail rather than merging with or replacing existing objects. No `DROP SCHEMA` is part of installation. Do not remove a schema that somebody else created.

For Supabase, use a PostgreSQL connection supplied by your project’s Connect panel, with the database name and supported direct/session-pooler settings. Use TLS when connecting remotely. Do not paste passwords into chat or into these files.

## 5A. Import all CSVs with psql (recommended when using CSV)

Install/open the PostgreSQL `psql` client on the computer holding the extracted files. Your cloud database server does not need access to your local CSV files: `\copy` reads them on the psql client.

1. Open a terminal in the extracted import-kit directory. It must contain `03_import_all.psql` and `csv/`. File paths in `\copy` resolve from this working directory.
2. Replace `YOUR_HOST`, `YOUR_PORT`, `YOUR_IMPORT_USER` and `YOUR_DATABASE` below. `-W` asks for the password interactively.

```bash
psql -X -h YOUR_HOST -p YOUR_PORT -U YOUR_IMPORT_USER -d YOUR_DATABASE -W -v ON_ERROR_STOP=1 -f 03_import_all.psql
```

For a remote TLS connection, set `PGSSLMODE=require` (or your organisation’s stricter verified TLS configuration) in the terminal before running psql. PowerShell uses `$env:PGSSLMODE = "require"`; bash uses `export PGSSLMODE=require`.

3. Expect CREATE TABLE/CREATE INDEX messages, 17 COPY counts, a validation result and final `COMMIT`. The expected table counts are in the manifest and section 10.
4. If any command fails, stop. ON_ERROR_STOP and the open transaction prevent a partial committed installation when the psql process exits. Fix the reported connection, permission or missing-file problem before retrying. Do not issue COMMIT after a failed statement.
5. Do not execute `01_create_schema.sql` first when using this installer: it is included automatically.

`\copy` is a psql command, not ordinary SQL. It will not run in a web SQL editor.

## 5B. Alternative: Supabase SQL Editor, pgAdmin Query Tool or DBeaver SQL editor

If you prefer a graphical tool:

1. Open your target database’s SQL editor.
2. Open/copy **the entire `02_setup_and_load_sql_editor.sql` file** into a new query.
3. Execute it as a single script/batch, including BEGIN and COMMIT. Do not execute only a selected fragment.
4. Check the table counts and successful COMMIT. This performs the same installation as the CSV route; all input rows are embedded in this file.
5. If the client leaves a failed transaction open, issue `ROLLBACK;`. Resolve the failure before retrying the entire file.

The 17 CSVs remain available for review or manual import if you want them. For a manual CSV import, create tables first with `BEGIN;`, the contents of `01_create_schema.sql`, then `COMMIT;`; import each manifest entry in listed order with CSV format, header on, UTF-8 encoding, comma delimiter and matching columns. The manual multi-step path is not atomic across GUI imports; prefer A or B for reliable setup. Foreign keys must stay enabled.

## 6. Validate and grant read-only visibility

Run the whole `04_validate.sql` file in a new query. It is read-only: it should pass and list 17 table counts totalling 928.

Check foreign keys separately:

```sql
SELECT count(*) AS validated_foreign_keys
FROM pg_constraint c
JOIN pg_namespace n ON n.oid = c.connamespace
WHERE n.nspname = 'northwind_graph_demo'
  AND c.contype = 'f' AND c.convalidated;
-- Expected: 31
```

If your app’s existing read-only role cannot see this new schema, an administrator can edit and run `06_readonly_access_template.sql`. This grants USAGE/SELECT only on the new schema’s objects, not write access. Do not replace the existing role’s privileges or change the original schema grants. Do not expose the demo schema in a public REST API just for metadata profiling; the app uses a PostgreSQL connection.

## 7. Discover the graph without disconnecting databases

### Strict isolation route

In a test instance/workspace, add a PostgreSQL connection scoped to `northwind_graph_demo` only, using a read-only account. Leave the production workflow workspace and its connections as-is. The currently running app accepts Supabase PostgreSQL endpoints in its connection form; generic local PostgreSQL discovery would require adapter configuration/code work, which this package does not do.

### Same-workspace route — conditional, not guaranteed identical planning

If you choose to show the new cluster in the same workspace:

1. Open **Data Intelligence → Connections**.
2. On the existing PostgreSQL connection, choose **Edit connection**. Record its ID and original schema list first. The form may require re-entering its URI; use your existing connection details privately.
3. Keep every existing schema selected/listed, and append `northwind_graph_demo` to the Schemas field. For example, if it currently says `northwind,public`, use `northwind,public,northwind_graph_demo`. Do not replace the list with the demo schema alone.
4. Use **Test connection**, then **Save and profile**. Keeping this existing connection ID preserves the source identity for the original qualified tables; compare original table/field IDs afterwards. This does not prove cached query grants remain valid: refreshes can invalidate metadata-dependent plans, so review/revalidate them if the app requests it.
5. Wait until profiling succeeds. Existing snapshots remain available until a successful replacement. If the schema was already configured, use **Refresh metadata** instead.
6. Under **Metadata**, confirm the original tables are still present and exactly 17 new tables are discovered in `northwind_graph_demo`.
7. Open **Semantic Intelligence** and use **Regenerate Semantic Intelligence**. Wait for completion, then inspect the new nodes/edges and FK evidence. You may see inferred labels or relationships requiring review; an FK proves a structural link, not business truth.
8. Use `relationship_guide.csv` for suggested readable labels. Review only the new demo mappings if necessary. Do not rename/merge original Northwind entities or accept unverified joins to operational sources merely to connect the clusters. Label visibility/count depends on model configuration, mapping reviews, graph filters and application limits; not every CSV row becomes a visible node.

This installation uses 17 additional datasets. The current adapter profiles at most 100 tables/views per connection and has time/field bounds. If the expanded scope exceeds these bounds, original tables could be omitted from the new snapshot. Check dataset counts/warnings before proceeding; use the isolated route or a separate read-only principal/connection with a deliberately limited scope instead. A second connection in the same workspace is still not a planner exclusion, and a duplicate endpoint/account may be deduplicated.

## 8. Check the unchanged workflow before any approved external writes

Keep the prompt verbatim. Inspect planning/source selection in a test or dry-run/review stage that does not execute external actions; do not launch an existing active run solely to obtain a comparison.

Required checks:

- The selected restocking sources remain your original Northwind products/inventory/incoming-stock sources, category source and supplier source. No `northwind_graph_demo` table is used for stock, incoming stock, ranking or sourced web evidence.
- Original source IDs, joins, incoming-stock treatment, five-item ranking and reasons agree with the recorded baseline for the same data snapshot. A separate FK demo must not multiply operational product rows.
- Web risks have actual source URLs and remain separate from the inventory result. Synthetic certification/site rows are not web supply risks.
- Sheet creation, email sending and Calendar booking still have three distinct approval gates. No approval is inferred from importing data or opening the graph.
- The briefing and actual Sheet link are planned for the connected inbox and for 23 October 2026, 3:00–3:30 PM IST. Do not substitute demo addresses or links.

If a demo source appears in a restocking plan, do not approve or execute that plan. Restore the app’s original schema list on the SAME saved connection, save/profile, regenerate metadata and re-check the baseline. The demo tables can remain physically in PostgreSQL without being discovered by that connection, provided their schema is excluded. If all-schemas discovery is enabled, narrow it explicitly. Replanning with a wider metadata context is not guaranteed deterministic even when the prompt is unchanged.

## 9. Optional removal/rollback

You do not need to delete demo data to restore original discovery: remove only `northwind_graph_demo` from the app’s configured schema list and refresh. Do not disconnect or delete existing connections.

If you also want to remove the new database objects, inspect `90_remove_demo_schema.sql` and run the whole file once against the database where you imported the kit. It drops only the 17 demo tables/schema, in reverse dependency order. It contains no CASCADE and no original-table references, so unexpected external dependencies cause failure rather than being deleted. Refresh the app metadata after cleanup. Historical graph snapshots may still be retained by the app; cleanup does not delete workflow history.

## 10. What was verified and what was not

Verified against a fresh, Unix-socket-only PostgreSQL 16 test instance:

- CSV/psql import and SQL-editor installer both succeed.
- All 928 rows and 31 foreign keys validate; provenance flags are present.
- The project's actual PostgreSQL metadata adapter discovers all 17 datasets, and its relationship builder discovers all 31 declared relationships.
- A pre-existing mock Northwind inventory table retains identical values after install and removal.
- Re-import into an existing demo schema fails instead of modifying it.
- Removal without CASCADE succeeds and preserves the mock original source.

No live PostgreSQL, MongoDB, Google tools, workflow run or deployed graph was changed or tested. This evidence establishes package/import and discovery behaviour in the isolated fixture, not a zero-error guarantee for your live workflow or exact semantic labels.

Official import reference: https://www.postgresql.org/docs/current/sql-copy.html

### CSV contents and import order

| Order | Table / CSV | Rows | Foreign keys |
|---|---|---:|---:|
| 1 | business_regions.csv | 8 | 0 |
| 2 | facility_types.csv | 5 | 0 |
| 3 | handling_protocols.csv | 8 | 0 |
| 4 | packaging_materials.csv | 8 | 0 |
| 5 | packaging_profiles.csv | 24 | 2 |
| 6 | certification_standards.csv | 10 | 1 |
| 7 | transport_modes.csv | 5 | 0 |
| 8 | material_families.csv | 12 | 1 |
| 9 | supplier_sites.csv | 48 | 3 |
| 10 | warehouses.csv | 24 | 3 |
| 11 | inspection_checklists.csv | 32 | 2 |
| 12 | distribution_lanes.csv | 72 | 4 |
| 13 | site_certifications.csv | 144 | 3 |
| 14 | warehouse_capabilities.csv | 96 | 3 |
| 15 | material_packaging_rules.csv | 96 | 3 |
| 16 | lane_site_assignments.csv | 144 | 3 |
| 17 | site_material_approvals.csv | 192 | 3 |
