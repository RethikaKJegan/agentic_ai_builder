# Phase 3 implementation and verification

## Scope and evidence boundary

Implemented in the existing repository, preserving the uncommitted Phase 1/2 work.
No production deployment, service restart, business-data migration, paid model
request, real email, or external business write was performed.

Backend acceptance uses isolated synthetic records, a configured test event
adapter, controlled intent/planner/evaluator/model transports, the actual Registry,
CrewAI bridge, GraphRunner, persistence and dispatch queue. Browser acceptance
uses an isolated production build with intercepted backend responses. These checks
verify local implementation, not production readiness or real Subway business
conclusions.

## A. Exact files changed for Phase 3

| File | Change and existing component reused |
| --- | --- |
| `shared/contracts/durable-automation-v1.json` | Additive native consent with nullable connection; preserve legacy case subscriptions; add workflow subscriptions, event-source consent, bounded predicates, reviewed replacement and eligible retry controls. |
| `workflow_api/overview_automation.py` | Enable native recurring/delayed Subway preparation and review; discover configured event adapters; preserve reviewed predicates; activate through DurableAutomation; expose scoped execution history. |
| `workflow_api/action_plans.py` | Apply the existing run-owned adaptive controller to scheduled/event Subway plans, including explicitly requested approved follow-up actions. |
| `workflow_api/subway_automation.py` | New small consent helper: pin the reviewed catalogue fingerprint, validate native query scope and enforce logical occurrence date/entity filters. No executor or scheduler added. |
| `workflow_api/workflow_events.py` | New helper over existing subscription/delivery/occurrence records and lifecycle jobs; authenticated adapter discovery, conditions, schema checks, deduplication, poison handling, ordering and dispatch. |
| `workflow_api/automation.py` | Native consent without Google for native readers; fresh worker authorization; approved-root/effective-plan integrity; event occurrences; pause/retry/replacement/history/metrics; terminal occurrence limits. Existing case paths retained. |
| `workflow_api/temporal_queries.py` | Add previous/current calendar quarters to the existing IANA calendar resolver. |
| `workflow_api/source_freshness.py` | New adapter-attestation helper; distinguish metadata revision, unknown business-data version, synchronization, extraction and reporting coverage. |
| `workflow_api/restored_subway_sources.py` | Explicit historical-snapshot status with unknown sync/extraction/coverage and no invented refresh capability. |
| `workflow_api/subway_queries.py` | Preserve actual reporting predicates and freshness in native result/receipt provenance. |
| `workflow_api/workflow_adaptive.py` | Reuse evaluation/replanning for occurrences; expose trigger context and deterministic freshness limitations; preserve exact approved writes; require verified business findings before follow-up; revalidate automation authority before reasoning. |
| `workflow_api/lifecycle.py` | Route occurrence replay through bounded, owner-scoped retry eligibility, retaining the existing queue and lease protocol. |
| `runtime/action_plans.py` | Materialize occurrence-specific query dates and authenticated entity filters; preserve them during validation; enrich Subway automation reports with objective, trigger and assessment. Generic report payloads retain their existing shape. |
| `runtime/graph.py` | Apply recurring consent to native readers, suspend paused work and enforce cumulative occurrence action allowances before invocation. |
| `runtime/adaptive_control.py` | Permit only the approval gate belonging to the currently selected adaptive action. |
| `runtime/service.py` | Add deterministic source limitations to the existing public adaptive projection. |
| `frontend/src/api/overview-automation.ts` | Map additive event/history/eligible-retry fields. |
| `frontend/src/api/adaptive.ts` | Map deterministic evidence limitations. |
| `frontend/src/api/orchestration.ts` | Map scoped automation metrics. |
| `frontend/src/features/investigations/OverviewAutomationReview.tsx` | Existing review UI gains event consent, periodic active-status refresh, execution history, eligible retry and reviewed replacement. |
| `frontend/src/features/investigations/DurableAutomation.tsx` | Include scoped metrics in the existing health/details presentation. |
| `frontend/src/features/builder/AdaptiveProgress.tsx` | Show deterministic freshness/evidence blockers. |
| `tests/test_subway_automations.py` | New synthetic end-to-end and reliability acceptance tests. |
| `frontend/src/features/investigations/overview-automation.test.tsx` | Event consent, execution history, retry and reviewed-edit coverage. |
| `frontend/src/features/investigations/orchestration.test.tsx` | Await the asynchronously enabled validation control before clicking it. |
| `frontend/e2e/overview-automation.spec.ts` | Desktop/mobile event/history journeys; align existing assertions with current editor navigation and labels. |
| `openspec/changes/subway-automation-reliability/{proposal.md,tasks.md,specs/subway-automations/spec.md,verification.md}` | Scope, requirements, work tracking and this report. |

