# Phase 6 verification

Scope: correction-plan sections 19–21. Phase 1–5 and unrelated user changes are preserved. Production Google Workspace login remains explicitly deferred. No shared schema, table or migration change is introduced.

## Root causes corrected

- Run collection status filtering occurred after LIMIT and never issued a usable next cursor. GET history now applies workspace/workflow/status/date filters before keyset pagination with explicit bounded pages. Persisted event sequences support paginated recovery without rewriting stored evidence.
- Run/event refreshes could overlap; old selected data could disappear after interruption; terminal history could poll indefinitely. A shared in-flight read helper and serialized feed retain confirmed data, resume by sequence with bounded backoff, drain remaining event pages and stop terminal-run polling. Workflow overview no longer runs finite SSE alongside interval snapshots.
- Monitoring materialized all runs and workflow documents. SQL aggregates replace full run decoding; latest/audit, trigger and enforced-revision documents are bounded. Readiness pages have independent cursors.
- Runtime decision authorization accepted any workspace member rather than the exact gate role. Decisions now enforce workflow.approve, exact recorded gate roles and workspace membership. Public projections show required roles and eligible actions. Confirmed decision retries retain their original gate identity when a later gate exists. Historical approvals display their own recorded gate.
- Trigger preparation could be confused with provider connectivity or actual activation. Monitoring shows release state, provider/type/source/schedule, preparation and poll evidence. Configured live activation rejects missing polling connectors/grants/resources, unsupported incoming adapters and missing webhook signing secrets. Existing signatures, deduplication and Registry revalidation remain enforced.
- Browser policy editing used local role flags and effective draft labels could imply enforcement. Draft edit UI now requires a server-authenticated administrator; browser-only rules stay separate from read-only enforced revision scope/version. Wrapped governance tabs now grow vertically on mobile.

## Exact existing-code edits

Originals and exact replacements were shown before applying each incremental patch. The consolidated [implementation review](implementation-review.patch) contains the final reviewed replacements. Existing files changed:

- `frontend/e2e/session-recovery.spec.ts`
- `frontend/src/api/client.ts`
- `frontend/src/api/integration.test.tsx`
- `frontend/src/api/state.ts`
- `frontend/src/features/builder/ExecutionView.tsx`
- `frontend/src/features/builder/NodeTrace.test.tsx`
- `frontend/src/features/builder/useWorkflowTrace.ts`
- `frontend/src/features/governance/AgentControlTab.tsx`
- `frontend/src/features/runs/ServerRunView.tsx`
- `frontend/src/screens/app.governance.tsx`
- `frontend/src/screens/app.integrations.tsx`
- `frontend/src/screens/app.monitoring.tsx`
- `frontend/src/screens/app.workflows.index.tsx`
- `runtime/graph.py`
- `runtime/service.py`
- `tests/test_runtime.py`
- `workflow_api/activation.py`
- `workflow_api/live_providers.py`
- `workflow_api/main.py`
- `workflow_api/trigger_sources.py`

New implementation/test artifacts: runtime/history.py, frontend/src/features/runs/useRunFeed.ts, frontend/src/api/phase6-runtime.test.tsx, frontend/e2e/phase6.spec.ts, frontend/playwright.phase6.config.ts, frontend/scripts/audit-phase6-actions.mjs, tests/test_phase6_runtime.py, tests/test_phase6_postgres_runtime.py, docs/phase6-runtime-readiness.md, and this OpenSpec change/evidence. No new mutation endpoint or production policy editing API. Existing GET routes accept compatible query parameters; canonical operation payloads and shared contracts are unchanged.

## Verification results

- Frontend: 210 tests across 25 files passed, including 9 new Phase 6 tests. Final strict TypeScript and ESLint pass without lint warnings.
- Canonical schemas/fixtures and generated UI contract drift pass; strict Phase 6 OpenSpec and diff integrity pass. Current action inventory: 291 controls across 50 files. SQL inventory: 390 calls, retained separately from historical Phase 2 evidence.
- Initial backend combined suite: 171 passed, 23 subtests passed, 306 warnings. Final affected approval/history/lifecycle run: 79 passed, 23 subtests passed. New Phase 6 standalone run including the two-gate history case: 14 passed. Final combined rerun and rollout evidence recorded below after completion.
- Real PostgreSQL: 61 tests and 23 subtests passed (146 warnings) before the final original-gate replay refinement; final same-suite rerun recorded below. Disposable database/role/connection state is removed by the verification runner. No production PostgreSQL cutover.
- Isolated Next.js 16.4 production build passed; final artifact BUILD_ID GiTNNMbzBigpDNyu8LzfS.

## Failed attempts corrected

