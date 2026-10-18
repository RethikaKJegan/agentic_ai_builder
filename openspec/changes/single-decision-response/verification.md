# Verification — 18 October 2026

## Observed cause
The new run run_296bda9138dd44c19b261bffc2978975 was created after the previous deployment. Database query and normalization succeeded; its research child again failed MODEL_OUTPUT_SCHEMA_INVALID. The earlier typed-schema change did not resolve the complete cause.

The user explicitly authorized read-only model diagnostics using research instructions, registered public-search schemas and a synthetic query, excluding business records/credentials and Google actions. The first live diagnostic reproduced SDK output_text containing four adjacent complete control JSON envelopes: three search decisions followed by a speculative empty finish. The former json.loads rejected Extra data. A second diagnostic returned one envelope and succeeded, confirming the variable response shape.

## Change
In the model factory's control mode, the decoder now reads the entire response as at most 16 complete schema-valid control envelopes and returns only the first decision. Every remaining envelope must also validate; trailing prose, partial JSON, unknown actions, wrong inputs and excess frames fail closed. No speculative later tool action or completion claim is dispatched. Ordinary non-control business JSON remains single-document only. Provider usage accounting includes the whole response. Instructions explicitly request one decision and stopping before any simulated tool execution.

This does not change workflow versions, Registry grants, action approvals, credentials, source scopes or database write policy. The draft-v2 Registry banner is separate from the published-v1 runtime failure.

## Evidence
- Focused protocol tests: 10 passed, 7 subtests passed. Includes the reproduced concatenated-envelope case, invalid suffixes, frame limits, actual factory usage accounting and real CrewAI bridge.
- Full protocol/delegation/report/manual-worker regression: 48 passed, 7 subtests passed.
- Authorized live diagnostics after correction: tool-selection and finish decisions both succeeded; the final single-decision instruction check also returned a valid tool action. No actual search, database query or Google connector was invoked by these diagnostics.
- Contracts and strict OpenSpec passed. Deployment evidence is .local/research-control-diagnostic/activation.json; config and frontend remain unchanged.
- No user workflow was created, resumed or executed. Failed runs remain terminal. User starts a new run of published v1 and reviews each Google action approval when reached.

Logs: .local/research-control-diagnostic/{diagnose.log,diagnose-2.log,after-fix-diagnostic.log,finish-diagnostic.log,final-live-diagnostic.log,focused-tests.log,regression-tests.log,contracts.log,openspec.log,activation.log}. Raw captures contain synthetic public diagnostic outputs only. No live end-to-end Google execution is claimed.
