## ADDED Requirements

### Requirement: Optional inbox monitoring advertises availability
The session SHALL report inbox-monitor availability. The UI SHALL avoid polling
or presenting the legacy customer-reply monitor when explicitly unavailable.

#### Scenario: Isolated client has no legacy reply monitor
- **WHEN** Runs or Monitoring opens
- **THEN** unsupported inbox polling does not produce recurring service errors
- **AND** normal run and business-case functionality remains available

### Requirement: Process leases do not change tenant authority
Dedicated-store startup SHALL distinguish a validated worker process lease from
workspace/user ownership while retaining foreign tenant-row rejection.

#### Scenario: A stale process lease survives an unclean stop
- **WHEN** the dedicated client starts with a valid process lease row
- **THEN** startup retains the client's original identity
- **AND** the existing supervisor arbitrates lease ownership normally
