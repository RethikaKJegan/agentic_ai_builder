- [x] Expose the record writer without mandatory environment destinations.
- [x] Validate prompt-owned metadata and bind execution to the reviewed workflow.
- [x] Show spreadsheet write access in the editor before publication.
- [x] Verify distinct spreadsheets, restricted targets, approvals and restart recovery.
- [x] Update setup documentation and validate Python/frontend/OpenSpec checks.

## Verification — 2026-10-12

- Full Python regression suite: 221 tests passed. Expected negative-case injection/Slack diagnostics remain visible.
- Frontend Vitest: 90 tests passed; typecheck, lint and production build passed.
- Playwright `e2e/sheet-access.spec.ts`: desktop and mobile checks passed (2 tests). Screenshots in `.local/sheet-access-desktop.png` and `.local/sheet-access-mobile.png`; mobile screenshot visually inspected.
- Shared contracts, generated-client drift, strict OpenSpec (zero issues) and diff formatting passed.

Backend cases exercise prompt-owned targets with no environment list, another spreadsheet ID, legacy targets, default action approvals, per-workflow isolation, forbidden redirects/operator-ceiling expansion, restart deduplication and both domain flows through actual runtime/Registry/CrewAI code with offline model/OAuth/HTTP transports. UI browser fixtures use mocked API responses to inspect scope visibility and panel bounds; they do not publish a live workflow. No live Google write, email, model call, credential edit, running-backend restart or deployment occurred. Google edit consent and automatic-write policy remain one-time setup. New workflow target selection requires no spreadsheet-specific environment edit.
