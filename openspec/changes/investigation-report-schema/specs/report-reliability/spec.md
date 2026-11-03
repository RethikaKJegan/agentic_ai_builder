## ADDED Requirements

### Requirement: Strict bounded investigation results
Investigation analysis SHALL request its exact citation-constrained schema from the configured provider and retain local validation, accounting and one-call limits.

#### Scenario: Report generation
- **WHEN** an investigation analysis uses the configured OpenAI bridge
- **THEN** the request uses strict JSON schema and schema overhead is reserved
- **AND** invalid output still fails validation without automatic paid replay

### Requirement: Explicit task exclusions
Task selection SHALL honor explicit excluded task clauses and retain positive requested tasks.

#### Scenario: Comparison without warranty
- **WHEN** an objective asks to compare inspection and says Do not assess warranty
- **THEN** inspection is selected and warranty is not required
