## ADDED Requirements
### Requirement: Visible Disable action
The workflow dropdown SHALL always show Disable. It SHALL be enabled only for an active release with workflow.publish permission and no action in progress. The existing confirmation and endpoint SHALL remain unchanged.

#### Scenario: Inactive workflow
- **WHEN** a workflow has no active release
- **THEN** Disable remains visible but unavailable

#### Scenario: Active workflow
- **WHEN** a publisher opens an active workflow menu
- **THEN** Disable is available and uses the existing confirmation flow
