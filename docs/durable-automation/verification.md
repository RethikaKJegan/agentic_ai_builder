# Phase 3 verification — 5 November 2026

Repository `/home/raf/agentic-ai-builder`; branch `agentic_ai_builder`. Inspection began at `453f37d` with the completed Phase 2 work present as uncommitted input. During this work that input was committed as `d818ecd` (the Phase 2 checkpoint); this implementation made no Git commit and preserved that work.

`AGENTS.md` requires OpenSpec artifacts. The supplied Phase 3 brief explicitly prohibits new OpenSpec documents/workflows; the conflict was reported before implementation and the user's explicit phase instruction was followed. No OpenSpec or frontend files were changed. No deployment, production-data reset, service restart, dependency installation or live model/provider write was performed.

## Audit and reuse

Inspected the actual branch/instructions, contributor runtime/API handoffs, Phase 1/2 code/contracts/traces, BusinessCases, LifecycleDriver, lifecycle/reassessment, TriggerScheduler, WorkerSupervisor/LeaseHeartbeat, live provider startup/authentication, Google connection/tool binding, WorkflowStore/PostgreSQL adapter, procurement quote/fulfilment authorization/recovery patterns and MailConnector. Existing trigger jobs already had durable leasing/claims; existing Gmail had thread reads, timestamps and journals; existing mapped reads refreshed current data; Phase 2 had durable typed waits and immutable revisions. Missing pieces were generic case subscriptions, atomic event-to-job handoff, scoped recurring consent/occurrences, multi-day active-time suspension, timers and their API integration.

Those gaps now extend the existing components. There is no replacement workflow engine, case store, planner, scheduler thread or permanent LLM session. Procurement-specific/legacy IMAP loops are not used for these case subscriptions.

## Implemented boundaries

- Generic scoped subscription records retain case/stage/wait references, selected provider connection, correlation, participants, expected information, typed payload paths, deadline, cursor, state and retry/error metadata. Provider-specific connection/correlation checks live in the adapter.
- The Gmail adapter uses the approved workflow's current registered `extension_mail_thread` assignment and selected Google connection. It matches actual send thread/message/RFC identifiers, expected sender, reply reference and provider receipt timestamp. It rejects unrelated/self/automatic/bulk replies; message evidence and provenance are persisted without granting tool authority. Deduplication covers repeated deliveries and later subscriptions to the same case/account/provider.
- Existing case event/supply transactions commit evidence, processed identity and stable lifecycle job together. Existing claims/leases/heartbeats fence dispatch, and case serialization prevents concurrent case jobs. Workers use fresh owner identity and bounded LifecycleDriver turns. Already completed effects are preserved; unknown effects require reconciliation.
- Existing TriggerScheduler ticks subscriptions, timers and recurrence preparation and drains the existing lifecycle queue. The integration is verified through an actual scheduler tick, not only direct helper calls.
- Five-field cron/IANA recurrence, stable UTC occurrence IDs, next occurrence, pause/cancel, skip/coalesce/bounded catch-up, allow/forbid overlap and histories are persistent. Each occurrence creates a distinct run through the existing pinned-automation entry point, with fresh mapped source reads and scoped business consent.
- Recurring consent records exact account, operations/input constraints, identity/destination restrictions, business purpose, content scope, schedule, action/occurrence ceilings, approver and expiry. Existing exact-payload approval machinery records authorized gates. Out-of-scope actions remain paused; current consent/account/Registry/owner authority is checked before consequential operations. OAuth alone is insufficient.
- Timers support follow-up, reply/approval deadline, escalation, delay and retry-after. Expiry is an actual system observation, not a fabricated reply or permission to send. The evaluator must propose any follow-up, and normal approval remains mandatory. Multi-day waits preserve consumed budgets and receipts while excluding audited waiting time from active execution deadlines.
- Authenticated scoped APIs create/inspect/control subscriptions, consent, schedules, occurrences, jobs and timers. Listing is paginated/bounded; canonical run/case receipt references avoid duplicating large source payloads in queue records. API JSON Schema is `durable-automation-v1`; existing v1/v2 workflow/plan/case contracts remain unchanged.

See [README.md](README.md) for all API paths, request fields, worker configuration, cron/DST semantics and authorization behavior.

## Exact test commands and results

All test commands ran from the repository root with controlled model/source/Google transports and disposable databases.

### Phase 3 acceptance

```sh
PYTHONDONTWRITEBYTECODE=1 .venv-integrations/bin/python -B -m pytest -q -p no:cacheprovider \
 tests/test_durable_automation.py --basetemp /tmp/durable-phase3-accepted
```

**27 passed, 10 warnings, 177.40 s.** Log `/tmp/durable-phase3-accepted.log`.

