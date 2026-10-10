# Agentic AI Builder Instructions

This repository is isolated under `/home/raf/agentic-ai-builder`. Do not modify Praxi or the fire-detection project.

## Contributor routing

Before implementation work, read:

- `docs/contributors/ownership.md`
- `docs/contributors/onboarding.md`
- the relevant file under `docs/contributors/handoffs/`

When a user explicitly identifies themselves as Suprajha, Aravind, Harihar, or Rethika:

1. Show that contributor's segment, responsibilities, out-of-scope work, dependencies, current status, verification evidence, known defects, unresolved decisions, downstream notifications, and next actions.
2. For Aravind, include Suprajha's planner handoff.
3. For Harihar, include the accepted workflow, agent, and tool contracts.
4. For Rethika, include the complete accumulated context from all previous contributors.
5. Distinguish recorded facts from assumptions.
6. Do not edit code, change credentials, or claim completion from identity recognition alone. Wait for an explicit implementation request.

## Contract authority

The versioned files under `shared/contracts/` are the source of truth for workflow, agent, and tool data shapes. The existing UI models are integration mappings, not the execution authority.

## OpenSpec workflow

Use OpenSpec planning artifacts before implementation changes. Validate contracts and tests before marking tasks complete. Keep changes scoped to this repository.
