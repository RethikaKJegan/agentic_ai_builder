# Verification

22 October 2026. Renamed visible MESH product branding to PraxilonAI in shared logo, landing/cinematic copy, login, Overview, application page-title metadata and frontend catalog publisher labels. Removed Powered by attribution from desktop/mobile branding and updated the fixed workspace avatar initial. Existing three-dot mark unchanged.

Removed only Knowledge from the shared sidebar/navigation definition, including the mobile All pages menu. Knowledge route, API, command-palette access and underlying functionality preserved. Technical names (useMesh, component import paths, node types, storage keys, graph identity namespaces and favicon filenames) remain stable. Backend, configuration and user records were not edited.

Production build, explicit typecheck, full frontend lint, 72 domain tests across 10 suites, shared contracts and strict OpenSpec passed. Isolated desktop 1600×1100/mobile 390×844 browser checks passed for landing/login/workspace branding and accessible names, absence of MESH/Powered by visible text, page titles for Workflows/Integrations/Data Intelligence/Governance/Runs/Knowledge, collapsed sidebar, mobile menu, preserved direct Knowledge page and no horizontal page overflow. Zero browser errors/backend writes; screenshots reviewed. No new tests were added for this reversible presentation-only change.

Private build/browser/deployment evidence and rollback are under .local/praxilonai-branding; no credentials included here.

Public desktop/mobile verification passed with zero browser errors/backend writes. Frontend activation retained 289 static assets and rollback; auth, connection IDs, graph and saved workflow bindings remained unchanged. Backend PID 445360 and worker PID 296194 unchanged. Login/logout protection passed.
