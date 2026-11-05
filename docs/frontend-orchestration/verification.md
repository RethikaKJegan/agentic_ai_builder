# Phase 4 verification — 5 November 2026

Repository `/home/raf/agentic-ai-builder`, branch `agentic_ai_builder`, starting commit `edbbc82`. Initial worktree was clean. This implementation made no Git commit, deployment, production service restart, dependency installation or live model/provider write. Browser servers and PostgreSQL were disposable local acceptance infrastructure.

The Phase 4 brief explicitly prohibits new OpenSpec artifacts/workflows, whereas root/frontend `AGENTS.md` requires them. That conflict was reported before implementation; the explicit user phase instruction was followed. No OpenSpec artifacts changed. Repository ownership/onboarding/Harihar handoff, installed Next.js guidance, existing investigation/lifecycle UI and authentication/transport, Phase 1–3 guides, contracts, implementations and tests were inspected before implementation.

## Audit, reuse and changes

The existing UI already provided goal/composition planning, Google account selection, workflow save/validate/approve/execute, approval decisions, run/event inspection, persistent process/package cases, evidence/provenance, lifecycle reports and recovery. Missing integrations were the connected action-plan APIs, five-state adaptive control/typed waits, complete action-instance receipts and Phase 3 subscriptions/consent/schedules/timers/history.

These now extend the existing **Workflow → Business Investigation** route and components. No separate app/chatbot, workflow engine, scheduler, case store or provider integration was introduced. Existing legacy/dynamic investigation routes remain available. Connected compositions reopened from existing lists are routed to their connected-plan inspector.

Reused: `WorkflowClient`, same-origin proxy/session/origin protections, `useBackend`, existing workflow operations, `GoogleAccountSelect`, `InvestigationContext`, `BusinessLifecycle`, `SavedDetails`, `Outcome`, `ApiFeedback`, existing run inspector and shared visual styles. Backend execution still uses existing BusinessComposition, Registry, LifecycleDriver, GraphRunner/CrewAI, durable queue, connector journals and persisted cases.

Implemented interactions: natural-language goals and explicit resource/account inputs; ordered action/dependency/agent/tool/binding/evidence/output/approval/completion review; saved workflow review; each approval's actual resolved payload/digest and approve/reject; cancellation; persisted five-state monitoring, evaluator decisions and immutable revisions; typed missing-input supply; saved findings/provenance and verified artifact links; explicit reply monitoring and timers; recurring account/recipient/resource consent scopes, cron/timezone/limits, independent workflow selection, occurrence history/errors/receipts and pause/resume/cancel/revoke.

State is read from backend records. Polling never submits work. URL references reopen saved plans/runs/cases. Scoped panels clear on identity changes, stale reads are discarded, controls use current case revision and backend decision eligibility, and duplicate clicks are locked. Stable command keys are scoped by owner/workspace/operation/payload; only digests and opaque keys enter browser session storage. Explicit identical-key retries handle unknown outcomes; in-memory keys also survive unavailable browser storage. No automatic mutation retry or simulated progress/result is introduced. Unknown effects/interrupted evaluator calls remain blocked for existing operator reconciliation.

## Integration defects found and corrected

Real browser/API execution exposed issues that helper-only backend acceptance had not covered:

1. The existing composition UI parser required textual conditions; connected actions use typed conditions or null. It now accepts those actual backend shapes, with a captured-response regression.
2. The existing canonical workflow client parsed response envelope metadata (`correlation_id`, `contract_versions`) as workflow fields. It now removes only those transport fields before strict canonical validation. Unknown execution fields still fail.
3. Standard save/approval APIs ran legacy tool-input materialization on already compiled connected plans. This inserted false missing-input requirements and changed pinned agent/binding semantics. Connected plans now retain their immutable compiled shape after owned-composition verification. Current Registry assignment/review and exact-payload approvals remain required. Forged markers without an owned composition and tampered plans are rejected by new public-operation tests.
4. Occurrence/control records deliberately reference canonical executions and do not duplicate an original request. The additive UI adapter accepts that actual shape. Recurring choices exclude case-owned adaptive revisions; the backend retains its own restriction.

