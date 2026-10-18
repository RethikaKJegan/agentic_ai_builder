## ADDED Requirements
### Requirement: Updated presentation
The UI SHALL show Semantic Intelligence terminology, hide the Data Intelligence Questions tab, format demo database display names as Postgres or MongoDB, and provide a larger Overview prompt input without changing execution or stored identifiers.

#### Scenario: Inspect data sources
- **WHEN** a user opens Data Intelligence
- **THEN** the Questions tab is absent and Semantic Intelligence is available
- **AND** source display names use engine labels while requests retain original identifiers

#### Scenario: Enter a longer prompt
- **WHEN** a user opens Overview
- **THEN** the prompt input displays ten rows and permits vertical resizing
