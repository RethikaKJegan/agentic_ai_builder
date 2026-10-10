# Design

## Context

The accepted v1 workflow, agent, and tool contracts provide the data objects but do not define how services communicate, authorize requests, control branches, or report lifecycle state. The existing UI must consume these contracts through an API boundary, while the future runtime must enforce them server-side.

## Goals / Non-Goals

**Goals:**

- Provide stable JSON-compatible contract files for API and runtime control behavior.
- Use one error shape across UI, backend, planner, registry, and runtime.
- Make permission and approval decisions explicit and auditable.
- Make workflow revisions and runs stateful, correlated, and idempotent.
- Keep the contracts independent of FastAPI, TanStack, CrewAI, and database internals.

**Non-Goals:**

- Implementing authentication middleware or an identity provider.
- Implementing the UI API client or runtime state machine.
- Connecting external services or creating production credentials.

## Decisions

### Contract artifact layout

```text
shared/contracts/
├── api-payloads-v1.json
├── error-format-v1.json
├── auth-permissions-v1.json
├── branching-approvals-v1.json
└── run-status-versioning-v1.json
```

Examples and transition fixtures live beside the schemas. The UI maps its existing models to these payloads through a client boundary.

### State transitions

Workflow revisions and runs use explicit enumerated states. Invalid transitions are rejected rather than silently coerced. Every state-changing operation includes the actor/source and correlation IDs.

### Authorization model

Authorization is evaluated as subject identity plus role/scope plus workflow/tool assignment. A successful role check cannot override an unassigned tool or a blocked connector.

### Branch and approval model

Conditions produce declared outcomes. Edges select outcomes. Approval gates pause a run and require an authorized decision. Rejection and timeout paths are explicit and never silently continue external writes.

### Idempotency

Execution requests accept an idempotency key. The key is stored with the run request and reused to return the existing result for duplicate requests within the retention policy.

**Alternative considered:** Let each service define its own statuses and errors. Rejected because the UI, runtime, and observability layer would disagree about state and recovery.

## Risks / Trade-offs

- [Contract grows too broad] → Keep v1 limited to shared fields and add later behavior through new changes.
- [Permission names drift] → Use a controlled permission vocabulary and contract fixtures.
- [Branch behavior is ambiguous] → Require declared outcomes and explicit rejection/timeout paths.
- [Idempotency retention is misconfigured] → Make retention a documented deployment setting and include duplicate-request tests.
- [UI needs fields not in the contract] → Add a reviewed contract extension instead of leaking UI-only fields into execution payloads.

## Migration Plan

1. Add the five contract schemas and examples.
2. Validate the schemas and state-transition fixtures.
3. Review with the four contributors.
4. Use these contracts when implementing the planner, UI/API integration, and runtime changes.

Rollback is reverting this contract change before service implementation; no production data is migrated.
