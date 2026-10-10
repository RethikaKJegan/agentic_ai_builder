# Provider configuration

## ADDED Requirements

### Requirement: Project-local secret storage
The setup SHALL preserve existing settings, store secrets only in ignored owner-readable project files, and provide placeholder-only examples.

#### Scenario: Existing environment configuration
- **WHEN** the project has an existing .env
- **THEN** existing variable values remain intact and missing integration settings are appended

### Requirement: Evidence-based integration status
The validator SHALL use non-destructive requests and report success only after authentication, where required, and API response verification.

#### Scenario: Missing credentials or approval
- **WHEN** provider credentials, resource IDs, authentication, or permission to post are missing
- **THEN** the integration is reported as requiring setup or approval rather than working
