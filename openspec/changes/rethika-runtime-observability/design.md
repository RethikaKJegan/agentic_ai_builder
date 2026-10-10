# Design

## Context

Rethika receives approved workflow submissions, validated agent definitions, authorized tool assignments, and UI execution requests. The runtime must remain application-owned for graph control even when CrewAI constructs agent/task execution units.

## Goals / Non-Goals

**Goals:**

- Make execution authorization and revalidation unavoidable.
- Support branches, approvals, retries, timeouts, budgets, and connector idempotency.
- Produce durable run records and redacted traces for operations and debugging.

**Non-Goals:**

- Planning or selecting tools.
- Rebuilding the existing visual design or independently defining shared API payloads. This change may add the specified Workflows overview and editor lifecycle integration using jointly reviewed contracts.
- Executing arbitrary model-generated code or unapproved destinations.

## Decisions

1. **Application-owned graph orchestration:** CrewAI provides agent/task execution, while the application controls dependencies, branches, approvals, budgets, and transitions.
2. **Revalidation at the execution boundary:** data accepted earlier by the UI or planner is not trusted indefinitely; the runtime rechecks revision, policy, assignment, and approval state.
3. **Connector adapter boundary:** each connector receives a normalized authorized invocation and returns a redacted result; SMTP is the first concrete adapter.
4. **Event-first run recording:** state transitions and important decisions are recorded with idempotency/correlation metadata before or atomically with side effects where supported.
5. **Provider-agnostic observability:** emit structured events suitable for Langfuse and/or OpenTelemetry without coupling workflow semantics to one observability vendor.

## Risks / Trade-offs

- **[Risk] A crash occurs between recording and an external side effect.** → Use idempotency keys, connector-specific reconciliation, and explicit unknown-result states.
- **[Risk] Runtime retries duplicate side effects.** → Require connector idempotency and never retry non-idempotent actions without policy approval.
- **[Risk] Traces leak prompts or credentials.** → Redact at event creation and maintain allowlisted metadata fields.

## Migration Plan

1. Implement dry-run graph validation and state transitions.
2. Add CrewAI task construction without enabling connectors.
3. Add approval/budget controls and run persistence.
4. Enable SMTP through authorized credential references and controlled tests.
5. Add Langfuse/OpenTelemetry exporters and operational dashboards.
6. Roll back by disabling connector invocation while preserving run records and dry-run validation.

## Published workflow lifecycle and Workflows tab

### User experience

The top-level Workflows tab, outside the individual editor, lists workflows as soon as they are created. Each row/card displays name, draft revision, published revision if present, trigger activation/health, active run count, latest run state/time, and pending approval count. A workflow can be active and waiting without a run currently executing; do not display simulated motion or claim continuous agent execution. Users can view live progress, run an authorized published version manually, edit a draft, or delete the workflow here. Creation and editing of other workflows remain available during execution.

Edit opens the existing editor and creates or loads a draft without modifying the immutable published revision. The editor's top action is Publish for the first release and Republish when an existing release has draft changes. Display validation/activation progress and safe failures. A successful release updates the overview. The overview may link to detailed run events but must not require opening each editor to see activity. Approval decisions continue through the accepted approval UI; merely displaying an approval count does not approve it.

### Records and contracts

Persist workflow revisions, published releases, trigger definitions/bindings, automation identities, event receipts, dispatch jobs, polling checkpoints, run events, and lifecycle audit records. A release binds a workflow revision, agent/tool versions, authorization references, trigger configuration, and input/output mappings. A trigger binding records workspace, provider/resource, event type, delivery mechanism, credential reference, filters, schedule/timezone or polling interval where applicable, checkpoint, and subscription health. Never store credentials in workflow or event payloads.

Release activation state is distinct from accepted workflow revision and run states. Proposed activation states are preparing, active, failed, disabled, and deleting; finalize them through shared-contract review rather than inserting them into v1 run states. Review lifecycle operations, optimistic concurrency, idempotency, pagination, overview fields, stream sequencing/resume, trigger schemas, automation permissions, and deletion policy with all owners. Exact endpoint names and payloads must follow that review; these notes are not alternative API authority.

### Publish and republish

1. Authorize the builder and validate the selected revision, approvals, agents, assignments, credentials, trigger resources, event mappings, and budgets. Compare the expected published revision to prevent concurrent edits from silently overwriting a release.
2. Persist an idempotent preparing release. Prepare subscriptions, scheduler jobs, or polling registrations using explicitly authorized provider adapters. Buffer verified candidate events durably without dispatching them before activation.
3. Once every required trigger is ready, atomically switch the active release pointer and dispatch eligibility. Assign each accepted dispatch job an immutable release reference so later republishing does not change its execution version.
4. On failure, record an actionable activation error, keep the old release serving, and compensate newly created subscriptions/jobs. Reconcile uncertain provider results after restart; do not mark a release active solely because a provider request was attempted.
5. Retire obsolete bindings after cutover. Deduplicate deliveries across overlapping subscriptions. Runs/jobs already bound to the old release continue with that release unless disabled/deleted policy explicitly cancels them. New eligible events use the new release.

