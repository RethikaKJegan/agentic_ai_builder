## ADDED Requirements
### Requirement: Interactive dynamic investigation workflow
The system SHALL expose shared preparation, registered dynamic agents/tools, persisted execution, scoped evidence/memory and explicit recovery in the existing investigation experience. Proposed capabilities SHALL NOT imply executable tool grants. Normal approval and action controls SHALL remain authoritative.

#### Scenario: Business goal to report
- **WHEN** a user generates a business investigation
- **THEN** a durable planning job prepares a composition and the UI displays its actual dependencies and setup requirements
- **AND** execution requires normal validation/approval and displays persisted task results, evidence and qualifications

#### Scenario: Historical investigation
- **WHEN** an existing legacy investigation link is opened
- **THEN** its original execution and history remain accessible

#### Scenario: Failed execution
- **WHEN** persisted failure state is inspected
- **THEN** root-cause and recovery controls reflect current backend eligibility and do not automatically replay uncertain effects
