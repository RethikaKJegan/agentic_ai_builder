## ADDED Requirements
### Requirement: Acceptance instructions distinguish tested behavior from intended checks
The whole-app guide SHALL identify steps, expected outcomes and execution boundaries, and SHALL leave unexecuted acceptance cases marked NOT RUN.

#### Scenario: A tester follows the guide
- **WHEN** a feature needs optional provider configuration or privileged authority
- **THEN** the guide identifies that prerequisite and records missing setup as BLOCKED rather than PASS

#### Scenario: Continuous stability is requested
- **WHEN** the guide explains stability qualification
- **THEN** it separates proposed operational targets and checks from monitoring or availability already verified
