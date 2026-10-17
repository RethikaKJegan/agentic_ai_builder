# Phase 7 verification

Scope: correction-plan sections 22–24. Production Google Workspace authentication remains deferred by user. This work repairs and runs the full release regression suite, fixes defects it exposes, and records remaining release blockers explicitly. No production authentication, shared contract, database schema or provider credential change is introduced.

## Root causes and exact edits

- Default browser configuration omitted explicit test origins/provider isolation, shared a persistent database and ran obsolete button/automatic-publication assumptions. It now runs every spec with one worker, a production frontend, exact test origins, real connectors explicitly off and a fresh temporary database. Browser-only Registry fixture tools have declared source inputs instead of falsely appearing ready with unresolved mappings.
- Legacy tests assumed runtime events were on the editable canvas. They now enter Execution, inspect the exact recorded graph and reselect a node after changing runs. Existing canonical grants, blocked-risk/approval cases, historical UUID and actual event assertions remain.
- The agent communication dialog was conditional on a currently loaded graph, so switching runs unmounted it; Workflow plan also received the selected historical revision. A stable configured-workflow prop preserves the dialog while exact historical revision reads remain separate. Whole-project communication is reachable without a root run without substituting a draft execution graph.
- Existing workflow loads discarded the authoritative registry_review. The editor now retains that review and displays actual blockers before action attempts.
- Added a complete real API desktop/mobile journey and settings/integration fault/recovery cases. Edited executable agent instructions still require fresh trusted Registry acceptance: the dedicated offline test server has an explicit tools.manage/admin/workspace-authorized operator checkpoint that calls real Registry validation and issues no tool grants. It is absent from production and rejects already-active workflows. This is fixture control-plane setup, not a product API or relaxed production policy.
- The old offline model always returned {}, which is invalid for hierarchy decisions. The explicit offline provider now returns a contract-valid finish decision; actual CrewAI/runtime behavior, budgets, events and failure paths still execute. Offline model/provider results are not claimed as live provider outcomes.

Exact originals/replacements were recorded before application in incremental review patches; final replacements are in [implementation-review.patch](implementation-review.patch).

Production frontend files changed:
- frontend/src/features/workflows/SheetAccessReview.tsx
- frontend/src/features/builder/Builder.tsx
- frontend/src/features/builder/ExecutionView.tsx
- frontend/src/screens/app.workflows.$id.tsx

Existing test/config code changed:
- frontend/e2e/sheet-access.spec.ts
- frontend/e2e/agent-communication.spec.ts
- frontend/e2e/api-integration.spec.ts
- frontend/e2e/baseline.spec.ts
- frontend/e2e/delegated-tools.spec.ts
- frontend/e2e/dynamic-delegation.spec.ts
- frontend/e2e/multitask-delegation.spec.ts
- frontend/e2e/project-agent-communication.spec.ts
- frontend/e2e/workflow-traces.spec.ts
- frontend/playwright.config.ts
- scripts/serve_ui_test_api.py

New artifacts: frontend/e2e/helpers.ts, frontend/e2e/phase7.spec.ts, frontend/src/api/phase7-release.test.tsx, frontend/src/api/phase7-registry-read.test.tsx, frontend/scripts/audit-phase7-actions.mjs, docs/phase7-release-verification.md and this OpenSpec change/matrix/inventories/evidence. No new production mutation/read endpoint or migration.

## Verification boundaries

Clean npm ci completed with 530 locked packages. package.json/package-lock.json remain unchanged. Initial offline attempts lacked the existing .npmrc and then tarballs; restoring repository configuration and fetching exact locked tarballs resolved installation. All 530 installed main-frontend versions match the clean installation. The live node_modules directory was not reinstalled. npm emitted upstream deprecation notices; no dependency upgrade or policy change was made.

Final frontend: 212 tests across 27 files pass; strict types and lint pass. Isolated Next.js 16.4 production build passes; final artifact ID **qE8U-c_-I5gXY-qvIVGw6**. Contracts/fixtures and generated validator drift pass. Strict Phase 7 OpenSpec and source diff integrity pass. Action inventory: 291 controls in 50 files.

The exact requested backend command passed **86 tests and 29 subtests** in 44.48 seconds (158 warnings). Required runtime dependencies are installed: CrewAI 1.0.0, FastAPI 0.143.0, pytest 9.1.1, psycopg 3.3.6 and OpenTelemetry SDK 1.45.1. pytest 9 supplies built-in subtests; a separate pytest-subtests package is unnecessary. pip check reports no broken requirements.

The comprehensive run executes all tests and connector_extension/tests with a real dedicated nonadministrative PostgreSQL database, installed CrewAI and offline provider transports. No skipped database/dependency result is counted as passing. Actual final totals, cleanup and live evidence are appended after completion.

## Failed/interrupted attempts

