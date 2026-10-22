## ADDED Requirements
### Requirement: Fixed account workspace access
The website SHALL require a valid signed website session before serving workspace pages or forwarding browser backend API traffic, including backend session bootstrap, while retaining the current workspace subject and permissions.

#### Scenario: Anonymous access
- **WHEN** an anonymous visitor opens /app or requests /api/backend/session
- **THEN** pages redirect to /login and the API returns AUTHENTICATION_REQUIRED without contacting the backend

#### Scenario: Successful login
- **WHEN** the configured engineering account submits its correct password from the same origin
- **THEN** the server sets an expiring HttpOnly cookie and the browser opens /app

#### Scenario: Invalid authentication
- **WHEN** credentials or a session signature are invalid, or the session has expired
- **THEN** workspace access is denied

### Requirement: Preserve tool and workflow boundaries
Website authentication SHALL preserve existing workspace identity, Google and database connections, and separate action approvals.

#### Scenario: Provider ingress
- **WHEN** a provider sends a signed webhook or the independently bound Google OAuth callback
- **THEN** the existing provider validation still runs without a website-login requirement

#### Scenario: Logout
- **WHEN** an authenticated user signs out from the same origin
- **THEN** website and backend session cookies are cleared without deleting workspace records or browser drafts