No new agent framework, scheduler, broker, database or Subway application was added.

## B. Scheduling and lifecycle

Overview keeps the existing interpretation, ontology selection, Registry review,
workflow approval and explicit recurring-consent activation. Subway uses
`subway_query`, not the generic query catalogue. Native read consent needs no
Google account. External operations retain the selected-account requirement.

The stored temporal recipe is resolved against each durable occurrence's logical
due time, including delayed workers, IANA zones, DST and calendar quarters.
Generated queries must preserve the exact bounds and reviewed source scope.

Each occurrence gets its own run, adaptive state, memory, checkpoints, evidence,
report and history. The reviewed root workflow remains immutable while permitted
read/reasoning revisions are run-local. Pausing prevents new actions/reasoning;
an already dispatched operation may finish. Resume retains checkpoints and the
original execution/resource deadline. Cancellation/revocation prevents further
authorized continuation; it cannot undo an external operation already dispatched.

Edits use a separately reviewed, authorized replacement and retain both histories.
A paused replacement can be activated atomically while the old definition is
retired. Retry is capped and idempotent: eligible pre-dispatch failures or safely
resumable runs may continue; terminal or uncertain side effects require review.
The last authorized completed occurrence terminates the automation without
advertising another future run.

Existing skip/coalesce/catch-up and forbid/allow overlap policies remain. Catch-up
and coalescing work are bounded per tick. Existing durable identifiers,
transactions, claim tokens, leases, heartbeats and worker fairness are reused.

## C. Event execution

Only server-registered adapters exposing owned source descriptors, authentication
and bounded polling are discoverable. No live Subway business-event adapter is
installed by this change. The test adapter advertises `invoice.created`; event
types are descriptor-driven, not a hardcoded list of supposedly available feeds.

Authentication precedes acceptance and replay checks. Tenant/owner scope,
self-contained payload schemas, literal-path conditions and reviewed entity
bindings are checked. Conditions cannot be broadened beyond the reviewed plan.
Event identity plus payload fingerprint prevents conflicting reuse. The invoice
fixture also binds the authenticated numeric invoice identity, follows its declared
PO relationship, verifies the 120 − 100 = 20 numeric difference, and persists the
qualified assessment without inventing company tolerance or overbilling policy. Accepted
payload, trigger identity, logical event time and run/queue references persist.

Optional sequence numbers are monotonic within a subscription; older sequences
are rejected. Events without sequence numbers remain independent deduplicated
occurrences. Poison payloads are rejected durably. Authenticated malformed
polling envelopes are recorded by fingerprint without raw sensitive contents so
later events can progress. Authentication or changed-source configuration errors
remain explicit blockers. A forbidden overlap defers intake without advancing
the provider cursor.

Adapters own real source authentication and transport. An API request or snapshot
cannot install an adapter or grant itself source authority.

## D. External integrations and freshness

Existing registered integrations are reused. Native analysis followed by a
mocked mailbox draft is verified with current credential scopes, exact recipient
consent, workflow approval, exact-payload approval and a persisted receipt.
Replaying the scheduler does not repeat the effect. Replanning cannot add, remove
or change an approved external action. Missing/revoked credentials block rather
than produce fabricated success.

Existing generic Sheets/mail automation tests also exercise their real runtime
paths with controlled external HTTP. No live delivery, spreadsheet write,
calendar action or production credential verification was performed.

