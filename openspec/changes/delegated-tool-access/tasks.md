- [x] Add shared connector authorization and bounded subagent tool decisions.
- [x] Preserve dynamic tools through planner/Registry resolution and show tool handoffs.
- [x] Test Sheets-backed verification concurrently with master work and rejection paths.
- [x] Validate contracts, OpenSpec and regression suites; document evidence and limits.

Evidence: 190 Python tests and 80 frontend tests pass. Eleven delegated-tool tests cover actual GoogleSheetsConnector reads, bounded CrewAI master/child overlap, correction of a contradicted claim, exact assignment denial, schema errors, model/tool budgets, Google access denial, public Registry policy revocation, cancellation and dynamic generation. Two desktop/mobile Playwright checks inspect tool input/output and child findings from the actual runtime fixture at frontend/e2e/fixtures/delegated-tools.json. Production build, types, lint, shared contracts, strict OpenSpec validation and git diff --check pass.

OAuth, Google HTTP and model responses in this evidence are offline transports; no live Google account read or live model verification is claimed. The existing live backend connector configuration is reused. No backend restart, publication, credential change or external write was performed. In-flight connector calls remain bounded by their configured adapter timeouts and cannot be forcibly stopped by threads.
