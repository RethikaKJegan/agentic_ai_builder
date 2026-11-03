## ADDED Requirements
### Requirement: Actionable contribution validation
The planner SHALL diagnose contribution binding defects precisely and correct only unambiguous grounded representations, without inventing references or workflow actions.

#### Scenario: Invalid contribution representation
- **WHEN** a proposed contribution cannot be linked to an actual action and owned retrieved reference
- **THEN** correction feedback identifies the failed constraint and preserves the existing bounded attempt limit

#### Scenario: Grounded representation
- **WHEN** a contribution uses an unambiguous equivalent reference representation
- **THEN** any normalization preserves the exact saved definition identity and records the transformation
