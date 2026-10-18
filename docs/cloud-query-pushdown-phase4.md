# Data queries: Phase 4 database pushdown

Phase 5 supersedes the average/cross-connection limitations below for its explicitly
supported subset; see [bounded federation](cloud-federation-phase5.md). This file
records the original Phase 4 scope and verification.

The Questions screen now explains the physical execution strategy before Run.
The server recomputes capabilities from the saved, validated logical plan; no SQL,
Mongo program, database identifier or credential is accepted from the browser or
generated as executable model text. Existing ownership, permissions, ten-minute
expiry, graph freshness, concurrency and audit rules remain in force.

Supported same-connection PostgreSQL plans compile projection, equality/range/null
filters, strict joins, grouping, count/sum/min/max, arithmetic with addition,
subtraction and multiplication, sorting and result limits. Catalog identifiers
are quoted, filter values are bound, and text comparisons use C collation.
Runtime column types must still match the catalog. Complete target uniqueness,
non-null keys and complete source matching are checked before filters. Health
reads are rolled back before opening a read-only repeatable-read transaction;
validation and results then share its snapshot. A named cursor bounds result
fetches. Source projections have a checked row cap and a combined 64 MB database
working-set budget; work_mem is 8 MB per operation.

MongoDB single-collection plans compile projection, scalar filters, grouping,
count/sum/min/max, supported exact arithmetic, sorting and result limits into one
aggregation. Snapshot read concern requires a supporting replica set/server;
unsupported deployment configurations fail safely. Simple collation preserves
exact string comparison. Missing values become null. Runtime checks distinguish
booleans, integers, decimals and strings, rejecting type drift, arrays, objects
and non-finite numbers. Decimal fields require BSON Decimal128; binary floating
point is not silently promoted. Integer projections retain integers. An empty
ungrouped count is zero; the other empty aggregates return null. Disk use is
disabled; MongoDB's aggregation/document memory limits remain additional bounds.

Arithmetic pushdown uses an exact envelope: absolute operands and intermediates
at most 1e16 and at most eight fractional digits. Within the one-million-input-row
budget this fits both the application decimal engine and Decimal128 without
rounding a sum. Values outside that envelope stop execution without results.
Average, division, unsupported types, Mongo date fields, and cross-connection
joins use the existing bounded application executor. Cross-database early
aggregation remains deferred; complete many-to-one checks and weighted aggregates
need further equivalence coverage before that optimization can safely ship.

Database queries check up to 1,000,000 rows per dataset; fallback reads remain
limited to 5,000. Both support up to four datasets, 500 output rows, 2 MB of
serialized transferred data and 45 seconds overall. Database statements have a
maximum ten-second timeout, reduced to the remaining budget. No query is queued
beyond that synchronous window, so no background job/cancellation API is added.
Budget failures return no partial totals. Ordering among equal sort keys, or
without an explicit sort, is unspecified across execution strategies.

Additive optional `physical_plan` and `execution` objects are defined in
shared/contracts/data-sources/queries-v1.schema.json and consumed by the Zod
client. The former describes operations, snapshot mode, limits and fallback
reason. The latter reports elapsed milliseconds, result rows and their serialized
data bytes for database execution (complete input rows/bytes for application
execution). These are data-payload measurements, excluding protocol overhead and
validation/metadata responses. Source evidence reports source rows checked,
separately from result rows transferred. Row data/results are not stored in query
history or sent to the planning model. Separate databases have no shared snapshot.
Workflow/agent/tool contracts remain unchanged; no contributor signoff is inferred.

Verification completed on 2026-10-17:

- 108 backend tests across pushdown, questions, relationships and sources passed.
  Integration checks used isolated real PostgreSQL tables and a temporary MongoDB
  replica set. Each engine correctly aggregated 6,004 complete source rows into
  a single result. Tests cover nulls/missing values, decimal precision, projections,
  grouping, limits, strict joins, schema/type drift, deadlines and transfer bounds.
- 47 focused frontend/domain tests, TypeScript, scoped ESLint and isolated Next.js
  production build passed. Two production browser fixtures passed on desktop and
  mobile, including physical review, transfer evidence, clarification and layout.
- Shared contracts and strict Phase 4 OpenSpec validation passed. The broader
  legacy frontend suite is not claimed green.
- Connected MongoDB returned the independently known 91 customer documents.
  Connected PostgreSQL returned calendar-year-1997 discounted line sales grouped
  by product: all five totals matched independent SQL. Final execution checked
  2,155 order details, 830 orders, 77 products and two complete joins; it returned
  five result rows. Existing relationship review decisions were preserved.

Reproduce database tests with `BUILDER_TEST_POSTGRES_DSN` pointing to an isolated
database whose owner may create/drop test schemas, then run
`.venv-integrations/bin/python -m pytest -q tests/test_data_query_pushdown.py`.
The MongoDB tests launch a temporary replica set on loopback port 27249 and stop
it afterward. The local verification runner also creates/deletes a dedicated
PostgreSQL database and role; no cloud fixture data was inserted or changed.

The verified artifact is deployed. Public desktop/mobile browser acceptance ran
a real model-generated count through the Questions UI: 830 PostgreSQL orders,
one result row, 20 serialized data bytes, read-only repeatable-read execution.
No page errors or mobile overflow occurred. The frontend and backend services
are active; the worker remained active. Frontend rollback artifact:
`.local/ui-rollbacks/query-pushdown-phase4-20261017/.next`.
