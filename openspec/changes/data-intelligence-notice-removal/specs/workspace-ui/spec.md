## ADDED Requirements
### Requirement: Exact notice removal
Data Intelligence SHALL omit the shared-demo identity paragraph while preserving every existing tab, control, error and backend behavior.
#### Scenario: Page load
- **WHEN** Data Intelligence loads with shared_demo_identity true
- **THEN** the specified notice is absent and all existing sections remain available
