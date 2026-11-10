## ADDED Requirements

### Requirement: Distinguish planning caveats from clarification
Generic query agents SHALL receive trusted execution-time guidance that representable authorized queries leave clarification empty, row counts require no measure/unit, and sampled metadata alone does not establish result sampling or require user input. Actual coverage SHALL come from the query executor rather than model claims.

#### Scenario: Account-scoped record count
- **WHEN** the user specifies the dataset and requests its accessible record count
- **THEN** the guidance selects a row-count metric without requiring a measurement unit or pre-execution coverage evidence

### Requirement: Preserve unresolved meaning guards
Nonempty query clarifications SHALL continue to block source reads. Guidance SHALL preserve clarification for actual source/field/relationship ambiguity and unsupported operations.

#### Scenario: Ambiguous operating hours
- **WHEN** the intended hours measure is not established
- **THEN** no heuristic removes clarification or executes the query
