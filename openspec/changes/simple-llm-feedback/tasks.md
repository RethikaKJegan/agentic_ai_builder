- [x] Add shared bounded feedback and wire planner and runtime model boundaries.
- [x] Test correction, repeated invalid output, denied retries and accounting.
- [x] Validate contracts/specification and reload services with readiness checks.

Backend and worker restarted successfully; session HTTP 200 and current
RuntimeWorker ready. No workflow was generated, executed or approved by the
deployment check. Refresh and retry the supplier-audit prompt to verify live model
behavior. Existing reviewed revisions are unchanged; runtime correction is
available only when their remaining execution allowance permits another call.

135 regression tests and 25 subtests passed across feedback, dynamic delegation,
delegated tools, runtime, control protocol and live-provider suites. Additional
targeted checks passed for real CrewAI malformed-output correction and ordinary
graph-agent correction without strict-input changes. Feedback preserves the
request, records one correction and charges both model calls. Repeated invalid
output stops; approval, provider, budget, unknown-effect and access failures are
not replayed. Recipient/cost feedback includes actionable hints and prior safe
draft. Contracts, strict scoped OpenSpec and diff checks passed. Tests use offline
model/transports; no live supplier-audit generation success is claimed.
