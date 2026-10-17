# Phase 1 implementation and verification — 2026-10-17

## Scope and status

The requested local UI/backend scope is implemented. Google Workspace production login was explicitly deferred by the user. Complete production Phase 1 acceptance remains open: production startup fails closed, and public authenticated HTTPS success has not been verified. No production-ready claim is made. Phase 2 has not been started by this change.

## Verified root causes and resulting behavior

1. The frontend proxy defaulted to test API port 8011 while the live launcher defaults to 8000. The default now matches live 8000; test harness configuration explicitly retains 8011. Configured nondefault private ports remain supported.
2. The launcher merged `.env` and process configuration, but backend origin middleware independently read `os.environ`. Origins are now validated once and passed directly into `create_app()`. Surrounding whitespace is trimmed; unauthorized schemes, hosts and ports are rejected.
3. Next.js normalizes loopback addresses in `NextURL` to localhost. Same-origin proxy validation now uses the actual Host header, preserving exact origin identity for 127.0.0.1 and localhost.
4. Public hostname allowance and global development-admin sessions were unsafe together. Development is restricted to explicit local/test configuration and loopback hosts/origins; production startup refuses until the deferred real identity adapter exists.
5. A 120-second proxy deadline was shorter than the 180-second provider deadline. Normal APIs and synchronous planning now have separate timeouts. Bounded planner attempts determine the compatible synchronous deadline and durable job lease.
6. Slow generation depended on a single browser request. Durable scoped planning jobs persist queue/status/result, provide cancellation and suppress late cancelled results. The UI shows actual job state/reference and cancellation, retaining prompts on failure.
7. Proxy failures were collapsed into generic unavailable errors and envelopes were checked only by three property names. Canonical envelope/error validation, distinct malformed/invalid-contract/network/timeout/wrong-service codes, permitted cookie/header forwarding, SSE forwarding, bounded bodies and no-store responses are implemented.
8. Correlation IDs were not consistently propagated. Sanitized transport IDs now flow into backend envelopes through request-local context without changing shared contracts.
9. Session failures could leave stale UI permissions or interrupt recovery polling. Expired authority is cleared immediately; transport connectivity remains observable and polling restores current session permissions after verified recovery. Known production sessions are never automatically renewed as development-admin sessions.

## Exact changes

`implemented.patch` contains the complete original/replacement diff for this change, relative to the working copy at task start. The incremental review patches were shown before existing files were edited. Pre-existing database contention changes are excluded from the consolidated implementation patch.

Existing implementation files changed:

- `frontend/src/app/api/backend/[...path]/route.ts`
- `frontend/src/api/client.ts`
- `frontend/src/api/state.ts`
- `frontend/src/features/workflows/ApiFeedback.tsx`
- `frontend/src/screens/app.index.tsx`
- `workflow_api/main.py`
- `workflow_api/live_providers.py`
- `workflow_api/service.py` — only correlation context import/use added over the pre-existing working copy
- `scripts/run_live_backend.py`

Existing test files changed:

- `frontend/src/api/proxy.test.ts`
- `tests/test_customer_pipeline.py`
- `tests/test_integrated_procurement.py`
- `tests/test_live_providers.py`
- `tests/test_sheet_records.py`

Launcher fixtures now explicitly opt into local/test authentication rather than inheriting permissive launcher defaults.

New implementation files:

- `workflow_api/security.py` — origin/environment/deadline validation; no Google login implementation
- `workflow_api/planning_jobs.py` — scoped durable planning queue and worker
- `frontend/src/lib/backend-config.ts` — validated private server configuration
- `frontend/src/instrumentation.ts` — startup validation

New test/verification files:

- `tests/test_phase1_security.py`
- `frontend/src/api/phase1-proxy.test.ts`
- `frontend/src/api/planning-jobs.test.ts`
- `frontend/e2e/phase1.spec.ts`
- `frontend/playwright.phase1.config.ts`
- `docs/phase1-deployment.md`
- OpenSpec proposal/design/tasks/specification and review/evidence files in this directory

