# Verification — 18 October 2026

Only one inventory run existed: run_08c5789e74b74e3e93f41f87efbab2ec, blocked before node execution. The shared client stored a permanent retry key based on execute_workflow and its payload, so reopening Run for identical inputs returned that earlier run instead of a new execution.

RunWorkflowDialog now provides its own randomly generated execution key. It retains this key across uncertain retries and duplicate clicks in the same mounted dialog; a newly opened dialog has a new key. The shared API client and backend idempotency contracts are unchanged.

Focused UI tests: 3 passed (fresh dialog identity, same-dialog uncertain retry, double-click/cancel/input validation, permission/event-only controls). Broader file: 24 passed, one pre-existing stale navigation mock failure in configured integrations (GoogleToolChecks requires useNavigate, which the test mock does not export); unrelated product behavior was not changed. Typecheck, scoped lint, contracts, strict OpenSpec and isolated production build passed after resolving isolated build fixture paths.

Deployment retains previous static assets and restarts only the frontend; backend and worker PIDs/configuration are checked unchanged. Activation evidence is .local/fresh-manual-run-intent/activation/result.json. No workflow execution or Google action is requested by deployment. User must refresh the browser, reopen Run and click Start run; the returned run ID must differ from the old blocked ID. Runtime still requires separate action approvals before Google writes.
