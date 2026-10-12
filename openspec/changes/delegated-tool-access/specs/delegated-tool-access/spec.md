## ADDED Requirements

### Requirement: Authorized tools inside delegated tasks
The runtime SHALL allow a delegated child to choose and invoke its exact reviewed tools and consume connector output before returning findings to the master.

#### Scenario: Subagent checks spreadsheet facts
- **WHEN** a tool-enabled child requests an authorized spreadsheet read
- **THEN** the configured connector reads rows and the child receives those rows for its next decision
- **AND** the master can continue independent work during the read
- **AND** the master receives the child's findings before final synthesis

### Requirement: Shared execution boundaries
Delegated tools SHALL enforce exact agent grants, current Registry authorization, schemas, approvals, destinations, timeouts and cumulative budgets and persist invocation evidence.

#### Scenario: Tool is not assigned to the child
- **WHEN** a child requests an unassigned tool
- **THEN** no connector call occurs and the task fails

#### Scenario: Connector fails or access is revoked
- **WHEN** a required read fails or its grant is revoked
- **THEN** no successful verified final output is accepted

### Requirement: Dynamic tools remain available without fixed routes
The Registry integration SHALL retain tools owned by dynamic children without appending fixed graph execution steps for those tools.

#### Scenario: Planner produces a verification specialist
- **WHEN** a dynamic child declares an available connector capability and the workflow references its tool
- **THEN** reviewed grants become available inside child execution and no duplicate fixed tool node is generated
