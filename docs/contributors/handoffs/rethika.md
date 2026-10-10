# Handoff — Rethika

- **Segment:** Runtime and observability, including the planned published workflow lifecycle.
- **Status:** in-progress — core runtime implemented and locally verified; lifecycle/trigger contract review and extended acceptance pending.
- **Contract versions:** workflow-schema-v1, agent-contract-v1, tool-contract-v1, api-payloads-v1, error-format-v1, auth-permissions-v1, branching-approvals-v1, run-status-versioning-v1. No accepted shared contract changed.
- **Completed work:** Approved revision/auth/provenance/grant checks; durable idempotent runs and canonical events; actual CrewAI construction/execution with bounded model bridge; deterministic branches/joins; approval decisions/rejection/timeout paths; cumulative budgets; credential-reference SMTP adapter; interrupted-call denial; trusted worker identity resolution; redacted OTel export. Existing runtime API routes are opt-in connected. See `runtime/README.md` for exact configuration and limits.
- **Verification evidence:** Fresh evidence and commands are recorded in the implementation review below; all earlier upstream implementation evidence remains attributed to its owner.
- **Known defects / limits:** Production auth/PostgreSQL and live provider quota reservation remain absent. Upstream external-write publication approval integration remains unavailable. Default dev runtime has no model/connector adapter or automatically started worker. Tests use offline model/SMTP transports, not real email delivery. Ambiguous condition expressions/configuration fail closed. Registry approval/reference persistence across restart needs reviewed integration. Basic redaction/injection detection is not exhaustive.
- **Dependencies:** Suprajha's canonical drafts; Aravind's current exact assignments, policy/scopes/credentials and approval evidence; Harihar's exact approved revisions and trusted API/auth boundary. Rethika explicitly accepted their delivered boundaries in this session; unfinished upstream integration is not claimed complete.
- **Downstream consumers:** Harihar for runtime/approval DTO wiring and remaining UI tasks; Aravind for authorization/approval and restart review; Suprajha for executable expression/input mappings; cross-segment POC integration and operational consumers for run/trace/connector evidence.
- **Unresolved decisions / blockers:** All-owner lifecycle/trigger/automation/overview/stream contract signoff; restart reauthorization and durable approval evidence; final transport/permission/retention decisions; supported real event source and explicitly approved provider setup. No release/trigger UI availability is claimed.
- **Next actions:** Review `openspec/changes/rethika-runtime-observability/contract-review.md` and companion draft schema, record real owner signoffs, then implement lifecycle sections 5–8. Configure live adapters/worker and connect publication approval evidence before enabling external-write end-to-end workflows. Keep final acceptance and archive open.

## Aravind registry delivery — 2026-10-09

Suprajha’s planner handoff was explicitly accepted by Aravind. Registry implementation and local verification are complete: 35 tests passed; shared contracts valid; strict registry OpenSpec validation passed. Read `docs/contributors/handoffs/aravind.md` and `docs/contributors/examples/aravind-registry.json` for the complete service boundary, authorization policy, safe metadata, assignment bindings, and limitations. Your downstream review is required before Aravind task 4.4 can be completed. This file records notification, not your acceptance.

Consume only authorized assignments for approved workflow revisions and revalidate their exact subject/workspace/workflow/agent/tool/version binding before execution. Pending approvals have no executable grants. Registry authorization records are process-local; refresh quota/credential policy and enforce runtime budgets in your segment.

## Harihar UI/API delivery and review request

Harihar delivered canonical workflow loading/saving/versioning, planner draft rendering, safe errors, server-configured local development sessions, registry discovery and gated deterministic revision approval/publication. No runtime, connectors or workflow gate decisions were implemented. Read [Harihar API boundary](../harihar-api.md) and `docs/contributors/handoffs/harihar.md` for the exact routes, DTO projections, UI availability states, verification evidence and eight execution-input groups.

Review the exact approved workflow revision, trusted auth boundary, Aravind assignment revalidation, execution idempotency envelope, run/event/approval DTOs, legal run observations and hierarchy mapping before connecting execution. Runtime/approval endpoints currently fail unavailable; the UI does not fabricate runs or grant pending approvals. Global run/approval collection operations are absent from the accepted operation-name contract and need shared-owner agreement. Production login and PostgreSQL remain separate from Harihar's local POC session/SQLite adapters.

This is a repository review request and partial upstream delivery, not your acceptance or a ready-for-execution claim. Harihar's full AI-workflow publication in task 2.2, tasks 3.1–3.3 and 4.4 remain open until the live dependency boundaries and your review are delivered.

### Updated Harihar registry/publication handoff

