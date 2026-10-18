- [x] Render matching pending approvals in Execution with gate labels and existing previews.
- [x] Verify exact decision binding, rejected/mismatched runs, permissions and database review behavior.
- [x] Validate frontend and deploy the UI.

Evidence: 32 focused tests passed (ExecutionView, API integration and DatabaseWorkflowReview). Production build, typecheck, lint, shared contract validation and strict OpenSpec validation passed. Playwright desktop and mobile checks used read-only real run data with mocked pending status and decision responses; exact approval binding and refresh passed without real decisions. Frontend deployed using an isolated build and rollback copy; backend unchanged.
