## ADDED Requirements

### Requirement: Canonical generic grouped model output
Generic query model output SHALL omit redundant fields already represented by group_by when metrics are present. Other projections and explicit query payloads SHALL retain strict validation. Canonical output SHALL be persisted before durable query identity and consent checks.

#### Scenario: Status repeated as projection
- **WHEN** a generic query model returns status in fields and group_by with count metrics
- **THEN** redundant fields are removed without changing metrics, grouping, filters or scope

### Requirement: Distinguish group metrics from overall totals
Trusted query and report guidance SHALL distinguish per-group counts from engine matched_rows. A grouped metric named overall_total SHALL NOT be presented as a global total merely because of its label. Null/absent and blank-string groups SHALL retain their actual engine semantics.

#### Scenario: Displayed groups are paginated
- **WHEN** only part of the grouped result is displayed
- **THEN** global matched population comes from the engine and displayed groups are not treated as complete
