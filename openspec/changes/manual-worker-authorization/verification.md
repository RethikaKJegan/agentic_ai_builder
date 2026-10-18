# Verification — 18 October 2026

The API and worker have separate Registry approval memory. Manual execution previously could not reconstruct pending assignment approvals after publication in the API process. Recovery now requires a validated published revision, its recorded approver as the current authenticated executor, current workflow.approve permission, current Registry approval role and exact workspace. Current Registry scopes, tool availability and policies still apply. Existing lifecycle recovery and per-action gates remain intact.

The fresh-service regression passed, covering an independently initialized Registry and denial for another subject, revoked approval permission, missing approval role, missing scopes and a draft. Runtime/Registry/lifecycle/report regressions: 90 passed and 29 subtests passed; one unrelated existing assertion fails because test_safe_planner_errors_and_missing_runtime expects an empty tool list although four database tools are registered. The same failure was reproduced with the pre-change execution_assignments implementation. Contracts and strict OpenSpec passed.

A fresh worker preflight loaded the user's exact persisted published workflow planned_dac02e184983cf1d v1 and authorized all ten grants. The revision was unchanged and all three runtime action approval gates remained. No worker lifespan, model call, connector invocation or workflow execution was performed by that preflight. The existing blocked run is terminal; user must start a new run after deployment, using the same published revision.

Evidence: .local/manual-worker-authorization/{focused-tests.log,regression-tests.log,baseline-check.log,contracts.log,openspec.log,preflight.json,activation.json}. No user workflow or cloud action is retried automatically.
