# Proposal

## Why

The project needs a dependable way to turn a user's natural-language objective into a validated, generic workflow plan that every downstream segment can consume. Suprajha's implementation is the first service implementation after the shared contract gate, so it must produce only the accepted v1 workflow, agent, tool-reference, API, error, permission, branching, approval, and run metadata shapes.

## What Changes

- Add a natural-language planning capability that accepts a user objective and planning context.
- Produce a structured workflow draft containing tasks, agent requirements, deterministic steps, tool references, conditions, approval gates, and unresolved requirements.
- Use structured model output and validate it against the accepted shared contracts before returning it.
- Return stable API and error payloads for invalid input, incomplete requirements, authorization failures, and invalid model output.
- Preserve generic domain support; procurement, email, spreadsheet, and other workflows are examples, not hard-coded modes.
- Publish planner capability identifiers and agent requirements for Aravind's Agent and Tool Registry work.
- Do not modify the existing Lovable UI, implement the Tool Registry, or execute workflows.

## Capabilities

### New Capabilities

- `workflow-planner`: Converts a natural-language objective into a validated, reviewable workflow draft.

### Modified Capabilities

- None.

## Impact

- New planner service and tests under the project backend area.
- Uses `shared/contracts/` as the sole source of truth for request, response, workflow, agent, tool-reference, error, permission, branching, approval, and run metadata formats.
- Depends on the accepted `shared-contract-pack-v1` and `api-and-control-contracts-v1` changes.
- Downstream consumers are Aravind's registry, Harihar's existing UI/API integration, and Rethika's runtime; none are implemented by this change.
