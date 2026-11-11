## ADDED Requirements

### Requirement: Verified compatible counts support deterministic percentages
Content preparation SHALL receive deterministic percentage evidence for compatible
complete count aggregates from verified completed direct query dependencies. It SHALL
include numerator/denominator counts, query references, formula, rounding and scope.
It SHALL NOT calculate counts from displayed records or merge incompatible populations.

#### Scenario: Filtered count divided by complete total
- **WHEN** the same scoped source supplies complete filtered and total count aggregates
- **THEN** the content step receives a deterministic percentage for use in report and spreadsheet

### Requirement: Invalid denominators and incomplete results remain limited
Incomplete scans, missing aggregate coverage, grouped results, joins, conflicting
scopes/revisions, non-count metrics, malformed counts or non-subset populations SHALL
not yield percentage evidence. Zero denominators SHALL produce an undefined result.

#### Scenario: No total population
- **WHEN** compatible complete counts have zero denominator
- **THEN** no numeric percentage is invented
