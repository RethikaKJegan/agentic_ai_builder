- [x] Define additive connection API contract and migrations.
- [x] Implement backend OAuth, persistence, refresh and disconnect.
- [x] Add safe callback proxy handling and Google connection UI.
- [x] Verify security/lifecycle cases, frontend checks and browser flows.
- [x] Deploy and document exact external Google configuration requirements.

Verification: 12 focused backend OAuth tests passed; preceding full run also passed 24 existing deployment/authentication tests. Frontend strict types, scoped ESLint, 28 Google UI/proxy tests, isolated production build, shared contracts, strict OpenSpec and whitespace checks passed. Google provider responses are mocked only in automated lifecycle tests; no real successful consent is claimed.

Deployment: frontend build rollback `.local/ui-rollbacks/google-phase1-20261017-164557`. API restarted for additive routes; background worker stayed active. Exact GET callback Nginx location installed and validated with `nginx -t`, with access logging disabled; existing other route protections retained. Nginx pre-change configuration is `.local/google-nginx-before.conf`. Temporary preview 3100 stopped after verification.

Public read-only UI checks: 1366×768 and 390×844, all seven capability options present, no horizontal mobile overflow, no browser errors. Live callback cancellation returned 303/cancelled and replay returned expired. Google authorization endpoint returned redirect_uri_mismatch: administrator must register `https://praxi.bellcorpstudio.com/api/backend/integrations/google/callback` on the existing web OAuth client. Real Google consent, account verification against a connected account, token refresh and reconnect remain manual acceptance checks after registration. No accounts, email sends or workflow tool bindings were changed by verification. The existing shared demo identity is explicitly shown in UI; separate personal user isolation is not supplied by this phase.
