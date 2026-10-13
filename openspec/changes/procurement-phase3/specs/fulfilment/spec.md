## ADDED Requirements
### Requirement: Reviewed activation
Fulfilment SHALL bind operator-configured buyer/manager contacts to the active project without resending POs.
#### Scenario: Existing POs
- **WHEN** an authorized operator activates fulfilment
- **THEN** existing order identities and sends are preserved
### Requirement: Grounded durable updates
Messages SHALL match PO thread and actor, apply once with source evidence, and obey quantity and transition guards.
#### Scenario: Duplicate
- **WHEN** an update is seen after restart
- **THEN** quantities and notifications are not duplicated
### Requirement: Buyer confirmed closure
Closure SHALL require explicit buyer receipt, acceptance and resolution for all quantities.
#### Scenario: Supplier delivery
- **WHEN** delivery is reported by the supplier
- **THEN** the order stays open pending buyer confirmation
### Requirement: Canonical effects
Tracking, Calendar updates and notifications SHALL retain canonical run evidence and uncertain sends SHALL NOT replay.
#### Scenario: Submission uncertainty
- **WHEN** send acknowledgement is uncertain
- **THEN** the action stops for reconciliation