The first browser diagnostic run had 32 passing cases, 5 failures, 1 interrupted and 16 unexecuted after confirmed communication/Registry fixture problems. A test artifact was also rebuilt while that superseded server was using it, invalidating its journey attempt; the run was stopped and the final artifact was built only after test shutdown. A strict Testing Library type error in a new test was corrected. Subsequent focused runs exposed undeclared fixture tool inputs, a hidden collapsed lifecycle duplicate selector, missing explicit Registry acceptance for edited instructions, and a route-announcer alert matching a test's broad selector. Fixtures/selectors were corrected while preserving server denials. A further real journey reached execution and failed because {} was not a valid hierarchy model decision; the offline provider fixture was corrected. Final focused complete journey/failure/recovery: **3 passed in 27.8 seconds** on desktop/mobile, using actual canonical APIs and CrewAI. No unsuccessful attempt is counted as a passing final check. Existing expected missing/conflict paths emit Database transaction failed diagnostics, and upstream deprecation/telemetry warnings may appear; no zero-warning claim is made.

## Deferred and unavailable release acceptance

See [acceptance-matrix.md](acceptance-matrix.md). The real isolated journey tests every implemented lifecycle step, including editing an agent/branch, exact persistence, explicit Registry/revision approval, publication/activation, actual isolated execution, event/output inspection, controlled node failure and idempotent replay without extra runs.

Production public authentication/full public mutation journey is **unexecuted/deferred** because Google Workspace login was explicitly postponed. Supported side-effect-free product simulation is **unavailable**: the UI and tests expose that limitation and verify it does not create a run. Validation, mocked visual fixtures and offline real execution are not called successful product simulation. These remain production release blockers, so production_ready must stay false.

Live smoke remains read-only: no generation/save/decision/publication/activation/execution, provider probe, email or Sheets mutation is submitted. Normal configured background automation continues. The initial global workflow collection/overview remains unbounded. Production-managed policy editing remains unavailable, and changed executable agent definitions still need trusted operator Registry acceptance. No production readiness or provider delivery claim is made.

## Final comprehensive backend result

All **684 backend/connector tests passed**, **96 subtests passed**, **zero skipped**, in **990.58 seconds (16m30s)**. The run used actual isolated PostgreSQL across all configured PostgreSQL/concurrency/migration/API/runtime/connector fixtures and installed CrewAI; 1,194 warnings were recorded. No missing dependency was counted as passing. The dedicated test database, nonadministrative role and private connection file were removed after completion. This count includes the separately reported required 86-test backend subset; the counts are not added together.

## Final visual audit finding

The remaining sheet-access test still expected removed publication wording; after correcting its text assertion, the preserved desktop panel bounds check exposed a real defect: the panel began at x = -230 px. The obsolete desktop absolute positioning override was removed so the existing fixed viewport-bounded positioning applies at desktop/mobile widths. The targeted remaining visual run had 5 passes and this single bounds failure; the final full run is repeated after the production fix. No assertion was removed or weakened.

The all-spec diagnostic before the sheet-panel fix was stopped after exposing the obsolete Sheets text and the preserved bounds assertion. The corrected remaining visual subset passed five scenarios and failed only the desktop bounds check at x=-230. The release artifact was rebuilt after that fix, with a fresh complete browser run required; earlier partial/failed runs do not satisfy the final browser gate.


## Final browser and deployed verification

The final complete default browser suite passed **all 55 scenarios across 18 spec files in 3.6 minutes** after the Sheets panel fix. No required case was skipped. The final isolated production artifact **qE8U-c_-I5gXY-qvIVGw6** was loaded into the running frontend and its build identity was verified in the public HTTPS response. Exact four-file production source hashes match the tested checkpoint. The previous build and source originals are retained with a frontend-only rollback script under `.local/phase7-rollout/`; rollback was prepared, not exercised against production.

All **20 live HTTP checks passed**: HTTPS shell 200, HTTP redirect 301, unauthenticated public session/runs 403 without a session cookie, private anonymous runs 401, local authenticated proxy reads, invalid-origin and public-host rejection, invalid-origin mutation rejection before handling, pagination and event sequence bounds, filters, invalid page parameters, monitoring and worker health. These checks do not constitute an authenticated public production journey.

Live Chromium checks passed on **desktop (1440×1000) and mobile (390×844)**: editor Design/hierarchy, exact recorded execution, opening Agent communication, returning to the editable draft, monitoring filters and governance tabs. Public HTTPS shell and expected protected-session denial also passed. No page errors, failed static assets or direct private API browser calls were reported. The selected live workflow had only one communication run, so switching runs was not exercised against production; it is covered by the isolated browser regressions. The Sheets desktop/mobile viewport assertions passed in the complete isolated suite; those screenshots use explicitly mocked visual data, not live provider delivery.

Backend and worker retained their previous PIDs (3906013 and 3906022); only the frontend restarted (3928194). All three services are active with zero automatic restarts. Worker health shows one active worker and four ready components; older stale heartbeat records remain historical. No production workflow/provider mutation or database migration was performed. Private evidence includes `http-smoke.json`, `browser-smoke.json`, `editor-smoke.json`, `services-after.txt`, screenshots and the rollback checkpoint.

## Recorded release decision

Phase 7 implementation, test repair, automated verification and read-only deployed checks are complete. **Production readiness remains false**: Google Workspace production login/authenticated public lifecycle is deferred by the user, and supported side-effect-free product simulation is unavailable. No external provider delivery, real public authenticated lifecycle, production run-switch test or exercised rollback is claimed. The earlier automatic-review usage-limit rejection did not execute its smoke cell; after the user resumed, the authorized checks were executed successfully.
