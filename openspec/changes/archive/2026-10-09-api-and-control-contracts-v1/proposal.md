# Proposal

## Why

The first contract stage defines workflow, agent, and tool data, but the four implementation segments still need shared rules for communicating over APIs, reporting failures, enforcing permissions, controlling branches and approvals, and tracking workflow revisions and runs.

This change completes the remaining shared contract layer before the planner, UI integration, and runtime are implemented in parallel.

## What Changes

- Define API request and response envelopes for planning, workflow lifecycle, validation, approval, execution, tools, and runs.
- Define a stable error envelope with codes, messages, fields, details, request IDs, and retryability.
- Define authentication subjects, roles, permissions, scopes, and authorization decisions.
- Define condition evaluation, branch selection, approval pauses, rejection paths, and timeout semantics.
- Define workflow revision states, run states, run events, correlation IDs, and idempotency references.
- Keep all contracts backend-neutral and map the existing UI through the API/client boundary.

## Capabilities

### New Capabilities

- `api-payloads-v1`: Defines shared API request/response payloads and pagination/correlation conventions.
- `error-format-v1`: Defines stable error envelopes and retryability semantics.
- `auth-permissions-v1`: Defines authenticated subjects, roles, permissions, scopes, and authorization outcomes.
- `branching-approvals-v1`: Defines conditions, branches, approval gates, rejection, timeout, and pause/resume semantics.
- `run-status-versioning-v1`: Defines workflow revision lifecycle, run lifecycle, events, idempotency, and correlation.

### Modified Capabilities

None. These contracts build on the accepted workflow, agent, and tool contracts.

## Impact

- Adds shared contract files under `shared/contracts/` and documentation under `docs/blueprint/`.
- Gives Suprajha, Aravind, Harihar, and Rethika stable interfaces for their implementation segments.
- Does not yet implement FastAPI, UI API clients, CrewAI execution, authentication middleware, or external connectors.
