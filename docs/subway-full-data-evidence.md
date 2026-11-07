# Complete Subway query evidence

The earlier 25-row package readers are inspection tools. They are retained for old
workflows but removed from the default capability selection for new Subway questions
when the full-query feature is enabled. They no longer define the new business-answer
path. The existing v4 ontology and source bindings remain immutable.

## New workflow path

Normal chat action planning now receives the available query capability and a scoped
catalog from the current Subway metadata. It builds three ordinary workflow actions:

1. `subway.plan_query`: a metered model action that produces a strict typed query from
   the user's goal and exact catalog IDs.
2. `tool.subway_query`: a deterministic read-only executor that independently validates
   the plan against the authenticated client, pinned v4 ontology, current owned sources,
   metadata generations, scalar field allowlist and declared relationships.
3. `content.prepare`: a source-backed report using the actual query receipt and results.

Query planning uses the existing model budget/accounting; the executor makes no hidden
model calls. Tests use controlled model fixtures and never submit business data to an
external model. Normal user-initiated workflows use the already configured platform model.

## Complete data versus displayed rows

Queries examine every relevant source record. Supported predicates include equality,
inequality, numeric/date comparisons and null checks. Supported metrics include row and
nonnull counts, numeric sum/average, minimum/maximum (including dates), and grouping.
Filters apply before aggregates. The numeric executor retains decimal representations;
it does not silently round fiscal values or invent conversion rates. Monetary totals
with different or missing stored currencies must be grouped by currency or filtered to
one currency; they cannot be returned as one mixed-currency total.

Details can return up to 500 rows per page with an offset, exact total match count and
`has_more`. Aggregate output pagination limits the displayed groups, not the source
records used to calculate each aggregate. Scanned-source counts, matched counts and
result pagination are separate receipt fields. Oversized/timed-out/type-invalid queries
fail explicitly without returning a misleading partial total. Source processing budgets
remain (two million rows per source, 256 MB projected bytes, ten thousand groups and
100-second execution budget); they do not silently truncate a query.

The executor supports declared scalar many-to-one left joins, including across the two
restored databases. It reads complete target keys, rejects nonunique targets, keeps every
base record and records exact matched/missing/unmatched reference counts. Filters on
target fields can intentionally select a matched subset; coverage describes joins before
those filters. Array/fanout joins are not advertised as scalar joins because they can
multiply amounts and require an explicit grain. Arbitrary expressions, SQL, Mongo pipelines,
collection/operator injection and writes are not accepted.

Each execution has an immutable query receipt: structured query, query hash, ontology
version, source authority hash, exact coverage, source dataset/revision/generation/read
stamps and join counts. The receipt table is scoped to Subway workspace and owner.

## Actual link investigation and resolution

The investigation checked the complete data rather than the old 200-record sample.

- Finance has **213,676 stage records**. Of these, **213,665** point to an existing
  approval. **11** point to four absent approval IDs. These have no matching inverse
  `approvals.stages` reference and no matching approval reference in purchase orders,
  GRNs, invoices, budget modifications, vendor mappings or smallware PO/GRN records.
  Corresponding stage/approval service code confirms the normal native approval-ID
  lookup. The cause of absence cannot be inferred, but the stage facts remain usable:
  a left join preserves all 213,676 instead of discarding the eleven or blocking all data.
- Central has 24 app records: four originally matched properties by native ID, one
  stores its property ID as string `"5"`, and 19 have no property association at all.
  The `App.properties` schema explicitly declares Number/ref AppProperties, and numeric
  target `_id: 5` exists. The query executor resolves that link using the declared
  numeric reference and records **one normalized reference**, producing **five matched
  apps, zero dangling references and 19 absent optional associations**.

Normalization is restricted to exact safe integer strings on references whose source
model declares Number and target identity metadata is integer. Text/object identifiers
are not generally coerced. No original records were changed. Query coverage records the
conversion separately, so the previous native-ID-only ontology diagnostic remains
understandable as historical evidence rather than being overwritten.

## Verification and compatibility

Actual restored data checks include all **43,439 purchase orders**, complete counts by
status, complete amounts grouped by stored currency (two currencies), independent
native-database comparisons, a specifically filtered final-ID record beyond the first
25, the complete stage→approval left join, and the resolved app→property relationship.
A fresh controlled query-plan→query→report workflow completed with two metered model
fixture calls and one query tool call; zero external model calls and zero source writes.

Old package readers, ontology versions and published workflow pins are retained. Only
new Subway plans prefer the full-query path. Simpsons' process/data/credentials/Google
connections remain separate. No source database writes or new business action authority
are introduced. Final tests, deployment and live verification are recorded in
`openspec/changes/subway-full-data-evidence/verification.md`; private receipts are under
`.local/tenants/subway/full-data-evidence/`.
