# Proposal

## Why

The four contributors need stable contracts before parallel implementation begins. They also need a predictable handoff process so that when Suprajha, Aravind, Harihar, or Rethika takes ownership, Codex presents the correct responsibilities, dependencies, completed work, defects, and unresolved handoff items.

This change defines only the first three shared contracts and the contributor handoff protocol. API payloads, error formats, authentication, branching, approvals, run states, and versioning remain later contract stages.

## What Changes

- Define the canonical workflow schema v1.
- Define the runtime agent contract v1.
- Define the Tool Registry/tool contract v1.
- Define contributor-specific responsibilities and handoff records for Suprajha, Aravind, Harihar, and Rethika.
- Require each handoff to include completed work, verification evidence, known defects, unresolved decisions, dependencies, affected contracts, and next actions.
- Require a contributor-identification response when a contributor states their name, without treating that response as authorization to change code.
- Stop after the first three contracts and handoff protocol; do not implement API, authentication, branching, approval, run-status, versioning, or runtime behavior in this change.

## Capabilities

### New Capabilities

- `workflow-schema-v1`: Defines the canonical workflow document and typed nodes used by all later stages.
- `agent-contract-v1`: Defines the fields, limits, permissions, and capabilities required for runtime agent configurations.
- `tool-contract-v1`: Defines registered tools, capabilities, connector metadata, authorization, and least-privilege assignment.
- `contributor-handoff`: Defines named contributor onboarding, ownership display, dependency notices, defect handoffs, and completion records.

### Modified Capabilities

None. These contracts refine the first implementation boundary for the new project.

## Impact

- Adds planning artifacts under `/home/raf/agentic-ai-builder/openspec/changes/shared-contract-pack-v1`.
- Establishes schemas that Suprajha, Aravind, Harihar, and Rethika will consume.
- Requires later API, UI-integration, and runtime changes to reference these contracts rather than inventing new formats.
- Does not modify the existing UI archive, Praxi, or the fire-detection project.
