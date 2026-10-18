# Verification — 18 October 2026

Scope: submission eligibility and actionable setup errors only. The user explicitly selected “Only fix submission and show the missing setup.” No spreadsheet export module was added, no Google scopes/credentials/policies changed, and the saved Northwind workflow was not edited.

- 53 tests passed, 16 subtests passed, one unrelated legacy test deselected: tests/test_phase3_actions.py, tests/test_workflow_api.py, tests/test_registry.py. Real Registry coverage verifies pending grants can be submitted without authorization/approval; denied tools and unresolved setup remain blocked. HTTP tests verify requirement details survive the route.
- The deselected test_safe_planner_errors_and_missing_runtime expects /tools to be empty, but the existing database tools are registered. Its failure was reproduced with the original HEAD submission function patched back in memory. This broader suite is not claimed entirely green.
- Shared schemas/fixtures and strict scoped OpenSpec validation passed. Patch whitespace checks passed.
- Verified no active planning/runtime work, then restarted only agentic-builder-backend.service. Backend reports active. Frontend/worker, credentials and cloud databases were unchanged.
- Real Chromium against the running frontend at localhost:3001 opened planned_27a66f680da69766 and clicked Submit for approval. The expected 403 now includes the exact Google Sheets destination requirement, visibly rendered in the existing Publication requirements list. Zero page errors. Screenshot: .local/registry-submission-fix/live-ui.png.
- The unresolved Northwind draft remains validated and blocked on its actual spreadsheet setup. No workflow approval, publication, activation, database operation, model call or external Google action was performed. Pending-only submission behavior is verified by isolated HTTP/Registry tests; no live review request was created.

The attempted automatically enabled spreadsheet export adapter was rejected by automatic approval review before application. The user chose to exclude that feature. Praxi was not modified.
