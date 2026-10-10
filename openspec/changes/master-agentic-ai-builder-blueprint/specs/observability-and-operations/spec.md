# Spec Delta

## Purpose

Defines the operational record and trace requirements needed to inspect workflow planning, execution, tool activity, performance, cost, and failures.

## ADDED Requirements

### Requirement: Unique execution identity
Each workflow execution SHALL have a unique run ID linked to the workflow ID, version, initiating user, and execution status.

#### Scenario: New run
- **WHEN** an approved workflow starts
- **THEN** the system SHALL create a unique run record before agent or tool execution begins

### Requirement: Execution event capture
The system SHALL capture agent, tool, model, duration, token, estimated cost, error, approval, and status events for each run.

#### Scenario: Tool failure
- **WHEN** a connector returns an error
- **THEN** the run record and trace SHALL include the tool identity, failure state, and relevant error classification

### Requirement: Trace privacy
Sensitive credentials and protected data SHALL be excluded or redacted from observability records according to the project’s data-protection policy.

#### Scenario: Credential-bearing payload
- **WHEN** an execution event contains a secret or credential
- **THEN** the recorded event SHALL redact or omit that value

### Requirement: User-facing run visibility
The UI SHALL present simplified execution progress, status, failures, and links or references to detailed engineering traces.

#### Scenario: Run inspection
- **WHEN** a user opens a completed or active run
- **THEN** the UI SHALL show its current state and relevant step outcomes without exposing protected data
