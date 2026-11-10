# Unified workflow data queries — 9 November 2026

Implemented locally in agentic-ai-builder. No production deployment, live-service
restart, paid model call, Google provider write, credential modification or real
customer source mutation was performed. Existing unrelated cache/archive/screenshots
and other workspace files were preserved. Shared contracts were not changed.

## Behavior delivered

Business Investigation connected planning now discovers a generic account-scoped
query capability beside identified-case readers. The workflow can generate a typed
query without a complaint ID, submit a durable job, wait without holding an HTTP
request, and resume downstream reports/Sheets/email through existing bindings and
exact-payload approvals. A bounded correction handles a model choosing a case reader
for a no-ID population request. Single-case investigations still require identity.

Google connection selection already propagated through the UI and backend; this is
preserved. Existing goal_inputs resolves explicit recipient addresses and "email me"
using the owned selected account. No account fallback or extra confirmation added.

Query results include actual engine rows/metrics, filters, join checks, source
revisions/timestamps, warnings and explicit complete-population versus returned-row
counts. Engine aggregation is independent of display pagination. Sampled projection
is rejected as population evidence. The existing workflow report/steps UI displays
persisted progress, coverage, rows and warnings.

Read-only query submission and polling use a stable account/run/node identity.
Restart reattaches to the same durable job and reserves the tool budget once.
External effect retry/reconciliation safeguards remain in place. Every recurring
occurrence prepares an executable query afresh; recurring consent must pin the exact
reviewed query and is checked before reads. Schema/permission changes stop execution.

## Reused components

DataQueries, DataQueryJobs, Registry policy/assignment, structured OpenAI planner,
CrewAI bounded model adapter, connected action bindings, GraphRunner leases and
checkpoints, report/Sheets/email connectors, selected-account resolution, and
DurableAutomation occurrence/consent machinery. No parallel scheduler/query engine
or new database was added.

## Files

- workflow_api/workflow_queries.py — typed capability, durable job adapter, registration.
- workflow_api/data_queries.py — shared metadata catalogue and typed-plan persistence.
- workflow_api/data_source_routes.py; workflow_api/live_providers.py — installation.
- workflow_api/action_plans.py — discovery, guidance, metered query planning/correction.
- workflow_api/automation.py — exact recurring query consent.
- runtime/graph.py — durable read waits, reattachment and one-time reservation.
- runtime/action_plans.py; runtime/crew.py — typed query output and strict model transport.
- runtime/recovery.py — actionable query failure classification.
- frontend/src/features/investigations/QueryEvidence.tsx; ConnectedPlan.tsx;
  frontend/src/screens/app.index.tsx — existing prompt/result UI integration.
- tests/test_workflow_queries.py; tests/test_workflow_query_integration.py;
  tests/test_workflow_population_acceptance.py — backend regression/acceptance.
- frontend/src/features/investigations/query-evidence.test.tsx;
  frontend/e2e/workflow-queries.spec.ts; frontend/playwright.workflow-queries.config.ts.
- This OpenSpec proposal/design/spec/tasks/verification package.

## Verification

All model/provider acceptance below uses controlled transports. Real CrewAI,
Registry, graph runtime and Google adapter/journal code execute against fixture
HTTP providers. These checks do not prove live-provider delivery or unrestricted
natural-language interpretation.

- Baseline data_queries + connected_action_plans: 79 passed.
- Broader query jobs, Subway full queries, goal planning and durable automation:
  137 passed, three PostgreSQL cases initially skipped without a configured DSN.
- New query adapter/full-path/recurrence final checks: 18 passed; bounded case-reader
  correction: one additional pass.
- Separate Simpson/Subway population fixtures: 10 passed (five aggregate patterns
  per customer, 603 source rows, independently calculated expected results).
- Final combined new/core/automation regression: 56 passed (latest query/error/scope changes).
- Final engine/adapter regression after plan-identity hardening: 48 passed.
- Frontend: 40 passed; final typecheck and lint passed.
- Isolated production frontend build passed, in /tmp/unified-query-build/frontend;
  the existing frontend build output was not overwritten.
- Desktop/mobile browser acceptance: two passed. Mocked API responses verify
  no-ID prompt submission, selected account, persisted coverage and refresh.
  Initial failures were invalid/incomplete fixture account metadata and a
  case-sensitive tab selector; both corrected without loosening application checks.
