## ADDED Requirements

### Requirement: Business answers query all relevant supplied records
Subway queries SHALL apply explicit filters before complete aggregations, return exact
matched counts and distinguish result pagination from data scanning. New planning SHALL
prefer the full-data capability rather than package inspection samples.

#### Scenario: Matching record is beyond the initial sample
- **WHEN** a validated query filters for that record
- **THEN** it is returned independently of the former 25-row inspection bound

### Requirement: Relationships preserve unmatched source evidence
A query SHALL use only allowlisted relationships and preserve unmatched source rows in
left joins, with exact measured match coverage. It SHALL NOT fabricate missing parents.

#### Scenario: A reference has no native parent
- **WHEN** a query traverses the relationship
- **THEN** source facts remain present and missing target values remain explicit
- **AND** no total is described as fully matched without its coverage qualification

### Requirement: Query content conveys no execution authority
Generated plans SHALL be validated against authenticated current Subway metadata and
pinned model/relationship evidence. No caller-provided SQL, Mongo operators, credentials
or arbitrary collection names SHALL be executed. Existing workflow budgets SHALL meter
query-plan model generation.

#### Scenario: A query selects another client's source
- **WHEN** execution validates it
- **THEN** access is denied before the database is queried
