# Persistent lifecycles in Business Investigation

The existing Workflow → Business Investigation section now creates and reopens
persistent lifecycle cases. The existing investigation route also accepts `?case=`.
Legacy and dynamic composition investigations retain their routes and controls.
No additional application, navigation tab or execution scheduler was introduced.

Choose an authorized client knowledge package/process, enter the investigation goal
and available user inputs, and create a case. Prepare resolves available evidence.
Start/Drive/Resume use the backend lifecycle engine. Agent stages retain the normal
workflow validation/approval and exact external action approval gates. After an
approval, use Drive / continue. Refresh and reopen read authoritative server state.
Cancel preserves the case and its audit history.

Progress follows the pinned process definition: Simpson has twelve stages; the
controlled retail fixture has eight. Stage details include dependencies, capability
assignments, input/output availability, saved timestamps, errors and pending events.
Evidence distinguishes ACTUAL, DERIVED, INFERRED and SYNTHETIC, with source/mapping
references, assumptions, limitations and confidence. Actual source reports alone do
not prove physical completion. Reports show execution and business outcomes
separately and retain the analytical qualification and pending real-world waits.

Agents & tools reuses CompositionInspector for the saved master/specialist graph,
tools, receipts, approvals, memory and runtime failures. Memory & recovery reads
backend memory, learning, recovery, history and reassessment sections. Late evidence
can be explicitly reviewed with event-to-input bindings; the backend checks allowed
fields, authentic source, revisions and write barriers. Archived conclusions remain
inspectable. No frontend business-rule evaluation or independent learning occurs.

New commands receive unique request keys. On an unknown response, execution stops
and offers an explicit retry with the identical body/key. Normal mutation commands
carry the observed revision; conflict responses refresh server state without replay.
No case/evidence payload is stored as browser authority. The session storage entry
contains only a scoped command digest and request key. Workspace/owner changes clear
loaded content. Backend authorization remains authoritative for every operation.

## Files and reused interfaces

Frontend implementation:

- `frontend/src/api/business-lifecycle.ts`: validated lifecycle/process/index types and declared user-input mapping.
- `frontend/src/api/client.ts`: existing authenticated envelope transport extended with lifecycle reads/commands.
- `frontend/src/features/investigations/BusinessLifecycle.tsx`: case controls, inspection sections and authorization/reassessment forms.
- `frontend/src/features/investigations/LifecyclePanels.tsx`: pinned stages, provenance, waits and qualified report presentation.
- `frontend/src/features/investigations/InvestigationList.tsx`: opt-in embedding in the existing list.
- `frontend/src/features/investigations/InvestigationWorkspace.tsx`: reopen using the existing investigation route.
- `frontend/src/screens/app.workflows.index.tsx`: enables lifecycle embedding on Workflow.
- `frontend/src/features/investigations/lifecycle.test.tsx` and `frontend/src/test/fixtures/business-lifecycle.json`: component/command regressions.
- `frontend/e2e/business-lifecycle.spec.ts` and `frontend/playwright.lifecycle.config.ts`: actual HTTP lifecycle acceptance and existing navigation regressions.

Reused: InvestigationList/Workspace, CompositionInspector, ApiFeedback, useBackend,
WorkflowClient transport, established Sheet/status/layout styles, existing normal
workflow and external-action approval endpoints. No client role flag grants authority.

Backend integrations under `/business-ontology/v1` include process definition reads,
Simpson convenience process/create, case create/get/prepare/start/drive/resume/cancel,
authenticated events, reviewed reassessment and archived revisions, case sections,
client packages and composition views. Existing `/workflows/.../validate` and
`approve` plus `/approvals/.../decision` remain the approval authority.

Two bounded read endpoints were added: `GET /cases?before=` (50 items plus cursor)
and `GET /process-definitions` (100 summaries). Both scope by authenticated workspace
and owner. Full stage/evidence documents are retrieved only for the selected case.
Files: `workflow_api/business_cases.py`, `workflow_api/business_ontology_routes.py`,
`tests/test_business_lifecycle_ui.py`. The test-only HTTP fixture server is
`scripts/serve_lifecycle_ui_test_api.py`; it uses disposable storage, actual Registry,
CrewAI/runtime and deterministic model/evidence transports, never live connectors.

## Verification and deployment

Exact commands, outcomes, deployment identity and limitations are recorded in
`openspec/changes/business-lifecycle-ui/verification.md`.
