# Proposal

## Why

The four segment implementations are separate ownership boundaries, so a final integration stage is needed to prove that planner output, authorized assignments, the existing UI, runtime control, connector behavior, and observability use the same contracts. This change defines the generic end-to-end verification gate without adding a fifth owner.

## What Changes

- Connect the four accepted segment outputs in dependency order.
- Verify planner-to-registry-to-UI-to-runtime data flow using the shared contracts.
- Verify approval, rejection, idempotency, error, run-history, and trace behavior.
- Demonstrate one generic workflow with an explicitly approved real connector.
- Record defects and notify the owner responsible for each boundary.
- Do not redefine contracts or silently repair segment implementations inside integration tests.

## Capabilities

### New Capabilities

- `cross-segment-poc-integration`: Validates the complete platform flow and records end-to-end acceptance evidence.

### Modified Capabilities

- None.

## Impact

- Integration fixtures, end-to-end tests, contributor handoff updates, and POC verification documentation.
- Depends on accepted implementations from all four owner changes.