- PostgreSQL: three passed against a disposable Unix-socket-only PostgreSQL 16
  cluster and non-superuser role. First run: two passed, cancellation failed because
  initdb defaulted to SQL_ASCII and returned bytes for SHOW; a UTF-8 disposable
  database resolved the setup issue. The owned cluster was stopped after checks.
- Canonical schemas/fixtures valid; strict OpenSpec validation passed; diff whitespace clean.

Logs: /tmp/unified-query-tests.log (79-test baseline),
/tmp/unified-query-final.log (48 final engine/adapter checks),
/tmp/unified-broad.log, /tmp/unified-final-backend.log,
/tmp/unified-population.log, /tmp/unified-correction.log,
/tmp/unified-recurring.log, /tmp/unified-frontend.log,
/tmp/unified-types-final.log, /tmp/unified-lint-final.log,
/tmp/unified-build.log, /tmp/unified-browser-final.log,
/tmp/unified-postgres-utf8.log.

## Supported-capability matrix

| Category | Local implementation/qualification | Limit |
| --- | --- | --- |
| No-ID workflow queries | Implemented and controlled full-path tested | Current owned metadata/relationships required |
| Numeric inclusive filters | Tested against both customer fixtures | Exact supported numeric fields only |
| COUNT/SUM/MIN/MAX/AVG | Independently verified over full matching population | Existing engine null/type/precision rules |
| Reviewed joins/grouping/sorting | Existing engine reused; relevant regressions pass | Generic strict many-to-one inner joins; no arbitrary joins/dedup |
| Query-to-report-to-Sheets-to-email | Real runtime/adapters, controlled model/HTTP | Existing exact-payload approval and selected account required |
| Restart during query | Tested | Expired/failed jobs stop rather than silently resubmit |
| Recurring fresh query preparation | Tested for two daily occurrences | Existing schedule UI/API; exact query consent |
| Account/permission changes | Rechecked before execution/result retrieval | Changes require review |
| Browser refresh/mobile | Two browser scenarios passed | Mocked API; not full live-browser acceptance |
| Data Intelligence Questions | Retained | Existing source/type/permission limitations remain |

## Five independently verified request patterns

For Simpson fixture complaints/operating_hours and Subway fixture purchase_orders/
total_amount, identical operations use the same adapter/runtime implementation:

1. Find records with measure 0–100 inclusive and count them.
2. Find records with measure 0–100 inclusive and return the minimum.
3. Find records with measure 0–100 inclusive and return the maximum.
4. Find records with measure 0–100 inclusive and return the average.
5. Find records with measure 0–100 inclusive and return the sum.

Each test compares query output against independent Decimal calculations across
603 rows, including values beyond row 500 and a missing value. This qualifies the
structured query execution semantics with controlled proposals; it does not claim
live OpenAI paraphrase accuracy. Separate controlled CrewAI tests verify workflow
generation, strict query output, report generation, actual receipt URL binding,
approval, email, restart, duplicate triggers and selected-account preservation.

## Remaining scope and release blockers

The entire original unified-intelligence specification is NOT complete:

- Natural-language recurrence is not automatically converted into a saved schedule
  and consent review. Use the existing DurableAutomation UI/API; no silent scheduling
  or inferred consent was introduced.
- Clarifications found by the outer planner reuse existing typed missing-input UI.
  A query-planning action discovering ambiguity during execution stops safely;
  restart-safe clarification/resume for that path remains to be integrated.
- Recurring relative dates ("today") require a separately reviewed relative-date
  contract; current recurring consent pins exact typed query content.
- Arbitrary joins, deduplication, conversions, custom business denominators and
  unsupported source fields are not newly enabled.
- Actual tenant metadata readiness and operating-hours semantics were not audited
  against live Simpson/Subway sources. Controlled fixtures establish integration,
  not a guarantee that every current tenant field/type is executable.
- Full frontend/backend platform suites and staging/live-provider qualification
  were not rerun. No production readiness or deployment claim is made.
- Existing final-platform-validation NOT READY decision, prior full-browser failures,
  shared-store bootstrap audit and staging/operational qualification gaps remain
  separate and unresolved.

Loading these changes in the running environment requires the operator's normal
service rollout. No live process was restarted during this task.
