## ADDED Requirements

### Requirement: Automatic tenant-scoped source resolution
The system SHALL select the latest active validated Subway demonstration version for eligible new workflows without source instructions, honor explicit historical/version requests and persist the resolved source before model routing.

#### Scenario: Ordinary investigation
- **WHEN** a Subway user requests a procurement investigation without naming a dataset
- **THEN** the active validated demonstration source and its ontology/policy are pinned through execution and labeled as modeled

#### Scenario: Explicit current operations
- **WHEN** a user requires real current operations unsupported by the restored sources
- **THEN** the resolver returns a source limitation without substituting modeled evidence

### Requirement: Validated version activation and reproducibility
The system SHALL validate tenant, integrity, schema, references, arithmetic, ontology and rule compatibility before atomic numeric-version activation. Existing workflows and schedules SHALL retain their approved pins across activation, replanning and restart.

#### Scenario: Compatible newer version
- **WHEN** an authorized operator registers a valid compatible higher numeric revision
- **THEN** it becomes the default atomically while existing workflow versions retain their original source

### Requirement: Protected recoverable demonstration cleanup
The system SHALL inventory dependencies and delete only retired, inactive, unreferenced demonstration operational data with a verified recovery archive. Audit, historical sources, shared ontology, evidence and backups SHALL remain intact.

#### Scenario: Referenced retired version
- **WHEN** a retired dataset is referenced by a saved workflow, receipt, schedule or resolution audit
- **THEN** cleanup retains it and reports the dependency
