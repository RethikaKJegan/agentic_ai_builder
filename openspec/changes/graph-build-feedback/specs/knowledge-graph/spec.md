## ADDED Requirements
### Requirement: Timely graph build feedback
The detailed explorer SHALL refresh immediately after a build request and publish
current build status without losing navigation state or replacing v1 graph nodes.

#### Scenario: Build completes in detailed view
- **WHEN** a queued or running graph build finishes
- **THEN** the detailed graph and build button reflect its result through active polling

#### Scenario: Build fails in detailed view
- **WHEN** the worker reports a build failure
- **THEN** the error is displayed and the build control permits retry without tab switching
