## ADDED Requirements

### Requirement: Executable generated query shapes
The model transport SHALL distinguish projected detail queries from grouped or ungrouped aggregate queries and use exact authorized catalog identities. Detail coverage counts SHALL come from actual executor receipts. Direct query validation and approved budgets SHALL remain authoritative.

#### Scenario: Detail report and complete population count
- **WHEN** a detail task requests order rows and the complete matching count
- **THEN** generated detail queries have projected fields and no metrics/grouping
- **AND** reports obtain matching counts from executor coverage without treating displayed rows as complete

#### Scenario: Grouped report and invalid scope
- **WHEN** a model plans a grouped aggregate
- **THEN** projection is empty and metrics operate per group
- **AND** unknown fields, unsupported joins and missing explicit filters remain rejected

### Requirement: Safe validation diagnostics
Rejected query outputs SHALL produce validator rule diagnostics without persisting raw model text or automatically increasing approved retry allowances.

#### Scenario: Rejected query output
- **WHEN** a query planning output violates the execution contract
- **THEN** runtime diagnostics identify its validation rule without source values or rejected output
