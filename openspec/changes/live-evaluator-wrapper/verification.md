# Verification — 12 November 2026 IST

The saved run run_e5be9eb110d644b992e3dcd802f20a86 blocked at its first adaptive evaluation before any source action. Read-only reproduction confirmed that the configured LivePlannerProvider omitted evaluate_actions although its underlying provider implements it.

Changes:
- Explicit evaluate_actions delegation preserves context, caller output-token budget, decisions and provider exceptions.
- Public interface audit also found workflow_title missing; it now delegates to the same configured provider. generate, plan_actions and select_capabilities retain existing behavior.
- Missing evaluator blocks with ADAPTIVE_PROVIDER_UNAVAILABLE before reserving model usage. Unexpected evaluator failures emit a safe exception-class diagnostic without raw provider/source text.
- Recovery presentation identifies evaluator service errors. Existing external-action reconciliation guidance takes precedence when external actions may have executed.

A parity test checks all current public provider operations and their parameter names, preventing another provider method from silently disappearing at the wrapper. Real adaptive and recurring automation tests use the actual wrapper and underlying structured evaluator with offline responses, execute authorized synthetic reads, and complete verified assessments. Separate tests check provider exception propagation, safe diagnostics, unavailable-provider budgets and UI recovery messages. Tests do not send mail, create calendar events or use live model calls.

The private saved-failure replay verifies the historical missing method and corrected delegation while preserving the original failed run. Existing completed/blocked runs and schedule authorizations are not rewritten; a fresh execution after service reload is required.

Current presentation work predates this fix but postdates older release manifests. Its current hashes and source copies are captured separately for preservation. Rollback copies, a consistent Subway SQLite backup and deployment/preservation receipts are under .local/subway-evaluator-wrapper-20261112/.

Public-operation audit: generate, plan_actions, select_capabilities, evaluate_actions and workflow_title are all present on the wrapper with matching parameter names. Intent routing deliberately unwraps the provider to access its configured model transport; that path already supports the live wrapper. The older adaptive orchestration path already checks evaluator availability. No additional missing consumed wrapper operations were found.

Final focused checks: 34 wrapper/presentation tests and six workflow-title tests passed. Contract schemas/fixtures, generated UI contract drift, strict OpenSpec and git diff --check passed. Integration runs use synthetic source rows and offline evaluator responses; no production workflow was resumed and no mail was sent.

Deployment and final results: the broader provider/adaptive/recurring regression packet passed all 107 tests. The final focused packet passed 34 tests, including the new evaluator diagnostic presentation; six title tests also passed (packets overlap). Only agentic-builder-subway restarted. Authenticated HTTPS health passed across operator, Simpsons and Subway; foreign-source access remained denied. Configurations, protected records, Subway source bindings/credentials, durable workflow/run histories and unrelated service PIDs were preserved. Existing profiling timestamps are excluded from binding comparisons. Simpsons ephemeral data_query_jobs metadata changed from 22 to 19; existing terminal-job TTL cleanup applies to that table, so it is explicitly excluded from the durable-history count check and recorded in the verification receipt. No source data, blocked run, schedule or mail action was modified by the rollout.

Deployment correction: a later check of the service's systemd override showed that the wrapper tests above exercised workspace code while the service ran an isolated workflow UI release that excluded those fixes. Health checks alone did not prove its implementation. See ../live-release-evaluator-consistency/verification.md for the active-release patch, explicit module-origin tests, exact-launcher check and hosted diagnostic proof. The previous deployment should not be treated as proof that evaluate_actions was available in the running release.
