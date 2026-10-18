## ADDED Requirements
### Requirement: Manage saved connections
Users with connection-management permission SHALL be able to add, edit, disconnect, reconnect and delete owned database connections. Reconnect SHALL verify replacement credentials while retaining the connection identifier. Delete SHALL remove app connection credentials, snapshots and profiling/scheduling records, retain audit history, and request a relationship rebuild without changing cloud data.

#### Scenario: Reconnect after disconnect
- **WHEN** an owner supplies and verifies credentials for a disconnected connection
- **THEN** the existing connection is restored and metadata profiling is queued

#### Scenario: Delete an owned connection
- **WHEN** an owner confirms deletion
- **THEN** the saved connection disappears and in-flight profiling cannot restore it
- **AND** no cloud deletion is performed

#### Scenario: Unauthorized deletion
- **WHEN** a reader or another owner attempts deletion
- **THEN** the request is rejected and the connection remains
