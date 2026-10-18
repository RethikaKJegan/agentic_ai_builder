# Data queries: Phase 5 bounded federation

Phase 6 adds background jobs and encrypted temporary results. See
[durable query jobs](cloud-query-jobs-phase6.md); the original Phase 5 arithmetic
and federation scope below remains, while its synchronous-only/no-result-storage
statements describe the historical Phase 5 release.

Phase 5 extends the existing Questions review/run flow with trusted federated
aggregation and native average finalization. The logical query contract stays the
same. Model output remains restricted metadata-bound query intent, never an
executable SQL statement or MongoDB program. Existing ownership, read/management
permissions, plan expiry, graph/review freshness, concurrency and success audit
checks still apply. Credentials and relationship review decisions are unchanged.

## Supported execution

Federation requires aggregate metrics over a PostgreSQL base and optional
same-connection PostgreSQL join prefix. The remaining join targets are complete,
bounded PostgreSQL tables or MongoDB collections. Metrics must reference only
PostgreSQL prefix fields and use addition, subtraction or multiplication, with
count/sum/average/minimum/maximum. Grouping and filters can use dimension fields.
All relationships must already be declared or explicitly accepted, and strict
many-to-one checks must pass. Multiple remote dimensions, composite keys and
remote-to-remote join chains are supported within the existing four-dataset cap.
A return to the base connection after the first remote join is not optimized.

The physical planner selects this shape only after the service validates join
pairs. Unsupported expressions, per-row division, cross-source metric operands,
projection-only federation, unsupported scalar types, MongoDB date fields and
other join shapes retain bounded application execution with a review-time reason.
The fallback is complete input execution, not a partial scan or an automatic retry
of failed federation. Arithmetic/envelope/relationship/budget failures never return
an incomplete answer.

## Correctness and snapshots

Each complete dimension is read once in its own native snapshot and reused for
validation and result merging. A PostgreSQL read-only repeatable-read transaction
then executes complete source/type checks and local strict joins, an unfiltered
frontier key domain grouped with original row counts, and filtered partial
aggregates. The key domain includes every prefix key needed by remote joins.

The coordinator checks every target key for uniqueness/non-null values and every
complete source key for a match BEFORE local or dimension filters can hide an
invalid relationship. Domain records carry original row weights, so join evidence
reports fact rows, not just the number of distinct keys. Partial states are grouped
by prefix output keys and frontier keys, joined to the validated dimension data,
filtered on dimension fields and merged into final output groups. Sorting and the
user's result limit apply only after complete merging.

Counts retain row/non-null distinctions; sums/minima/maxima retain a non-null
count so empty aggregates stay null. Average transfers sum plus non-null count
and divides once under the application's 38-digit decimal context. Partial
averages are never averaged together. The existing pushdown envelope (absolute
operand/intermediate <=1e16, at most eight fractional digits, <=1M fact rows)
keeps these partial sums exact before final division. Numeric join keys preserve
exact integer/decimal equivalence; booleans and text are not coerced into numbers.

Same-connection PostgreSQL and single-collection MongoDB averages also use exact
sum/count states and final application sorting/limit, with complete groups bounded
to 5,000 records. Per-row division remains application-only. Empty ungrouped
results produce count zero and other aggregate values null.

Separate source snapshots do not provide an atomic cross-database view. Fragment
read windows and snapshot modes are displayed, including separate reads of two
collections on the same remote connection. PostgreSQL key-domain and partial
aggregate reads share one repeatable-read snapshot. Metadata/review freshness is
rechecked between fragments and before returning results; that is not a guarantee
against row changes in other databases between their independent reads.

## Bounds and evidence

PostgreSQL facts retain the 1,000,000-row budget per dataset and 64 MB combined
projected source working-set budget. Each complete dimension, key-domain result
and partial aggregate result must fit 5,000 records. Intermediate payload transfers
cumulatively fit 2 MB; final output separately fits 2 MB and at most 500 rows.
The 45-second total deadline, per-statement database timeouts and existing MongoDB
memory/document limits remain. High-cardinality grouping/dimensions fail safely;
a selective filter does not bypass complete relationship validation.

Optional execution fragments in `queries-v1.schema.json` report source IDs,
engine, purpose, snapshot, start/finish time, duration, checked source row counts
and serialized intermediate rows/bytes. Overall federated transfer measurements
include complete dimensions, the key domain and partial states, not just final
result rows. Native average transfer measurements count partial states as well.
These are serialized data payload measurements, excluding protocol and validation
responses. Source evidence counts each dataset once; fragment evidence shows
repeated validation/aggregation reads. No SQL, credentials, row samples or results
are stored in query history or sent to the planning model. No async jobs, shared
snapshot service, result cache or cancellation endpoint is introduced.

## Verification

Verification evidence is recorded under `.local/query-federation-*` and the scoped
OpenSpec tasks. Integration tests use disposable PostgreSQL schemas in a dedicated
test database and a temporary loopback MongoDB replica set. They do not insert or
modify connected cloud data. Browser fixture tests verify presentation separately
from actual engine/service tests; they do not establish live cross-source review
acceptance.

Run the backend suite with `BUILDER_TEST_POSTGRES_DSN` pointing to an isolated
PostgreSQL database whose owner may create/drop test schemas:

```
.venv-integrations/bin/python -m pytest -q tests/test_data_query_federation.py tests/test_data_query_pushdown.py tests/test_data_queries.py tests/test_data_relationships.py tests/test_data_sources.py
```

MongoDB tests require `mongod` and start/stop a temporary replica set on loopback
port 27249. Frontend checks require the repository's Node 22 environment.

Verified and deployed on 2026-10-17: 137 backend tests, 68 frontend/domain tests,
four production desktop/mobile browser fixture scenarios, TypeScript, scoped lint,
production build, contracts and strict OpenSpec passed. Public real-model execution
returned an average over all 77 products matching independent SQL sum/count. A live
federated sales/average query checked 2,155 order details, 77 products and eight
MongoDB categories with two strict joins. All eight category totals and weighted
averages matched independent SQL plus a separate category lookup. It transferred
24 intermediate records / 2,744 serialized bytes in 11.273 seconds. The existing
accepted category relationship was used without changing reviews. Public desktop
and mobile checks passed. Evidence: `.local/query-federation-phase5/`.

Backend/frontend/worker services are active. Previous frontend build is retained
at `.local/ui-rollbacks/query-federation-phase5-20261017/.next`. Broader legacy test
suites and contributor acceptance are not claimed.
