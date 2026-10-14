## ADDED Requirements
### Requirement: Understandable live diagram
The communication view SHALL use a diagram as its only presentation. Cards SHALL identify coordinators, helpers, recorded spawned instances and execution status. Connections SHALL explain task assignment, returned results and information sharing. Clicking a card or connection SHALL expose readable recorded details with technical evidence collapsed.

#### Scenario: Multiple helper instances
- **WHEN** a coordinator starts the same registered specialist for two tasks
- **THEN** separate spawned cards show their parent, task and independent results

#### Scenario: Live updates
- **WHEN** polling receives a spawned agent or handoff
- **THEN** the diagram updates, retaining selection and indicating active recorded work separately from completed work

#### Scenario: No execution evidence
- **WHEN** only configured relationships or historical events without communication evidence are available
- **THEN** the diagram identifies planned or unrecorded work without claiming an agent was spawned or information exchanged

#### Scenario: Whole project
- **WHEN** multiple action runs belong to a project
- **THEN** the same diagram and inspector present their actual workflow names, agents and recorded exchanges without business-domain label rules
