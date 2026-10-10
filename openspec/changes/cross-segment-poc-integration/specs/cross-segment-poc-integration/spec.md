# Spec Delta

## Purpose

Provides the final integration gate that proves the four independently owned segments exchange accepted contracts and complete a safe, observable generic workflow.

## ADDED Requirements

### Requirement: Connect the four segment outputs

The integration SHALL pass a workflow from planner output through authorized registry assignments, the existing UI/API boundary, and runtime execution without translating into an unversioned parallel format.

#### Scenario: Generic workflow submission

- **WHEN** a valid generic objective is planned, assigned, edited, approved, and submitted
- **THEN** the runtime receives the same versioned workflow and authorized tool references represented by the UI

### Requirement: Verify control and failure paths

The integration SHALL verify validation failures, authorization denial, approval rejection, branch selection, timeout, retry exhaustion, budget exhaustion, duplicate requests, and connector failure.

#### Scenario: Prohibited action

- **WHEN** a workflow attempts an unauthorized tool or rejected approval path
- **THEN** the action is blocked and the UI, run record, error response, and trace show the same safe reason

### Requirement: Demonstrate safe real connector behavior

The integration SHALL demonstrate at least one explicitly approved connector with controlled credentials, destination allowlists, idempotency, and redacted output.

#### Scenario: Approved SMTP demonstration

- **WHEN** an approved test workflow invokes SMTP with configured test credentials and destination
- **THEN** the message result, run status, correlation ID, and trace reference are recorded without exposing secrets

### Requirement: Record ownership and acceptance evidence

The integration SHALL record test evidence, contract versions, defects, and owner notifications for each failed or incomplete boundary.

#### Scenario: Boundary defect

- **WHEN** an end-to-end test fails at a segment boundary
- **THEN** the evidence identifies the owning segment, affected contract, reproduction, and downstream impact without masking the failure
