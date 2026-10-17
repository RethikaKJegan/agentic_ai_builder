# Phase 3 verification — 2026-10-17

Scope: correction-plan sections 8–11. Earlier Phase 1/2 and existing user changes are preserved. SQLite remains live; Google Workspace production login remains deferred. Public development authentication remains blocked.

## Implemented behavior

- Separate Save draft, Validate, Submit for approval, Approve, Publish and Activate, each with state/permission explanations. Publication never implies approval or activation. Activation confirms trigger execution implications.
- Durable explicit approval submission uses existing revisions/mutations, exact revision/base checks, Registry readiness and idempotency. Shared v1 schemas/statuses remain unchanged. Submitted revisions have a review queue. Current status, server revision, actual confirmed saved time and Registry blockers are visible.
- Dirty drafts survive browser reload; background fetches do not overwrite them. Save results preserve newer edits entered in flight. Revision conflicts retain edits and offer explicit reload/reapply. Shared navigation, browser Back and unload warn before leaving dirty workflows. Duplicate agents are isolated; old approval/binding metadata is cleared. Saved revisions can be inspected without replacing current drafts.
- Run published loads the actual published schema, requires execute permission/runtime/publication, validates each canonical input type, supports cancellation, blocks event-only manual runs, preserves entered values/errors and durable retry identity, and links confirmed run IDs/status to exact details. Conflicting/duplicate run-detail loads are guarded.
- Settings validates HTTP/envelope/value confirmation, loads server state before enabling edits, checks administrative authority, rejects invalid/secret values, retains input on failure and displays success only after confirmation.
- Integration configuration and actual verification are separate. Unsupported live checks stay unverified. Only a server-installed trusted SMTP AUTH/NOOP probe supports live verification, without sending mail. Browser credentials/destinations are rejected. Failed probes return safe connection-failed state.
- Knowledge/reply loading and failure states are corrected; local governance/agent effects are explicitly draft-only; destructive local/server actions confirm.
- Complete source action inventory: **242 source controls across 42 files**. The matrix records every location/handler and its owner behavior, APIs, permissions, feedback and actual coverage. Native/form/primitive delegation is explicit; no claim is made that every unused primitive has a dedicated browser test.

## Passing checks

- Frontend: **161 tests passed** across 21 files. Tests cover explicit transitions, denied states, cancelled activation, in-flight edits, conflicts, persistence/navigation, typed run inputs, cancellation/deduplication, stable retry keys across clients, history viewing, review queue, settings failure/unknown initial state, and integration truthfulness.
- TypeScript and ESLint passed. Final isolated Next.js 16.4 production build passed (BUILD_ID `OjE7A5YMwIsURDKRrUBOK`), including type checking; the active frontend build was not modified during build/test.
- Relevant backend lifecycle/runtime/security/worker/provider suite: **168 passed, 29 subtests passed** before the final published-overview correction. Focused final lifecycle/overview/Phase 3 regression: **43 passed, 11 subtests passed**.
- Customer/reply behavior: **14 passed, 2 subtests passed**. The initial command named a nonexistent reply-policy test file and ran no tests; it was corrected to the repository's actual reply tests and is not counted as a pass.
- Real PostgreSQL: **27 passed, 6 subtests passed**, comprising existing Workflow API acceptance and seven new Phase 3 action boundaries. Uses a dedicated isolated nonadministrative role/database, including approval submission, confirmed timestamps, settings permissions/validation, honest integration checks and published-without-activation overview. The temporary database, role and private connection file were removed after testing; production PostgreSQL was not changed.
- Production browser suite: **14 scenarios passed** on desktop/mobile for real isolated lifecycle transitions, typed deterministic execution, settings save/reload, event-only/manual distinctions, planning progress/cancellation and session recovery. The final-artifact rerun also passed all 14 scenarios in 48.8 seconds.
- Canonical schemas/fixtures and generated client drift pass. Strict Phase 3 OpenSpec, Python syntax, source action inventory drift, SQL inventory drift and `git diff --check` pass. SQL inventory now includes 378 calls.

## Failures found and corrected

Initial backend checks found an invalid timestamp clock reference; it now uses the service lifecycle's configured clock. Initial TypeScript checks found a duplicated-agent origin mismatch and React 19 ref/test API mistakes; these were corrected without disabling checks.

The full initial frontend run exposed old assertions expecting chained publication/simulation and SQLite-era assumptions in fixtures. They now assert explicit independent actions and real runtime availability. A duplication test fixture initially had no agents; it now supplies a real canonical agent definition and verifies clone isolation.

The first browser attempts used a removed Overview control, the wrong persisted-draft version, and an approved fixture labeled published. Those fixtures were corrected. The explicit run dialog requires Start run; old immediate-execution tests now make that explicit interaction.

Crucially, the real browser found an application defect: overview `published_version` depended on an activated release. It now queries actual published revisions independently, so manual Run published works before activation and remains available under a newer draft. Release identity/state remain independent. Focused SQLite and actual PostgreSQL regressions verify this behavior.

One lint attempt included a temporarily staged compiled build directory inside `frontend`; the staged artifact was moved to the private rollout directory and source-only ESLint passed. No lint rule was disabled.

No failed run is included in passing totals. Offline/mock provider responses in automated tests are verification fixtures, not replacement product APIs or proof of live provider credentials. No live SMTP test, model call, workflow execution, approval, settings mutation, email or Sheets mutation is submitted by deployment smoke.

## Completed regression and live rollout

The full SQLite/backend/connector suite completed: **511 passed, 73 subtests passed**, in 678.52 seconds (914 warnings, no failures). PostgreSQL-only suites were excluded from that SQLite invocation and verified separately as described above. The full run began before the final published-overview correction; the focused final 43-test suite and real PostgreSQL cases verify that correction. The final frontend artifact also passed all 14 browser scenarios.

The controlled live rollout completed on 2026-10-17. The worker drained and stopped cleanly, followed by the API. Four private SQLite backups were created before API restart. After the updated API started, all **57 preexisting tables** retained their row counts: 30 main tables (1,011,929 rows), 24 procurement tables (2,469 rows), one effect table (157 rows), and two sheet-resource tables (49 rows). These checks verify table counts, not content hashes. The tested frontend BUILD_ID `OjE7A5YMwIsURDKRrUBOK` replaced the active build; the previous build and 28 existing-source originals remain available for rollback. Workers resumed only after preservation checks passed. No database snapshot was restored over live activity.

Live read-only HTTP checks passed: HTTPS application 200, HTTP-to-HTTPS 301, anonymous backend read 401, authenticated local backend/proxy reads 200, invalid origin/public backend Host rejected, public development session/API 403 without a session cookie, propagated request ID and `Cache-Control: no-store`. Desktop/mobile local and public HTTPS browser checks passed with no page errors, failed static assets or direct private-backend browser requests. API, frontend and worker services are active with zero restarts. Worker health confirms exactly one active worker and all four current components (TriggerScheduler, RuntimeWorker, ProcurementWorker, ReplyWorker) ready with no reported errors. Historical stopped-worker health rows remain visible as stale history. Both HTTP listeners remain loopback-only on ports 8002 and 3001. Private evidence is in `.local/phase3-rollout/`.

Exact reviewed existing-file changes are consolidated in `implementation-review.patch`; incremental patches remain alongside it. New files and operating behavior are documented in `docs/phase3-ui-actions.md` and `live-rollout-plan.md`.

Google Workspace public login and successful authenticated production API requests remain deferred. Live provider connectivity is not claimed verified by configuration checks. Historical failed/blocked runs are preserved, not silently repaired. No live database migration occurs in Phase 3.
