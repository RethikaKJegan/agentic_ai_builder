## ADDED Requirements

### Requirement: Deployment verifies the service source path
Deployments SHALL resolve the service working directory and executable source path, and SHALL verify the tested evaluator implementation in that release before reloading.

#### Scenario: Service runs an isolated release
- **WHEN** systemd launches a release directory different from the workspace
- **THEN** deployment validates and updates the actual release without discarding its unrelated adaptations

#### Scenario: Release preparation is repeated
- **WHEN** the release is prepared again
- **THEN** it preserves the evaluator implementation and its diagnostics instead of restoring older code
