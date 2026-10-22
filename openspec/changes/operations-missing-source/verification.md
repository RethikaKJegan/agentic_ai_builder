# Verification

22 October 2026. Reproduced public GET /api/backend/data-operations returning 404 DATA_SOURCE_NOT_FOUND. Existing write policy referenced dbconn_cd1a345806cd28bdc9ecae87c247ea3d, while current owned connected sources were dbconn_241b52b0becfc0d7ae4de2ba38867284 and dbconn_b5d62643d7d2ef0a6a58edaf6d09b39a. The supplied historical correlation ID was not found in the searched local logs; root cause was independently reproduced with a fresh request.

Minimal backend patch: catalog discovery skips only owned-connection DATA_SOURCE_NOT_FOUND/404 entries. Other failures propagate, valid targets remain discoverable, and exact context checks for read/prepare/execute remain unchanged. Stale policy is not remapped, edited or granted to current connections. The current catalog therefore returns HTTP 200 with no available targets plus existing history. Enabling operations on a current dataset still requires explicit server policy; this change does not enable cloud writes.

UI: only the shared shell Operate Approvals item and its orphan badge removed, including mobile shell representations. Command/shortcut links, approval page, run gates and review controls preserved. Operations empty state now explains unavailable current policy targets.

Validation: 33 backend tests passed, including disposable real PostgreSQL/MongoDB CRUD and three new local catalog regressions (missing/unowned/disconnected references, valid targets, exact permissions and unrelated errors). 77 frontend/domain/Operations tests passed. Production build, explicit typecheck, full lint, shared contract validation and strict OpenSpec passed. Isolated desktop/mobile browser checks confirmed status 200, no DATA_SOURCE_NOT_FOUND/Retry read, targeted navigation removal and direct approval page access, with zero browser errors/writes or page overflow. Screenshot reviewed.

Activation: no active runtime runs. Backend service restarted to load the patch; worker remained untouched. First activation automatically rolled back because its full-response comparison included dynamic correlation IDs/registry review fields. The check was narrowed to saved workflow and persisted connection/graph/refresh data, and the identical tested patch was reactivated successfully. Configuration and policy hashes unchanged; connection documents, graph, saved workflow and refresh settings unchanged. Frontend activation retained 247 assets and rollback, and verified unchanged auth/connection IDs/graph/workflow bindings.

Private reproduction, activation/browser evidence and rollback live under .local/operations-connection-fix. No credentials in this document.

Public desktop/mobile browser verification passed the same checks with zero browser errors and backend writes.
