## ADDED Requirements
### Requirement: Stable metadata retry
The recovery operation SHALL disable automatic checks for the two existing connections without changing connection identities or source schema contents, and SHALL start at most one new workflow run using a persisted idempotency key after profiles and graph are ready.
#### Scenario: Approval boundary
- **WHEN** the recovered inventory run reaches the Sheet creation approval
- **THEN** recovery does not decide that approval or invoke later Sheet, email or Calendar writes
