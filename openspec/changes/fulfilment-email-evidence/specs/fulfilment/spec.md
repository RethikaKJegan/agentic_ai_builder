## ADDED Requirements
### Requirement: Email-only fulfilment claims
Fulfilment extraction SHALL distinguish order context from supplier statements.
#### Scenario: Acceptance without date changes
- **WHEN** the supplier accepts an order without reporting a delivery date
- **THEN** extraction instructions require a null reported date and prohibit order-record summaries in email evidence
