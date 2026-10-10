# Tasks

## 1. Agent registry

- [x] 1.1 Implement agent definition validation against `agent-contract-v1`; verify incomplete, over-privileged, and secret-bearing fixtures are rejected.
- [x] 1.2 Implement capability catalog and planner-handoff adapter; verify Suprajha's capability identifiers map without inventing new permissions.
- [x] 1.3 Add agent versioning and workspace ownership metadata; verify revisions and authorization context are traceable.

## 2. Tool registry

- [x] 2.1 Implement tool registration against `tool-contract-v1`; verify SMTP, Google, GitHub, Slack, weather, HTTP, and webhook fixtures load correctly.
- [x] 2.2 Implement credential-reference storage and secret rejection; verify raw credentials never appear in serialized registry or workflow payloads.
- [x] 2.3 Implement availability, risk, quota, cost, timeout, retry, and approval metadata checks; verify incomplete metadata is rejected.

## 3. Matching and authorization

- [x] 3.1 Implement capability-to-tool matching with input/output schema compatibility; verify eligible and incompatible candidates.
- [x] 3.2 Implement subject, workspace, role, scope, destination, allowlist, risk, quota, and approval policy evaluation; verify denied-operation fixtures.
- [x] 3.3 Implement authorized assignment responses with contract versions, correlation IDs, opaque credential references, and safe error mapping; verify Harihar and Rethika consumer examples.

## 4. Tests and handoff

- [x] 4.1 Add registry and authorization tests for unassigned tools, revoked scopes, unavailable providers, unsafe destinations, and cross-agent isolation; verify the suite passes.
- [x] 4.2 Create the Aravind handoff listing registry endpoints, capability identifiers, assignment examples, policy decisions, and unresolved defects; verify downstream inputs are named.
- [x] 4.3 Run contract validation and strict OpenSpec validation; verify no planner, UI, or runtime code is implemented in this change.
- [ ] 4.4 Perform Aravind's acceptance review: run the full registry and authorization test suite, contract validation, strict OpenSpec validation, and positive/negative assignment scenarios; record pass/fail evidence and obtain Harihar's and Rethika's review of the registry handoff before marking the segment ready.

## Workflow follow-up

- Start after Suprajha's planner handoff is accepted.
- Notify Harihar and Rethika when authorized assignment examples are available.
- Archive after implementation review and task completion.
