## ADDED Requirements
### Requirement: Hide passive Registry summary
The workflow editor SHALL NOT display the passive red Registry blockers summary beneath revision controls. Existing action gating and actual API failure feedback SHALL remain unchanged.

#### Scenario: Draft has pending tool approvals
- **WHEN** the editor loads a draft with Registry reason codes
- **THEN** the passive red summary is absent
- **AND** server validation and approval requirements remain enforced
