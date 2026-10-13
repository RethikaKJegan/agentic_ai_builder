## ADDED Requirements

### Requirement: Versioned procurement records
The extension SHALL define versioned project, BOQ, vendor, RFQ, quotation, award, PO, fulfilment, approval and evidence records without modifying canonical shared contracts.

#### Scenario: Schema verification
- **WHEN** offline examples are validated
- **THEN** required fields, typed values, decimal precision and closed record shapes are checked

### Requirement: Evidence driven transitions
State definitions SHALL specify transition guards, partial fulfilment and closure conditions. JSON Schema alone SHALL NOT be represented as enforcing cross-record or actor-authority rules.

#### Scenario: Supplier delivery without buyer confirmation
- **WHEN** a supplier reports delivery without explicit verified buyer receipt and acceptance
- **THEN** order closure remains forbidden by the defined policy

### Requirement: Trusted approval policy
The reviewed default SHALL require human approval for external writes. Agents SHALL recommend only. The definition artifacts SHALL NOT activate runtime automation.

#### Scenario: Policy remains inactive
- **WHEN** procurement policy files are added
- **THEN** existing services, workflows and connector approval gates remain unchanged

### Requirement: Stop conditions
The definition SHALL specify how missing input, ambiguous identity, conflicting evidence, unknown write outcomes and unverified compliance halt affected actions while preserving history.

#### Scenario: Uncertain send
- **WHEN** a provider write result is unknown
- **THEN** the defined recovery requires reconciliation before retry, never an automatic repeat
