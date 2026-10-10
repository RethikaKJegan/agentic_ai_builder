# Implementation Readiness

## Status

The shared contract gate is complete and ready for implementation work.

## Completed gates

- New Mesh UI from `incoming/pixel-perfect-match-latest.zip` migrated to Next.js in `frontend/`; demo/nonworking actions removed and baseline build, tests, lint and desktop/mobile browser scenarios verified. Old `agentt.zip` is historical input.
- First shared contract pack accepted: workflow, agent, tool, and contributor handoff contracts.
- Second shared contract pack accepted: API payloads, errors, authentication and permissions, branching and approvals, run status, and versioning.
- All four contributors reviewed the second pack: Suprajha, Aravind, Harihar, and Rethika.
- `python3 scripts/validate_contracts.py` passes.
- Strict OpenSpec validation passes for both contract changes.
- Separate implementation plans exist for Suprajha, Aravind, Harihar, and Rethika.
- Every implementation plan includes an owner-specific acceptance review requiring tests, contract validation, strict OpenSpec validation, scenario evidence, and downstream handoff review.

## Implementation order

1. Suprajha: natural-language planning pipeline.
2. Aravind: agent and Tool Registry implementation, consuming Suprajha's accepted capability identifiers.
3. Harihar: connect the existing UI to the accepted API and workflow payloads without rebuilding the UI.
4. Rethika: runtime, connectors, approvals, execution controls, and observability after upstream handoffs.
5. Cross-segment integration and generic POC verification after all four segment handoffs.

## Current implementation boundary

Suprajha's planner is implemented with Aravind's acceptance recorded. Aravind's registry is locally verified with downstream reviews pending. Harihar's new Next.js UI baseline is verified; backend API integration remains open. Rethika's runtime remains dependent on accepted upstream integration handoffs. No contributor may invent a parallel payload, permission model, workflow format, or execution state model.

## Verification commands

```bash
python3 scripts/validate_contracts.py
openspec validate harihar-ui-workflow-api --type change --strict --json
```