An initial new history syntax error was corrected before deployment. Two old backend tests expected unauthorized workspace members to approve unknown roles; they now assert rejection and unchanged approval-waiting state. Old frontend fixtures omitted runs.view, new trace paging properties or expected a different historical error phrase; fixtures/messages were corrected. Strict optional cursor types and independent trigger/policy paging were corrected. Initial isolated build lacked the shared fixture directory; adding the shared-contract link resolved its typecheck failure. An actual nullable approval action digest was accepted compatibly. First browser run: 25 passed, 3 failed (mobile governance tab overlap and two 12-second waits incompatible with the documented 15-second polling interval). Tab wrapping was fixed; recovery tests now cover two cycles with a 60-second test bound and retain all authorization/recovery assertions. No failed attempt is counted as passing. Expected test missing/conflict paths can emit existing Database transaction failed logs; no zero-warning claim is made.

## Limits and checks not performed

Google Workspace production authentication and successful authenticated public API requests remain deferred by user; public development sessions remain denied. Live verification is read-only: no generation, save, decision, publication, activation, execution, provider probe or email/Sheets mutation is submitted. Normal configured background automation resumes after the controlled restart. Provider browser tests use explicit offline fixtures against the real isolated API.

The global workflow collection and initial workflow overview remain unbounded and may be slow with more than 53,000 workflow records. Phase 6 paginates run/event/readiness history and removes duplicate SSE polling; it does not claim a complete workflow-discovery scaling change. Monitoring counters still aggregate the workspace population in SQL. Browser-only policy drafts remain non-enforcing; production policy edit controls remain unavailable. Existing gates with unassigned approver roles fail closed and are not rewritten. Safe simulation remains unavailable. The complete Phase 7 release journey/full repository verification remains unexecuted.

Private live backup/rollback/service/build/HTTP/browser evidence is kept under .local/phase6-rollout. Rollback restores prior source and frontend build while preserving current business data; database snapshots must not be restored over later writes without a separate recovery decision.

## Final predeployment acceptance

Final combined backend run: **172 passed, 23 subtests passed**, 306 warnings, 82.00 seconds. Final real PostgreSQL run after original-gate retry refinement: **61 passed, 23 subtests passed**, 146 warnings, 71.88 seconds; temporary role/database/private connection file removed. Final frontend: **210 passed across 25 files**; strict types/lint pass. Final production browser artifact: **28 passed in 2.2 minutes** on desktop/mobile, including the corrected wrapped tabs and two-cycle session recovery. Build ID **GiTNNMbzBigpDNyu8LzfS**. No required check is failing.

## Completed live deployment

The controlled rollout completed on 2026-10-17. Exact verified BUILD_ID **GiTNNMbzBigpDNyu8LzfS** is active and appears in the public HTTPS app response. API PID **3906013**, worker PID **3906022**, frontend service PID **3906014** (Next child **3906029**) are active with zero restarts. Backend/frontend listeners remain **127.0.0.1:8002** and **127.0.0.1:3001**. No nginx, firewall, DNS, production credentials or identity-provider configuration changed.

Four fresh SQLite backups totaling approximately 2.5 GB were created after graceful worker/API/frontend shutdown and before restart, with private manifests and all table counts. The live table set and selected append-only workflow/run/event/idempotency/release/receipt counts were verified against the backup without loss. Background activity may add rows after restart; no point-in-time equality claim is made for mutable job/lease state. No schema migration, production PostgreSQL cutover or snapshot restore occurred.

**19 read-only HTTP checks passed**: exact public build and HTTPS 200, HTTP redirect, public development session/API rejection without login issuance, anonymous backend rejection, invalid origin/Host rejection, authenticated local proxy reads with no-store/request IDs, bounded run/event cursor pages, workflow filter, monitoring page bound and invalid filter/cursor rejection, worker health. The live bounded monitoring sample completed in **3.301 seconds**; this is one measurement, not a general performance guarantee.

Live desktop/mobile browser checks passed monitoring, status/date controls and browser-draft/enforced governance tab navigation; no page errors, failed assets or direct private-backend browser requests were observed. Mobile governance screenshot was inspected and wrapped tabs are usable. Public HTTPS shell returned 200 and protected development session returned 403 as intended. Exactly one current worker and all four current components were ready with no reported errors; historical stale/stopped worker/component records remain evidence.

Private evidence: .local/phase6-rollout/completion.json, services-before.txt/services-after.txt, source-checkpoint.json, database-backup-manifest.json, persistence-check.json, http-smoke.json, browser-smoke.json, worker-health-final.json, screenshots and rollback.py. Prior Phase 5 frontend artifact/source are retained. No required Phase 6 test or live smoke check remains failing. Full Phase 7 verification and Google Workspace login remain pending.
