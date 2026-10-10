# Tasks

## 1. Canonical workflow schema v1

- [x] 1.1 Define `workflow-schema-v1.json` with workflow identity, revision, status, inputs, outputs, stakeholders, agents, tools, nodes, edges, conditions, approvals, policies, and metadata; verify the schema loads successfully.
- [x] 1.2 Define typed node kinds, stable IDs, edge references, condition outcomes, and layout metadata rules; verify valid and invalid workflow fixtures.
- [x] 1.3 Add generic workflow examples for at least three domains; verify none require procurement-specific schema fields.

## 2. Agent contract v1

- [x] 2.1 Define `agent-contract-v1.json` with identity, role, goal, instructions, model, input/output schemas, capabilities, tools, permissions, limits, retries, timeouts, approvals, and guardrails; verify the schema loads successfully.
- [x] 2.2 Add valid, incomplete, over-privileged, and secret-bearing agent fixtures; verify invalid fixtures are rejected and secrets are not accepted.
- [x] 2.3 Document how the agent contract maps to the existing UI Agent model without making the UI model authoritative; verify the mapping notes identify demo-only fields.

## 3. Tool contract v1

- [x] 3.1 Define `tool-contract-v1.json` with tool ID, provider, capability, schemas, authentication, permissions, availability, risk, quotas, cost, retries, timeout, and approval requirements; verify the schema loads successfully.
- [x] 3.2 Add registry fixtures for SMTP, Google, GitHub, Slack, Open-Meteo, and approved HTTP/webhook capabilities; verify complete and incomplete entries behave correctly.
- [x] 3.3 Add authorization fixtures for missing credentials, unallowlisted destinations, unavailable tools, and cross-agent tool isolation; verify prohibited assignments are rejected.

## 4. Contributor handoff protocol

- [x] 4.1 Create `docs/contributors/ownership.md` with the four named owners, segment responsibilities, upstream inputs, downstream consumers, and contract dependencies; verify all owners and boundaries are present.
- [x] 4.2 Create onboarding and handoff templates for Suprajha, Aravind, Harihar, and Rethika; verify each template includes status, completed work, evidence, defects, unresolved decisions, dependencies, downstream notifications, next actions, and blockers.
- [x] 4.3 Document name-based onboarding behavior for “I am Suprajha,” “I am Aravind,” “I am Harihar,” and “I am Rethika”; verify each response path identifies the correct scope and accumulated context.
- [x] 4.4 Define hard-block versus warning rules for upstream defects; verify a contract violation blocks dependent work while an independent cosmetic issue does not.
- [x] 4.5 Define the no-implicit-implementation rule for contributor onboarding; verify identity recognition produces a briefing without modifying code.

## 5. Contract review and handoff validation

- [x] 5.1 Have Suprajha, Aravind, Harihar, and Rethika review the three contracts and record accepted versions or requested changes; verify every review has an owner and decision.
- [x] 5.2 Run strict OpenSpec validation and contract fixture checks; verify the shared-contract-pack-v1 change is valid before the next contract stage begins.
- [x] 5.3 Record the next blocked stage explicitly: API payloads, error format, authentication/permissions, branching/approvals, run status, and versioning; verify no later-stage implementation is included in this change.

## Workflow follow-up

- After this change is reviewed and accepted, create the API/error/authentication contract change.
- Before any contributor starts their implementation segment, use the handoff briefing for that contributor.
- When Rethika joins, provide the complete accumulated handoff context from Suprajha, Aravind, and Harihar.
