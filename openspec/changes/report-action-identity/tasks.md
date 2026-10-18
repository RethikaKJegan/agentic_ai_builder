- [x] Reproduce and correct report identity collisions without weakening fingerprint checks.
- [x] Verify retries, new runs, changed/uncertain inputs and downstream action identities.
- [x] Run connector/native-runtime regressions, contracts and scoped OpenSpec checks.
- [x] Deploy and verify service readiness without executing external actions.

Deployment: backend/worker restarted and both services are active; session
returned HTTP 200 and the current RuntimeWorker reports ready. No workflow was
started and no Google action approved or executed by this verification. Existing
workflow v2 and historical failed runs remain unchanged. Live end-to-end success
after this deployment still requires a new run and the user's action approvals.

Evidence: read-only inspection found the old fixed report effect completed and
its report hash different from the failed run's new tabs. 52 connector tests and
6 subtests passed (report, setup and generic connector suites); 18 inventory
runtime/planner tests passed. Native tests run the same saved workflow twice with
changed research, distinct spreadsheets/events and correct report links in both
emails and meetings; each action waits for its own approval. Retry reuse,
changed-input rejection, unknown-result reconciliation, legacy receipt retention,
revision isolation and approval rejection paths pass. Contracts, strict scoped
OpenSpec and diff checks pass. Tests use offline transports, not live Google writes.