Native receipts preserve dataset identity, metadata revision/generation, read
time, actual reporting predicates and adapter freshness. Unknown synchronization,
extraction and business-data versions stay unknown. Restored snapshots are marked
historical. Metadata profiling is not business-data refresh. Period-sensitive
adaptive completion requires source coverage attestations; technically successful
historical/unknown queries cannot establish current-period completeness.

No supported operational refresh feed was found. This change does not invent an
incremental business-data synchronization pipeline.

## E–G. Verification results

Final local results and reproducible commands follow. All final checks passed;
the eight PostgreSQL skips are explicitly classified below.
Counts across rows overlap and must not be added as unique tests. Final acceptance
and legacy automation suites together contain 64 passing cases.

| Check | Result | Log |
| --- | --- | --- |
| Phase 1/2 baseline before Phase 3 changes | 38 passed | `/tmp/subway-phase3-baseline.log` |
| Broad existing backend regression, 19 modules | 391 passed; 2 failures found and fixed as described below | `/tmp/subway-phase3-regression.log` |
| Corrected full Overview integration module plus native external-action test | 14 passed | `/tmp/subway-phase3-corrections.log` |
| Expanded backend/recovery/worker/PostgreSQL selection | 147 passed, 8 skipped, 5 subtests passed | `/tmp/subway-phase3-final.log` |
| New Phase 3 acceptance before the additional invoice/PO scenario | 23 passed | `/tmp/subway-phase3-acceptance-final.log` |
| Full event → declared invoice/PO join → verified numeric difference | 1 passed; included in the final combined Phase 3 run | `/tmp/subway-phase3-invoice.log` |
| Final combined Phase 3 acceptance | 24 passed, 82 warnings; 0 failed or skipped | `/tmp/subway-phase3-acceptance-complete.log` |
| Final existing automation regression | 40 passed | `/tmp/subway-phase3-legacy-final.log` |
| Frontend | 608 passed across 90 files | `/tmp/subway-phase3-ui-final.log` |
| Desktop/mobile production-build browser journeys | 20 passed | `/tmp/subway-phase3-browser-final.log` |
| Typecheck, lint, isolated production build | Passed | `/tmp/subway-phase3-{types,lint,build-final}.log` |
| Shared contracts, generated contract drift, diff whitespace and strict OpenSpec | Passed | validator output and `/tmp/subway-phase3-spec.log` |

The two broad-suite failures exposed report-context enrichment reaching generic
automations. Enrichment was restricted to Subway; the complete affected module
then passed. Browser assertions for older navigation/labels were aligned with the
current existing UI. A test clicked validation before it became enabled under
concurrent load; it now waits for the enabled state. No production behavior was
changed for these UI assertion fixes.

The eight PostgreSQL tests are skipped because `BUILDER_TEST_POSTGRES_DSN` is not
configured. SQLite concurrency and reconstruction are verified; deployed
PostgreSQL failover, multi-host coordination and load capacity are not certified.
Deprecation warnings are retained; they are not failed tests.

The production build is isolated at `/dev/shm/subway-phase3-build/frontend`.
The active repository `.next` output was preserved.

### Mandatory acceptance mapping

| Requested test classes | Evidence and qualification |
| --- | --- |
| 1, 19: scheduled natural-language chain | Overview prepare/review/activate, native query, actual CrewAI/runtime, independent due occurrences, results/history; interpretation and models are controlled fixtures. |
| 2, 7: autonomous scheduled investigation | Additional retrieval, run-local revision and distinct verified query receipts; exact reviewed root preserved. |
| 3, 4, 20: events and duplicate prevention | Configured authenticated fixture, conditions, schema rejection, invoice-identity filter and declared PO join, verified numeric difference, poison/out-of-order/conflicting identity handling, queue/run/result persistence. No live feed claim. |
| 5, 6: restart/crash | Reconstructed scheduler, concurrent due ticks, expired/reclaimed lease and stale token rejection; existing send-before-job-commit recovery and uncertain-send tests. Controlled recovery, not production chaos testing. |
| 8: freshness | Logical reporting window plus unverified coverage blocks completion; adapter attestation coverage checks and visible limitations. |
| 9, 10: integration failure and approvals | Native-only consent denies external tools; fresh worker revocation; existing revoked-connection and exact-payload approval tests; native analysis to mocked approved draft. |
| 11, 12: concurrency and isolation | Concurrent due transactions, durable claims, owner-scoped history/consent, existing runtime workers and Subway/Simpsons isolation regressions. PostgreSQL tests skipped as above. |
| 13: lifecycle | Activation, pause/resume without invocation, reviewed replacement, disable, immutable history, bounded idempotent retry and replay restrictions. |
| 14: Knowledge Map | Existing native receipt/ontology-usage and composition presentation regressions; scheduled runs use the same actual query/checkpoint hooks. |
| 15, 16, 17: earlier phases and Simpsons | Baseline and broad regressions include full queries, investigations, adaptive execution, memory, runtime, dedicated client auth and Simpsons isolation. |
| 18: exhaustion | New occurrence action-limit enforcement plus existing adaptive turn/token/tool/provider capacity and uncertain-effect limits. |

