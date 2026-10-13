## ADDED Requirements

### Requirement: Scoped source ingestion
The extension SHALL ingest explicitly selected requirements/vendor tables through authorized canonical tools and preserve source snapshots, incomplete data and project-scoped identities.

#### Scenario: Missing quantity
- **WHEN** a selected requirement lacks a valid quantity
- **THEN** its BOQ record is persisted for clarification and no RFQ or provider write is prepared

### Requirement: Approval gated first slice
The coordinator SHALL prepare tracking creation, exact Sheet projections and RFQ drafts through dedicated approval-gated canonical workflows and persist only confirmed outcomes.

#### Scenario: Pending creation
- **WHEN** tracking creation reaches its pending action gate
- **THEN** no Google mutation occurs and project advancement waits without approving the action

### Requirement: Durable bounded coordination
Project plans, workflow/run references and synchronization states SHALL survive restart with stable retry identities. Unknown or rejected external writes SHALL NOT be automatically repeated.

#### Scenario: Restart during approval
- **WHEN** the coordinator restarts while a draft is pending review
- **THEN** it resumes observation of that same run without creating another draft
