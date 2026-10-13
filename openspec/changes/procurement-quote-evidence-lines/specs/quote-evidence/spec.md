## ADDED Requirements
### Requirement: Ordered grounded evidence
Evidence SHALL match real source text, allowing ordered nonadjacent quoted lines and whitespace formatting differences.
#### Scenario: Joined genuine lines
- **WHEN** extraction combines genuine lines separated by another source block
- **THEN** evidence passes without changing extracted monetary values
#### Scenario: Invented line
- **WHEN** any quoted line is absent or out of order
- **THEN** evidence remains invalid
### Requirement: Evidence-only recovery
Pending quotes rejected only for evidence formatting SHALL be revalidated from the original completed extraction and matching source digest before normal qualification.
#### Scenario: Existing pending quote
- **WHEN** the recorded evidence passes the corrected check and all qualification guards
- **THEN** the quote progresses through validation without another model request or replaying confirmed mail
