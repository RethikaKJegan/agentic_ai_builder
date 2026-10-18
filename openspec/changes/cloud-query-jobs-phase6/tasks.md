## Implementation
- [x] 1. Durable queue, admission, ownership, encryption/expiry and fenced recovery
- [x] 2. Execution progress/cancellation hooks and worker lifecycle integration
- [x] 3. Versioned job contract, API routes and refresh-safe Questions UI
- [x] 4. Lifecycle, cancellation-race, recovery, permission and real database tests
- [x] 5. Frontend tests/types/lint/build and desktop/mobile browser acceptance
- [x] 6. Document precise limits, deploy verified artifacts and verify live jobs

## Verification — 2026-10-18

178 backend tests; 103 frontend/domain/proxy tests; types/scoped lint/production build; ten desktop/mobile production browser fixture checks; shared contracts and strict OpenSpec passed. Actual PostgreSQL cancellation, process-kill recovery, PostgreSQL-store claim competition and publication races were verified in isolation. Live real-model federation matched all eight independent category sums/weighted averages across 2,155 facts; the same job/result remained available after API restart and browser refresh. A second active job cancelled and exposed no result. Three observed fragments transferred 24 records / 2,744 serialized bytes in 12.775 s execution time. Persistence checks verified successful ciphertext and no cancelled-result ciphertext. Raw aggregate rows were removed from Phase 6 JSON captures after equal canonical SHA-256 comparison.

API/frontend/worker active. Frontend rollback: `.local/ui-rollbacks/query-jobs-phase6-20261018/.next`. Scope, configured time/retention limits, cancellation semantics, existing development identity boundary and legacy synchronous API behavior are documented in `docs/cloud-query-jobs-phase6.md`. No cloud data, credentials or review decisions changed; no contributor acceptance or broader legacy test claim is inferred. Evidence logs: `.local/query-jobs-*`; public verification: `.local/query-jobs-phase6/public-jobs.json`.
