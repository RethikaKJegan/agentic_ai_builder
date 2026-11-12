## ADDED Requirements

### Requirement: Complete high-cardinality aggregates with bounded resources
The query executor SHALL compute all matched groups within existing source/time authority using bounded memory and private size-bounded temporary storage. It SHALL fail without returning partial totals if an actual resource budget is exhausted.

#### Scenario: More than ten thousand groups
- **WHEN** a valid query has more than ten thousand groups within resource budgets
- **THEN** it returns an ordered display page and exact total group and matched record counts
- **AND** decimal precision, filters, joins and currency semantics are preserved

### Requirement: Byte-bounded display pagination
The executor SHALL keep successful responses within the existing byte budget and distinguish displayed rows from complete aggregate computation.

#### Scenario: Requested page exceeds response budget
- **WHEN** display rows exceed the response byte bound
- **THEN** it returns the largest fitting prefix with exact returned-row count, has_more and next_offset
- **AND** total rows and matched counts retain their complete source meanings

#### Scenario: A single row cannot fit
- **WHEN** even one row with its required metadata exceeds the response budget
- **THEN** it rejects the result without an empty non-progressing continuation page