Test setup corrections included typed account-list metadata, fixture required-capability lists, scheduler constructor arguments, selecting the exact newly planned independent workflow, explicit wait-state synchronization and isolated server startup. No existing regression assertion or authorization check was weakened. Intermediate failed runs are not successful qualification.

## Exact final checks

Commands run from repository root unless noted, with controlled model/source/Google transports and disposable persistence. Commands omit shell output redirection below; log paths identify the retained output.

### Frontend

```sh
PATH=/home/raf/.nvm/versions/node/v22.23.3/bin:$PATH npm --prefix frontend run test
PATH=/home/raf/.nvm/versions/node/v22.23.3/bin:$PATH npm --prefix frontend run typecheck
PATH=/home/raf/.nvm/versions/node/v22.23.3/bin:$PATH npm --prefix frontend run lint
```

Full suite: **499 tests in 74 files passed**, 27.08 seconds, `/tmp/frontend-phase4-frontend-verified.log`. Types and lint passed (`/tmp/frontend-phase4-types-verified.log`, `/tmp/frontend-phase4-lint-verified.log`). An overlapping final storage-unavailable retry-key follow-up passed **15 tests**, 2.82 seconds (`/tmp/frontend-phase4-storage-followup.log`); it is not added to the distinct total.

The isolated `.local/frontend-phase4-stage` copy uses the existing installed dependencies and preserves deployed build assets:

```sh
PATH=/home/raf/.nvm/versions/node/v22.23.3/bin:$PATH npm --prefix .local/frontend-phase4-stage run build
```

The isolated build passed (`/tmp/frontend-phase4-build-final.log`). A final source build/type/lint confirmation after the storage-unavailable guard is recorded in `/tmp/frontend-phase4-build-source-final.log`, `/tmp/frontend-phase4-types-source-final.log`, and `/tmp/frontend-phase4-lint-source-final.log`. No production build directory or live application service was replaced.

### Real frontend → backend browser acceptance

```sh
PATH=/home/raf/.nvm/versions/node/v22.23.3/bin:$PATH \
 frontend/node_modules/.bin/playwright test --config frontend/playwright.orchestration.config.ts
```

**7 passed, 2.5 minutes**, `/tmp/frontend-phase4-browser-final-pass.log`. Both backend and staged frontend are local self-managed test servers; all domain/model/Google transports are controlled. The backend still executes actual planning validation, immutable composition, Registry review, CrewAI, GraphRunner, approvals, receipts, cases, queue jobs and worker/recovery code.

| Journey | Executed assertions |
| --- | --- |
| A, desktop and mobile | Prepared case with original natural-language goal → model-proposed plan → real evidence/CrewAI findings → exact Sheet approval → verified Sheet → exact Gmail approval → send → typed reply wait → page refresh → explicit reviewed subscription → matching reply after three simulated days → same case/run reevaluation/completion. Actual artifact link, zero browser page errors and no horizontal overflow. |
| B, daily report | Natural-language goal in existing Business Investigation → backend-generated plan → normal save/validate/approve → explicit recurring consent → exact independent workflow revision schedule → two distinct occurrences/runs → genuinely changed mapped source outputs → independently verified report/send receipts → persisted occurrence list. |
| C, missing information | Planner requests an absent recipient → persisted typed input wait → actual recipient supplied with current revision/wait ID → execution completes. |
| D, adaptive replanning | Evaluator requests additional inspection retrieval → immutable revision 2 → normal successor workflow review → completed read preserved → new retrieval verified → final completion. |
| E, uncertain effect/restart | Controlled Gmail transport accepts send then loses acknowledgement → canonical `ACTION_EFFECT_UNVERIFIED` → worker/runtime reconstruction → page refresh retains blocked state → scheduler tick does not resend. |
| E, revoked account | Select actual owned account → revoke that account → planning fails visibly → no account substitution, report creation or send. |

Stale approval/revision rejection, exact payload visibility, double-click protection, owner/workspace changes, unavailable browser storage and explicit same-key recovery are additionally exercised by frontend interaction/transport and existing backend tests. Rejection/cancellation controls use existing APIs; their existing regression coverage remains intact.

