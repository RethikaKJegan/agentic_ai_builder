## ADDED Requirements

### Requirement: Enforce typed control payloads at the provider boundary
The model control transport SHALL use registered closed input schemas directly for tool actions and closed business output schemas directly for finish actions when those schemas can be represented strictly. Open schemas SHALL retain the existing encoded fallback. Existing runtime tool authorization and action approval gates SHALL remain authoritative.

#### Scenario: Research tool decision
- **WHEN** a researcher selects an authorized public search tool with a closed input schema
- **THEN** the response schema requires the exact typed tool inputs and rejects an encoded string or missing required input

#### Scenario: Research completion
- **WHEN** a research agent completes with a closed findings schema
- **THEN** the response schema validates its structured business result directly

#### Scenario: Open object capability
- **WHEN** a tool or business result uses an open schema
- **THEN** its existing encoded-object transport remains compatible
