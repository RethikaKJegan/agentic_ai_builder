# Proposal

## Why

The newly supplied Mesh UI is the visual baseline, migrated from TanStack Start to Next.js App Router in `frontend/`. It currently supports local draft editing; demo execution and configuration actions are removed. Harihar's segment connects that UI to the accepted planner, registry, workflow, approval, and run APIs without rebuilding its established experience.

## What Changes

- Replace the old archive baseline with the newly supplied Mesh UI in `frontend/`.
- Migrate TanStack Start routing and Vite application hosting to Next.js App Router.
- Remove demo and nonworking actions; keep local draft editing honest until backend integration.

- Preserve the existing UI structure, routes, and generic visual language from `incoming/pixel-perfect-match-latest.zip`.
- Add a typed API/client boundary for planning, workflow revisions, validation, approvals, tool metadata, execution requests, and run history.
- Replace local demo persistence progressively with backend-backed state.
- Connect agent/tool inspectors, approval controls, publish/version controls, run status, and history views.
- Display safe contract errors, loading states, unavailable tools, and simulated features accurately.
- Do not implement the planner, Tool Registry, runtime, or new visual redesign.

## Capabilities

### New Capabilities

- `ui-workflow-api`: Connects the existing workflow builder UI to the versioned backend contracts.

### Modified Capabilities

- None.

## Impact

- Existing frontend source from the supplied archive and new API client/adapters/tests.
- Consumes Suprajha's planner payloads and Aravind's registry metadata.
- Provides approved workflow submissions and execution controls for Rethika.
