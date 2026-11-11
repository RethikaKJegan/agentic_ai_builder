## ADDED Requirements

### Requirement: Recorded exact ontology usage
New connected workflows SHALL pin an authorized ontology version and source mapping
identities. Completed verified queries SHALL record exact mapped fields they used.
No matching rows SHALL NOT imply observed source facts. Failed, synthetic or foreign
receipts SHALL NOT establish executed usage. Source collection names alone SHALL
NOT associate concepts across connections. Historical runs SHALL remain unchanged.

#### Scenario: Aggregate query
- **WHEN** a verified query groups, filters or calculates using a mapped field
- **THEN** that concept is highlighted with its exact field and query reference

#### Scenario: Missing associations
- **WHEN** historical execution lacks exact saved usage references
- **THEN** the graph explains that usage is unavailable and allows full exploration

### Requirement: Reusable workflow evidence display
The map SHALL show recorded plan and execution associations by workflow step across
tenants, including report consumption. Delivery actions SHALL NOT inherit concept
usage. Current ontology fallback SHALL NOT establish historical usage.

#### Scenario: Saved version unavailable
- **WHEN** the pinned ontology version cannot be loaded
- **THEN** current definitions remain explorable without executed highlights
