# Production reliability and investigation UI — 6 November 2026 (IST)

**Implemented and tested in controlled development infrastructure. Not deployed,
live-provider verified, multi-host verified or production-qualified.**

The starting branch was `agentic_ai_builder`, HEAD
`1244201e87cb2968c53bbda8290c4df91574577e`. Prior Phase 1/2 changes, original
archives and concurrent Subway ontology/query work were preserved. Repository
instructions, contributor ownership/handoff, attached Phase 3 requirements and
prior foundation/distributed verification evidence were inspected. No shared
canonical workflow/agent/tool contract was changed. No production service was
restarted or migrated; no paid model call, source write, real email or external
resource creation was performed.

## Existing components and implemented changes

| Component | Existing behavior reused | Phase 3 change / verification |
| --- | --- | --- |
| Runtime/Registry | Durable claims, live leases, fencing, dispatch revalidation, budgets, connector journals | Shared provider/credential windows and protected account slots use existing serialized transactions; actual tool dispatch resolves trusted credential references. |
| PostgreSQL | Restricted-role schemas, adapter and migration fixtures | Actual backend termination, unavailable database during effect completion, lock timeout, detected deadlock and pg_dump/restore drills. Shutdown states `57P01/57P02/57P03` now classify as temporary unavailability. |
| Graph/ontology | Owner projections, immutable revisions, source mappings, semantic reviews, exact pins | Singleton bounded polling through existing authorized readers; changed evidence creates revisions, failed/revoked reads mark stale without overwriting a concurrently newer head; unchanged preparations preserve historical hash semantics and pins. |
| Human recovery | Existing case/approval/clarification/event waits and recovery service | Restored the actual quiesced fixture main/auxiliary SQLite stores during a graph-grounded event wait, reconstructed services and completed without repeating approved sends/reports. |
| Investigation UI | Existing workflow/task graph, agents, receipts, approvals, memory, resume/cancel | Existing knowledge and memory drawers now display bounded pinned graph references, predicates, freshness, actual reconciliation evidence and admin alert status. No new execution authority. |
| Monitoring | Runtime events/traces, worker health, storage metrics | Tested deterministic scoped alerts for backlog, unavailable workers/components, failed/dead-letter runs, uncertain outcomes, stale graphs and recognized model/connector failures; admin-only diagnostics. No external alert delivery. |
| Backup/migration | Existing SQLite snapshot/online backup and PostgreSQL tooling | Full table-dump equality for restored fixture stores, preserved events/approvals/checkpoints/receipts/graph versions, PostgreSQL isolated-schema restore and current migration regressions. |

### Confirmed defects and test-harness issues

1. Actual PostgreSQL backend termination produced a shutdown SQLSTATE that was not
   retryable. The connection-loss test failed; error classification was corrected
   without authorizing invocation replay. The corrected reliability suite passed.
2. Polling a new but identical preparation could create needless graph revisions
   because preflight identity changes. The unchanged-content comparison retains
   the old hash definition and refreshes the original pin only when every other
   hashed field agrees. Existing historical graph hashes were not redefined.
3. Existing saved-workflow browser fixtures still expected the retired overview
   composition-job generation path. They now enter the saved workflow directly;
   real prompt generation remains covered by the actual orchestration server.
4. The lifecycle browser fixture assumed every bounded driver stop was an approval
   wait. It now issues another explicit UI command after a persisted budget stop,
   retaining all server budgets. Both desktop/mobile lifecycle checks pass.
5. An initial browser invocation used the generic test server instead of the
   dedicated lifecycle/orchestration configurations. Correct configurations fixed
   unavailable test endpoints. Two subsequent orchestration failures came from
   parallel Playwright runs deleting the same artifact directory; separate output
   directories resolved them. Final eight orchestration checks passed.
6. Initial restore fixtures missed the journal directory and used an unsuitable
   pg_dump connection environment. Fixture setup was corrected, not product
   security. An outage assertion incorrectly expected the internal error code in
   the public run envelope; it now reads the persisted scoped error field.
7. A polling authentication exception could stop the whole batch, and a failed
   old poll could mark a concurrently refreshed revision stale. Authentication
   lookup is now inside per-projection handling and failure invalidation is fenced
   to the selected revision. Both race/revocation regressions pass.
