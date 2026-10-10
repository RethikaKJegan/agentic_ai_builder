# Generic tool workflow execution

## ADDED Requirements

### Requirement: Graph-owned workflow execution
The runtime SHALL execute agent and tool nodes in the approved workflow graph order. A CrewAI manager SHALL NOT also be registered as a worker in the same crew. Specialist work SHALL NOT be invoked outside its declared graph node.

#### Scenario: Hierarchical workflow execution
- **WHEN** an approved workflow contains a master agent and specialist agents
- **THEN** runtime agent invocations SHALL pass CrewAI validation and execute each graph node at most once

### Requirement: Registry-schema-derived tool inputs
The Registry adapter SHALL use the selected tool's accepted input schema and explicit workflow input mappings to construct executable tool nodes. It SHALL record unresolved required inputs when it cannot derive a mapping, and such a workflow SHALL remain blocked from approval until resolved.

#### Scenario: Tool has a same-named workflow input
- **WHEN** a tool input property matches a declared workflow input
- **THEN** the generated tool node MAY map that property from the declared input

#### Scenario: Required tool input is unavailable
- **WHEN** a required tool property has no explicit or safe same-named input mapping
- **THEN** the adapter SHALL record an unresolved requirement and SHALL NOT invent a value

### Requirement: Executable condition branches
The planner SHALL retain each declared condition node and connect its declared outcomes. The offline rule-based planner SHALL request an explicit boolean condition result when it cannot derive a condition from structured workflow data.

#### Scenario: Conditioned workflow
- **WHEN** a workflow declares a condition with yes/no outcomes
- **THEN** both outcomes SHALL be represented by outgoing graph edges and remain executable by the deterministic runtime
