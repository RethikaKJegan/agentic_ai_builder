## Implementation
- [x] Restore communication visibility for tool-backed agents and procurement child runs; clarify manual start in the editor.
- [x] Integrate connectors and durable coordinator with the existing backend.
- [x] Add generic prompt planning and reviewed project setup in the existing UI.
- [x] Add approval-gated sending with confirmed identifiers and deduplication.
- [x] Verify generation/publication/execution, approval denial and regression checks.

51 focused native/legacy planner/Registry tests and 6 focused UI tests passed. Frontend typecheck/lint, shared contracts and generated-client drift passed. Provider responses were simulated; no live Google writes, emails, approvals or workflow publication were performed. Live acceptance requires restart and a controlled new workflow.

Communication follow-up: 14 focused communication/manual-start UI tests passed; typecheck, scoped lint, contract drift, diff checks and strict OpenSpec passed. Existing published workflows were not rewritten or executed.
