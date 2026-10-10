# Tasks

## 1. Integration fixtures

- [ ] 1.1 Create a generic end-to-end workflow fixture with planner requirements, agent definitions, authorized tool assignment, approval gate, branch, and run policy; verify every referenced contract version is explicit.
- [ ] 1.2 Create controlled test identity, workspace, destination, credential-reference, and idempotency fixtures; verify no raw credentials or uncontrolled destinations are present.

## 2. End-to-end verification

- [ ] 2.1 Verify planner-to-registry-to-UI-to-runtime flow for the generic workflow; verify the canonical payload remains consistent across boundaries.
- [ ] 2.2 Verify approval, rejection, branch, timeout, retry, budget, authorization, duplicate-request, and connector-failure paths; verify each produces safe UI, API, run, and trace evidence.
- [ ] 2.3 Verify one approved real connector demonstration, beginning with SMTP if configured; verify destination allowlists, idempotency, redaction, and trace linkage.

## 3. Acceptance and handoff

- [ ] 3.1 Record contract versions, test results, run IDs, trace references, and defects; verify each defect has an owner and downstream notification.
- [ ] 3.2 Run all contract validators, strict OpenSpec validation, and the complete integration suite; verify the project acceptance gate is reproducible.
- [ ] 3.3 Update all four contributor handoffs and implementation-readiness documentation with final acceptance status; verify no existing Praxi or fire-detection files changed.
- [ ] 3.4 Perform the final acceptance review with all four owners: independently confirm each segment's test evidence, replay the generic end-to-end flow, and record approval or a named defect owner for every failed scenario.

## Workflow follow-up

- Start only after Suprajha, Aravind, Harihar, and Rethika implementation changes are accepted.
- Do not archive until the generic POC and required failure paths have evidence.
