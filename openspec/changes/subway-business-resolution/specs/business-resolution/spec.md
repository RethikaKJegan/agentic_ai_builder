## ADDED Requirements

### Requirement: Structured business readiness
New model selections SHALL distinguish nonblocking methodological notes from a missing business definition, using an explicit readiness state and separate question/notes fields. A ready state SHALL have an empty blocking question. An unresolved state SHALL have a nonempty blocking question. Contradictory legacy clarification text SHALL not be silently ignored.

#### Scenario: Descriptive source comparison
- **WHEN** a descriptive request can retain distinct source measures separately with explicit limitations
- **THEN** notes do not require user confirmation solely to describe those source values
- **AND** planning does not invent an approved measure, equivalence, policy or permission

#### Scenario: Business policy needed
- **WHEN** a requested authoritative classification requires an unspecified policy
- **THEN** planning stops with the actual missing business question

#### Scenario: Previously saved interpretation
- **WHEN** a selection predates the structured readiness field
- **THEN** its existing clarification behavior remains unchanged
