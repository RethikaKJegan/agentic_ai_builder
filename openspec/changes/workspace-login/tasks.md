## Implementation
- [x] Add server-only credentials/session helpers and protected page/API routing.
- [x] Add styled login, landing links and logout.
- [x] Configure private local credential material and document deployment.
## Verification
- [x] Verify invalid credentials, tampering/expiry, CSRF and API bypass denial.
- [x] Run focused regressions, contracts, types, lint and production build.
- [x] Verify desktop/mobile login, refresh and logout with isolated browser fixtures.

## Evidence — 22 October 2026

- 56 focused authentication/proxy/session-recovery tests passed; 75 domain/planning/runtime/Registry UI tests passed (131 frontend tests total).
- 62 Python security, Google callback, procurement planning and inventory-report runtime tests passed. The inventory fixture verifies separate Sheet/email/calendar approvals and actual created Sheet links, with fake providers only.
- TypeScript, ESLint, isolated Next.js production build, canonical contract validation, strict scoped OpenSpec validation and diff whitespace checks passed.
- Three production-browser scenarios passed: desktop and mobile login (bad password, success, shared subject/permissions, refresh, integrations navigation, logout, back navigation, re-login and local storage preservation), plus landing Launch Workspace navigation.
- Browser identity remained local-builder/local-workspace; website login grants no backend permissions. Signed provider ingress preserves existing backend verification.
- Private local configuration: frontend/.env.local (hash/signing secret), .local/workspace-login-credentials.txt (generated eight-digit password). Neither tracked. Preview: .local/workspace-login/login.png.
- Isolated artifact: .local/workspace-login/frontend. Live frontend/backend/worker not restarted or deployed. No cloud database or Google provider calls/writes were made for this change; source connections, workflow records and browser draft keys were not modified.
- Existing unrelated WorkflowControls.tsx/banner change, its OpenSpec artifact and the pre-existing deleted cache log were preserved.
- Initial browser verification exposed Next proxy's absolute redirect requirement; corrected and added TLS-gateway redirect coverage before final passing verification.

## Authorized live deployment — 22 October 2026
- [x] Retain previous frontend artifact and deploy the verified login build with existing server environment.
- [x] Verify public HTTPS login, protected API, workspace identity and connection IDs.
- [x] Verify desktop/mobile Launch Workspace → login → /app and logout on the live website.

Live deployment completed on 22 October 2026 with the existing frontend environment and private login configuration. Public HTTPS checks passed: anonymous API returns 401, valid login returns 200 with Secure/HttpOnly/SameSite cookie, /app loads, backend auth/permissions and saved database/Google connection IDs match the before-deploy snapshot, logout blocks API access again. Live desktop/mobile browser checks passed Launch Workspace → /login → /app, refresh, logout and direct-app protection with zero browser exceptions. Backend PID 296193 and worker PID 296194 remain unchanged. No workflow executions or Google/provider writes were performed. Evidence: .local/workspace-login/live-http-verification.json and live-browser-verification.json. Previous build retained at .local/ui-rollbacks/workspace-login-20261022-final/previous.next. An initial verification assertion incorrectly expected capitalized cookie attributes; it triggered automatic rollback. Corrected that check to case-insensitive matching, then redeployed and verified successfully.
