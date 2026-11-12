## ADDED Requirements
### Requirement: Strict investigation evaluation
The provider SHALL enforce a closed decision transport and validate decoded decisions against the canonical investigation contract before runtime evidence and authority checks.

#### Scenario: Query evidence is ready
- **WHEN** an approved recurring read completes
- **THEN** the evaluator receives its bounded result preview and source coverage/freshness metadata and can continue reviewed reporting without requiring a future delivery receipt

#### Scenario: Invalid response
- **WHEN** provider output is incomplete or violates the transport or canonical contract
- **THEN** no action executes and safe diagnostics identify the validation stage without recording raw response or business values
