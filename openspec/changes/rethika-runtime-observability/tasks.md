# Tasks

## 1. Runtime boundary

- [x] 1.1 Implement approved workflow loading and pre-execution revalidation; verify stale, invalid, revoked, and unauthorized revisions are rejected.
- [x] 1.2 Implement application-owned graph state transitions and run creation using `run-status-versioning-v1`; verify legal transitions and idempotent run requests.
- [x] 1.3 Implement CrewAI agent/task construction from accepted agent definitions without allowing model output to bypass application policy; verify dry-run task creation.

## 2. Control flow and safety

- [x] 2.1 Implement dependencies, deterministic nodes, conditions, branches, unmatched paths, retries, timeouts, and failure propagation; verify branch fixtures.
- [x] 2.2 Implement approval pauses, approvals, rejections, and timeout policies; verify no rejected or pending action invokes an external tool.
- [x] 2.3 Implement model, token, tool, retry, duration, cost, and side-effect budgets; verify each limit pauses or fails the run with a stable reason.

## 3. Connectors and observability

- [x] 3.1 Implement authorized connector invocation with opaque credential references, destination allowlists, timeout, retry, and idempotency controls; verify SMTP success and missing-authorization failures.
- [x] 3.2 Implement run records, events, correlation IDs, redacted errors, and trace metadata; verify secrets and raw provider payloads are excluded.
- [x] 3.3 Add Langfuse/OpenTelemetry integration behind an observability adapter; verify trace references are linked to run IDs without making observability availability a side effect permission.

## 4. Tests and handoff

- [x] 4.1 Add runtime security and failure-path tests for tool isolation, connector failure, timeout, retry exhaustion, approval rejection, budget exhaustion, and duplicate execution; verify the suite passes.
- [x] 4.2 Create the Rethika handoff listing runtime inputs, authorized assignment requirements, state transitions, connector behavior, trace fields, and unresolved defects; verify all upstream owners and downstream operational consumers are named.
- [x] 4.3 Run contract validation and strict OpenSpec validation; verify runtime code does not alter shared contracts or touch the existing Praxi/fire-detection projects.
- [x] 4.4 Perform Rethika's acceptance review: run the full runtime security/failure-path suite, contract validation, strict OpenSpec validation, dry-run execution, approval rejection, budget exhaustion, and connector authorization scenarios; record pass/fail evidence before marking the segment ready.

## 5. Published release and trigger contracts

- [x] 5.1 Review versioned release, trigger, automation identity, lifecycle operation, overview, and event-stream contracts with all owners; document permission and UI/API mappings without changing Harihar's specifications or silently extending v1.
- [x] 5.2 Inventory supported trigger adapters separately from outbound tools; verify unsupported sources remain unavailable and SMTP sending is not represented as incoming email support.
- [x] 5.3 Resolve registry restart authorization through reviewed persistence or trusted reconstruction/reassignment; verify stale process-local references cannot authorize execution after restart.

## 6. Activation and event execution

- [x] 6.1 Persist immutable releases and idempotent activation operations; verify successful activation, partial failure compensation, concurrent publish conflict, and restart reconciliation.
- [x] 6.2 Implement verified push event ingestion, polling with durable checkpoints and explicit backfill policy, and timezone-aware schedules behind provider adapters; verify schema/filter/input mapping and workspace isolation.
- [x] 6.3 Implement durable receipts, deduplicated dispatch jobs, leases, concurrency limits, retries, dead-letter/replay handling, and causation filters; verify crash recovery and no duplicate external effects.
- [x] 6.4 Bind dispatch to a release and trusted automation identity; revalidate registry grants, approvals, credentials, quota, and budgets before execution; verify revoked/stale grants block tool use.
- [x] 6.5 Implement atomic republish cutover and trigger reconciliation; verify new dispatch uses the new release, existing runs/jobs retain their version, and failed republish preserves the old release.

## 7. Workflows overview and lifecycle integration

- [x] 7.1 Integrate the top-level Workflows tab with persisted draft/published versions, activation health, active run count, latest status, and pending approvals; verify updates are visible outside each editor and other workflows remain editable.
- [x] 7.2 Add authenticated live updates with sequence/resume, snapshot reconciliation, polling fallback, and stale connection indicators; verify reconnection, out-of-order events, and workspace isolation.
- [x] 7.3 Connect overview Run, Edit, and Delete actions plus the editor's top Publish/Republish button using the reviewed existing UI/API boundary; verify draft/live isolation, safe errors, and no business execution merely from publishing.
- [x] 7.4 Implement disablement and confirmed idempotent deletion with tombstones, trigger cleanup/retries, queued cancellation, safe running cancellation, retained audit evidence, and publish/delete serialization; verify pending approvals cannot resume deleted workflows and other workflows remain unaffected.

## 8. Extended acceptance

- [x] 8.1 Replay first publish, automatic event execution, live overview, parallel workflow editing, republish during a run, disablement, and deletion end to end; record release/run/event IDs and trace evidence.
- [x] 8.2 Test invalid/duplicate/self-originated events, activation failure, concurrency conflicts, polling checkpoints, restart, revoked authorization, stream reconnect, delete races, and provider cleanup failures.
- [x] 8.3 Demonstrate one authorized real event source after fake push/poll/schedule adapter coverage; document exact supported providers and limits without claiming all registry tools are trigger-capable.
- [x] 8.4 Run contract validation, strict OpenSpec validation, and relevant integration/security tests; include the extended lifecycle evidence in Rethika's acceptance and handoff before completion.

## Workflow follow-up

- Start after Suprajha, Aravind, and Harihar handoffs are accepted.
- Run the first real connector only with explicit credentials, allowlists, approvals, and test destinations.
- Archive after implementation review and task completion.

- The extended lifecycle is part of Rethika's change. Do not mark acceptance complete using only the original runtime tests; sections 5–8 also require evidence.
