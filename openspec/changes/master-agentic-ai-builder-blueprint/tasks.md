# Tasks

## 0. Shared contract gate — all four owners

- [x] 0.1 Freeze the v1 canonical workflow schema, including node types, edges, inputs, outputs, policies, and layout metadata; verify valid and invalid fixture documents.
- [x] 0.2 Freeze the agent and tool contracts, including capabilities, permissions, credentials, limits, risk, quotas, and approval requirements; verify contract fixtures.
- [x] 0.3 Freeze API payloads, error envelopes, authentication/permission rules, branching/approval semantics, run statuses, and versioning rules; verify serialization and example responses.
- [x] 0.4 Record the approved contracts and ownership matrix in `docs/blueprint/`; verify all four owners sign off before parallel implementation begins.

## 1. Suprajha — natural-language planning pipeline

- [ ] 1.1 Implement requirement intake and planning request handling; verify a generic business-process prompt reaches the planner without procurement-specific branching.
- [ ] 1.2 Implement OpenAI structured workflow planning for objectives, stakeholders, tasks, dependencies, agents, deterministic actions, conditions, approvals, inputs, outputs, and capabilities; verify schema-valid output fixtures.
- [ ] 1.3 Implement agent-versus-deterministic classification and unresolved-requirement reporting; verify missing approval rules are flagged instead of invented.
- [ ] 1.4 Implement planner error handling and safe rejection of malformed model output; verify invalid model responses never become executable workflows.
- [ ] 1.5 Add planner tests and documentation for at least three domain examples; verify each produces the shared workflow payload without hard-coded domain runtime logic.

## 2. Aravind — agent and Tool Registry

- [ ] 2.1 Implement agent capability definitions and configuration validation against the shared agent contract; verify incomplete or over-privileged agents are rejected.
- [ ] 2.2 Implement Tool Registry entries for SMTP, Google, GitHub, Slack, Open-Meteo, and approved HTTP/webhook capabilities; verify schemas and availability metadata are stored.
- [ ] 2.3 Implement capability-to-tool matching with authentication readiness, permissions, quotas, cost, risk, reliability, and approval filters; verify eligible and rejected candidates.
- [ ] 2.4 Implement credential references and least-privilege tool assignment without storing raw credentials in workflow payloads or prompts; verify secrets are absent from serialized definitions.
- [ ] 2.5 Add registry and authorization tests; verify an agent cannot invoke an unassigned tool or an unallowlisted destination.

## 3. Harihar — existing Lovable UI integration and workflow API

- [x] 3.1 Integrate the supplied `incoming/pixel-perfect-match-latest.zip` Mesh UI into `frontend/`, migrate it to Next.js App Router and remove demo/nonworking actions without redesigning its established visual experience; verify build, types, lint, domain tests and desktop/mobile browser scenarios (evidence in Harihar's handoff).
- [ ] 3.2 Implement the frontend API/client boundary for planning, workflow loading, saving, versioning, validation, approval, execution, and run status; verify request and error payloads match the shared contracts.
- [ ] 3.3 Replace localStorage/demo workflow state progressively with backend-backed repository behavior; verify a planned workflow loads into the existing builder and survives refresh through the API.
- [ ] 3.4 Connect the existing agent inspector, tool panels, approval controls, publish/version controls, run status, and monitoring views to real backend state; verify each screen handles loading, success, error, and unavailable states.
- [ ] 3.5 Preserve the existing generic routes and domain coverage while labeling unconnected connectors and simulated features accurately; verify no demo behavior is presented as a real external action.
- [ ] 3.6 Add frontend integration tests for planner-to-builder, edit-to-save, validation errors, approval gating, and run-history display; verify the UI never creates a separate workflow format.

## 4. Rethika — runtime and observability

- [ ] 4.1 Implement approved-workflow loading, revalidation, and authorization before execution; verify stale, invalid, and unauthorized versions are rejected.
- [ ] 4.2 Implement CrewAI agent/task construction and application-owned graph execution for dependencies, conditions, approval pauses, retries, timeouts, and failures; verify branch and approval scenarios.
- [ ] 4.3 Implement runtime budgets for model calls, tokens, tools, retries, duration, cost, and side effects; verify execution stops or pauses at each applicable limit.
- [ ] 4.4 Implement connector invocation beginning with SMTP email, including credential references, authorization, timeout, retry, and idempotency behavior; verify controlled success and no-credential failure paths.
- [ ] 4.5 Implement run records, unique run IDs, execution events, redaction, and Langfuse/OpenTelemetry instrumentation; verify traces include required metadata and exclude secrets.
- [ ] 4.6 Add runtime security and failure-path tests for tool isolation, connector failure, timeout, retry exhaustion, approval rejection, budget exhaustion, and idempotency protection.

## 5. Cross-segment integration and POC verification

- [ ] 5.1 Connect Suprajha’s planner output to Aravind’s capability/tool selection and Harihar’s existing UI; verify a natural-language requirement becomes an editable backend-backed workflow.
- [ ] 5.2 Connect Harihar’s approved workflow submission to Rethika’s runtime; verify the UI can start, pause, resume, reject, complete, and inspect a run.
- [ ] 5.3 Run one generic end-to-end demonstration using at least one real connector and explicit validation or approval behavior; verify outputs, run records, and trace references.
- [ ] 5.4 Run security, integration, and failure-path tests across all four segments; verify prohibited actions are blocked and errors remain actionable.
- [ ] 5.5 Produce contributor setup documentation for the UI, backend, PostgreSQL, connector credentials, optional Langfuse, OpenSpec, and ownership workflow; verify a new contributor can follow it from a clean environment.

## Workflow follow-up

- Review the revised ownership matrix and shared contract gate with Suprajha, Aravind, Harihar, and Rethika.
- Separate OpenSpec implementation changes now exist for Suprajha, Aravind, Harihar, and Rethika. Apply them in dependency order.
- Apply only the approved segment change through Codex.
- Run OpenSpec verification and archive each completed change after acceptance criteria are met.
- Each segment owner must provide test evidence and receive downstream review before their handoff is marked ready; passing OpenSpec validation alone is not implementation acceptance.
