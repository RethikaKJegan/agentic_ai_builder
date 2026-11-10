## ADDED Requirements

### Requirement: Objective-scoped query discovery
Connected workflows SHALL reuse existing owned ontology retrieval before enforcing the query planner catalogue byte bound. Every supplied executable scalar field of a retained source SHALL be preserved; unsupported object/array descriptors MAY be excluded. The 120000 byte bound SHALL remain.

#### Scenario: Account catalogue exceeds the bound
- **WHEN** an authorized population objective matches a bounded subset of a large account catalogue
- **THEN** only relevant source candidates and reviewed relationships reach query planning
- **AND** the generic query capability requires no case identifier

#### Scenario: Relevant source cannot fit
- **WHEN** a complete relevant executable source cannot fit the existing retrieval budget
- **THEN** discovery returns an actionable limitation instead of truncating fields

### Requirement: Typed binding diagnosis and bounded correction
Invalid model-generated internal bindings SHALL identify the action, namespace, key and destination and MAY receive one metered correction. Unknown user business inputs SHALL remain explicit clarification inputs.

#### Scenario: Missing internal context key
- **WHEN** generated content references a namespace as if it were its own child key
- **THEN** the planner receives the exact invalid binding and declared context
- **AND** no context value or business identifier is invented

### Requirement: Scope and downstream compatibility
Execution SHALL enforce current account authorization, reviewed metadata revision and objective source scope through existing query jobs and durable runtime. Existing Questions and saved workflows SHALL remain compatible.

#### Scenario: Generated query expands source scope
- **WHEN** a query names an owned dataset absent from its reviewed objective catalogue
- **THEN** execution rejects it before a source read

### Requirement: Supplied scalar input references
Goal-mode planning SHALL normalize an exact redundant self-path on an existing scalar input without creating values, flattening structured inputs or changing selected-account authority.

#### Scenario: Recipient string referenced as its own child
- **WHEN** a generated recipient binding uses path [recipient] against an existing scalar recipient
- **THEN** the binding references that supplied scalar directly
- **AND** exact-payload approval still applies to any email execution

#### Scenario: Missing or genuinely nested input
- **WHEN** an input is absent or a binding targets a real nested object or a different invalid path
- **THEN** existing clarification and strict traversal checks remain in force
