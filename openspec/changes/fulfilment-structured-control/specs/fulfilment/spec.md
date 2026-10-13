## ADDED Requirements
### Requirement: Structured pure extraction transport
Fulfilment control SHALL delegate the original request without model reconstruction and SHALL synthesize a schema-bound object.
#### Scenario: Extraction transport recovery
- **WHEN** only a side-effect-free extraction failed schema validation
- **THEN** one attempt with the new transport is allowed and previous failures remain recorded
