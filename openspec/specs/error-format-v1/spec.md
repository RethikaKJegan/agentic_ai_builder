# error-format-v1 Specification

## Purpose
Defines a stable, actionable, and privacy-safe error format shared by the planner, API, UI, Tool Registry, approval flow, and runtime.

## Requirements

### Requirement: Structured error envelope
Every reported failure SHALL include an error code, safe message, request ID, and retryability indicator.

#### Scenario: Validation failure
- **WHEN** a workflow fails validation
- **THEN** the response SHALL identify the validation error without exposing credentials or internal secrets

### Requirement: Field and detail context
Errors SHALL support an optional field path, machine-readable details, and a list of related errors for actionable correction.

#### Scenario: Invalid edge
- **WHEN** an edge references a missing node
- **THEN** the error SHALL identify the edge field path and the missing reference

### Requirement: Safe external error mapping
Provider errors SHALL be mapped to stable internal codes and SHALL not expose raw provider credentials, prompts, or unrestricted response bodies.

#### Scenario: Connector error
- **WHEN** an external connector returns an authentication error
- **THEN** the system SHALL return a safe authorization error and record provider details only in protected diagnostics
