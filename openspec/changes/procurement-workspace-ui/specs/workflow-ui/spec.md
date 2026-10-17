## ADDED Requirements
### Requirement: Stable procurement visualization
The UI SHALL show a bounded set of procurement stages and real agent teams regardless of repeated polling/action count.
#### Scenario: Repeated actions
- **WHEN** many RFQ or polling actions are recorded
- **THEN** stage count stays fixed and each exact action remains inspectable within its stage
### Requirement: Distinct workspaces
Design, agent hierarchy and execution SHALL have separate views while sharing the selected workflow and revision.
#### Scenario: Project hierarchy
- **WHEN** a procurement parent wraps generated child workflows
- **THEN** hierarchy reads actual associated agent definitions rather than claiming the wrapper has no master
### Requirement: Accessible project workspace
Procurement setup/status SHALL expose overview, setup, vendors/quotes, orders and activity in a responsive dialog with existing action authority unchanged.
#### Scenario: Confirmed start
- **WHEN** the backend confirms a successful procurement start
- **THEN** navigation can open execution without approving or starting another operation
