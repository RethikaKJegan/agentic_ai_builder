## ADDED Requirements

### Requirement: Ordinary summaries use workspace context and declared defaults
The system SHALL interpret ordinary authorized/access-permitted record wording as existing service access scope, without inventing an active/status business filter. Unspecified summary dimensions SHALL use total matching count, requested date/source scope, query coverage and available source-backed findings and limitations, without requiring a report template. Explicit business filters SHALL be preserved.

#### Scenario: Short daily complaint summary
- **WHEN** a user requests a summary of authorized complaints dated today
- **THEN** planning uses scoped metadata and the workspace timezone without requesting an authorization field or summary template

#### Scenario: Explicit business approval status
- **WHEN** the user explicitly requests a business authorization or approval status
- **THEN** planning uses a supported exact mapping or requests that missing meaning rather than discarding the filter

### Requirement: Self-mail resolves from the selected account before interpretation
The system SHALL provide the existing validated owner-scoped selected account and resolved recipient to routing and action planning. It SHALL use self-mail only for explicit self-mail intent, retain approval gates and never substitute accounts or infer an unspecified third-party recipient.

#### Scenario: Email me
- **WHEN** the user says email me and selects a connected owner-scoped Google account
- **THEN** routing receives the same resolved recipient used by action planning

#### Scenario: Unknown manager
- **WHEN** a user requests delivery to an unresolved manager
- **THEN** the recipient remains a genuine missing requirement
