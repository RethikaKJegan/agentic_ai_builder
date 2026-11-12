## ADDED Requirements

### Requirement: Preserve conjunctive query meaning
Flat filters SHALL remain AND predicates. Provably unsatisfiable combinations on the same field SHALL be rejected before scanning source rows rather than returned as a clean zero-match finding.

#### Scenario: Null and ordered comparison
- **WHEN** a conjunction requires the same field to be null and ordered below a nonnull value
- **THEN** validation rejects the query before source dispatch
- **AND** no filters are dropped or reinterpreted as alternatives

#### Scenario: Compatible predicates and legitimate zero matches
- **WHEN** predicates are compatible but no source record matches
- **THEN** the executor retains its existing valid zero-match result

### Requirement: Alternative-condition workflow branches
Workflow planning SHALL represent requested alternative conditions using separate supported query branches where the query grammar has no OR operator. Reports SHALL use all relevant branch outputs and preserve each branch's complete counts and coverage, without inventing a distinct union count for overlapping conditions.

#### Scenario: Negative or missing recorded values
- **WHEN** a user requests both alternative categories
- **THEN** the generated workflow plans separate conjunctive reads for each category
- **AND** reporting receives both actual query receipts
