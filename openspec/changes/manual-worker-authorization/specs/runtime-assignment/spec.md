## ADDED Requirements

### Requirement: Recover approved manual assignments across workers
The runtime SHALL recover exact Registry assignment approval evidence for an immutable validated published revision when its original approver is the currently authenticated executor and retains required approval authority. Current Registry scopes, availability and policy SHALL still be enforced.

#### Scenario: Fresh worker receives an approved manual run
- **WHEN** a fresh worker loads an approved published revision for its original authorized approver
- **THEN** process-local missing approval evidence is reconstructed without changing the workflow or skipping action approval gates

#### Scenario: Approval authority is absent
- **WHEN** the caller differs from the original approver or lacks approval permission or scopes
- **THEN** pending assignments remain unauthorized
