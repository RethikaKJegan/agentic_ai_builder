## ADDED Requirements

### Requirement: Safe provider failure reporting
The planner SHALL report SDK timeouts and connection failures as retryable provider failures without reflecting credentials or raw provider responses.

#### Scenario: Generation exceeds the provider deadline
- **WHEN** the model request raises APITimeoutError
- **THEN** the API returns PLANNER_PROVIDER_TIMEOUT with retryable=true
- **AND** no invalid-data claim or workflow side effect is reported

### Requirement: Planning-specific deadline
Workflow generation SHALL use a configurable bounded planning timeout while preserving existing runtime call limits and zero SDK retries.

#### Scenario: Complex workflow needs more than one minute
- **WHEN** workflow generation calls the model
- **THEN** the default planning timeout is 180 seconds
- **AND** the provider request explicitly uses that timeout

### Requirement: Normalize unambiguous generated save configurations
Fresh planner proposals SHALL combine disjoint setup literals and dynamic mappings into one supported input mapping and close explicitly declared save-field schemas when additionalProperties is omitted, without changing saved workflow semantics or fabricating output.

#### Scenario: Model splits setup and case fields
- **WHEN** a fresh proposal has fixed spreadsheet fields in input and disjoint dynamic identity/fields mappings
- **THEN** generation preserves all settings as literal expressions and dynamic references in one mapping
- **AND** overlapping keys and unsupported literals are not guessed

#### Scenario: Generated field object omits an extra-property restriction
- **WHEN** a mapped save-field output schema declares explicit properties but omits additionalProperties
- **THEN** generation sets additionalProperties=false before validation
- **AND** explicit open schemas remain rejected by the save validator
