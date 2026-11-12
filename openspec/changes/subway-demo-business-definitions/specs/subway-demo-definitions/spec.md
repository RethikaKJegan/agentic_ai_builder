## ADDED Requirements

### Requirement: Explicitly selected analytical assumptions
New Subway requests SHALL receive the versioned example profile only when the
objective explicitly selects `Use Subway demo definitions v1`. The profile SHALL
remain separate from company observations and authoritative policy. Explicit
request definitions SHALL override example defaults.

#### Scenario: Selected restaurant analysis
- **WHEN** an authorized Subway request selects the profile
- **THEN** discovery, query planning and saved knowledge context include its definitions, provenance and content hash
- **AND** source and query validation remain authoritative

#### Scenario: Existing behavior and isolation
- **WHEN** a request does not select the profile or uses another tenant or ontology version
- **THEN** no example profile is supplied
- **AND** no historical ontology, source record or execution permission is changed

### Requirement: Bounded metadata discovery
Discovery SHALL preserve all authorized source descriptors and supported relationship
identities while bounding objective-ranked field suggestions. It SHALL expose
returned and total field counts as metadata coverage, never as business-record coverage.

#### Scenario: Real catalogue exceeds the discovery budget
- **WHEN** full field metadata exceeds the existing context allowance
- **THEN** discovery supplies bounded field suggestions without dropping source descriptors or changing query completeness
- **AND** dataset-only selection retrieves objective-ranked planning fields
