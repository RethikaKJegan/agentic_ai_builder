## ADDED Requirements
### Requirement: Inspect agent relationships
The editor SHALL provide a communication diagram showing master/sub-agent relationships, workflow routes and stable identifiers.
#### Scenario: Inspect a configured hierarchy
- **WHEN** a workflow contains a master and sub-agents
- **THEN** the diagram shows parent relationships and unique node UUIDs without claiming those relationships executed
### Requirement: Inspect actual handoffs
The runtime SHALL record bounded redacted application handoffs with unique UUIDs and distinguish data mappings from control transitions.
#### Scenario: Inspect a mapped output
- **WHEN** a node maps a prior node output into its inputs
- **THEN** the handoff records its source, receiver, mapped fields and exact run revision
### Requirement: Keep run evidence matched
The diagram SHALL use the exact selected run revision and exclude evidence from other runs or revisions.
#### Scenario: View a historical run
- **WHEN** the selected run used an older graph
- **THEN** the diagram loads that revision and explicitly identifies missing historical handoff evidence
