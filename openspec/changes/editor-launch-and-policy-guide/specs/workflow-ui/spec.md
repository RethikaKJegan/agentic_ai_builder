## ADDED Requirements
### Requirement: Exact revision combined preparation
The editor SHALL provide a combined save/validate/approval/publish/activate action, report per-stage progress, and stop on failure, edits made during the sequence, conflicts or absent authority. It SHALL reload authoritative saved/release state before continuing and never bypass existing server approval checks.
#### Scenario: Approval waiting
- **WHEN** a validated revision needs approval unavailable to the session
- **THEN** it is submitted through the existing API and the editor reports Awaiting approval without publishing or activating
#### Scenario: Resume
- **WHEN** preparation is retried after an interruption
- **THEN** confirmed server stages are reconciled before further transitions and no automatic mutation retry is initiated
### Requirement: Editor active release execution
Run SHALL use the exact active release revision, collect needed inputs, retain existing duplicate/idempotency protection and verify active release identity before execution. Once accepted, the returned run SHALL be selected in editor Execution without navigation to Runs.
#### Scenario: Dirty draft
- **WHEN** an edited draft differs from an active release
- **THEN** Run is labelled with the active revision and executes that revision without saving or running the draft
### Requirement: Policy handbook guidance
Organization Policies SHALL use the approved imperative guidance statements and omit unavailable technical metadata, while preserving real approval requirements and safeguard settings.
#### Scenario: Missing policy version
- **WHEN** policy version is absent
- **THEN** its row is omitted instead of showing a placeholder or fabricated version
