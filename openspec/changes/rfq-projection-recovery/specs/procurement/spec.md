## ADDED Requirements
### Requirement: Confirmed RFQ projection recovery
A failed sent-RFQ projection SHALL be recoverable once only after validating active authority, the exact stored intent, a confirmed send and a fresh table read.
#### Scenario: Original row unchanged
- **WHEN** the sheet still holds the prior known RFQ revision
- **THEN** a new identity-based projection may run without resending mail and the previous failure remains recorded
#### Scenario: Conflicting row or failed send
- **WHEN** observed fields differ from both known prior and desired values or email submission is uncertain
- **THEN** recovery stops for review
