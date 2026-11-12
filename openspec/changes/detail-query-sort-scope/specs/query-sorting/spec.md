## ADDED Requirements
### Requirement: Authorized detail sort scope
Detail queries SHALL be allowed to sort by authorized base-source fields independently of display projection. Aggregate queries SHALL only sort returned group or metric columns.

#### Scenario: Unprojected base sort
- **WHEN** a detail query sorts by a permitted base field omitted from its display columns
- **THEN** the complete matching population is sorted before pagination without exposing the sort field as a result column

#### Scenario: Unavailable sort field
- **WHEN** a detail sort references an unknown, unrelated or joined field
- **THEN** validation rejects the query before source execution
