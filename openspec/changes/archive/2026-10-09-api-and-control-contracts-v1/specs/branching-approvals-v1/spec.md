# Spec Delta

## Purpose

Defines deterministic condition evaluation, branch reachability, approval pauses, rejection behavior, and timeout behavior for workflow execution.

## ADDED Requirements

### Requirement: Explicit branch outcomes
Every condition SHALL declare possible outcomes, and every reachable branch SHALL identify the outcome that selects it.

#### Scenario: Missing branch outcome
- **WHEN** a condition edge has no declared outcome
- **THEN** validation SHALL reject the workflow before approval

### Requirement: Deterministic branch selection
The runtime SHALL evaluate a condition once for a node execution and SHALL follow only the edge matching the resulting declared outcome.

#### Scenario: Standard branch
- **WHEN** a condition evaluates to `standard`
- **THEN** the runtime SHALL follow the `standard` edge and skip nonmatching branches

### Requirement: Approval pause and resume
An approval node SHALL pause execution, expose an approval request, and resume only after an authorized decision.

#### Scenario: Approval granted
- **WHEN** an authorized approver accepts a pending approval
- **THEN** the run SHALL resume at the configured approved path

### Requirement: Rejection and timeout paths
Approval rejection or timeout SHALL follow an explicit stop, branch, or retry policy and SHALL never silently continue an external side effect.

#### Scenario: Approval rejected
- **WHEN** an approver rejects an approval
- **THEN** the runtime SHALL follow the configured rejection path and record the decision
