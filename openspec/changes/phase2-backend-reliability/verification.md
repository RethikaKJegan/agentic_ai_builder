# Phase 2 implementation and verification — 2026-10-17

Scope: correction-plan sections 4–7. This builds on the deployed Phase 1 and preserves the earlier overview-contention edits. Google Workspace production authentication remains explicitly deferred. No live PostgreSQL cutover is performed.

## Changes

- Explicit read-only transactions across workflow/workspace/runtime/lifecycle/reply/procurement/source paths; SQLite query-only enforcement, bounded busy timeout and safe category/duration metrics. Transaction-state failures are distinct from contention and PostgreSQL deadlock/serialization failures.
- Durable activation preparation, ownership/expiry, exact operation-to-release mapping, provider calls outside transactions, optimistic revision/release/Registry revalidation, atomic activation, durable compensation and lease-aware restart recovery.
- PostgreSQL driver using real psycopg transactions, row locks and bound values; versioned JSON/dialect compatibility migration; separate auxiliary schemas for procurement, effects and sheet-resource observations. Schema-scoped writer serialization deliberately preserves SQLite atomicity; parallel-write throughput is not claimed.
- Maintainable inventory of 375 SQL/storage calls, 46 literal table names and ten dynamic procurement subtype tables. Includes dynamic expressions and catalog/migration SQL. Repeated names across independent databases are not one shared table.
- Explicit opt-in snapshot/import/validation tooling. Row order, exact row checksums, constraints, indexes and serial high-water marks are checked before commit. Nonempty targets and invalid legacy integrity are rejected. Migration/backup/cutover/rollback procedures are in `docs/phase2-backend-reliability.md`.
- API mode queues execution/resumption; the separate worker process has no HTTP listener. Durable worker ownership, standby takeover, dispatch claim tokens, run/job lease renewal, stale/cancellation fencing, safe uncertain-effect recovery, indexed bounded/fair run batches and just-in-time dispatch claiming.
- Bounded graceful draining retains worker-group ownership until drained; procurement workers can restart after stop/lease loss. Safe component health/backlog is exposed through authenticated `/worker-health`; runtime-disabled health works.

Exact existing-file changes are consolidated in `implementation-review.patch`, relative to each earliest Phase 2 staged original, preserving Phase 1 and preexisting user edits. Incremental reviewed patches remain in this directory.

New implementation files: `workflow_api/activation.py`, `postgres.py`, `auxiliary_database.py`, `worker_control.py`; `scripts/run_builder_worker.py`, `migrate_builder_database.py`, `inventory_builder_sql.py`; `requirements-postgres.txt`; `migrations/postgres/001_compatibility.sql`. New regression files are `tests/test_phase2_reliability.py`, `test_phase2_workers.py`, `test_phase2_migration.py`, `test_postgres_backend.py`, and `test_phase2_postgres_concurrency.py`.

## Verification evidence

- Final real PostgreSQL acceptance/concurrency/migration run: **129 passed, 23 subtests passed**, no skips, in 146.15 seconds. PostgreSQL 16 with psycopg 3.3.6, isolated schemas and a dedicated non-superuser/non-createdb/non-createrole test role.
- These exercise existing workflow, lifecycle, runtime, graph, observability, procurement-store, sheet-creation and recovery assertions against actual PostgreSQL, plus two simultaneous editors, conflicting activations, stale claims, interrupted invocations, same-key retries, approval backlog fairness and slow dispatch.
- Seven migration checks include workflow/history/queue/release preservation, deleted event-sequence high-water marks, rejection of nonempty targets, transactional rollback, bound literal safety and exact migration of all three connector stores.
- Final shutdown/health/queue/launcher tests: **17 passed** in 10.89 seconds, including real thread stop/start and ownership renewal during drain. Two final ownership/health cases also passed on PostgreSQL after the drain change.
- Relevant SQLite lifecycle/runtime/live-provider regression: **104 passed, 23 subtests passed**. Latest component/security regression: **63 passed**. API/worker compatibility regression: **56 passed, 6 subtests passed**.
- Frontend: **137 passed** across 20 test files; typecheck and lint passed. Frontend source/build unchanged by Phase 2, so the active tested Phase 1 build is retained.
- Shared contract schemas/fixtures, generated UI-contract drift check, strict Phase 2 OpenSpec validation, Python syntax checks, SQL inventory drift check and `git diff --check` pass.