This supersedes the missing assignment-integration and task 2.2/3.1 statements above. Harihar now delivers explicit trusted registry configuration, exact agent matching, authorized assignment/revalidation, safe UI assignment states and publication gating. Tasks 2.2 and 3.1 are complete; 10/13 Harihar tasks are complete. See `docs/contributors/harihar-api.md` for the operator JSON format and trusted Python `app.state.workflow_service.registry_adapter.execution_assignments(workflow, auth)` boundary. It returns currently revalidated exact grants without exposing references in HTTP UI responses. Approved canonical agent references carry server-issued allowed tool IDs; new edited revisions clear grants.

Review these inputs and the existing run/event/approval DTOs before implementing or enabling runtime consumption. Runtime must check approved workflow/version, trusted subject/workspace, scopes, every tool binding, budgets, destination resolution and current quota/policy/approval evidence; references are process-local. No connector or live approval service was implemented by Harihar. External-write approval evidence, runtime execution/history and global collection agreement remain your/shared-owner dependencies. Harihar tasks 3.2/3.3 require your services and 4.4 requires your actual review; no acceptance is invented.

Verification recorded by Harihar: 50 Python tests, 61 frontend tests, 8 production browser scenarios, build/types/lint, canonical contract checks and strict OpenSpec all PASS. Tests make no provider/connector calls. This is a repository handoff update only; no external message was sent.

## Rethika consumer acceptance — 2026-10-10

Rethika explicitly accepted Aravind's delivered registry boundary and Harihar's delivered UI/API execution boundary in the contributor session, including process-local authorization and local-development limitations, and authorized Rethika implementation. Fresh verification: 50 Python planner/registry/API tests PASS using `.venv-integrations/bin/python`; shared contracts PASS; all 16 strict OpenSpec checks PASS. Acceptance covers delivered inputs, not unfinished runtime integration, production authentication, live connectors, or new lifecycle/trigger contracts. No external notification was sent.

## Core runtime implementation review — 2026-10-10

Fresh verification: 94 Python tests PASS (50 upstream, 44 runtime); 61 frontend
consumer/domain tests PASS; frontend TypeScript PASS; shared schemas/fixtures PASS;
generated-client drift check PASS; strict Rethika OpenSpec validation PASS with
zero issues; runtime dependency check PASS. No real model/email/trigger/provider
trace export was made by this verification. CrewAI import warnings are nonfatal.

The suite includes actual CrewAI dry-run and offline kickoff, actual OTel SDK spans,
exact registry-issued tool binding/approval/revocation scenarios, no-tool-before-gate,
rejection/timeout stop/branch/retry, deterministic branch/join and error-path isolation,
cumulative workflow/agent budgets, explicit model request bounds, duplicate/restart
run identity, tool isolation, unknown invocation recovery, safe SMTP transport,
secret-bearing result rejection, worker identity resolution and HTTP consumers.

Reviewable offline evidence: `.local/runtime-review/evidence.json` and its
repository-local database contain completed run
`run_6d7724cd39494fb2b628863faf3eacf6`, five canonical events and five in-memory SDK
spans. This is explicitly a deterministic test fixture with test-only approval
provenance, not real workflow release/connector acceptance.

Inputs: exact approved ID/version/document with workspace/validation/review
provenance; current trusted execution identity; currently authorized exact registry
assignments; explicit server model pricing/adapter and credential-reference resolver;
workflow inputs/request ID/retry key. Worker authentication must be freshly resolved.
Authorization/credential references are never UI response fields.

Transitions: queued → running; running → paused_for_approval/completed/failed/blocked/
cancelled; paused_for_approval → running/rejected/failed/blocked/cancelled. Terminal
states do not resurrect. Draft edits do not change old approved documents; a newer
approved revision supersedes manual execution. Release-specific immutable cutover
semantics remain new-contract work and are not claimed here.

Connector behavior: exact agent binding and current metadata, schema, scopes, policy,
approvals, destination and duration checks before invocation; committed intent before
external call; no automatic SMTP resend after uncertain submission. Stable Message-ID
is reconciliation data only. No live quota reservation/restart approval service exists.

Trace fields: event/run/workflow/version IDs, timestamp/source/type, safe node/outcome/
status/approval/error codes, correlation ID and application trace reference. No prompt,
credential, raw provider result or input payload is exported. Export is at least once
on delivery/checkpoint crash; consumers can deduplicate by event_id.

Remaining blockers: joint review of the concrete lifecycle/trigger contract proposal,
restart-safe authorization/approval reconstruction, incoming provider adapters, durable
release/event/jobs, overview streams and UI lifecycle actions, extended scenarios and
an explicitly approved real event-source demonstration. Existing external-write
publication approval integration also remains closed. Final task 4.4 and sections
5–8 acceptance stay open; this core review does not declare the segment ready.

Repository notification: Suprajha should review executable expression/input mappings;
Aravind should review trigger scopes/restart authorization; Harihar should review
lifecycle DTO/overview/stream integration; cross-segment POC/operations should consume
the run/trace limits and evidence. No external message was sent.
