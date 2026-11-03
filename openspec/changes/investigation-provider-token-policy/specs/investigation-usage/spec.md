## ADDED Requirements

### Requirement: Provider-managed investigation tokens
Investigations SHALL impose no application input/output token or per-call monetary ceiling while preserving actual usage accounting, call limits, timeouts and strict evidence validation. Other runtime modes SHALL keep their existing enforcement.

#### Scenario: Large investigation
- **WHEN** investigation input or output exceeds the former combined token ceiling
- **THEN** the request omits max_output_tokens and records provider-reported usage
- **AND** a second unauthorized model call is still rejected

### Requirement: Qualified report recovery
An optional final narrative that is truncated by the provider SHALL preserve the source-backed report without an automatic paid retry.

#### Scenario: Provider truncates final summary
- **WHEN** retrieved evidence and prerequisite analyses are available but summary generation truncates
- **THEN** the report retains source observations, prior interpretations and registered gaps
- **AND** explicitly states that model-written narrative was unavailable
