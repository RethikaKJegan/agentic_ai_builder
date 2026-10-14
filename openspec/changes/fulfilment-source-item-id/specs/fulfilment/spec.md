## ADDED Requirements
### Requirement: Source-grounded item identities
The fulfilment validator SHALL check exact item identity in fresh source text and SHALL retain quantity, unit and order-scope checks.
#### Scenario: Evidence subset omits identifier line
- **WHEN** the source explicitly contains the item identity but the model quotes other genuine source lines
- **THEN** omission of the identity line from that subset alone does not reject the event
