# Design

## Context

Suprajha's planner emits capabilities and unresolved tool requirements, not permissions or credentials. The registry must consume that handoff and produce safe assignments for UI display and runtime enforcement.

## Goals / Non-Goals

**Goals:**

- Keep agent validation, tool discovery, matching, and authorization in one explicit boundary.
- Support real connector metadata while keeping secrets outside workflow and agent payloads.
- Make every assignment explainable through contract versions, scopes, policy decisions, and correlation IDs.

**Non-Goals:**

- Calling providers or executing tools.
- Generating planner workflows.
- Owning UI presentation or CrewAI runtime orchestration.

## Decisions

1. **Capability-first matching:** match planner capabilities before provider selection, so the same workflow remains generic across providers.
2. **Policy evaluation before assignment:** evaluate identity, workspace, scopes, allowlists, risk, quotas, and approval requirements before returning an executable assignment.
3. **Credential references only:** the registry returns opaque credential IDs and provider metadata; secret retrieval remains a protected runtime concern.
4. **Versioned decision records:** every accepted or denied assignment records contract versions, request ID, policy inputs, and decision reason for downstream debugging.

## Risks / Trade-offs

- **[Risk] A broad capability could match an unsafe connector.** → Require schema compatibility, destination policy, risk checks, and explicit approval metadata.
- **[Risk] Registry metadata becomes stale.** → Include availability timestamps/versioning and revalidate before runtime execution.
- **[Risk] Provider-specific behavior leaks into the workflow.** → Keep provider details in tool metadata and expose stable capability identifiers.

## Migration Plan

1. Add registry schemas/adapters and fixture-backed policy evaluation.
2. Register initial approved tools without enabling external execution.
3. Consume Suprajha's planner handoff and publish assignments for UI/runtime tests.
4. Roll back by disabling assignment issuance; retain contract files and planner drafts.