8. Final load measurement now aggregates parent and child transaction metrics.
   Preliminary process runs reported only the parent counters. Reproduction labels
   now identify PostgreSQL versus SQLite correctly; final artifacts use both fixes.

## Exact verification evidence

Counts below are per command, **not summed across overlapping suites**. Subtests
and repeated runs are not additional distinct cases. Earlier failed attempts are
retained in `/tmp` logs and are not described as passing. The Phase 1/2 reports
remain historical and unchanged.

All backend commands use:

```sh
PYTHONDONTWRITEBYTECODE=1 .venv-integrations/bin/python -B -m pytest -q -p no:cacheprovider
```

Each command appends the listed modules and `--basetemp /tmp/NAME`, redirecting
stdout/stderr to `/tmp/NAME.log`.

| NAME | Modules | Final result |
| --- | --- | --- |
| `phase3-runtime-graph` | `tests/test_runtime.py tests/test_dynamic_delegation.py tests/test_delegated_tools.py tests/test_foundation_fault_tolerance.py tests/test_process_recovery.py tests/test_distributed_execution.py tests/test_phase2_workers.py tests/test_production_reliability.py tests/test_knowledge_synchronization.py tests/test_account_knowledge.py tests/test_account_knowledge_api.py tests/test_distributed_configuration.py` | 184 passed; 18 subtests; 239.69s |
| `phase3-domain-acceptance` | `tests/test_production_acceptance.py tests/test_distributed_acceptance.py tests/test_foundation_acceptance.py tests/test_account_knowledge.py tests/test_agent_memory_recovery.py tests/test_simpsons_client_isolation.py tests/test_subway_client_auth.py` | 69 passed; 455.45s |
| `phase3-postgres-regression` | Nine core PostgreSQL modules listed below | 157 passed; 23 subtests; zero skips; 508.80s |
| `phase3-postgres-qualified` | `tests/test_production_postgres.py tests/test_distributed_postgres.py` | 21 passed; zero skips; 22.30s; includes PostgreSQL synchronization/revocation |
| `phase3-outage-qualified` | `tests/test_production_outage.py` | 1 passed; zero skips; 4.26s |
| `phase3-reliability-final` | `tests/test_production_reliability.py tests/test_knowledge_synchronization.py tests/test_distributed_configuration.py tests/test_account_knowledge_api.py` | 15 passed; 24.44s; final API limits, polling revocation/races and actual shared tool dispatch |
| `phase3-quality-evaluations` | `tests/test_semantic_kg.py tests/test_business_investigations.py tests/test_adaptive_orchestration.py` | 66 passed; 315.12s |

Later source/API changes were checked by the final focused suites; the entire
repository was not tested. There is no aggregate all-repository test claim.

### PostgreSQL environment and outage boundaries

The existing private Phase 2 PostgreSQL 16 cluster under `/tmp/builder-phase2-pg-*`
was restarted on its original Unix socket and port 55437 with TCP listening
disabled. No unrelated database/service was stopped. Tests use the dedicated
`builder_test` role without superuser/createdb/createrole and unique disposable
schemas. The test DSN was loaded privately from
`.local/phase2-verification/postgres.json` into `BUILDER_TEST_POSTGRES_DSN`.
No production DSN was read or used.

The nine core module arguments:

```text
tests/test_phase2_postgres_concurrency.py tests/test_postgres_backend.py tests/test_durable_automation_postgres.py tests/test_generic_lifecycle_postgres.py tests/test_phase3_postgres_actions.py tests/test_phase4_postgres_journey.py tests/test_phase5_postgres_state.py tests/test_phase6_postgres_runtime.py tests/test_phase2_migration.py
```

PostgreSQL runs use a Python wrapper which privately sets the test DSN then calls
`pytest.main(['-q','-p','no:cacheprovider', *modules, '--basetemp', path])`.
The outage command additionally sets `BUILDER_DISPOSABLE_PG_ROOT` from that same
owned-cluster metadata. Its fixture checks the exact private path/socket/port,
then stops/restarts only that instance. Other PostgreSQL suites ran after this
downtime drill, not concurrently with it.

The outage happens **after a controlled provider effect and before checkpoint**.
The database is brought back, the 30-second lease is expired using the test clock,
and restart blocks `UNKNOWN_INVOCATION_RESULT`; the provider invocation count
remains one. The drill asserts <30 wall-clock seconds, but uses a 31-second fake
lease advance. This does not establish a real-time production RTO.

