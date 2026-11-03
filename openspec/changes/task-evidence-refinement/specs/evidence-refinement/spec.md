## ADDED Requirements
### Requirement: Source-backed resolution
The backend SHALL resolve only saved, authorized mappings and native references, preserving original values and conservative candidate identity.
#### Scenario: Controlled complaint code
- **WHEN** a complaint references a supported controlled-code record
- **THEN** retrieval includes its description and source references without replacing the stored identifier
### Requirement: Task-scoped evidence
Requirements and gaps SHALL use stable facts and requested task scope, with concrete registered recovery actions and provenance.
#### Scenario: Comparison without warranty
- **WHEN** a user requests only inspection comparison
- **THEN** unrelated policy and incorporation requirements do not block that comparison
### Requirement: Uncertainty and scenario isolation
Unknown facts SHALL remain unknown and generated scenario events SHALL be isolated from live evidence.
#### Scenario: Unverified incorporation
- **WHEN** no supported incorporation evidence exists
- **THEN** effectiveness remains unestablished and no scenario value is inserted into live results
