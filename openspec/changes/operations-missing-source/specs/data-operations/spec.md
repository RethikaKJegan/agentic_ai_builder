## ADDED Requirements
### Requirement: Resilient authorized target discovery
Operations catalog discovery SHALL omit policy entries whose exact owned connection is missing without failing discovery of valid targets. Only DATA_SOURCE_NOT_FOUND with status 404 SHALL be skipped. Execution, preparation and read authorization SHALL still reject missing targets and SHALL NOT transfer grants to other connections.
#### Scenario: Removed connection
- **WHEN** policy references an owned connection that no longer exists
- **THEN** catalog reads succeed and that target is absent while valid owned targets remain
#### Scenario: Other discovery failure
- **WHEN** a different error occurs
- **THEN** the error remains visible rather than being silently suppressed
### Requirement: Targeted navigation removal
Only the shell Operate Approvals item SHALL be removed; approval functionality and other links SHALL remain available.
#### Scenario: Operations empty state
- **WHEN** there are no available authorized targets
- **THEN** the UI explains that a current connection and explicit server policy are required without proposing an automatic write-permission transfer