A separate connection is terminated with the restricted role's own
`pg_terminate_backend`; the incomplete transaction rolls back and the next
transaction succeeds. Actual lock timeout and PostgreSQL-detected deadlock are
classified correctly. The existing global advisory write lock remains in place.
Network partitions, host failure and physical storage loss were not reproduced.

The PostgreSQL backup test dumps/restores only its own `check_*` schema using
pg_dump/pg_restore and compares retained run, event and graph documents. The
SQLite acceptance uses the existing online snapshot helper, adds a disposable
probe after backup, restores each main/auxiliary store, checks complete SQL-dump
equality and integrity, then reconstructs case/runtime/automation and resumes the
same event wait. This is a quiesced consistent fixture set, not a production
cross-store online-backup consistency proof.

## Sustained load

Reproduction commands:

```sh
PYTHONDONTWRITEBYTECODE=1 .venv-integrations/bin/python -B -m tests.production_load_benchmark
# With BUILDER_TEST_POSTGRES_DSN privately set to a disposable test database:
PYTHONDONTWRITEBYTECODE=1 .venv-integrations/bin/python -B -m tests.production_load_benchmark --postgres
```

Each point uses **96 approved jobs**, real runtime/Registry/store transactions,
separate worker processes, a 150ms controlled provider and independent durable
provider-effect ledger. Both SQLite and PostgreSQL runs enable server controls
and fair polling. Each backend executes 288 jobs over its one/two/four-process
points. Test targets fixed before measurement: zero lost/duplicate jobs,
completion within 180s, P99 ≤120s. These are controlled engineering targets,
not customer-agreed SLOs. Planning/approval setup is outside execution latency.

| Store | Processes | Jobs/sec | P50 s | P95 s | P99 s | Average queue wait s | Aggregate lock wait s |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| SQLite | 1 | 2.548 | 18.693 | 35.650 | 37.497 | 18.274 | 0.446 |
| SQLite | 2 | 3.658 | 12.077 | 24.896 | 25.989 | 12.197 | 9.558 |
| SQLite | 4 | 7.107 | 6.918 | 12.853 | 13.270 | 6.731 | 23.347 |
| PostgreSQL | 1 | 3.237 | 14.645 | 28.326 | 29.545 | 14.676 | 0.302 |
| PostgreSQL | 2 | 5.046 | 9.523 | 18.195 | 18.882 | 9.425 | 5.073 |
| PostgreSQL | 4 | 6.288 | 6.895 | 14.467 | 15.004 | 6.817 | 21.083 |

All final points met the predeclared targets with zero lost jobs, duplicate
effects, retry events or database transaction failures. Four versus one process
improved throughput about 2.79× on SQLite and 1.94× on PostgreSQL in this run.
The four-process PostgreSQL measurement includes 21.08 aggregate seconds of lock
wait across processes; serialization remains a demonstrated scaling cost.

Final JSON artifacts: `evidence/sqlite-process-load.json` and
`evidence/postgres-process-load.json`, copied from
`/tmp/phase3-load-qualified.json` and `/tmp/phase3-pg-load-qualified.json`.
They contain queue wait, average latency, provider busy fraction, retry/effect
counts and aggregated transaction/lock-wait metrics. Child counters subtract
inherited parent values; the aggregate includes parent setup plus child execution.
Busy fraction measures provider time, not OS CPU utilization. The PostgreSQL
workflow store is real; the provider-double ledger is SQLite. Runs shared one
development host with other tests and are not statistically isolated benchmarks.

The separate fair-polling and shared/reserved-capacity tests verify that an
account backlog cannot consume configured protected slots or exhaust another
account's provider allowance without the configured shared bucket. This is not
multi-host reserved CPU or an account fairness SLO under arbitrary workloads.

## Domain and quality acceptance

**Simpson:** existing generic planner/compiler, ontology preparation, graph,
working memory, actual CrewAI, exact-payload report/send approvals, durable event
wait and duplicate-event rejection. Controlled model/HTTP transports provide
explicit fixture evidence. One scenario kills a waiting worker, restores all
fixture stores and reconstructs services before completing without repeating the
completed effects. The prior three-day human/event-wait acceptance also passes;
graph-enabled execution does not bypass freshness expiry or silently repin.
Trace: `/tmp/phase3-domain-acceptance/` under the production acceptance test's
fixture directory, `phase3-restored-acceptance-trace.json`.

