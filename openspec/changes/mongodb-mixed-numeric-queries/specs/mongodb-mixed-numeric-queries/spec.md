## ADDED Requirements

### Requirement: Bounded mixed-numeric database aggregation
MongoDB fields whose reviewed metadata contains only supported numeric types SHALL be eligible for database aggregation, including integer/number mixtures. Every actual source value SHALL still pass BSON type and existing numeric-envelope checks. Double conversion SHALL preserve its binary value through a decimal round trip.

#### Scenario: HMR source exceeds the application row cap
- **WHEN** an authorized numeric HMR range query targets more than 5,000 source records
- **THEN** supported Mongo numeric metadata selects the existing bounded database executor
- **AND** complete matching-population metrics are independent of display limits

### Requirement: Preserve unsupported-shape and precision guards
Unsupported mixed types, PostgreSQL floats, lossy decimal conversion and existing resource-limit violations SHALL NOT be silently accepted or truncated.

#### Scenario: Double loses precision during conversion
- **WHEN** converting a BSON double to decimal and back changes its binary value
- **THEN** execution rejects the source with no partial result
