- [x] Keep Disable visible with existing state/permission checks.
- [x] Verify active/inactive menu states and deploy the frontend.

Evidence: one application-code line changed in app.workflows.index.tsx. Production build/type validation, scoped ESLint, strict OpenSpec and diff checks passed. Browser checks verify visible/enabled Disable for active releases, visible/disabled for inactive releases and existing confirmation; confirmation was dismissed and all writes blocked. Desktop/mobile views checked. Frontend deployed with rollback retained; backend and actual workflow activation states unchanged.
