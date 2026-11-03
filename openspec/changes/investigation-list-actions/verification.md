# Investigation list actions — 3 November 2026

Deployed on https://praxi.bellcorpstudio.com/app/workflows in build `A8GKRkwv5mpFqeJJ5XTSx`.

## Behavior and files

`frontend/src/features/investigations/InvestigationList.tsx` adds a separate accessible three-dot menu beside each investigation link, persistent rename dialog, confirmed delete, busy/error states and current edit/delete permission checks. Menu clicks do not navigate. Existing cards, general workflows and graph execution remain available.

`frontend/src/api/client.ts` and `investigations.ts` add typed rename/delete calls and optional display names. Existing proxy PUT/DELETE methods are reused.

`workflow_api/business_investigations.py` adds owner/workspace-scoped presentation metadata without changing immutable objective, plan hash, knowledge or historical runs. Rename requires `workflow.edit` and workspace write; delete requires `workflow.delete` and workspace write. Delete is a retained-history tombstone: hidden from list and inaccessible for new execution. Active/queued work prevents deletion; run creation rechecks deletion in its write transaction. Stale plans can be cleaned up without executing or rewriting them.

`workflow_api/investigation_jobs.py` filters deleted rows before list limits and returns display names. `workflow_api/business_ontology_routes.py` exposes PUT and DELETE on the existing plan resource. No company records or shared execution contracts change.

## Verification

- Backend investigations/jobs, including new persistence, authorization, name validation, stale-plan cleanup and active-work guards: **46 passed**, 10 warnings, 117.88 seconds (`/tmp/investigation-actions-backend.log`).
- Existing investigation presentation suite: **6 passed** (`/tmp/investigation-actions-ui-tests.log`).
- Browser suite: **6 passed**, 30.5 seconds: two new desktop/mobile action journeys plus four existing graph/execution/evidence/input/error flows (`/tmp/investigation-actions-browser.log`). Fixture action tests verify error recovery, saved name after reload, canceled delete, confirmed delete and persisted absence. No production records are involved.
- Types, full lint, staged production build, shared contracts, UI contract drift, strict scoped OpenSpec and diff checks passed. Initial staging lacked the sibling shared-contract fixtures; the staging layout was corrected and the final build passed. No checks were skipped.

Public HTTPS browser acceptance passed normal sign-in, anonymous 401, list loading, desktop/mobile menus and both dialogs. All production rename/delete dialogs were canceled. Nonexistent-resource PUT/DELETE returned 404, verifying deployed routing without modifying existing workflows. Screenshots `menu-desktop.png` and `menu-mobile.png` were visually inspected. No browser errors or horizontal overflow. Live receipt: `.local/investigation-actions-release/public-check.json`.

Background queues were idle before restart. Consistent SQLite backup, preservation hashes and the old frontend build are retained in `.local/investigation-actions-release/`. Old static assets were retained for open browsers. Backend/worker/frontend are active. Original ontology versions, plan documents and run documents compared unchanged; the metadata table remained empty after live acceptance. Zero paid model calls or company writes.

## Try another supported goal

> Review replacement evidence for complaint A-2025-9-070. Compare its linked inspection with the original complaint and explain the recorded symptom where available. Prepare a source-backed report separating technical replacement recommendations from recorded commercial authorization. Identify agreements, differences and missing supporting evidence. Do not assess warranty or perform operational actions.

This combines comparison with replacement evidence review for a verified accessible complaint, using the existing capability catalogue. Actual authorization remains unknown unless supported; successful workflow completion does not imply commercial approval. This exact new prompt was not sent to a paid model during this UI task.
