## ADDED Requirements
### Requirement: Consolidated run operations
Runs SHALL show Total runs, Active, Completed and Failed from the existing monitoring response, preserve run history and reply controls, and provide expandable monitoring details including sources, policies, audit, status distribution, traces and pagination. Failed initial reads SHALL NOT show fabricated zero KPIs. A failed refresh SHALL identify retained values as stale.
#### Scenario: Monitoring migration
- **WHEN** a user navigates the application
- **THEN** Monitoring has no independent navigation entry and its old URL redirects to Runs, where its functionality remains available
### Requirement: Neutral illustrative attribution
Usage & Limits SHALL omit the yellow notice and Sample badges while distinguishing illustrative numbers using a small neutral legend and asterisk. Reported values SHALL remain unchanged.
#### Scenario: Governance presentation
- **WHEN** missing numeric values are shown
- **THEN** example values are identifiable without yellow warning styling
### Requirement: Existing execution preservation
The change SHALL preserve approval navigation and approval functionality, backend monitoring APIs, configuration and workflows without backend modifications.
#### Scenario: Run inspection
- **WHEN** a user inspects run monitoring
- **THEN** the UI uses existing read APIs without initiating workflow actions