`manifest.json` records exact executed reply snapshot source paths and SHA-256 hashes. `screenshots/reply-desktop.png` and `screenshots/reply-mobile.png` capture the final real controlled UI and were visually inspected. Raw sources are under `.local/frontend-phase4-evidence/`; they contain the final case plus actual pre-reply report/send run snapshot, explicitly qualified. The three actual-shape frontend JSON fixtures derive from executed Phase 3/4 controlled records, not invented provider results. Browser test source and exact result log cover all journeys; no claim of live provider/model quality is made.

During acceptance, deliberate rejected commands/uncertain effects produce existing redacted database-transaction diagnostic messages in the fixture server. Final assertions verify the resulting saved states and effects; these messages are not silently relabelled successful provider operations.

### Backend phases and public frontend API bridge

```sh
PYTHONDONTWRITEBYTECODE=1 .venv-integrations/bin/python -B -m pytest -q -p no:cacheprovider \
 tests/test_connected_action_plans.py tests/test_adaptive_orchestration.py \
 tests/test_durable_automation.py tests/test_orchestration_frontend_api.py \
 --basetemp /tmp/frontend-phase4-final-phases
```

**86 passed, 14 warnings, 673.69 seconds**, `/tmp/frontend-phase4-final-phases.log`. This run includes two new bridge tests. A final third guard test was added; all **three public bridge tests passed**, 2 warnings, 16.40 seconds (`/tmp/frontend-phase4-api-guard-final.log`). Two overlap the 86-test suite, so this adds exactly one distinct test.

### Runtime, Registry, planning, workers and workflow API

```sh
PYTHONDONTWRITEBYTECODE=1 .venv-integrations/bin/python -B -m pytest -q -p no:cacheprovider \
 tests/test_runtime.py tests/test_registry.py tests/test_planner.py tests/test_planner_provider_errors.py \
 tests/test_dynamic_delegation.py tests/test_delegated_tools.py \
 tests/test_business_preparation.py tests/test_business_planning.py tests/test_lifecycle.py \
 tests/test_phase2_workers.py tests/test_phase2_reliability.py \
 tests/test_manual_worker_authorization.py tests/test_workflow_api.py \
 --basetemp /tmp/frontend-phase4-final-platform
```

**245 passed, 43 subtests passed, 234 warnings, 231.74 seconds**, `/tmp/frontend-phase4-final-platform.log`.

### Existing cases, Simpson, retail, composition and memory

```sh
PYTHONDONTWRITEBYTECODE=1 .venv-integrations/bin/python -B -m pytest -q -p no:cacheprovider \
 tests/test_business_cases.py tests/test_business_case_runtime.py tests/test_simpson_lifecycle.py \
 tests/test_generic_lifecycle_phase6.py tests/test_business_composition.py tests/test_agent_memory_recovery.py \
 --basetemp /tmp/frontend-phase4-verified-core
```

**148 passed, 26 warnings, 718.79 seconds**, `/tmp/frontend-phase4-verified-core.log`.

### Google, research and report connectors

```sh
PYTHONDONTWRITEBYTECODE=1 .venv-integrations/bin/python -B -m pytest -q -p no:cacheprovider \
 tests/test_google_tools.py tests/test_google_connections.py tests/test_inventory_report_runtime.py \
 tests/test_supplier_discovery.py connector_extension/tests/test_connectors.py \
 connector_extension/tests/test_sheet_report.py connector_extension/tests/test_sheet_creation.py \
 connector_extension/tests/test_generalized_sheets.py connector_extension/tests/test_generalized_features.py \
 connector_extension/tests/test_application.py --basetemp /tmp/frontend-phase4-verified-connectors
```

**141 passed, 6 subtests passed, 222 warnings, 478.95 seconds**, `/tmp/frontend-phase4-verified-connectors.log`.

The final relevant non-PostgreSQL backend suites cover **621 distinct tests and 49 subtests**, with zero final failures. Earlier overlapping runs are excluded. These are relevant regression results, not an all-repository or production-readiness claim.

