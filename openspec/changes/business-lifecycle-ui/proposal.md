# Persistent lifecycles in the existing Business Investigation interface

Audit: Workflow navigation is owned by src/screens/app.workflows.index.tsx and its
existing InvestigationList section. The existing /app/workflows/investigate route
selects legacy and dynamic composition workspaces. WorkflowClient.read supplies
same-origin authenticated API envelopes; useBackend supplies current session/scope
and permissions. Existing CompositionInspector/Report and Dynamic workspace provide
normal workflow/action approval and run details. Reuse these routes/components,
Sheet, ApiFeedback, status styling, and test/staging conventions. No new tab/page.

Add a lifecycle workspace within InvestigationList and the existing investigate
route. Read scoped process/case lists, package configurations and full pinned cases.
Render stage order/dependencies dynamically. Use explicit bounded backend commands,
stable scoped request keys for uncertain retries, backend revisions and no browser
scheduler. Show provenance, pending physical activity, real agent/tool records,
memory/feedback/history and explicit event/reassessment commands when authorized.
Preserve legacy/dynamic investigations and their existing approval interfaces.

Backend gap: case/process list reads are missing. Add bounded owner/workspace-scoped
GET list endpoints only; existing engine/authorization semantics stay unchanged.
Verify unit/browser flows with controlled backends, Phase 4–6 regressions, real
frontend types/lint/tests/build and existing deployment prerequisites. Deploy only
through the established target/procedure when current credentials and authorization
are available; never seed real systems with fixture events or send live messages.