**Subway:** supported revision-2 package reads cover stores, vendors and purchase
orders through the same Registry/runtime/delegation machinery, graph snapshots
and execution memory. A separate provider-selection-to-actual-CrewAI test checks
package graph grounding. Controlled rows are explicitly fixtures, not real company
findings. No policy or record join is invented. Current concurrent Subway v4/full
query changes are not attributed to this phase or universally qualified by these
revision-2 tests.

| Evaluation | Expected result / evidence |
| --- | --- |
| Citation validity and source accuracy | Existing investigation tests reject unsupported references/output shapes and retain source-backed results. |
| Missing/contradictory evidence | Missing inputs wait explicitly; conflicts remain conflicts; no inferred approval or completeness. |
| Semantic graph meaning | Invented IDs, references, generic predicate claims and ungrounded confidence are rejected; changed evidence removes current review validity. |
| Coordination and tool correctness | Actual Registry/CrewAI fixtures require dependencies and exact prepared tool resources; premature completion/unauthorized operations fail. |
| Memory relevance | Owner/account/pin scoping and validated experience gates remain enforced; historical execution is not a business fact. |
| Adaptive recovery | Missing evidence can add a read, revisions preserve completed effects and invalidate changed approval scope, uncertain writes block replanning. |

These are deterministic expected-outcome evaluations using controlled model
responses, including the existing structured OpenAI evaluator adapter. They do
not score live-model business judgment, arbitrary prompts, or compare quality
across live model releases. That subjective/provider acceptance remains open.

## Frontend verification

Commands run from `frontend` with Node 22.23.3 in PATH:

```sh
npm test -- --reporter=dot
npm run typecheck
npm run lint
npm run build
BUILDER_E2E_FRONTEND_DIR=/home/raf/agentic-ai-builder/frontend npm run test:e2e -- --config=playwright.lifecycle.config.ts e2e/dynamic-investigation.spec.ts e2e/business-lifecycle.spec.ts --output=/tmp/phase3-lifecycle-browser-results
BUILDER_E2E_FRONTEND_DIR=/home/raf/agentic-ai-builder/frontend npm run test:e2e -- --config=playwright.orchestration.config.ts --output=/tmp/phase3-orchestration-browser-results
BUILDER_E2E_FRONTEND_DIR=/home/raf/agentic-ai-builder/frontend npm run test:e2e -- --config=playwright.lifecycle.config.ts e2e/dynamic-investigation.spec.ts --grep 'pinned graph' --output=/tmp/phase3-panel-qualified-results
```

Final unit suite `/tmp/phase3-ui-qualified.log`: **533 passed in 82 files**, 41.02s.
Final types/lint logs: `/tmp/phase3-types-complete.log`,
`/tmp/phase3-lint-complete.log`, both pass. Final production build:
`/tmp/phase3-build-qualified.log`, passed, no deployment.

Browsers: **10 passed** in the lifecycle/saved-investigation run (4.9m), **8 passed**
in the real-backend orchestration run (4.0m). After the final authority-state
clearing build, **2 overlapping desktop/mobile panel checks passed** (12.9s).
Screenshots in `evidence/reconciliation-{desktop,mobile}.png` show the actual
rendered inspector; mobile checks wait for the drawer transition to settle.

Covered: persisted task/agent/tool state, review-before-execution, actual controlled
receipts, refresh/navigation, cancellation, missing information, recurring consent,
revoked selected account, no identity substitution, graph version/freshness,
reconciliation references and no eligible-resume control for an uncertain outcome.
The existing permission mechanisms govern actions. Failed reads never render as
successful progress. No hidden model reasoning is exposed.

Not every repository Playwright configuration was executed. The first generic
configuration attempt had 13 failures/5 passes; the first proper lifecycle attempt
had four fixture failures/6 passes; the first orchestration run had two artifact
collisions/6 passes. Corrected clean runs above replace them as acceptance evidence.
Expected controlled error scenarios also emit redacted database/binding warnings.

## Files attributable to Phase 3

Source:

