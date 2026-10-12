## ADDED Requirements

### Requirement: Private actionable authorization
The helper SHALL report actionable authorization failures without exposing credentials or callback URLs and SHALL allow selecting the intended account.

#### Scenario: Invalid pasted redirect
- **WHEN** a pasted URL is not the current session's loopback callback
- **THEN** the helper rejects it before token exchange and explains how to retry

### Requirement: Complete requested grants
The helper SHALL save a token only when every requested permission is granted and a refresh token exists.

#### Scenario: Scope response differs
- **WHEN** Google returns different scope names or additional grants
- **THEN** the helper accepts only grants covering all requested scopes, treating Sheets write as covering Sheets read

#### Scenario: Missing permission
- **WHEN** Google omits a required grant
- **THEN** the existing token remains unchanged
