# Design

## Context

The shared workflow, agent, tool, API, error, permission, branching, approval, run-status, and versioning contracts are accepted and validated. The planner is the first implementation boundary and must create drafts for review; it must not execute tools or depend on the existing UI's local simulation.

## Goals / Non-Goals

**Goals:**

- Provide one generic planning boundary for all supported domains.
- Use OpenAI structured output while keeping provider-specific details behind the planner boundary.
- Validate and normalize every draft against the shared JSON schemas and cross-reference rules.
- Preserve idempotency, authorization context, traceability, and safe error behavior.
- Produce clear handoff artifacts for Aravind, Harihar, and Rethika.

**Non-Goals:**

- Implement agent registration or Tool Registry selection.
- Execute CrewAI agents, connectors, approvals, or external side effects.
- Change or rebuild the existing Lovable/TanStack UI.
- Persist runtime event streams or implement Langfuse integration.

## Decisions

1. **Planner output is a workflow draft, not an executable run.** This keeps planning separate from runtime authorization and side effects. A runtime implementation can later consume the accepted draft without trusting model output directly.
2. **Structured output is validated twice: model-shape validation and contract/cross-reference validation.** JSON schema validation catches shape errors; cross-reference checks catch duplicate IDs, missing nodes, invalid tool references, unsafe secrets, and illegal transitions.
3. **Tool assignment remains unresolved until the registry stage.** The planner emits capability requirements and references only accepted tool identifiers; it never grants scopes or creates credentials.
4. **Idempotency is workspace-scoped.** The planner uses the API contract's idempotency key and workspace context so retries do not create duplicate planning results while separate workspaces remain isolated.
5. **The provider boundary is replaceable.** OpenAI is the initial model provider, but prompt construction and model invocation are isolated behind a planner adapter so another provider can be introduced without changing the external contract.

## Risks / Trade-offs

- **[Risk] Model output may be semantically incomplete even when it is valid JSON.** → Require explicit unresolved requirements and human review metadata rather than silently filling gaps.
- **[Risk] Planning prompts can accidentally include sensitive context.** → Minimize context passed to the model, redact secrets, and reject secret-like output before persistence.
- **[Risk] A large objective can produce an unwieldy graph.** → Apply bounded node/depth limits and return a reviewable validation error when limits are exceeded.
- **[Risk] Idempotency storage can become stale.** → Store contract version and request fingerprint with results and reject mismatched retries deterministically.

## Migration Plan

1. Add the planner service behind the accepted API contract.
2. Run unit and contract tests using generic fixtures.
3. Exercise the planner with review-only examples; do not enable external execution.
4. Hand off capability identifiers to Aravind, API payload behavior to Harihar, and draft/run boundary details to Rethika.
5. Roll back by disabling the planner route and retaining the shared contract files; no existing Praxi or fire-detection structure is changed.