The first full-suite attempt stopped on a test double that did not accept the new read-only keyword; the double now asserts that access is read-only. The initial PostgreSQL auxiliary run exposed direct SQLite-only test assertions; those now inspect the selected backend and all recovery invariants remain asserted. No failure is counted as a passing test.

The isolated PostgreSQL test database, dedicated role and private connection file were removed after validation. Future real PostgreSQL tests require a privately supplied `BUILDER_TEST_POSTGRES_DSN`; unavailable database/driver results are skips, not evidence of compatibility.

Full SQLite/connector regression: **498 passed, 73 subtests passed**, no skips, in 657.97 seconds. Later launcher/component adjustments were checked with the focused suites above. Logs remain privately in `.local/phase2-stage/`.

## Live rollout

Performed the exact local-mode service additions from `live-rollout-plan.md`. The previous combined backend was gracefully stopped and confirmed inactive before four private SQLite online backups were taken. Source rollback checkpoints preserve all 23 preexisting changed files relative to their earliest Phase 2 staged originals; no `git reset` was used.

Started the API alone and confirmed every preexisting table count matched its backup **before** starting workers: main database 30 tables / 996,627 rows; procurement 24 / 2,469; effect journal 1 / 157; sheet resources 2 / 49. These are row-count preservation checks, not a claim that row counts alone prove content identity. The original data files were never migrated/replaced, and complete private snapshots are retained. API-only health showed zero worker owners and zero active runs.

The first standalone worker launch exposed the installed FastAPI version's removal of `APIRouter.startup()`. It failed before any background group started. The launcher now uses the framework's public `lifespan_context`, with an actual startup/shutdown regression and successful live startup. No failed launch is counted as deployment success. Direct-backend smoke also explicitly respects the existing proxy-scoped session-cookie design; production cookie policy was not weakened.

The corrected worker acquired one durable group lease. Backend PID 3844039 and worker PID 3844417 were active/running with zero automatic restarts after the corrected start. Frontend PID 3828452 and its tested Next build were retained. Backend `127.0.0.1:8002` and frontend `127.0.0.1:3001` remain loopback-only; the worker has no HTTP listener. No nginx, firewall, DNS, Google credentials or unrelated project changed.

Live HTTP verification passed: HTTPS app 200; HTTP-to-HTTPS redirect 301; public development session/API 403 without issuing a session; anonymous backend 401; local authenticated backend and frontend proxy 200; authenticated worker health 200; bad origin 403; public backend Host 403. Request IDs survived the proxy and responses used `Cache-Control: no-store`.

Desktop/mobile live browser checks passed with local session and worker-health HTTP 200, no page errors, no static-asset failures and no direct private-port browser calls. The public HTTPS browser loaded the app with HTTP 200 and its development API stayed HTTP 403. After multiple heartbeat cycles, TriggerScheduler, RuntimeWorker, ProcurementWorker and ReplyWorker all reported ready.

Existing configured background activity resumed through the worker. Smoke checks submitted no new workflows, model requests, email, approvals or connector mutations. Dispatch backlog remained 32 completed / 10 failed, with no planning jobs. Existing failed/blocked history was retained, not repaired or silently retried. Public authenticated production requests remain untested because Google Workspace is deferred.

Private evidence and backups: `.local/phase2-rollout/` (mode 0700). The source/configuration-only rollback script does not overwrite post-rollout business data with older snapshots.

## Operational limits

- SQLite remains live. PostgreSQL is implemented/tested and migration is prepared; production data is not automatically moved or claimed migrated.
- A PostgreSQL cutover must cover every main/auxiliary store and artifacts with consistent paths/shared storage. Post-cutover writes require delta reconciliation before rollback to older SQLite data. No automatic reverse migration is promised.
- Conservative PostgreSQL write serialization, operational retention/alerts and multi-host deployment testing remain explicit limitations. This is not a production load-test or external network audit.
- No-tool legacy identities missing trusted origin fail closed and need reviewed reactivation. Pre-rollout read-only inspection found **29 active identities and zero missing trusted origins** in this live deployment.
- Google Workspace login and successful authenticated public HTTPS behavior remain deferred. Existing public development authentication must remain blocked. No new production-readiness claim is made.
