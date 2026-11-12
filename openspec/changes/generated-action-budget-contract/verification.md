# Verification — 12 November 2026

Request `906b6d2a-0281-4d07-8f50-504647697c75`, planning job `plan_a63d0de247c04fb69a1a2ca04378ed19`, failed before executable workflow preparation with HTTP 422 / ACTION_BINDING_INVALID / Action execution budget is insufficient. The old rejected proposal was not retained, so its exact offending action is not asserted. A read-only deployed-validator diagnostic reproduced all three invalid call-allocation variants.

New server-generated drafts derive call allowances from registered capability kinds before schema validation and review. Models receive at least one model call and zero direct tool calls; tools receive at least one tool call and zero model calls; writes receive exactly one dispatch. Valid higher read/model allowances remain. Registered tool timeout minimums are enforced in the draft. Malformed types, retries, aggregate limits, agent ceilings, binding/source constraints, and exact-payload approvals remain strict. Explicitly submitted, saved and executing plans are never normalized. Draft normalization is idempotent and mutates only its copied budget fields.

Strict invalid-budget errors now identify the exact action/capability, required allowance and observed values, and provide structured planner correction feedback. The old vague message is no longer used for this condition.

## Tests and boundaries

- Focused checkout suite: **20 passed**, including generic capability normalization, schema/type handling, explicit invalid-plan rejection, aggregate limits, write retry rejection, actual normal planning/execution, two daily email/Calendar occurrences and Subway persistent assessment/schedule pipeline. Provider and external transports are controlled.
- Read-only replay of an actual stored Subway composition (eight actions): original valid plan passed; deliberately incompatible allocations were rejected with exact action feedback; generated normalization produced a valid plan while preserving every non-budget action field, retry setting, completion criterion and aggregate constraint. Zero model calls, external effects or production writes.
- Exact isolated acceptance: **121 passed**, covering new budget cases, goal planning, Calendar, recurring research/email/Calendar, Subway persistent report/schedule execution and Subway automations. Exact-candidate isolation/integration regressions: **81 passed**. Counts overlap with focused suites and must not be summed.

The user's old failed request remains unchanged. No live daily schedule is created or changed and no email, Calendar event or spreadsheet is sent during verification. Exact arbitrary live-provider interpretation of the original prompt is not claimed. This fix prevents the modeled call-allocation mismatch in generated drafts; legitimate policy/ceiling/source/authorization errors must still fail closed.

Private evidence: `.local/subway-action-budget-20261112/`, including manifests, logs, read-only replay, consistent backup, deployment and preservation checks.

## Exact candidate verification

The isolated candidate is `.local/subway-action-budget-release-20261112/app`, copied with symlinks preserved from the active Subway report/layout release. Only `workflow_api/action_budgets.py`, `workflow_api/action_bindings.py`, `workflow_api/action_plans.py` and the new tests differ. The active old release is immutable. Canonical contracts, generated UI contracts, strict OpenSpec and whitespace checks passed.

The exact-candidate isolation/integration regression suite passed **81 tests**: Simpson client isolation and ontology, live evaluator wrapper, evaluator protocol, automation usage settlement, Gmail and report-model reliability. These use disposable stores and controlled transports; Simpson production was not queried or modified.

## Deployment and public checks

Subway alone restarted at 2026-11-12T16:46:10.749680+00:00. Active source: `.local/subway-action-budget-release-20261112/app`. The tested release manifest and consistent pre-deployment backup are retained. Original-row preservation checks passed for existing workflows, planning/run history, source records, ontology, receipts, credentials and schedules. Frontend, Simpson and unrelated service PIDs and shared source hashes remain unchanged.

Authenticated public session, tools, worker health, query availability and the retained failed planning-job history return 200. Smoke checks use GET requests only; no model call, source write, communication or schedule activation occurred. Generate a new draft from the original prompt to use the correction. The earlier failed request is preserved as history.
