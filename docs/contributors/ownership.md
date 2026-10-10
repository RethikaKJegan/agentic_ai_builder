# Contributor Ownership

## Shared contract gate

Suprajha, Aravind, Harihar, and Rethika jointly review the shared contracts. No individual segment may silently change a shared contract.

## Suprajha — planning pipeline

- **Inputs:** natural-language requirements, workflow schema v1
- **Owns:** planning request handling, structured planning, task/stakeholder extraction, agent/deterministic classification, capability identification
- **Delivers:** schema-valid workflow proposals and planner verification evidence
- **Downstream:** Aravind consumes capabilities and agent requirements; Harihar consumes workflow proposals; Rethika consumes approved workflow structure

## Aravind — agent and Tool Registry

- **Inputs:** Suprajha’s workflow proposals, agent contract v1, tool contract v1
- **Owns:** agent configuration validation, capabilities, tool registration, selection, permissions, credential references, risk, quotas, availability
- **Delivers:** authorized tool assignments and registry verification evidence
- **Upstream dependency:** Suprajha’s capability identifiers and agent requirements
- **Downstream:** Harihar consumes tool metadata; Rethika consumes authorized tool sets

## Harihar — existing Lovable UI integration and workflow API

- **Inputs:** workflow, agent, and tool contracts; existing UI archive
- **Owns:** API/client integration, workflow loading/saving/versioning, agent/tool panels, validation display, approvals/publish controls, run status/history
- **Delivers:** backend-connected existing UI and frontend verification evidence
- **Upstream dependency:** accepted planner output and registry contracts
- **Downstream:** Rethika consumes approved workflow submissions

## Rethika — runtime and observability

- **Inputs:** approved workflow, authorized agents/tools, UI execution request
- **Owns:** CrewAI execution, graph control flow, approvals, budgets, connectors, run records, traces, failures
- **Delivers:** bounded execution and observability verification evidence
- **Upstream dependencies:** all earlier accepted contracts and handoffs

## Handoff status vocabulary

- `not-started`: no implementation evidence exists
- `in-progress`: work is actively being implemented
- `ready-for-handoff`: deliverables and verification evidence exist
- `blocked`: a dependency or contract defect prevents safe continuation
- `accepted`: downstream owner reviewed the handoff
- `complete`: segment acceptance criteria are met
