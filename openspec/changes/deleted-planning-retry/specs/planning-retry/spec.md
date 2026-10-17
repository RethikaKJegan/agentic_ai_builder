## ADDED Requirements

### Requirement: Explicit regeneration after deletion
A planning submission whose retry key resolves to a completed result for a deleted workflow SHALL create or reuse one replacement planning job instead of reopening the deleted workflow.

#### Scenario: Deleted saved result
- **WHEN** a user deletes a workflow and submits the same prompt with the original durable planning key
- **THEN** the submission resolves to a new planning job with a distinct effective planner key and retains the old job unchanged

#### Scenario: Retry replacement submission
- **WHEN** that explicit submission is repeated or concurrent
- **THEN** it resolves to the same replacement job without duplicate model requests

#### Scenario: Existing result remains live
- **WHEN** the completed result has not been deleted in the requesting workspace
- **THEN** the original job remains the retry result

### Requirement: Separate deleted history from current workflow lookup
Latest-workflow reads SHALL return not found for tombstoned workflows. Explicit revision history SHALL remain readable under existing authorization.

#### Scenario: Historical revision
- **WHEN** a deleted workflow's authorized historical revision is requested explicitly
- **THEN** its retained evidence remains unchanged
