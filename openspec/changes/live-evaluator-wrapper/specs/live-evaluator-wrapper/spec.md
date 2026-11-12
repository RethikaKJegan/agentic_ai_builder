## ADDED Requirements

### Requirement: Live provider exposes consumed operations
The live provider wrapper SHALL expose the evaluator and other consumed public planning methods with their input/output and error behavior preserved.

#### Scenario: Adaptive evaluation uses the live wrapper
- **WHEN** runtime requests an evaluation with an output-token budget
- **THEN** the wrapper delegates that context and budget to the configured provider and returns its decision

#### Scenario: Provider cannot evaluate
- **WHEN** a runtime provider lacks a callable evaluator
- **THEN** the run blocks with a specific provider-unavailable code before reserving a paid call

#### Scenario: Unexpected evaluation exception
- **WHEN** evaluation raises an unexpected exception
- **THEN** diagnostics retain its exception class without source content or secrets
