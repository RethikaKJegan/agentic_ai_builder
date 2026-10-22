## ADDED Requirements
### Requirement: Organization governance presentation
Governance SHALL contain exactly three primary tabs named Organization Policies, Roles & Responsibilities, and Oversight & Accountability, using document sections and tables without draft editors or dashboard charts.
#### Scenario: Governance navigation
- **WHEN** a user opens Governance
- **THEN** the three read-only tabs expose policy reference, reported access and available activity evidence
### Requirement: Honest evidence and scope
The UI SHALL use existing read-only monitoring and session APIs, identify reported scope, avoid fabricated role grants or organization-wide enforcement, and show unavailable, loading and error states.
#### Scenario: Evidence inspection
- **WHEN** a user filters or inspects a reported event
- **THEN** its original ID, timestamp, type and run reference remain inspectable without backend writes
#### Scenario: Missing organization data
- **WHEN** organization policy or role assignments are not supplied
- **THEN** the UI reports that limitation without inventing policies, grants, actors or compliance claims
