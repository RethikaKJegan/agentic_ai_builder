# Data questions — Phase 3

The original-plan Phase 3 source-selection completion is documented in
[prompt-based source selection](prompt-source-selection-phase3.md). It adds
confirmed business context, source/field/join previews and completed logical-plan
evidence. Its workspace-only verification is separate from the historical release
and deployment recorded below. Later pushdown/federation/jobs documents supersede
the original executor limits and result-storage behavior described here.

Data Intelligence → Questions now generates a structured query plan from the owned
Phase 1 catalog and current Phase 2 graph. Review the fields, exact arithmetic,
filters, grouping, sorting and result limit, then select Run read-only query.
Planning itself reads metadata only. The configured OPENAI_MODEL/OPENAI_API_KEY
(and optional OPENAI_BASE_URL) are reused. Credentials and database row values are
never sent to the planning model. Results are calculated deterministically; there
is no second model call to invent an answer or summarize unavailable values.

Supported: scalar projections, equality/range/null filters, + - * / arithmetic,
count/sum/avg/min/max, grouping, sorting and up to three graph-backed equality joins
(four datasets total). count with an empty expression counts rows; count with an
expression counts non-null numeric expression results. Other aggregates ignore
null expression results. An empty ungrouped count is zero; empty sum/avg/min/max
are null. Strings compare exactly and sort using application Unicode ordering,
not database-specific collations. No DISTINCT, date bucketing, arbitrary SQL,
Mongo scripts, array/nested-field queries, outer/many-to-many joins or writes.
Unsupported or ambiguous requests require clarification or fail validation.

PostgreSQL identifiers are quoted from the catalog; the executor compiles SELECT
projections into the existing verified-TLS, read-only transaction adapter. A named
cursor fetches small batches. MongoDB compiles a field projection into find with
server/client timeouts and a row cap. BSON naive datetimes are interpreted as UTC;
zone-aware timestamps and filters normalize to UTC. PostgreSQL timestamps without
a zone retain local timestamp semantics. Date filters must use ISO values; full
timestamps are required for timestamp fields and explicit zones for UTC fields.
Decimals and integers outside JavaScript's exact integer range return as strings.
Numeric filter constants are restricted to the exact JSON integer range.

The initial executor reads the required columns of each complete bounded dataset,
then joins/filters/aggregates in memory. It does not push filters or aggregates to
the database. The limits are 5,000 rows per dataset, 2,000,000 bytes across reads,
500 output rows and a 45-second execution budget checked between batches/stages.
In-flight connections/statements also have adapter timeouts; cancellation is not
instantaneous. If an input limit is exceeded, no partial answer is returned.
The output limit applies after complete aggregation/sorting and is disclosed with
the total result-row count. Large sources need a future pushdown executor.

Only declared and user-accepted relationships are eligible. Acceptance alone is
not a validated join. Every execution reads all keys within its bounds and rejects
duplicate/null target keys and null/unmatched source keys before calculating a
result. These checks establish strict many-to-one matching for that execution;
they do not establish business meaning or permanent integrity. Rejected/proposed
edges cannot execute. Existing review decisions are preserved by this feature.

Plans expire after ten minutes, belong to their owner/workspace and bind the full
graph fingerprint (including source generations/revisions and reviews). Planning
and execution recheck freshness; changes during cloud reads discard the result.
Execution also verifies encrypted credentials remain available before each read.
Each request uses the session/origin boundary and requires both tools.read and
tools.assign. Up to four requests run per API process, one per owner/workspace.
The existing shared demo identity still shares its sources and plans.

Routes, all with existing safe envelopes and no-store headers:
- GET /data-queries: model availability and limits; requires tools.read.
- POST /data-queries/plan: {question}; returns a plan or clarification.
- POST /data-queries/execute: {plan_id}; executes the saved server plan.

Additive source-of-truth contracts: shared/contracts/data-sources/query-plan-v1.schema.json
and queries-v1.schema.json. Workflow/agent/tool contracts are unchanged.
data_query_plans stores metadata plans/questions, at most 20 per owner. Expired
records are purged on subsequent planning requests and cannot execute meanwhile.
Source row values and results are not persisted. Successful reads add audit events
without values. Results include per-dataset timestamps, metadata revisions, row
counts and join checks. Separate dataset reads do not share a database snapshot,
even when using the same connection record.

## Verification

Focused backend regression suite: 69 passing tests across data queries, data
relationships and data sources. Frontend: 33 focused tests across Questions,
Relationships and the existing proxy suite; types, scoped lint and isolated
production build passed. Both desktop/mobile fixture browser scenarios passed.
Shared contracts and strict Phase 3 OpenSpec validation passed. The known failures
in the broader legacy frontend suite remain documented in Phase 2; that full suite
is not claimed green.

Live checks used the configured model and existing Northwind sources:
- Natural-language PostgreSQL order count returned 830.
- A three-table query read 2,155 order details, 830 orders and 77 products; calendar
  year 1997 discounted line sales grouped by product returned the requested top five.
  Every total matched an independent read-only SQL aggregate.
- The real MongoDB projection reader returned 91 customers using a deterministic
  count plan. Live cross-source joins were not enabled by changing user reviews;
  cross-source behavior is covered by offline execution tests.

The verified frontend artifact was deployed and the existing frontend/API services
restarted; the worker stayed active. Frontend rollback:
.local/ui-rollbacks/data-queries-phase3-20261017/.next.

Deployed browser acceptance completed: a real model-generated order count returned
830 through the public Questions UI; desktop/mobile had no page errors or page
overflow. The final UTC timestamp handling passed the complete backend suite and
was loaded by a subsequent API restart. All three application services are active.
