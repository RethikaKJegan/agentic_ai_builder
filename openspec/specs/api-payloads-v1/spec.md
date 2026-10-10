# api-payloads-v1 Specification

## Purpose
Defines the stable request and response envelopes that connect the existing UI, planner, registry, validator, approval flow, runtime, and run history.

## Requirements

### Requirement: Correlated API envelopes
Every API request and response SHALL support a request ID and SHALL identify the relevant workflow, version, or run when applicable.

#### Scenario: Planning request
- **WHEN** the UI submits a natural-language requirement
- **THEN** the response SHALL include a request ID and a schema-valid workflow proposal or a structured error

### Requirement: Workflow lifecycle endpoints
The API SHALL provide contracts for planning, listing, reading, saving, validating, approving, and executing workflow versions.

#### Scenario: Save workflow revision
- **WHEN** the UI saves an edited workflow
- **THEN** the API SHALL return the persisted workflow ID, version, status, and validation state

### Requirement: Run and tool endpoints
The API SHALL provide contracts for tool discovery, capability discovery, run status, run events, and approval decisions.

#### Scenario: Run status request
- **WHEN** the UI requests a run by ID
- **THEN** the API SHALL return its current status, workflow version, steps or events, and available next actions

### Requirement: Consistent pagination
Collection responses SHALL use a consistent pagination shape with items, cursor or page information, and total information when available.

#### Scenario: Tool listing
- **WHEN** the UI requests registered tools
- **THEN** the response SHALL use the shared collection envelope rather than a provider-specific list shape
