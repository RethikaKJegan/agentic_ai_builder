## ADDED Requirements
### Requirement: Shared grounded preparation
Both planning paths SHALL use the same typed preparation service, preserving task-specific dependency expansion, coverage, source provenance and immutable knowledge pins.
#### Scenario: Prepare comparison
- **WHEN** an authorized user requests complaint comparison
- **THEN** preparation resolves supported mappings and comparison requirements without imposing unrelated warranty requirements
### Requirement: Authorized evidence adapters
Adapters SHALL reload scoped saved preparation, validate current source metadata and authority, and use existing read-only query validation.
#### Scenario: Revoked access
- **WHEN** source access is revoked after preparation
- **THEN** adapter execution is denied without company reads
### Requirement: Compatibility
General nonbusiness workflows and historical investigations SHALL retain their existing contracts.
#### Scenario: Existing generic goal
- **WHEN** no applicable business knowledge is configured
- **THEN** general workflow planning remains available without fabricated business grounding