### Commands

Run from `/home/raf/agentic-ai-builder`; use a new temporary pytest directory per
invocation. The DSN variables are intentionally unset for isolated local tests.

```bash
env -u BUILDER_DATABASE_URL -u BUILDER_AUXILIARY_DATABASE_URL \
    -u BUILDER_CLIENT_ID -u BUILDER_TEST_POSTGRES_DSN \
    TMPDIR=/dev/shm/subway-phase3-tmp CREWAI_TESTING=true \
    CREWAI_TRACING_ENABLED=false OTEL_SDK_DISABLED=false \
    PYTHONDONTWRITEBYTECODE=1 \
    .venv-integrations/bin/python -B -m pytest -q -p no:cacheprovider \
    --basetemp=/dev/shm/subway-phase3-user-verification \
    tests/test_subway_automations.py tests/test_subway_autonomy.py \
    tests/test_subway_intelligence.py tests/test_subway_full_queries.py \
    tests/test_durable_automation.py tests/test_overview_automation_integration.py \
    tests/test_runtime.py tests/test_simpsons_client_isolation.py \
    tests/test_subway_client_auth.py tests/test_workflow_ontology_usage.py

.venv-integrations/bin/python -B scripts/validate_contracts.py
.venv-integrations/bin/python -B scripts/generate_ui_contracts.py --check
git diff --check
node /home/raf/.npm/_npx/abab5bd700860149/node_modules/@fission-ai/openspec/bin/openspec.js \
    validate subway-automation-reliability --strict
```

Frontend commands: `npm run typecheck`, `npm run lint`, and
`npm test -- --reporter=dot --maxWorkers=2`, from `frontend/`. Build from an isolated
copy with shared/ontology/node_modules links, not the active `.next` directory.
The browser command executed from the repository frontend is:

```bash
BUILDER_E2E_FRONTEND_DIR=/dev/shm/subway-phase3-build/frontend \
    npx playwright test --config playwright.overview-automation.config.ts
```

## H. Remaining work, classified

1. **Implemented and locally verified:** reviewed scheduled/event workflow paths,
   native query consent, adaptive continuation, dates, fixture authentication and
   predicates, durable deduplication/dispatch, current worker authority, approved
   external follow-up, historical freshness limitations, controls/history/UI,
   scoped metrics and regression protection described above.
2. **Implemented but not live-tested:** configured OpenAI reasoning transports,
   server event-adapter interface and existing external integration execution with
   real providers. Controlled transports are not live integration certification.
3. **Blocked by unavailable infrastructure:** no configured live Subway business
   event feed or operational data refresh adapter; no PostgreSQL test DSN;
   production multi-host/load/failover validation remains outstanding.
4. **Blocked by missing external authorization:** no authorized real emails,
   business writes, deployment or production acceptance changes were performed.
5. **Blocked by missing authoritative business data:** live reporting coverage,
   actual synchronization history and unbound budget/approval/business policies
   cannot be inferred from historical records or source filenames.
6. **Not implemented:** a new ingestion engine, new external connector suite,
   fabricated live event feed, OCR/download support beyond existing document
   capabilities, automatic authority expansion during replanning, or automatic
   replay of uncertain external effects. Operational business refresh remains
   unavailable until a real supported authorized adapter is supplied.

Local Phase 3 implementation is not a claim of verified production readiness.
