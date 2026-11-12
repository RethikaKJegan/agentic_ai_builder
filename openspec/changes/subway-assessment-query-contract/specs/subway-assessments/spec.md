## ADDED Requirements

### Requirement: Canonical native-ID assessment selection
All registered Subway assessments SHALL validate requested detail fields against the authorized source catalog and execute an effective native-ID projection. Selection SHALL retain filters, ordering, offset and limit. Joins, aggregates, wrong base collections, foreign fields and excessive limits SHALL remain rejected. Caller input SHALL remain unchanged and original/effective selection SHALL be auditable.

#### Scenario: Planner selects additional purchase-order fields
- **WHEN** a valid bounded purchase-order detail query includes amount, supplier or other base fields
- **THEN** reconciliation SHALL select the same native records through an effective ID projection
- **AND** deterministic related-evidence retrieval and checks SHALL proceed without another model call

#### Scenario: Planner omits the ID from a detail projection
- **WHEN** requested base fields are authorized or the projection is empty
- **THEN** selection SHALL include the native ID without broadening record scope

#### Scenario: Requested query violates assessment boundaries
- **WHEN** a query contains foreign fields, joins, aggregates, a wrong collection or excessive bounds
- **THEN** it SHALL be rejected with its specific typed error

### Requirement: Typed assessment runtime failures
The assessment connector SHALL translate known API failures to runtime failures while retaining their code/status. Expected validation, authorization, staleness, timeout and bound failures SHALL have explicit recovery categories. Unknown exceptions SHALL remain failures and SHALL NOT become successful or automatically replayed effects.

#### Scenario: An invalid assessment reaches execution
- **WHEN** assessment validation fails
- **THEN** the run SHALL retain the specific error code rather than INVOCATION_FAILED
- **AND** report, search, spreadsheet and email dependencies SHALL not execute
