## ADDED Requirements
### Requirement: Metadata EDA dashboard
Data Intelligence SHALL provide an EDA tab showing source-backed schema insights
with connection selection, refreshed when discovered metadata revisions change.
Charts SHALL label sampled/declared metadata and SHALL NOT imply record-level
analysis or fabricated business statistics.
#### Scenario: A connection is profiled
- **WHEN** its metadata revision changes
- **THEN** an open EDA tab reloads its metadata overview
#### Scenario: No metadata or failed reads
- **WHEN** a connection has no successful snapshot or a read fails
- **THEN** the dashboard shows an explicit empty/partial state without invented values
