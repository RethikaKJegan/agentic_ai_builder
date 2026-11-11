## ADDED Requirements

### Requirement: Model query projections contain distinct field identifiers
The system SHALL remove repeated selected field IDs from model-generated query
projections without changing first-seen order or any other query semantics.
Typed schema, field access, dataset scope, output limits and source validation SHALL
remain enforced. Explicit client/tool query payloads SHALL not be silently repaired.

#### Scenario: Repeated projected field
- **WHEN** a query-planning model repeats one selected field ID
- **THEN** the persisted generated output contains it once and normal validation applies

### Requirement: Finished workers relinquish only their own execution lease
A completed advance call SHALL release its own lease when the run is no longer
running. It SHALL NOT change another worker's ownership or erase uncertain side-effect
state. Execution recovery SHALL continue to reconcile uncertain external actions.

#### Scenario: Failed read-only execution
- **WHEN** a worker finishes a failed read-only query step
- **THEN** its lease does not cause a spurious recovery wait

### Requirement: Independent runs can use bounded concurrent worker slots
Configured runtime concurrency SHALL apply in both active-standby and multi-active
modes. Singleton supervisor ownership SHALL remain intact. Independent runs MAY
advance in parallel within configured capacity without cancelling existing work.

#### Scenario: One slow run and one newly queued run
- **WHEN** two slots are configured and one run waits in a controlled connector
- **THEN** the other run can finish independently without duplicate invocation

### Requirement: Generated queries validate before source dispatch
Generated typed plans SHALL validate against the supplied scoped catalogue before
being persisted as completed planning output. A foreign dataset field SHALL NOT be
silently removed. New automatic drafts MAY include one pure-model correction in
an explicit two-call allowance; both attempts SHALL share the reviewed token/cost
cap. Runtime SHALL NOT enlarge a saved workflow budget.

#### Scenario: Correctable foreign-field output
- **WHEN** the first generated query uses a field from an unrelated dataset
- **THEN** one metadata-only correction may occur within budget before any source call

#### Scenario: Invalid correction
- **WHEN** the corrected query still violates its supplied catalogue
- **THEN** execution fails without creating a query job or calling the source
