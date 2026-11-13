## ADDED Requirements
### Requirement: Subway structured evaluator correction
Subway investigations SHALL allow one correction of a provider transport validation failure per unchanged evidence checkpoint through the normal charged evaluator loop. All canonical and evidence validation SHALL remain enforced. Malformed decisions SHALL never grant action execution. Repeated failures at the same checkpoint SHALL block. Other tenants SHALL retain existing behavior.
#### Scenario: Invalid JSON-encoded value after query
- **WHEN** a Subway evaluator produces malformed JSON after a verified query receipt
- **THEN** a safe format-only feedback message requests one corrected decision without replaying the query
#### Scenario: Repeated malformed output or other tenant
- **WHEN** correction fails again without new evidence, or another tenant encounters malformed output
- **THEN** the original failure blocks without external action or unbounded retries
