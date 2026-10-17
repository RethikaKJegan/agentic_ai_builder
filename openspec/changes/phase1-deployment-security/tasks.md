- [x] Implement and test exact origin handling and private live/test routing.
- [ ] DEFERRED by user: Google Workspace production login, identity/permission mappings and production smoke verification.
- [x] Enforce fail-closed production startup and explicitly local/test development sessions.
- [x] Harden and test API proxy, cookies, errors, correlation, request limits, SSE and timeouts.
- [x] Add durable scoped planning jobs, cancellation and frontend progress.
- [x] Run required backend/frontend regression checks and record passing/failing/unexecuted results.
- [x] Record deployment configuration, risks, exact patches and production verification limits.

## Final verification

355 backend cases and 73 subtests passed; 137 frontend tests passed; 12 selected desktop/mobile browser scenarios passed. Types, lint, isolated production build, contracts, generated-validator drift, strict OpenSpec and diff checks passed. Full evidence: `verification.md`. Production Google Workspace authentication and public HTTPS smoke verification remain explicitly deferred. Existing live services were not restarted.

## Authorized live rollout follow-up

- [x] Load the tested build and restart the two managed Builder services.
- [x] Verify real HTTPS routing/TLS, local authenticated reads, missing/expired sessions and invalid-origin/CSRF rejection.
- [x] Verify loopback listeners and probe the public hostname on known application ports.
- [x] Verify desktop/mobile live browsers without workflow execution.
- [ ] DEFERRED with Google Workspace: successful authenticated public requests and production identity-bound session/CSRF/permission verification.

Evidence: `live-rollout-verification.md`. Public HTML remains reachable; public API development sessions are intentionally rejected.
