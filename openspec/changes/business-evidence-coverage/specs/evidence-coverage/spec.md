## ADDED Requirements

### Requirement: Versioned business evidence coverage
Supported comparison, warranty and replacement tasks SHALL resolve explicit evidence contracts through source-qualified providers and retain source/generated provenance.

#### Scenario: Known rejected authorization
- **WHEN** valid cited authorization records establish rejection
- **THEN** authorization outcome is known and coverage is complete without inferring approval

### Requirement: Connected environment release
An owner-scoped immutable release SHALL identify exact cases/tasks, knowledge/mapping/provider/policy versions and independently expected validation results.

#### Scenario: Unexpected mandatory gap
- **WHEN** a designated complete case has missing or conflicting mandatory evidence
- **THEN** release is rejected

### Requirement: Preflight and runtime validation
New application investigations SHALL validate initial evidence before paid planning and revalidate authorization and relevant evidence during execution.

#### Scenario: Partial task readiness
- **WHEN** comparison is ready but warranty lacks required input
- **THEN** comparison can proceed and dependent assessment avoids unnecessary model calls

### Requirement: Accurate evidence presentation
Reports SHALL distinguish execution failure, decision evidence, optional limitations and unsupported capabilities without concealing generated provenance.

#### Scenario: Optional missing symptom
- **WHEN** comparison has all mandatory records but its optional symptom catalogue is unresolved
- **THEN** execution can complete with an informational limitation rather than a technical failure
