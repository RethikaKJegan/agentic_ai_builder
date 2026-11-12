## ADDED Requirements

### Requirement: Grouped percentages use a declared denominator
The system SHALL derive percentages only from complete compatible verified count receipts and a declared overall-population or within-group basis. It SHALL retain query provenance, reject incompatible evidence, and never report a zero denominator as zero percent.

#### Scenario: Overall-population percentage
- **WHEN** complete grouped numerator and denominator counts have an overall-population basis
- **THEN** each numerator group is divided by the complete denominator population using Decimal arithmetic

#### Scenario: A group has no matching numerator rows
- **WHEN** the complete denominator contains a group absent from a complete numerator query
- **THEN** the group's numerator is zero

### Requirement: Aggregate evidence is distinct from attached records
The report SHALL explain that the individual-record section excludes aggregate query results.

#### Scenario: Aggregate-only report
- **WHEN** there are no individual mapped records
- **THEN** its empty state does not imply that the run retrieved no query evidence
