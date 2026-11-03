## ADDED Requirements
### Requirement: Bounded task metadata
An otherwise valid planned source selection SHALL NOT fail solely because its full field list exceeds the per-agent reference budget. The server SHALL select exact relevant catalog fields within that budget, declare incomplete metadata and retain complete runtime source validation.

#### Scenario: Wide inspection source
- **WHEN** an authorized selected source has more field metadata than the agent reference budget
- **THEN** the proposal retains its actual source identity and bounded exact field metadata with omission counts instead of failing or inventing fields

### Requirement: Specific source binding correction
Planner correction SHALL distinguish invalid dataset selection, agent scope, and oversized reference metadata and supply exact allowed identifiers within its existing bounded attempts.

#### Scenario: Specialist source outside workflow scope
- **WHEN** a proposed specialist references a source outside the selected owned workflow scope
- **THEN** correction reports that scope violation and no grant or arbitrary replacement is created
