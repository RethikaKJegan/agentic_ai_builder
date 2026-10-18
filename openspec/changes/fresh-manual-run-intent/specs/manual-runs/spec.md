## ADDED Requirements

### Requirement: Distinguish new manual execution intents
The Run dialog SHALL supply a fresh idempotency key for each new dialog instance and retain the same key for retries within that instance.

#### Scenario: Run again after an earlier execution
- **WHEN** the user opens another Run dialog for the same published revision and inputs
- **THEN** its execution key differs from the previous dialog

#### Scenario: Retry an uncertain request
- **WHEN** the request fails with an uncertain transport outcome and the user retries in the same dialog
- **THEN** the same execution key is retained
