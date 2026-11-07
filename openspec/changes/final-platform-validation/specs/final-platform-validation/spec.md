## ADDED Requirements

### Requirement: Integrated release evidence
The platform SHALL be assessed using current source and explicit test environments.
Unavailable checks SHALL NOT be counted as passing; repeated executions SHALL NOT
be summed as distinct cases. External effects and production changes SHALL require
separate explicit authorization.

#### Scenario: Missing representative staging environment
- **WHEN** multi-host or live-provider acceptance cannot execute with available authority
- **THEN** the release report records a blocker and limits its readiness decision
