# Tasks

## 1. UI baseline and client boundary

- [x] 1.1 Integrate the supplied `incoming/pixel-perfect-match-latest.zip` Mesh React/TypeScript UI into `frontend/`, migrating to Next.js App Router without redesigning it; remove demo/nonworking actions and verify build, types, tests, navigation, and local draft editing.
- [x] 1.2 Add typed API/client adapters for planning, workflow lifecycle, validation, tools, approvals, execution, and runs; verify request/response types match accepted contracts.
- [x] 1.3 Add safe error, loading, unavailable, and correlation-ID handling; verify provider errors and credentials never reach the UI.

## 2. Workflow and planner integration

- [x] 2.1 Load Suprajha planner drafts into the existing workflow canvas; verify nodes, edges, agents, tools, conditions, and approvals render from the canonical payload.
- [x] 2.2 Implement workflow save, revision, validation, and publish flows; verify version and idempotency behavior across refresh and retries.
- [x] 2.3 Replace local workflow persistence progressively with backend-backed behavior; verify a saved workflow survives refresh without a second frontend format.

## 3. Registry, approval, and run views

- [x] 3.1 Display Aravind's authorized tool metadata and assignment state; verify unavailable, unauthorized, risky, and approval-required tools cannot be published.
- [ ] 3.2 Connect approval controls and branch/status displays to accepted control contracts; verify pending, approved, rejected, timed-out, and unmatched states.
- [ ] 3.3 Connect execution request, run status, event timeline, and history views; verify impossible transitions and duplicate requests are handled safely.

## 4. Tests and handoff

- [x] 4.1 Add frontend integration tests for planner-to-builder, edit-to-save, validation errors, authorization display, approval gating, and run history; verify the suite passes.
- [x] 4.2 Create the Harihar handoff listing API routes, mappings, UI states, remaining simulated features, and Rethika's execution inputs; verify every downstream input is named.
- [x] 4.3 Run contract validation and strict OpenSpec validation; verify existing Praxi and fire-detection projects remain untouched.
- [ ] 4.4 Perform Harihar's acceptance review: run the frontend build, unit/integration tests, contract validation, strict OpenSpec validation, and planner-to-builder/save/approval/run-history scenarios; record pass/fail evidence and obtain Rethika's review of the execution handoff before marking the segment ready.

## Workflow follow-up

- Start after Suprajha's planner payload and Aravind's registry metadata are available.
- Notify Rethika when approved workflow submission and execution-control examples are ready.
- Archive after implementation review and task completion.
