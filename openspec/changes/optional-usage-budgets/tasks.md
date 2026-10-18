- [x] Implement server-owned cumulative token/cost budget opt-out.
- [x] Verify repeated delegated calls, usage accounting, and retained boundaries.
- [x] Verify default enforcement and existing runtime regressions.
- [x] Configure and reload backend/worker; verify readiness without workflow execution.

Evidence: 115 tests passed across test_dynamic_delegation, test_runtime,
test_live_providers and test_delegated_tools. Two final targeted tests passed
after strengthening finite usage validation. Shared contracts, strict scoped
OpenSpec validation and git diff checks passed. The deployment .env now sets
BUILDER_ENFORCE_USAGE_BUDGETS=0. Both systemd services restarted successfully;
session and worker-health endpoints returned 200, one current worker is active,
RuntimeWorker is ready and active_runs is zero. No inventory workflow was run and
no Google actions were invoked for verification. Live end-to-end success remains
unverified. Old failed runs remain historical; start a new run of the same release.
