## ADDED Requirements

### Requirement: Bounded dataset routing
New model intent routing SHALL select at most four authorized dataset identities and SHALL not independently select fields or relationship endpoints. Existing query planning SHALL receive exact fields and supported relationships scoped wholly inside those datasets.

#### Scenario: Related field hints outside selected sources
- **WHEN** the global discovery catalog advertises fields from other sources
- **THEN** new intent transport cannot select those field identities or expand its source scope through them

#### Scenario: Invoice and linked order metadata
- **WHEN** selected datasets share a supported directed scalar relationship
- **THEN** scoped planning metadata includes that relationship and its exact key fields
- **AND** query execution still requires explicit valid joins and current authorization

#### Scenario: Existing explicit selection
- **WHEN** a saved or injected legacy selection specifies fields or relationships
- **THEN** its existing ownership, source-count and relationship validation remain unchanged
