## ADDED Requirements

### Requirement: Knowledge intent remains grounded through execution
The system SHALL bind the retrieved, owner-scoped business knowledge and its version to knowledge-intent content preparation. It SHALL expose only content preparation, require that knowledge as the content input and restrict citations to its supplied references. Source qualifications and unknowns SHALL be preserved.

#### Scenario: Explain operating hours
- **WHEN** a knowledge intent asks what operating hours means and the workspace supplies a source-cited definition
- **THEN** the plan prepares content from that pinned definition without planning or executing a record query

#### Scenario: Knowledge is unavailable
- **WHEN** retrieval supplies no relevant source-cited references
- **THEN** the system requests the missing definition or document without generating an answer

#### Scenario: Planner proposes a record reader
- **WHEN** a knowledge-intent planner proposes a query or case reader, or omits the required knowledge binding
- **THEN** validation rejects that plan through the existing bounded correction path

### Requirement: Historical knowledge query failure is explained accurately
The system SHALL preserve historical failed runs and their leases, and explain that an incorrectly planned knowledge query requires a new workflow.

#### Scenario: Previous knowledge query failed
- **WHEN** a knowledge-intent workflow failed with DATA_QUERY_INVALID
- **THEN** its view identifies the incorrect record-query plan and directs a new workflow without enabling unsafe lease recovery
