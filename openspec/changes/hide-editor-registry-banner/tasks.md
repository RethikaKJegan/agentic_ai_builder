- [x] Remove the editor banner without changing validation or authorization.
- [x] Verify editor controls and deploy the frontend.

Evidence: only WorkflowControls.tsx changed in application code (removed the passive banner and its unused local projection). 26 existing API/Registry/UI tests passed, including real publication rejection feedback and retained Registry state. Build/type validation, scoped ESLint, strict OpenSpec and diff checks passed. Desktop/mobile browser checks inject pending Registry blockers and confirm the banner is absent while revision controls remain. Frontend deployed with rollback retained; backend unchanged.