Coverage: reply-driven continuation after three simulated days; current selected-account send/thread receipts; unrelated/duplicate replies; cross-subscription deduplication; current evidence passed to Phase 2; completed Sheet/send preservation; distinct next-day runs with genuinely changed source observations; timezone/DST; recurring consent and narrower scope approval waits; deadline follow-up requiring fresh approval; durable approval timeout reevaluation; provider/consent revocation and expiry; cancelled schedule; crash after evidence commit; stale lease rejection/concurrent workers; crash after send but before job commit; uncertain Gmail send held for reconciliation; missed-run/overlap policies; idempotent control; native retail package scheduling; exact authenticated HTTP errors; actual TriggerScheduler dispatch.

A final error-observability follow-up passed **1 overlapping test, 26 deselected, 6 warnings, 7.02 s**, log `/tmp/durable-error-verified.log`. It verifies that the canonical `ACTION_EFFECT_UNVERIFIED` code is retained on the dead-letter job and uncertain occurrence. It is not added to the distinct total. The uncertain-effect artifact uses this final follow-up's raw trace; all raw source paths are recorded in the manifest.

### Phase 1 and Phase 2 regression

```sh
PYTHONDONTWRITEBYTECODE=1 .venv-integrations/bin/python -B -m pytest -q -p no:cacheprovider \
 tests/test_connected_action_plans.py tests/test_adaptive_orchestration.py \
 --basetemp /tmp/durable-final-phases
```

**57 passed, 10 warnings, 433.26 s.** Log `/tmp/durable-final-phases.log`.

### Runtime, Registry, planning, triggers and workers

```sh
PYTHONDONTWRITEBYTECODE=1 .venv-integrations/bin/python -B -m pytest -q -p no:cacheprovider \
 tests/test_runtime.py tests/test_registry.py tests/test_planner.py tests/test_planner_provider_errors.py \
 tests/test_dynamic_delegation.py tests/test_delegated_tools.py \
 tests/test_business_preparation.py tests/test_business_planning.py \
 tests/test_lifecycle.py tests/test_phase2_workers.py tests/test_phase2_reliability.py \
 tests/test_manual_worker_authorization.py --basetemp /tmp/durable-final-platform
```

**224 passed, 37 subtests passed, 98 warnings, 205.62 s.** Log `/tmp/durable-final-platform.log`.

A final overlapping runtime/lease confirmation (`tests/test_runtime.py tests/test_lifecycle.py tests/test_phase2_workers.py`, `/tmp/durable-runtime-confirmed`) passed **84 tests and 23 subtests, 30 warnings, 58.48 s**. It is not added to the distinct total.

### Existing cases, Simpson, retail, composition and recovery

```sh
PYTHONDONTWRITEBYTECODE=1 .venv-integrations/bin/python -B -m pytest -q -p no:cacheprovider \
 tests/test_business_cases.py tests/test_business_case_runtime.py tests/test_simpson_lifecycle.py \
 tests/test_generic_lifecycle_phase6.py tests/test_business_composition.py tests/test_agent_memory_recovery.py \
 --basetemp /tmp/durable-final-core
```

**148 passed, 26 warnings, 692.56 s.** Log `/tmp/durable-final-core.log`.

### Google/Gmail and research/report connectors

```sh
PYTHONDONTWRITEBYTECODE=1 .venv-integrations/bin/python -B -m pytest -q -p no:cacheprovider \
 tests/test_google_tools.py tests/test_google_connections.py tests/test_inventory_report_runtime.py \
 tests/test_supplier_discovery.py connector_extension/tests/test_connectors.py \
 connector_extension/tests/test_sheet_report.py connector_extension/tests/test_sheet_creation.py \
 connector_extension/tests/test_generalized_sheets.py connector_extension/tests/test_generalized_features.py \
 connector_extension/tests/test_application.py --basetemp /tmp/durable-final-connectors
```

**141 passed, 6 subtests passed, 222 warnings, 480.57 s.** Log `/tmp/durable-final-connectors.log`.

The five disjoint final suites total **597 tests and 43 subtests passed; zero final failures**. Focused/intermediate runs overlap and are not added. Warnings are the existing JSON Schema RefResolver/FastAPI lifespan deprecations. No all-repository or production-readiness claim.

### PostgreSQL availability and migration checks

```sh
PYTHONDONTWRITEBYTECODE=1 .venv-integrations/bin/python -B -m pytest -q -x -p no:cacheprovider \
 tests/test_durable_automation_postgres.py tests/test_postgres_backend.py \
 tests/test_generic_lifecycle_postgres.py --basetemp /tmp/durable-postgres
```

**116 skipped, 6 warnings, 2.86 s.** Log `/tmp/durable-postgres.log`. No configured test DSN was available. The four new PostgreSQL acceptance variants create/drop isolated test schemas when infrastructure is configured; they were not executed here. This is a remaining verification limitation, not a PostgreSQL execution success.

