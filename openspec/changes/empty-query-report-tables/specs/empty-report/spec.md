## ADDED Requirements

### Requirement: Complete empty query evidence yields a valid no-match report
When all direct query dependencies are complete verified zero-match results, content
preparation SHALL receive a trusted empty-result context. Empty generated spreadsheet
tabs SHALL become clearly labelled report-status tables before approval. It SHALL
not invent groups, measurements, averages or source records.

#### Scenario: Empty status aggregate
- **WHEN** a grouped query returns zero groups from a complete scan
- **THEN** the report can publish a no-matches table using the existing spreadsheet contract

### Requirement: Other reports and action authority remain intact
Nonempty tables, incomplete results, unverified inputs and mixed nonempty query
populations SHALL not be rewritten as no-match reports. Downstream table constraints
and normal action permissions, approval gates and receipt checks SHALL remain enforced.

#### Scenario: No source execution or provider replay
- **WHEN** no-match content is normalized
- **THEN** it does not execute or replay queries, spreadsheet writes or email actions
