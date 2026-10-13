## ADDED Requirements
### Requirement: Exact quotation matching
Replies SHALL match the saved RFQ thread, sender and scope and be processed once by message identity.
#### Scenario: Unmatched sender
- **WHEN** a message comes from a different contact
- **THEN** it does not become an authoritative quotation
### Requirement: Deterministic qualifying comparison
Totals SHALL use decimal arithmetic and exact scope, currency, validity and delivery checks.
#### Scenario: Cheaper late offer
- **WHEN** a lower price misses the delivery deadline
- **THEN** it is not selected as a qualifying winner
### Requirement: Reviewed purchasing policy
Automatic simulation awards and POs SHALL require an explicit published purchasing limit and bound policy evidence. Real purchase commitments SHALL remain pending approval.
#### Scenario: Missing limit
- **WHEN** no purchasing limit is reviewed
- **THEN** recommendations are recorded without automatic award or PO submission
### Requirement: Calendar milestones
Quote and PO milestones SHALL retain actual event IDs and must not duplicate after restart.
#### Scenario: Repeated worker tick
- **WHEN** the same milestone has a confirmed event ID
- **THEN** the coordinator reuses its recorded result