SQLite creation/reinitialization/restart tests verify the additive migration marker, subscriptions/cursors/deduplication, queue claims, schedule occurrences, timers and preserved cases. The existing PostgreSQL dialect/transaction boundary is reused; no production schema/data was reset. Run the disposable PostgreSQL checks before deployment.

### Contract, source and evidence gates

```sh
PYTHONDONTWRITEBYTECODE=1 .venv-integrations/bin/python -B scripts/validate_contracts.py
git diff --check
```

Shared schemas/examples passed, including executed recurring consent. Changed Python sources parse. Artifact checks verify manifest hashes, typed automation records/requests, event/queue linkage, distinct recurring runs, preserved completed Sheet receipt, matching reply evidence and uncertain-effect status.

Focused development runs exposed nullable receipt identifier typing, Gmail millisecond timestamp precision, waiting-job recovery, conditional active-time handling and fixture runner/API-envelope mismatches. Receipt narrowing remains limited to actual connector receipts and dependent input validation still rejects null identifiers. Callback persistence and bounded retry/poll metadata were corrected without weakening existing assertions. Intermediate failing runs were not counted as successful qualification; final results above supersede them.

## Complete executed traces

Repository artifacts contain full controlled test traces plus immutable compositions and delivery records read from the same disposable databases. They are not hand-authored model narratives. Manifest entries retain exact raw source paths/hashes, so enriched repository artifacts have different hashes from raw traces.

| Artifact | Runs | Jobs | SHA-256 |
| --- | ---: | ---: | --- |
| `reply-driven-trace.json` | 1 | 1 | `f3bf65c06c33985ccf052ba3c8eff4096e2b0326f87390716cbbaabc4a0fc4a2` |
| `daily-schedule-trace.json` | 2 | 2 | `fc8a58c5e51efb413ddabe12c30e53ab5da46801782113e22428b1f8aad538cb` |
| `deadline-followup-trace.json` | 2 | 3 | `21d4c5abd3101678678fedecdb0f2f0ea929bea6110196412e090de6d645d1d9` |
| `retail-schedule-trace.json` | 1 | 1 | `7fac8e77882b14dbcd5b38e43488d4d8898079500159862a8e1d21c89237c871` |
| `restart-recovery-trace.json` | 1 | 1 | `03d2960c5eb0a978c896c978611798e5cd2052551ad2b364dbfea01ce7a15056` |
| `uncertain-send-trace.json` | 1 | 1 | `3a8cbd65a48d8899ce8d38f501bb7a16fb9fbd5697a184d07eb52e9659dddd55` |

`reply-driven-trace.json` proves same-case/run continuation with one Sheet and one original send after a three-day wait. `daily-schedule-trace.json` proves two distinct pinned runs/occurrences, changed current source data and distinct report effects. `deadline-followup-trace.json` records an actual timeout, evaluator revision and independently approved follow-up. `retail-schedule-trace.json` uses native retail package/source contracts through the same worker. Recovery traces retain actual committed send and uncertain-effect histories. The retail package and all source/model transports are explicitly controlled fixtures, not official company policy or live model-quality evidence.

## Files changed for Phase 3

New implementation: `workflow_api/automation.py`.

Existing integration: `workflow_api/scheduler.py`, `workflow_api/lifecycle.py`, `workflow_api/business_cases.py`, `workflow_api/adaptive_orchestration.py`, `workflow_api/business_ontology_routes.py`, `workflow_api/action_bindings.py`, `runtime/adaptive_control.py`, `runtime/graph.py`, `runtime/service.py`, `scripts/validate_contracts.py`.

New contracts/example: `shared/contracts/durable-automation-v1.json`, `shared/contracts/examples/durable-automation-v1.json`.

New acceptance: `tests/test_durable_automation.py`, `tests/test_durable_automation_postgres.py`.

Documentation/evidence: `docs/durable-automation/README.md`, this report, `manifest.json`, and the six traces listed above. Existing Phase 1/2 artifacts, domain processes, source mappings, credentials, frontend and deployment/configuration files are unchanged.

## Remaining live/deployment/frontend requirements

No live Google/model readiness is claimed. An operator must configure/verify the selected owned account and required OAuth scopes, enable/review the registered read/write capabilities, approve the exact workflow and recurring business scope, supply real authorized recipients, configure fresh worker authentication and run the existing trigger/runtime workers under the intended process role. Live quotas, long-thread read limits, deliverability, retention, model quality and production operational recovery still need environment-specific validation. PostgreSQL migration/concurrency qualification remains unperformed because infrastructure was unavailable.

Unknown external effects and interrupted evaluator intents require existing reconciliation/operator review; email content cannot authorize recovery or broaden permission. Subscriptions/consent are explicit backend operations, not inferred from model prose or OAuth scopes.

Frontend integration remains separately scoped: connect the existing Workflow → Business Investigation screens to these APIs for reviewed consent/subscription creation, next-run/status/history views, pending approvals and reconciliation. No frontend implementation or deployment was performed.
