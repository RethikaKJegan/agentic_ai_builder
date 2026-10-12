## ADDED Requirements

### Requirement: Bounded local session recovery
The UI SHALL renew an expired local-development session after an explicit authentication rejection and retry the rejected request once.

#### Scenario: Backend restart
- **WHEN** an open workflow page receives a canonical authentication rejection
- **THEN** it obtains a valid local session and resumes overview polling without a page reload

#### Scenario: Concurrent requests
- **WHEN** multiple requests encounter session rejection during renewal
- **THEN** they share one renewal and preserve their original request bodies

#### Scenario: Persistent failure
- **WHEN** renewal fails or the retried request is rejected
- **THEN** the UI reports the error without an unbounded retry loop

#### Scenario: Overview recovers
- **WHEN** a fresh overview succeeds after a session error
- **THEN** the stale authentication banner clears

#### Scenario: Generate with stale availability
- **WHEN** the user generates a workflow while the cached session is missing or outdated
- **THEN** the UI refreshes its session before checking planner availability and distinguishes connection failure from permission denial
