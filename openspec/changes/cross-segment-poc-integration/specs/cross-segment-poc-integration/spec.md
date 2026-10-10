# Spec Delta

## Purpose

Provides the final integration gate that proves the four independently owned segments exchange accepted contracts and complete a safe, observable generic workflow.

## ADDED Requirements

### Requirement: Connect the four segment outputs

The integration SHALL pass a workflow from planner output through authorized registry assignments, the existing UI/API boundary, and runtime execution without translating into an unversioned parallel format.

#### Scenario: Generic workflow submission

- **WHEN** a valid generic objective is planned, assigned, edited, approved, and submitted
- **THEN** the runtime receives the same versioned workflow and authorized tool references represented by the UI

### Requirement: Resolve planned capabilities automatically

The integration SHALL normalize planner-created agents and resolve each requested capability through enabled, schema-compatible, credential-backed, policy-authorized Registry tools without accepting planner-created authority.

#### Scenario: Newly planned email workflow

- **WHEN** a planner draft requests `send_email` and an eligible SMTP tool is configured
- **THEN** the resolved workflow contains the selected tool, a workflow-scoped registered agent, and an authorization or approval-required state without an operator-authored workflow-specific binding

#### Scenario: No eligible tool

- **WHEN** no configured tool satisfies the requested capability and policy
- **THEN** the requirement remains unresolved and review exposes safe candidate exclusion reasons

### Requirement: Materialize executable workflow graphs

The planner and integration SHALL represent external actions as explicit tool nodes with typed input mappings and SHALL place external-write nodes only on an approved path.

#### Scenario: Spreadsheet event sends email

- **WHEN** a workflow reads spreadsheet data and conditionally sends email
- **THEN** the canonical graph contains distinct read, condition, approval, send, rejection, and output nodes with valid references

### Requirement: Bind approval to exact external action

Approval evidence SHALL be scoped to the workflow revision, assigned agent and tool, destination, and approved action boundary, and runtime execution SHALL revalidate it immediately before connector invocation.

#### Scenario: Recipient changes after approval

- **WHEN** a resolved email action targets a recipient outside the approved action boundary
- **THEN** Registry or runtime authorization SHALL block the connector invocation

### Requirement: Expose resolution and execution state

The UI SHALL distinguish requested capabilities, selected tools, pending approval, authorized assignments, unresolved requirements, workflow revision status, and run status.

#### Scenario: Tool selected automatically

- **WHEN** Registry resolves a planner capability
- **THEN** the editor identifies the selected tool and its authorization state without requiring manual workflow-specific binding configuration

### Requirement: Verify control and failure paths

The integration SHALL verify validation failures, authorization denial, approval rejection, branch selection, timeout, retry exhaustion, budget exhaustion, duplicate requests, and connector failure.

#### Scenario: Prohibited action

- **WHEN** a workflow attempts an unauthorized tool or rejected approval path
- **THEN** the action is blocked and the UI, run record, error response, and trace show the same safe reason

### Requirement: Demonstrate safe real connector behavior

The integration SHALL demonstrate at least one explicitly approved connector with controlled credentials, destination allowlists, idempotency, and redacted output using an offline adapter, and SHALL run a real connector smoke test only when the operator explicitly configures it.

#### Scenario: Approved SMTP demonstration

- **WHEN** an approved test workflow invokes SMTP with configured test credentials and destination
- **THEN** the message result, run status, correlation ID, and trace reference are recorded without exposing secrets

### Requirement: Record ownership and acceptance evidence

The integration SHALL record test evidence, contract versions, defects, and owner notifications for each failed or incomplete boundary.

#### Scenario: Boundary defect

- **WHEN** an end-to-end test fails at a segment boundary
- **THEN** the evidence identifies the owning segment, affected contract, reproduction, and downstream impact without masking the failure

### Requirement: Keep provider execution generic

The integration SHALL resolve provider-neutral planner capabilities through the
Registry and dispatch them through versioned server adapters without embedding a
workflow-specific provider branch in the planner or UI.

#### Scenario: Multiple provider choices

- **WHEN** a request asks to retrieve data, classify it, and notify a recipient
- **THEN** the planner emits capabilities and typed mappings, the Registry selects
  eligible tools, and the runtime invokes the selected tool IDs through their
  adapters with the same authorization boundary

#### Scenario: Configured metadata without an adapter

- **WHEN** a provider has credentials and Registry metadata but no runtime adapter
- **THEN** the tool remains unavailable for publication/execution and the UI shows
  a stable configuration/adapter blocker

### Requirement: Support generic triggers and updates

The integration SHALL represent incoming events, polling cursors, provider
receipts, update actions, and release-bound dispatch jobs explicitly; a read or
send tool SHALL NOT imply an incoming event source.

#### Scenario: New row trigger

- **WHEN** an authorized polling trigger observes a new record
- **THEN** it creates one deduplicated release-bound job with the configured input
  mapping and the workflow runs without a user-entered run ID

### Requirement: Expose generic execution observability

The integration SHALL expose provider-neutral run, approval, tool-call, budget,
failure, correlation, and trace data through the API and Monitoring UI.

#### Scenario: Completed provider run

- **WHEN** a published workflow completes an authorized provider action
- **THEN** Runs and Monitoring show its status, events, counters, failure state,
  correlation ID, and trace reference without exposing credentials or raw secrets
