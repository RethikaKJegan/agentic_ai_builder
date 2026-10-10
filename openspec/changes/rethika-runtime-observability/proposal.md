# Proposal

## Why

The platform needs a bounded execution layer that consumes only approved workflow revisions and authorized tool assignments, handles branching and human approvals, and records enough evidence to diagnose every run. Rethika's segment owns execution and observability after the planning, registry, and UI/API boundaries are available.

## What Changes

- Revalidate workflow versions and authorization immediately before execution.
- Build CrewAI agents/tasks from accepted agent definitions while keeping application-owned graph control.
- Execute dependencies, branches, approvals, retries, timeouts, budgets, and failures using the accepted control contracts.
- Invoke connectors through credential references and least-privilege assignments, beginning with SMTP email.
- Record run IDs, events, correlation IDs, idempotency outcomes, redacted errors, and Langfuse/OpenTelemetry traces.
- Add published release activation, provider-independent triggers, durable event dispatch, draft/live isolation, republishing, disablement, and deletion.
- Deliver the Workflows tab overview with live run summaries, Run, Edit, and Delete actions; use the top editor Publish/Republish button for release changes. These additions belong to this change and must reuse the existing UI/API boundary.
- Define technical integration and shared-contract review prerequisites without changing Harihar's specifications or silently extending accepted v1 contracts.
- Do not invent workflow formats, bypass approvals, expose secrets, or execute unapproved tools.

## Capabilities

### New Capabilities

- `workflow-runtime-observability`: Executes approved workflows with bounded controls and records safe, traceable run evidence.

### Modified Capabilities

- None.

## Impact

- New runtime, approval, connector, persistence, and observability modules/tests.
- Depends on accepted planner, registry, UI/API handoffs and all shared v1 contracts.
- Initial real connector target is SMTP; other integrations remain registry/runtime extensions.

## Scope extension — published workflow operations

Publish activates an approved version inside the shared platform, including configured supported triggers. It does not generate a separate hosted application or perform a business action merely because publishing occurred. Manual Run starts one execution. The Workflows tab provides live operational visibility outside individual workflow editors; editors remain available while published workflows operate.

Rethika owns the runtime and the additional overview/editor integration described here, coordinated with Harihar's existing UI/API implementation. No Harihar specification is modified by this change. Aravind's registry remains the authorization foundation; receiving events requires explicit trigger adapters and separately reviewed trigger permissions. Unsupported trigger sources must be shown as unavailable.

New trigger, release, automation identity, lifecycle operation, and overview/stream contracts require joint review before implementation. Current v1 contracts and registry code are unchanged by this planning update. Registry assignments are process-local today; durable storage or authorized reconstruction is a prerequisite for restart-safe automation.
