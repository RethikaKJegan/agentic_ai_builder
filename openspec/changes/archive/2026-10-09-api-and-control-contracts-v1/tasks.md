# Tasks

## 1. API and error contracts

- [x] 1.1 Define `api-payloads-v1.json` for planning, workflow lifecycle, validation, approval, execution, tool discovery, and run endpoints; verify schema loading and representative examples.
- [x] 1.2 Define `error-format-v1.json` with safe codes, messages, request IDs, field paths, details, retryability, and provider-error mapping; verify secrets are excluded from examples.

## 2. Authentication and permissions

- [x] 2.1 Define `auth-permissions-v1.json` for subjects, workspaces, roles, permissions, scopes, and authorization decisions; verify viewer, builder, approver, and admin examples.
- [x] 2.2 Add denied-operation fixtures for missing identity, viewer edit, unassigned tool, missing scope, and unauthorized approval; verify each produces a stable error code.

## 3. Branching and approvals

- [x] 3.1 Define `branching-approvals-v1.json` for condition outcomes, edge selection, approval gates, rejection paths, and timeout policies; verify complete and incomplete branch fixtures.
- [x] 3.2 Add state-transition fixtures for approved, rejected, timed-out, and unmatched-condition paths; verify no path silently continues an external write.

## 4. Run status and versioning

- [x] 4.1 Define `run-status-versioning-v1.json` for workflow revision states, run states, events, correlation IDs, and idempotency keys; verify schema loading and legal-state fixtures.
- [x] 4.2 Add duplicate-execution and invalid-transition fixtures; verify repeated idempotency keys do not create duplicate runs and illegal transitions are rejected.

## 5. Review and integration readiness

- [x] 5.1 Document API, error, permission, branching, approval, run, and versioning mappings for the existing UI and future runtime; verify each contract has a named consumer.
- [x] 5.2 Have Suprajha, Aravind, Harihar, and Rethika review the remaining contracts and record decisions; verify all review states are captured.
- [x] 5.3 Run contract validation and strict OpenSpec validation; verify the change is complete before service implementation begins.

## Workflow follow-up

- Use the accepted contracts when creating the four implementation changes.
- Notify all downstream owners when a contract version changes.
- Archive this change only after all review and validation tasks are complete.