No shared contract or generated validator changed. No existing workflow, registry grant, revision approval or active release was rewritten. Existing edits in `runtime/service.py`, `workflow_api/lifecycle.py` and the pre-existing portions of `workflow_api/service.py` were preserved.

## New API and persistence

Session data adds optional `planning_jobs_available`; existing clients remain compatible. New authenticated transport endpoints are POST `/planning-jobs`, GET `/planning-jobs/{job_id}` and DELETE `/planning-jobs/{job_id}`. Existing synchronous POST `/workflows/plan` remains available.

The additive SQLite table `builder_planning_jobs` and queue index are created idempotently. No destructive migration is performed. Prompts/results remain in private backend storage; cancellation/termination clears request payloads. Queued jobs survive restart, interrupted expired claims fail visibly, and uncertain model calls are not automatically replayed. The job worker never executes workflow tools or publishes a workflow. Full production migration/versioning and worker separation remain Phase 2 responsibilities.

## Passing checks

- Complete backend suite: 355 pytest cases passed, plus 73 passing subtests, in 478.47 seconds. The 866 warnings are reported warnings, not failures.
- Required backend subset independently passed: 134 cases plus 29 subtests, covering new Phase 1 tests and workflow API/lifecycle/runtime/live-provider suites.
- Frontend unit tests: 137 passed across 20 files.
- TypeScript: passed.
- ESLint: passed.
- Production Next.js build: passed in isolated `.local/phase1-verification/frontend`, preserving the active UI build.
- Selected browser verification: 12 passed, desktop and mobile. Two use the real local proxy/backend/planning endpoints with an offline planner. Two use intercepted job responses for UI progress/cancellation. Eight existing scenarios cover prompt-only generation/manual/event flows and expired-session recovery.
- Authoritative contract validation: passed.
- Generated frontend-validator drift: passed.
- Strict OpenSpec validation: passed.
- `git diff --check`: passed.

`pytest` was initially missing and installed into the existing `.venv-integrations` environment. It was not counted as a passing check until installed and the tests actually ran. Intermediate failures found and corrected a proxy identity-probe case, an import typo, Next.js loopback normalization, a fake-timer test race, an isolated-build fixture path, an ambiguous browser alert assertion and stopped session-recovery polling. The passing results above are from corrected runs.

## Failing and unexecuted checks

No failures remain in the completed final checks above. The complete 355-case backend result is from an actual finished run, not inferred from the required subset.

Unexecuted/deferred: Google Workspace login and production identity/permission enforcement, real authenticated public HTTPS smoke tests, public firewall/reverse-proxy deployment changes, live paid-model generation, external email/connector writes, and the complete legacy browser/release suite assigned to Phase 7. `npm ci` was not repeated; verification used installed locked dependencies without changing package manifests or lockfiles.

## Deployment limits and reminder

The existing backend on 8002 and UI on 3001 retain the same process IDs; neither was restarted. Isolated browser services on 8011/3100 exited after verification. No credentials, firewall settings, production identity settings, workflow execution or live external writes were changed.

Loading these source changes into the active app requires a controlled restart with explicit matching local/test environment, origins and private upstream port. Exact commands and limitations are in `docs/phase1-deployment.md`.

Before public deployment, return to Google Workspace authentication: configure the OAuth web client and actual Workspace domain, validate individual identities, map workspace/roles/permissions server-side, enforce secure expiring sessions/CSRF and approval separation, and use trusted automation identities. Then verify real HTTPS routing and the full lifecycle. This work remains explicitly deferred, not complete.

## Subsequent user-authorized deployment

The user subsequently requested deployment and live verification. Both Builder services have now been restarted with the tested build and local-only configuration. Live HTTPS/local-session/origin/CSRF/network checks completed; public development sessions are blocked. See [live rollout verification](live-rollout-verification.md) for exact results, service IDs, background-activity observations and remaining production-authentication limits. This supersedes the earlier no-restart statement for current deployment status.
