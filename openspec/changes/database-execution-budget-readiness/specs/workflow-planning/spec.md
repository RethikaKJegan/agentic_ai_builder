## ADDED Requirements
### Requirement: Executable database budgets
A database workflow SHALL reserve enough finite tool units for its selected registered adapters before publication; dynamic readers SHALL have a later model turn available to consume tool results.

#### Scenario: Query adapter requires four units
- **WHEN** a generated dynamic database reader proposes one tool unit
- **THEN** the editable proposal records a correction to at least four units and enough workflow allowance, within Registry ceilings

#### Scenario: Undersized reviewed revision
- **WHEN** a manually supplied database revision has insufficient adapter reservation capacity
- **THEN** validation rejects it before activation rather than allowing a guaranteed runtime budget failure

### Requirement: Executable query clarification contract
The executable database query tool SHALL accept only plans with an empty clarification field. General data-question planning MAY retain clarification requests, which SHALL NOT execute.

#### Scenario: Model puts operating notes in the stop field
- **WHEN** a delegated reader supplies operating notes in query clarification
- **THEN** tool-input schema validation corrects the model decision before any database dispatch, using the existing finite correction allowance
- **AND** no note is silently removed and no unreviewed query or source is authorized

### Requirement: Queryable document fields
Database workflows SHALL support exact catalog-backed MongoDB scalar object paths without array traversal or operators. Numeric integer/number observations SHALL share the existing numeric query domain. Specialist decision schemas SHALL constrain projected fields to current authorized, advertised field IDs.

#### Scenario: Nested complaint and inspection evidence
- **WHEN** a supported scalar is stored under a nested document path
- **THEN** the read returns that exact scalar under its catalog field ID
- **AND** arrays, operator paths, unsupported types and invented field IDs remain rejected before dispatch

### Requirement: Coordinated bounded evidence reads
Workflow database reads SHALL wait for the existing per-owner query slot within the connector deadline, preserving immediate busy responses for interactive queries. Sampled MongoDB scalar-only evidence projections SHALL preserve actual scalar values without imposing sample-only BSON type assumptions; aggregates and joins SHALL retain their stricter semantics.

#### Scenario: Three delegated readers share one owner
- **WHEN** independent workflow readers issue queries concurrently
- **THEN** they execute through the existing one-owner slot in sequence before the shared bounded deadlines
- **AND** expiration, revocation and cancellation remain checked

#### Scenario: Unsampled scalar differs from observed metadata
- **WHEN** a sampled boolean field contains a string in another record and the query requests scalar evidence only
- **THEN** that string is returned verbatim with a sampled-type qualification
- **AND** no coercion or arithmetic interpretation is invented

### Requirement: Logical validation and bounded source sampling
Delegated query decisions SHALL pass metadata-only logical validation before source dispatch, using the existing one-correction budget for invalid model plans. Sampled MongoDB evidence projections SHALL apply their result bound at the source and return an exact same-facet count, without transferring the full collection. Sampled BSON ordering SHALL be disclosed when used; ordinary query semantics SHALL remain unchanged.

#### Scenario: Sort field omitted from projection
- **WHEN** a model plan sorts by a field absent from its output
- **THEN** logical validation returns pure generation feedback before source dispatch and before reserving database tool units

#### Scenario: Large collection and a ten-row evidence request
- **WHEN** the requested evidence contains at most ten source rows
- **THEN** at most ten projected rows cross the source boundary, with exact total count and limited coverage preserved

### Requirement: Bounded read-only synthesis
Read-only database coordinators SHALL receive an explicitly qualified representative view of large specialist object arrays, preserving exact values, scalar notes and original source/count metadata. This presentation bound SHALL NOT apply to workflows allowing external writes. Pure truncated model output MAY receive the existing single bounded correction before any action is dispatched.

#### Scenario: Large retrieved evidence before final synthesis
- **WHEN** a read-only specialist returns more than three object records in one result field
- **THEN** the coordinator receives three exact records and an original/included count qualification
- **AND** original specialist results remain unmodified and the final report must disclose limited coverage

### Requirement: Structured open-object finish transport
Open business result objects SHALL use a strict recursive key/value transport rather than requiring the model to escape a second JSON document inside a string. The server SHALL reconstruct ordinary JSON values and validate the original business schema. Duplicate keys, malformed trees, invalid business shapes and incomplete decisions SHALL remain rejected; no failed response SHALL authorize a tool.

#### Scenario: Quotes, nested findings and dynamic field names
- **WHEN** a final report contains open maps, quotes, arrays, false or null values
- **THEN** strict typed values reconstruct the exact business object without parsing model-generated JSON inside a string

### Requirement: Single-query specialist scheduling
For read-only database specialists whose reviewed tool allowance permits only one query, the coordinator SHALL remove pending/completed specialists from available delegation choices and join required pending results before final synthesis. Duplicate assignments in one proposed batch SHALL receive bounded model correction before starting any task. Multi-query and external-write workflows SHALL retain their existing delegation semantics.

#### Scenario: Coordinator requests duplicate work while original readers are pending
- **WHEN** the once-per-run readers have been scheduled
- **THEN** the runtime waits for their results instead of inviting another paid duplicate task
- **AND** each specialist's query/result budget remains available to its original task

### Requirement: Stable automatic metadata checks
A routine automatic metadata check SHALL preserve an already ready source's published snapshot while its unchanged-generation job is queued or running. Actual schema changes, failed checks, manual invalidation, disconnects and credential-generation changes SHALL retain their existing invalidation behavior.

#### Scenario: Automatic check overlaps delegated planning
- **WHEN** an automatic check of a ready source is queued and running
- **THEN** current reviewed metadata remains queryable until publication
- **AND** an unchanged result preserves graph and plan identity

### Requirement: Affordable specialist tool choices
Specialist control choices SHALL omit tools whose reservation exceeds remaining reviewed agent or workflow allowances. Completed evidence SHALL remain available for synthesis with its existing coverage qualifications.

#### Scenario: Reader has consumed its single query allowance
- **WHEN** its first bounded query completes
- **THEN** the next model turn offers synthesis without an unaffordable second query
- **AND** no allowance is increased and no additional query is dispatched
