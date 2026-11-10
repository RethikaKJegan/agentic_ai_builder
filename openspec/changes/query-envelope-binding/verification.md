# Query envelope binding verification — 10 November 2026

## Confirmed cause and correction
The hosted Simpson count/report/email request failed during generation. Service diagnostics show both bounded planner proposals bound data.plan_query output path [] to tool.workflow_data_query input [query]. The response is an envelope containing the typed query, so strict input/output validation rejected it. No workflow execution was reached.

The automatic-input binder now selects [query] only for this known producer/consumer pair, whole-output binding, explicit dependency, required query property and exact declared child-schema equality. Other producers, consumers, targets, paths and binding kinds are unchanged. Existing validation, scope, approvals and runtime checks remain authoritative. Incompatible bindings now attach declared source/target schemas and paths to bounded correction feedback without runtime values. No shared contracts or data schemas changed.

## Evidence
- Exact failure reproduced with controlled transports before implementation.
- Final focused suite: 26 passed, covering normalization idempotency, eight rejected variants, scalar bindings, precise mismatch correction, query restart/recurrence and controlled runtime query/report/Sheets/email handoff.
- Broader connected/goal/query/clarification/discovery suite: 130 passed; the only initial failure was a new diagnostic test using a fixture without an owned selected Google account. The test was moved to the existing owned-account fixture and passes in the final 26-test run. Production account checks were retained.
- Exact four-action hosted proposal replayed from service diagnostics against copied Simpson data: one controlled planning call, correct query-child binding, selected account preserved, no missing inputs, zero query jobs, zero network calls or real provider effects.
- Canonical contract validation and strict OpenSpec validation passed; whitespace check passed.
- Baseline and candidate startup/auth/API rehearsals: six passed across operator, Simpson and Subway, using isolated SQLite copies, disabled networking/workers and existing-record write guards. An initial isolated baseline path violated the existing repository-local registry restriction; using a unique rehearsal directory beneath each staged source root corrected setup without changing application validation.
- Backend-only change; no new frontend build required. Existing production artifact retained.

Tests use controlled model and HTTP transports. No live model interpretation, complete live population query or email delivery is claimed. The fix addresses the reproduced binding failure; unresolved business definitions still require clarification.