- `workflow_api/resource_limits.py`: trusted shared windows and protected capacity.
- `runtime/graph.py`, `runtime/delegation.py`: credential reference propagation.
- `workflow_api/postgres.py`: shutdown availability classification.
- `workflow_api/knowledge_sync.py`, `workflow_api/live_providers.py`: bounded singleton polling.
- `workflow_api/account_knowledge.py`: unchanged-read pin preservation.
- `runtime/recovery.py`: graph freshness/authority failure categories.
- `workflow_api/operational_alerts.py`, `workflow_api/main.py`: scoped alerts, admin guards, bounded run knowledge.
- `frontend/src/api/{client,reliability}.ts`, `frontend/src/features/investigations/{CompositionPanels,ReliabilityEvidence}.tsx`: existing UI/API integration.

Tests/tooling:

- `tests/test_production_reliability.py`, `test_production_postgres.py`,
  `test_production_outage.py`, `test_knowledge_synchronization.py`,
  `test_production_acceptance.py`, additions to `test_account_knowledge.py`.
- `tests/production_load_benchmark.py`, existing `tests/worker_scaling_benchmark.py`.
- `frontend/src/features/investigations/reliability.test.tsx`;
  `frontend/e2e/{dynamic-investigation,business-lifecycle}.spec.ts`;
  `frontend/playwright.orchestration.config.ts` (select current isolated frontend).
- This OpenSpec change/evidence, `docs/production-reliability.md` and the existing
  generated SQL inventory. Inventory includes concurrent source additions; those
  unrelated changes are not attributed to this phase.

No commit, deployment or user-data migration was made. Exact working-tree diffs
remain available for review; prior Phase 1/2 and unrelated contributor changes
remain intact.

## Gates and final acceptance

Shared contracts and generated UI drift passed. Final SQL inventory: **1,192
calls**, 123 literal tables; this is an inventory, not universal PostgreSQL
qualification. Python AST parsing passed for **431 files**. Final whitespace and
strict `openspec validate production-reliability-ui --strict` checks pass.
The owned private PostgreSQL cluster was stopped after all checks; no production
service or unrelated test cluster was stopped.

- [x] Isolated process ownership, connection loss, database downtime, contention/deadlock, cancellation and unknown-effect recovery checks.
- [x] One/two/four-process bounded sustained workloads on SQLite and PostgreSQL.
- [x] Trusted shared-store credential buckets, protected account slots and fair bounded polling.
- [x] Version-preserving source polling, stale/disconnected-source handling and current-authority checks.
- [x] Existing investigation UI connected to supported graph/recovery/alert diagnostics and existing approvals/actions.
- [x] Controlled main/auxiliary backup/restore, migration compatibility and retained event-wait execution.
- [x] Representative Simpson/Subway supported acceptance and deterministic quality/isolation checks.
- [x] Relevant backend/frontend/browser checks and operational procedures documented.
- [ ] Actual multi-host/network-partition and physical storage-failure qualification.
- [ ] Soak-duration production load, customer-agreed latency/recovery SLOs and deployment-topology fairness.
- [ ] Shared-credential quotas across dedicated deployments that use separate authoritative stores.
- [ ] Seamless reviewed multi-day repinning/invalidation across every source and memory adapter.
- [ ] Live-provider/model-quality/delivery acceptance, external alert delivery and deployed metrics aggregation.
- [ ] Coordinated production backup RPO/RTO, rollout/rollback rehearsal in representative infrastructure.
- [ ] Production deployment, service restart or database migration (not authorized/performed).

Source changes are detected by supported bounded polling, not universal CDC.
Current actions cannot treat an old pin as fresh after relevant changes. Polling
capacity and source latency must be qualified for the deployment's source count;
there is no freshness guarantee under arbitrary backlog or provider failure.

Shared buckets/reserved capacity coordinate only within one authoritative store.
Separate Simpsons/Subway deployment databases do not magically share counters.
Use separate credentials or a qualified central quota gateway before claiming a
cross-store global quota. Existing planner clients outside runtime reservation
paths are not universally metered by these new counters.

Alerts are tested read-only conditions exposed to administrators; external
notification/acknowledgement delivery is not installed. The PostgreSQL global
advisory write lock remains and measured wait rises with more workers. Live
SMTP/Gmail/Calendar reconciliation remains provider/operator review; supported
report read-back does not automatically resume a workflow. No production exactly-
once or arbitrary-prompt business-success guarantee is made.

The development changes are ready for review and further production qualification.
The unchecked criteria require additional implementation or representative
infrastructure/explicit live targets and are not falsely marked complete.
