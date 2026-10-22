# Verification

22 October 2026. Direct-child constraints exist in frontend/src/domain/hierarchy.ts (maxChildren), frontend/src/domain/governance.ts and Builder.addChild. Runtime delegation uses max_tasks/max_rounds; current monitoring does not report maxChildren. The UI keeps this supported editor concept as Sub-agents per agent without claiming runtime enforcement.

Missing numeric cells within Usage & Limits now use fixed, explicitly tagged Sample values. A visible notice identifies these as illustrative placeholders. Per-row expanded source details distinguish samples from reported evidence. Reported values, including zero, remain unchanged. Samples do not enter configuration, storage, workflow payloads or backend requests. The period remains unavailable rather than invented. Other Governance tabs and pending Monitoring/navigation requests were not changed.

77 domain/Governance tests, frontend lint, shared contract validation and strict OpenSpec validation passed. Private build/browser/deployment evidence is under .local/usage-limit-samples, without credentials in this document.

Production build and explicit typecheck passed. Isolated desktop/mobile checks passed: sample labels, direct-child naming, real-value retention, section navigation, existing audit inspection and no document overflow. No browser errors or backend writes. Screenshots visually reviewed. Frontend-only activation retained 178 static assets and a rollback; before/after comparisons confirmed unchanged auth, connection IDs, graph records, workflow bindings and refresh settings. Backend and worker processes were not restarted.

Public desktop/mobile verification also passed with zero browser errors or backend mutations.
