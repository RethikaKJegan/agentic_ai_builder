# Phase 4 verification — 2026-10-17

Scope: correction-plan sections 12–16. Preserve prior Phase 1–3 and original user changes. Google Workspace production login remains deferred; public development authentication stays forbidden. SQLite remains live.

## Root causes and resulting behavior

- Generation forced automatic inputs and navigated directly to the editor. It now offers manual/automatic input choice, saves only a draft, presents the actual structured proposal, and requires explicit opening. Original prompts survive failures; retries and regeneration are explicit. Existing saved identities and dirty drafts are preserved.
- Editor mixed topology, presentation hierarchy and runtime status. Design, Agent hierarchy and Execution are separate views. Canonical delegated templates without graph nodes are included in hierarchy. Unsupported presentation semantics are labeled non-executable.
- Old run events overlaid the latest draft. Execution now atomically loads the exact run/version, events and historical agent definitions into a separate read-only graph, with safe loading/failure states and no unrelated fallback. Switching back preserves dirty edits.
- Timestamp sorting could reorder causal events. Read responses add the existing database sequence to event details without changing stored evidence or shared v1 schemas. Reconciliation validates identity/sequence and preserves legacy database order. Missing events do not imply completion.
- Overview could not distinguish latest published revision from the active revision. A new authenticated, workspace-scoped read endpoint exposes exact release identity/version/state and binding count without modifying the existing strict overview DTO.
- Mobile steps followed array insertion order, canvas could be squeezed by panels, keyboard connection editing was absent, and drag Undo captured the moved position. Dependency outlines, directed branch labels, local diagnostics, keyboard connection/removal, minimum canvas height and pre-drag history address those defects. React Flow and existing domain commands remain in place.

## Passing checks

- Frontend: **177 tests across 23 files**. Includes generation failure/prompt retention, explicit review/regeneration, dirty existing drafts, exact historical revisions, stale-response races, permissions, event sequence/identity, canonical hierarchy templates, graph diagnostics/order and keyboard connection controls.
- TypeScript and ESLint pass. Isolated Next.js 16.4 production build passes; staged deployment BUILD_ID `dSlxNhmnLRdenNgrcLhpm`. The active build is untouched until controlled rollout.
- Relevant API/lifecycle/runtime/security/worker/contention backend regression: **154 passed, 29 subtests passed** in 51.89 seconds. Earlier focused suite: **80 passed, 23 subtests passed**. These overlap and are not summed.
- Actual isolated PostgreSQL: **21 passed, 3 subtests passed** in 19.98 seconds. Includes six new release/event-sequence boundaries, seven Phase 3 action cases and eight existing runtime acceptance cases. The dedicated nonadministrative database, role and private connection file were removed after testing. Production PostgreSQL was not changed.
- Corrected production browser run: **18 passed** on desktop/mobile. The final deployed frontend artifact also passed all 18 scenarios in 1.1 minutes, including canonical hierarchy templates and the corrected manual-input generation journey. Scenarios cover real isolated API lifecycle transitions, exact v1 historical graph under edited v2, retained draft switching, canonical hierarchy, keyboard connect/undo/redo, save/reload, manual generation review, typed execution, settings, cancellation and session recovery. Offline fixtures never replace product APIs.
- Shared schemas/fixtures, generated validator drift, strict Phase 4 OpenSpec, Python syntax and SQL inventory pass. Current Phase 4 action audit: **272 source controls across 47 files**; SQL inventory **380 calls**. Phase 3 action inventory remains its historical checkpoint; the Phase 4 script/matrix is the current supplement.

## Failed attempts corrected

Initial new tests assumed the minimal support-triage fixture contained agents/conditions; explicit real agent and invoice fixtures corrected those assumptions. An unprivileged-role test initially supplied an empty role list, which the existing local fixture interprets as its builder default; it now explicitly revokes read permission on the test server and confirms 403. A deferred promise test needed an explicit TypeScript type.
The first browser attempt had 12 passes and six failures: two outdated Generate workflow assertions after cancellation (the recovery button is now Retry generation), two hidden dropdown-option matches for a run ID, and two real generation failures caused by forcing automatic source mode. The input-source choice fixes the product defect without relaxing validation; the other selectors now target the correct visible behavior. No failed run is counted as a pass.
One backend test fixture emitted the existing Database transaction failed log during a conflicting/idempotent browser planning path; the browser suite completed successfully. No zero-warning claim is made.

## Exact existing files modified

