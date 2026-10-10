# Proposal

## Why

The four segment implementations are separate ownership boundaries, so a final integration stage is needed to prove that planner output, authorized assignments, the existing UI, runtime control, connector behavior, and observability use the same contracts. This change defines and implements the generic end-to-end integration boundary without adding a fifth owner. The accepted segment implementations remain authoritative for their own concerns, while this change closes the gaps between them.

## What Changes

- Connect the four accepted segment outputs in dependency order.
- Normalize planner-created agents into workflow-scoped Registry definitions and resolve requested capabilities to eligible tools without trusting planner-supplied authority.
- Materialize executable tool nodes and typed input mappings in planned workflows.
- Connect revision approval, exact-action approval, publication, CrewAI agent execution, connector invocation, run records, and trace export.
- Verify planner-to-registry-to-UI-to-runtime data flow using the shared contracts.
- Verify approval, rejection, idempotency, error, run-history, and trace behavior.
- Provide a provider-agnostic execution path: planner capabilities resolve to any
  Registry-approved provider adapter, rather than hard-coding a Sheets-to-email
  workflow.
- Demonstrate one generic workflow with an explicitly approved real connector,
  while keeping offline adapters only for deterministic tests.
- Record defects and notify the owner responsible for each boundary.
- Preserve the accepted shared contracts; integration fixes are implemented at the owning service adapters and recorded explicitly here.

## Capabilities

### New Capabilities

- `cross-segment-poc-integration`: Validates the complete platform flow and records end-to-end acceptance evidence.

### Modified Capabilities

- None.

## Impact

- Planner, Registry adapter, workflow API, provider catalog and adapters, trigger
  configuration, UI state, integration fixtures, end-to-end tests, contributor
  handoff updates, and POC verification documentation.
- Depends on accepted implementations from all four owner changes.
