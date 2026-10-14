## ADDED Requirements
### Requirement: Wrapped compliance evidence
The quotation validator SHALL accept compliance words preserved across email whitespace wrapping and SHALL reject unsupported statements.
#### Scenario: Existing false clarification
- **WHEN** an existing quotation failed only evidence or compliance matching and its source hash and commercial fields still match
- **THEN** it can be revalidated through the existing qualification guards without another supplier reply
