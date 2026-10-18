## ADDED Requirements
### Requirement: Preserve unchanged model configuration
UI serialization SHALL preserve an omitted model temperature when its displayed default has not changed. Explicit edits SHALL remain serialized and subject to Registry review.

#### Scenario: Save an unchanged generated agent
- **WHEN** a generated model omits temperature and its UI projection is unchanged
- **THEN** saving preserves the original model configuration

### Requirement: Accept concise inventory report requests
The bounded inventory compiler SHALL recognize Google Sheet or spreadsheet wording and exact IST meeting intervals without requiring a redundant duration. Missing dates, zones and invalid intervals SHALL remain errors.

#### Scenario: Concise equivalent prompt
- **WHEN** a restocking report requests a new Google Sheet, email and review with a dated exact IST interval
- **THEN** the existing inventory compiler builds the report with three separate action approvals
