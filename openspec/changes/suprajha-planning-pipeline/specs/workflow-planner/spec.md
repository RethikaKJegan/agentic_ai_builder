# Spec Delta

## Purpose

Provides a generic, contract-safe planning capability that transforms a user's objective into a reviewable workflow draft for downstream registry, UI, runtime, and observability components.

## ADDED Requirements

### Requirement: Accept a planning request

The planner SHALL accept a request containing an authenticated subject, workspace context, user objective, optional constraints, and an idempotency key according to the accepted API payload contract.

#### Scenario: Valid generic objective

- **WHEN** an authorized builder submits a non-empty objective with a valid workspace and idempotency key
- **THEN** the planner accepts the request and returns a planning response identified by a request ID

#### Scenario: Missing objective

- **WHEN** a request omits the objective or supplies only whitespace
- **THEN** the planner rejects it with the accepted validation error format and identifies the objective field

### Requirement: Generate a structured workflow draft

The planner SHALL produce a workflow draft with explicit tasks, agent requirements, deterministic steps, tool references, dependencies, conditions, approvals, and unresolved requirements where applicable.

#### Scenario: Multi-step objective

- **WHEN** the model identifies multiple dependent actions in an objective
- **THEN** the response contains ordered workflow nodes and edges with stable identifiers and no implicit steps

#### Scenario: Generic domain objective

- **WHEN** the objective concerns a domain such as support, onboarding, procurement, or reporting
- **THEN** the planner uses the same contract shape without selecting a domain-specific code path

### Requirement: Keep capability and tool references explicit

The planner SHALL describe required agent capabilities and requested tool references without granting permissions or inventing unavailable tool definitions.

#### Scenario: Required capability identified

- **WHEN** a task requires classification, retrieval, notification, or another capability
- **THEN** the workflow draft records the capability requirement and leaves registry assignment to the Tool Registry

#### Scenario: Tool is not defined

- **WHEN** the objective implies an external operation that has no accepted tool reference
- **THEN** the planner records the requirement as unresolved or unsupported and does not fabricate credentials, scopes, or tool metadata

### Requirement: Represent conditions and human approvals

The planner SHALL express branches, approval gates, rejection paths, and unresolved decision points using the accepted branching and approval semantics.

#### Scenario: Risky external action

- **WHEN** a proposed step can create an external side effect or requires a human decision
- **THEN** the draft includes an approval gate or an explicit unresolved approval requirement before that step

#### Scenario: Conditional path

- **WHEN** an objective includes an if/then decision
- **THEN** the draft includes condition outcomes and explicit successor paths, including an unmatched or otherwise unresolved path where necessary

### Requirement: Validate model output before returning it

The planner SHALL reject malformed, incomplete, unauthorized, or unsafe structured model output before it reaches a downstream consumer.

#### Scenario: Valid structured output

- **WHEN** the model output conforms to all required v1 schemas and safety checks
- **THEN** the planner returns the normalized workflow draft

#### Scenario: Invalid structured output

- **WHEN** the model output contains duplicate identifiers, missing required fields, invalid references, secret material, or an illegal transition
- **THEN** the planner returns a stable non-success error with a request ID and does not persist or publish the draft

### Requirement: Preserve traceability and idempotency

The planner SHALL return correlation metadata and SHALL not create multiple planning results for the same valid idempotency key in the same workspace.

#### Scenario: Repeated request

- **WHEN** the same authorized subject submits the same idempotency key again
- **THEN** the planner returns the existing planning result or a stable in-progress response without creating a duplicate result

#### Scenario: Request trace metadata

- **WHEN** a planning request succeeds or fails
- **THEN** the response or error includes the accepted request and correlation identifiers without exposing model credentials or provider secrets