### PostgreSQL migration/concurrency qualification

Available PostgreSQL 16 binaries were used to initialize an isolated UTF-8 cluster under `/tmp/frontend-phase4-pg-utf8`, listening only on loopback port 55487. A disposable `builder_phase4` login has no superuser, create-database or create-role privileges. Tests create/drop isolated schemas. No configured application database was migrated or reset.

```sh
BUILDER_TEST_POSTGRES_DSN=postgresql://builder_phase4@127.0.0.1:55487/postgres \
 PYTHONDONTWRITEBYTECODE=1 .venv-integrations/bin/python -B -m pytest -q -p no:cacheprovider \
 tests/test_durable_automation_postgres.py tests/test_postgres_backend.py \
 tests/test_generic_lifecycle_postgres.py --basetemp /tmp/frontend-phase4-verified-postgres
```

**116 passed, 23 subtests passed, 146 warnings, 299.56 seconds**, `/tmp/frontend-phase4-verified-postgres.log`; zero skips. This includes the four durable automation PostgreSQL variants, migration/history/case compatibility, leases and concurrency. The disposable cluster was stopped after verification. Initial provisioning attempts used SQL_ASCII and then a superuser role; those setup failures were corrected to UTF-8 and a restricted test role before final qualification. No product behavior/assertion was weakened to pass them.

This resolves the earlier local PostgreSQL availability gap for these tests. Deployment still requires qualification against the actual intended PostgreSQL environment/version/permissions/operational setup.

### Contracts and source

```sh
PYTHONDONTWRITEBYTECODE=1 .venv-integrations/bin/python -B scripts/validate_contracts.py
git diff --check
```

Shared schema/example validation passed. Changed Python sources parse. Warnings are existing JSON Schema RefResolver/FastAPI lifespan deprecations; test-only browser startup also reports FastAPI shutdown-hook deprecation and Node color-environment notices. No shared contract, domain process, mapping, credential or production configuration changed.

## Frontend and integration files

New UI/client code:

- `frontend/src/api/orchestration.ts`
- `frontend/src/features/investigations/ConnectedInvestigation.tsx`
- `frontend/src/features/investigations/ConnectedPlan.tsx`
- `frontend/src/features/investigations/AdaptiveCasePanel.tsx`
- `frontend/src/features/investigations/DurableAutomation.tsx`
- `frontend/src/features/investigations/useOrchestrationCommand.ts`

Existing frontend integration: `frontend/src/api/client.ts`, `compositions.ts`, `frontend/src/app/api/backend/[...path]/route.ts`, `BusinessLifecycle.tsx`, `DynamicInvestigationWorkspace.tsx`, `InvestigationList.tsx`, `InvestigationWorkspace.tsx`.

Backend bridge: `workflow_api/service.py`. Acceptance: `tests/test_orchestration_frontend_api.py`, `scripts/serve_orchestration_ui_test_api.py`, frontend API/component tests, actual response fixtures, `frontend/e2e/connected-orchestration.spec.ts`, `frontend/playwright.orchestration.config.ts`.

The local-only browser server is never imported by a production launcher. It reuses existing controlled backend fixtures, loopback-only scenario controls and temporary stores. Product UI contains no controlled-provider proposals or domain keyword/action templates.

## Remaining limitations and deployment prerequisites

See [live-provider-checklist.md](live-provider-checklist.md). Live OAuth/Gmail/Sheets/Calendar permissions, deliverability, provider quotas, model quality and operational recovery are unperformed. Guest invitations remain unsupported by the Calendar adapter. Actual installed stage contracts must support the requested adaptive workflow; this phase does not silently rewrite company processes. Explicit operation-scope JSON and provider payload-path editors require informed operator review. Arbitrary client-authored executable-plan editing and autonomous reconciliation were not introduced.

The frontend now exposes the APIs, reviews, waits, histories and errors. Production worker identity/roles, backups/rollback, intended database migration rehearsal, origins/login/OAuth callbacks, enabled registered tools, authorized recipients and recurring consent still require environment-specific review. **No deployment was performed.**
