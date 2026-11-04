## ADDED Requirements

### Requirement: Persistent investigation interface
The existing Business Investigation interface SHALL create, reopen and inspect scoped persistent lifecycle cases using backend state and pinned dynamic stage definitions.

#### Scenario: Multiple processes
- **WHEN** a user opens a Simpson or configured retail case
- **THEN** the interface renders that case's own ordered stages and qualified business outcomes

### Requirement: Explicit authorized continuation
Lifecycle commands SHALL use bounded existing backend operations, exact revisions, unique new request keys and stable keys for explicit uncertain retries.

#### Scenario: Uncertain response
- **WHEN** a command response cannot be confirmed
- **THEN** the interface permits refresh and explicit retry of the exact command without automatic write replay

### Requirement: Qualified evidence and operational activity
The interface SHALL distinguish provenance, analytical completion, actual pending activity and normal workflow/action/business approval boundaries.

#### Scenario: Provisional completion
- **WHEN** analysis completes with generated assumptions or pending real events
- **THEN** the report retains provisional outcomes and does not claim physical activity completed
