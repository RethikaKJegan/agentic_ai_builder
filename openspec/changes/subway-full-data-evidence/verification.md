# Complete Subway evidence verification — 6 November 2026

## Deployed change

`BUILDER_SUBWAY_QUERY_ENABLED=1` is enabled only in Subway's dedicated backend.
Registry exposes the read-only `subway_query` connector. New action planning hides
legacy package sample capabilities and advertises metered `subway.plan_query` →
`tool.subway_query` → `content.prepare`. Existing saved workflows retain their exact
package pins/readers and v4 ontology remains unchanged. No new source write authority.

The query model receives strict structured output and the scoped current metadata
catalog. Query content is allowed only through the existing content target `query`;
account/recipient/resource authority rules remain. The runtime preserves this typed
query schema rather than rewriting it to the existing findings-analysis schema.
The executor independently checks current tenant/owner, tools permissions, source
revision/generation, pinned package, all fields, scalar relationship IDs and payload
schema. It never executes caller SQL, pipelines, operators or arbitrary collections.

## Real full-data results

A private copy of the current application store used actual read-only MongoDB sources:

- All 43,439 purchase orders counted, independently of any display limit.
- Complete amounts grouped by stored currency: 43,438 orders in currency ID 1 and
  one order in currency ID 3. Independent full native-record iteration matched the
  decimal-converted sums; native MongoDB aggregation matched all status counts.
  The final executor also rejected a mixed-currency sum without grouping/filtering.
- A specifically filtered last-ID purchase order, beyond the first 25 records,
  was retrieved with exact match count.
- Complete finance stage→approval left join: 213,676 stages retained, 213,665 matches,
  11 unmatched parents. No inverse stage link or referencing PO/GRN/invoice/budget
  modification/vendor mapping/smallware record recovers those four missing parent IDs.
  Stage model and service code confirm native approvalId lookup. No cause of absence
  is invented; existing stage facts remain usable instead of being dropped.
- App→property lookup resolved the string `"5"` to numeric 5 using the exact
  App.properties Number/ref declaration (app.model.js lines 44–47). Full coverage:
  five matches, one recorded normalization, 19 absent optional references, zero
  dangling populated references. No source records were changed.

Query results distinguish full scan, complete aggregate, exact matched count, total
result count, displayed page, has_more and left-join coverage. Detail pages can contain
up to 500 records, rather than fixing data access to the first 25. Resource/type/currency
failures return no partial total. Complete target uniqueness checks prevent joins from
multiplying amounts. Query receipts are per-execution and immutable, with query/source
hashes, ontology version, source stamps and measured coverage.

## Test evidence

- 62 affected regressions passed across full queries, connected action planning,
  dump grounding, Subway auth and Simpsons isolation.
- Final focused full-query suite: 18 passed, including complete counts/sums/averages,
  filtered late records, pagination, left joins, numeric-ref resolution, duplicate
  target rejection, wrong client/field/link denial, operator injection, stale sources,
  date extrema, empty aggregates, immutable receipts, currency separation and normal
  PO wording. These suites overlap; counts are not a distinct-test total.
- Fresh controlled workflow completed all three actual actions: plan/query/report.
  It used two bounded model fixture calls and one tool call, with normal Registry,
  runtime budgets, action bindings and schema verification. The model fixture asserted
  strict `scoped_read_query` transport. Zero external model calls/source writes.
- Independent actual-data receipt: `stage/full-query-verification.json`; final currency
  guard check: `stage/currency-verification.json`. Failed staging attempts were retained
  privately and corrected before activation (empty Mongo sort and analysis-schema
  specialization). They were never production runs.
- Shared contract schemas/fixtures, strict OpenSpec and `git diff --check` passed.

## Deployment and live checks

Before activation, private database/environment backups were created under `release/`.
Only the Subway backend configuration gained the feature flag. Registry/API checks
confirm the enabled tool, correct ontology counts (54/67/13), compilation and all four
historical package revisions. Actual foreign source IDs return 404 in both directions.
Fingerprints preserve client workflows/revisions, runs, Google accounts, metadata,
credentials and prior ontology/package documents. Simpsons backend PID is unchanged.

The public browser check exposed a frontend build mismatch: the running process
referenced webpack-c214e7193b6f0759.js, while the completed build on disk contained
webpack-1a6b38f22179e37d.js. The missing script returned 500 and prevented login React
hydration. Restarting only the frontend against its existing complete build restored
asset loading and React form handlers; no frontend source/build change was needed.
Both client login/ontology desktop/mobile results are recorded separately in
`browser-verification.json`. No paid/live-model test or user workflow was executed.

Private evidence directory: `.local/tenants/subway/full-data-evidence/`:

- `link-investigation.json`, `link-context.json`: full relationship and alternate-context checks.
- `stage/full-query-verification.json`, `stage/currency-verification.json`: real-data checks.
- `regressions-final.log`, `queries-final.log`: passing test results.
- `release/`: before-deployment SQLite/environment backups and code fingerprints.
- `preservation-before.json`, `live-verification.json`: live capability/isolation and preservation.
- `browser-verification.json` and screenshots: hydrated public client pages.

## Scope

Supported full-data operations are filters, grouping, counts, numeric sums/averages,
min/max (including dates), scalar many-to-one left joins and detail pagination. Explicit
processing/result budgets and array/fanout restrictions prevent misleading partial or
multiplied totals. This does not execute arbitrary SQL, restore nonexistent parents,
invent fiscal rounding/conversion policy, or enable archived business write actions.
Live AI interpretation remains the user's own chat test as previously requested.
