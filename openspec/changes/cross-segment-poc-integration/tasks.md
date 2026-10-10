# Tasks

## 1. Integration fixtures

- [x] 1.1 Extend planning normalization to create workflow-scoped agent identities, explicit executable tool nodes, branches, approval gates, and typed input mappings; verify canonical graph validation.
- [x] 1.2 Create controlled Registry fixtures for Google Sheets read and SMTP send with test identity, workspace, destination, opaque credential references, quotas, and idempotency data; verify no raw credentials or uncontrolled destinations are present.

## 2. Automatic Registry resolution

- [x] 2.1 Implement server-side planner-agent registration and capability-based tool selection without workflow-specific static bindings; verify permissions, schemas, credentials, risk, destination, quota, and stable candidate ordering.
- [x] 2.2 Persist resolved executable revisions, clear only satisfied unresolved requirements, and expose selected/pending/denied states through the existing API and editor.
- [x] 2.3 Connect exact-action approval evidence to Registry authorization and runtime revalidation; verify changed destination or action data cannot reuse approval.

## 3. End-to-end verification

- [x] 3.1 Verify prompt-to-planner-to-registry-to-UI-to-runtime flow for the generic Sheets-to-email workflow; verify the canonical payload remains consistent across boundaries.
- [x] 3.2 Verify approval, rejection, branch, timeout, retry, budget, authorization, duplicate-request, connector-failure, and typed data-mapping paths; verify each produces safe UI, API, run, and trace evidence.
- [x] 3.3 Verify the controlled offline SMTP demonstration and document the opt-in real SMTP command when configured; verify destination allowlists, idempotency, redaction, and trace linkage.

## 4. Acceptance and handoff

- [ ] 4.1 Record contract versions, test results, run IDs, trace references, and defects; verify each defect has an owner and downstream notification.
- [x] 4.2 Run all contract validators, strict OpenSpec validation, Python tests, frontend tests/typecheck, and the complete integration suite; verify the project acceptance gate is reproducible.
- [ ] 4.3 Update all four contributor handoffs and implementation-readiness documentation with final acceptance status; verify no existing Praxi or fire-detection files changed.
- [ ] 4.4 Record final acceptance from all four owners or name the unresolved owner/blocker for every failed scenario; do not invent human signoff.

## 5. Generic provider execution

- [ ] 5.1 Define a versioned Registry catalog for all configured provider actions: Google Sheets read/update, Drive, Calendar, Slack, GitHub, Open-Meteo, Open Library, Google Docs, generic REST, webhook, Gmail SMTP, and Brevo SMTP; include schemas, scopes, destinations, risk, quota, and approval metadata.
- [ ] 5.2 Extend planner capability normalization to recognize provider-neutral intents, trigger requirements, typed mappings, and declared condition outcomes without selecting credentials or provider IDs.
- [ ] 5.3 Implement provider adapters behind the Registry grant boundary; support real credentials only in explicit operator mode and retain offline adapters for tests.
- [ ] 5.4 Add generic Google Sheets polling/row-change trigger support with cursor, receipt, release binding, replay protection, and durable dispatch.
- [ ] 5.5 Add generic workflow graph validation for multi-agent branches, update actions, rejection/error paths, and trigger nodes; reject incomplete graphs before publication.
- [ ] 5.6 Replace manual run/approval lookup with server-backed collections, automatic pending approval notifications, and generic run/event projections.
- [ ] 5.7 Expose runtime events, counters, cost, duration, failures, correlation IDs, and trace references in Monitoring with optional OTLP/Langfuse export.
- [ ] 5.8 Add provider contract tests and one explicitly approved real smoke test per adapter class; never treat metadata validation as execution evidence.

## Workflow follow-up

- Start only after Suprajha, Aravind, Harihar, and Rethika implementation changes are accepted.
- Do not archive until the generic POC and required failure paths have evidence.