Publishing waits for events and does not itself invoke business tools. LLM calls occur only when execution reaches an AI node. Manual Run uses a distinct idempotent execution operation; draft tests use a clearly separate controlled test path and cannot activate production triggers.

### Provider-independent event pipeline

    Webhook / provider event / poll change / schedule tick
      -> verify source and workspace
      -> persist normalized event receipt
      -> match enabled binding, validate schema, filter, map inputs
      -> atomically persist deduplicated dispatch job + release reference
      -> durable queue worker
      -> authorize automation identity and revalidate release/assignments
      -> existing bounded runtime -> run records and live updates

Use three explicit adapter types: provider push subscriptions, polling with durable cursors or stable record IDs/change versions, and timezone-aware schedules. An outbound tool is not automatically a trigger: SMTP sending does not receive email, and notification fixtures do not subscribe to provider events. Capability discovery must distinguish callable actions from supported event sources. Require reviewed trigger authorization; do not grant event subscriptions from a tool's existing send/read authorization alone.

Verify provider signatures/challenges, freshness and replay constraints where supported; authenticate generic inbound webhooks. Derive workspace routing from protected subscription records rather than trusting inbound workspace IDs. Persist receipt before acknowledging delivery. Deduplication keys include workspace, source binding/event identity, and target workflow; define fallback identities per adapter when the provider supplies no event ID. Atomically save polling checkpoints with receipts to avoid loss after crashes. Define initial polling baseline/backfill explicitly so publishing does not unexpectedly run historical records.

Queue workers use leases, bounded concurrency, retries/backoff, dead-letter records, and explicit replay policy. Retries must not duplicate external effects: use connector-specific idempotency/reconciliation and preserve unknown results where necessary. Filter bot/self-originated events and record causation to prevent workflows triggering themselves indefinitely. Refresh quota and credentials rather than treating registry configuration snapshots as live reservations.

Use a server-managed automation identity authorized by the workspace. An inbound event cannot invent roles, scopes, or approvers. Call RegistryService.revalidate_assignment before each relevant connector invocation; reject expired approvals, revoked credentials, stale assignments, and policy changes. Because registry authorization references currently disappear on restart, implement reviewed durable registry integration or reconstruct and reauthorize bindings before resuming; never deserialize an old reference as authority.

### Live overview and recovery

Build a workspace-scoped persisted overview projection from release and run events. Load a paginated snapshot, then subscribe through authenticated server-sent events with sequence/resume information; use bounded polling when streaming is unavailable. Reconcile after reconnect and reject stale/out-of-order updates. Show connection loss and last update time rather than presenting stale data as live. Streams and queries must enforce workspace isolation and redact provider data. A server restart rebuilds jobs/subscriptions from durable state and reconciles provider registrations without duplicate activation.

### Disablement and deletion

Disable/unpublish prevents new dispatch while retaining definitions/history and applies an explicit policy to existing runs. Delete from the overview uses the established confirmation UI, requires reviewed lifecycle permission, and idempotently marks the workflow deleting/tombstoned before revoking bindings. Block new manual/automatic runs and cancel queued jobs. Signal running workers to cancel at safe boundaries; pending approvals cannot resume a deleted workflow. Actions already sent externally cannot be undone or represented as undone. Track failed provider subscription cleanup for retry while retaining local dispatch denial.

Hide a tombstoned workflow from the normal list once deletion is accepted and expose cleanup progress through an authorized operation record. Preserve minimal audit/run history according to the agreed retention policy; deletion is not silent history erasure. Shared provider credentials/subscriptions used by other workflows must remain intact. Serialize deletion against publication so an in-flight activation cannot revive the workflow.

## Additional implementation sequence and acceptance

1. Agree the release/trigger/lifecycle/overview contracts and automation identity policy with upstream owners; no implementation bypasses this gate.
2. Add durable release/event/job storage and a fake trigger adapter; verify crash recovery and publish cutover.
3. Implement supported trigger adapters, scheduler/polling services, source verification, deduplication, and bounded workers. List unsupported providers honestly.
4. Integrate the Workflows overview and existing editor's top Publish/Republish action within Rethika's change after Harihar's boundary is available.
5. Verify first publish, activation failure, live overview, simultaneous workflows, draft isolation, republish, concurrent requests, duplicate events, revoked authorization, restart, disablement, and delete races.
6. Demonstrate one supported real event source only after authorized provider setup; fake adapters provide independent coverage for push, polling, and schedules. Existing SMTP smoke checks are not incoming-trigger evidence.
