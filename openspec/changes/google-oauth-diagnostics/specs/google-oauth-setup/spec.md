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

### Requirement: Alternative HTTPS authorization
The helper SHALL accept a privately pasted refresh token obtained using the configured web client through Google's OAuth Playground, verify it with Google's official token endpoint, and require explicit scope evidence.

#### Scenario: Playground token is valid
- **WHEN** a pasted refresh token successfully refreshes and its returned scopes cover all configured permissions
- **THEN** the helper saves a private authorized-user token without a localhost redirect

#### Scenario: Refresh token cannot prove access
- **WHEN** refresh fails or its response omits required scope evidence
- **THEN** the existing token remains unchanged and no token value is displayed

#### Scenario: Equivalent Sheets grant is refreshed
- **WHEN** configuration requests both Sheets readonly and Sheets write but Playground grants Sheets write
- **THEN** the refresh request omits redundant Sheets readonly while the saved token must cover every originally configured permission

#### Scenario: Google reports a refresh failure
- **WHEN** the structured response contains a known OAuth error category
- **THEN** the helper displays only the allowlisted category and fixed guidance without response descriptions or token values
