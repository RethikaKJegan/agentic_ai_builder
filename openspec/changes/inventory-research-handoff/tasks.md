- [x] Implement the narrow compiled-report validated-result handoff.
- [x] Test delayed helpers, invalid results, failures and generic synthesis.
- [x] Run contract and scoped specification checks.
- [x] Reload services and verify readiness without running Google actions.

Deployment: both systemd services restarted, session returned HTTP 200, and the
current worker is active with RuntimeWorker ready. A run was already active at
the readiness check; no workflow was started or approved by this verification.

Verification: 8 inventory runtime tests passed, covering all three approval gates,
full delivery via offline Google transports, delayed valid output, invalid output,
research failure and cancellation. 43 planner/protocol/generic delegation tests
and 7 subtests passed separately. Shared contracts, strict scoped OpenSpec and
git diff checks passed. Existing published workflow v2 was inspected read-only:
its compiler marker, child capabilities and matching output schemas qualify.
The malformed provider text from the failed live turn was not retained; a
synthetic public coordinator diagnostic did not reproduce it. This change removes
that redundant coordinator invocation entirely for the compiled report rather
than relaxing schema validation or claiming to repair unseen provider text.
