## ADDED Requirements

### Requirement: Descriptive measures remain distinct
The system SHALL support descriptive summaries of multiple recorded measures without choosing an authoritative business basis. It SHALL validate and preserve selected source identities, grouping dimensions and aggregate operations. Policy classifications SHALL retain required business clarification.

#### Scenario: Multiple recorded value fields
- **WHEN** a descriptive summary has multiple supported candidate source measures
- **THEN** intent may select separate named metrics for each measure and proceed without conflating them

#### Scenario: A metric is omitted
- **WHEN** generated query content omits a pinned metric or changes its grouping
- **THEN** validation rejects it before reading source records

#### Scenario: An authoritative classification lacks its rule
- **WHEN** the requested decision requires an absent approved business definition
- **THEN** the existing needs-definition clarification remains blocking
