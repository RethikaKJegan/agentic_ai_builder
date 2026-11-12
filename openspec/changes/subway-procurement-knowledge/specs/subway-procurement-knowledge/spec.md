## ADDED Requirements

### Requirement: Source-bound Subway procurement semantics
The system SHALL version and hash-bind procurement definitions to the existing Subway ontology, retaining typed identity, source-specific states, dates, rule provenance and unresolved references.

#### Scenario: Unknown approval status
- **WHEN** a source status is not a supported source-defined approval state
- **THEN** the result preserves the raw value and unknown meaning without classifying it as pending

### Requirement: Evidence-aware deterministic assessments
The system SHALL execute reusable typed checks through tenant-authorized registered tools and preserve independent findings when prerequisites are missing.

#### Scenario: Missing budget reservation
- **WHEN** reservedAmount is absent
- **THEN** the reservation check returns INSUFFICIENT_EVIDENCE without deriving a reservation

### Requirement: Safe reconciliation
The system SHALL match receipt lines only to their source-defined PO line IDs, retain one monetary header per source record and prohibit arbitrary array joins.

#### Scenario: Partial deliveries
- **WHEN** multiple receipts reference one PO line
- **THEN** compatible received quantities are summed without duplicating PO header totals

### Requirement: Isolated modeled scenarios
The system SHALL keep modeled datasets out of live tools and mark modeled policy outcomes as nonauthoritative.

#### Scenario: Production execution
- **WHEN** an assessment is executed through the production connector
- **THEN** records originate exclusively from authorized sources and no scenario selector or caller-supplied records are accepted