See [consolidated exact original/replacement patch](implementation-review.patch) and the incremental review patches shown before applying existing-code edits. New files were added separately.
- `frontend/e2e/phase1.spec.ts`
- `frontend/e2e/prompt-only.spec.ts`
- `frontend/src/api/client.ts`
- `frontend/src/api/control.ts`
- `frontend/src/features/builder/AgentCommunication.tsx`
- `frontend/src/features/builder/Builder.tsx`
- `frontend/src/features/builder/MeshNode.tsx`
- `frontend/src/features/builder/NodeTrace.test.tsx`
- `frontend/src/features/builder/NodeTrace.tsx`
- `frontend/src/features/builder/useWorkflowTrace.ts`
- `frontend/src/screens/app.index.tsx`
- `frontend/src/screens/app.workflows.index.tsx`
- `runtime/service.py`
- `workflow_api/main.py`
- `openspec/changes/phase2-backend-reliability/sql-inventory.json` (generated review inventory; exact change in sql-inventory-review.patch).

## New components, API and migration status

New components: LifecycleJourney, PlanReview, GraphTools, HierarchyView and ExecutionView; pure graph-review domain helpers; read-only workflow_api/release_read.py; Phase 4 action audit script/matrix; frontend/backend/PostgreSQL/browser regressions and isolated Playwright configuration. GET `/workflows/{workflow_id}/release-state` requires workflow.view and existing session/origin controls; it returns only release ID/version/state/binding count. No new mutation API, credentials, connector action or database migration is introduced. details.recorded_sequence is additive within the existing event details object.

## Live rollout

The initial Phase 4 rollout completed. The worker drained cleanly and stopped, then the API stopped. Four SQLite backups were created privately. After updated API startup and before worker restart, **all 57 preexisting table counts matched**: main 30 tables / 1,020,315 rows; procurement 24 tables / 2,469 rows; effects one table / 157 rows; sheet resources two tables / 49 rows. This is row-count preservation, not a content-hash claim. Source originals for 14 existing files and the previous Phase 3 frontend build are preserved privately for rollback. No database snapshot was restored over new activity.

Live HTTP smoke passed HTTPS application 200, HTTP redirect 301, anonymous protected backend read 401, authorized local backend/proxy/settings/release-state 200, invalid origin/Host rejection, propagated request IDs and no-store, public development session/API 403 without a session cookie. The API and frontend remain loopback-only on 8002/3001. All three services are active with zero restarts. Worker health confirms exactly one active worker and all four current components ready without reported errors; historical old worker health rows remain stale history. Database telemetry at the final read reported zero contention/failures, with seven slow transactions.

Real read-only live desktop/mobile browser smoke passed Design, Agent hierarchy, exact historical execution, return to the draft, local runtime/session reads and public HTTPS loading, with no page errors, failed static assets or direct private-backend browser calls. Screenshots were visually inspected. This inspection found a publication-label race while global overview was loading; the guide now falls back to publication confirmed in the exact workflow document, and a new regression verifies it. Historical display layout was also made readable without changing saved design positions. The final frontend-only build `dSlxNhmnLRdenNgrcLhpm` passed all 18 browser scenarios, was loaded by restarting only the frontend, and passed the live desktop/mobile/public-HTTPS browser smoke again. The API and worker stayed running during this frontend-only refresh. Final screenshots confirm accurate publication state and readable historical paths. Final source types, lint and diff checks pass.

The first live browser smoke assumed a successful extra overview response and failed while selecting history. Follow-up read measured **53,563 overview items in 15.539 seconds**. The corrected smoke selects through the existing bounded run collection and passed. This existing unbounded overview can be slow or unavailable under concurrent load; it remains a real performance limitation for later pagination/monitoring work, not a claimed Phase 4 performance fix. No product API was mocked, data deleted or mutation replayed to pass smoke. Private evidence: `.local/phase4-rollout/`.

## Remaining limits and unexecuted checks

- Safe runtime simulation remains explicitly unavailable: no supported side-effect-free simulation adapter is connected. Validation is never presented as simulation or real execution. This is a displayed unavailable lifecycle stage, not a fabricated success.
- No live model generation, SMTP/provider verification, manual execution, trigger delivery, approval, publication, settings mutation, email or Sheets write is submitted by deployment smoke. Existing configured background worker activity resumes normally after restart. Isolated browser execution uses explicit offline connectors.
- Google Workspace production identity and successful authenticated public API requests remain deferred by user instruction. Public API/session rejection is intentional. Live provider connectivity is not inferred from configuration or trigger-binding count.
- The existing unbounded global overview has more than 53,000 items and can be slow/time out under concurrent reads. Pagination/scaling remains later work. No SQLite-to-PostgreSQL cutover, automatic conflict merge, broad run pagination or streaming redesign occurs here. Shared contracts and authoritative server validation remain intact. The full 511-test backend/connector suite passed in Phase 3; Phase 4 runs the relevant 154-test backend suite plus separate real PostgreSQL checks, not a new full-suite claim.

Operating behavior: docs/phase4-workflow-journey.md. All tests and backup artifacts stay inside this Builder repository. No unrelated application is changed.
