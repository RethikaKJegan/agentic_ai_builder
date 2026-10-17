## ADDED Requirements

### Requirement: Create requirements before source ingestion
Explicit requests to generate a new BOQ SHALL be planned without requiring an already-existing requirements spreadsheet.

#### Scenario: Restaurant from a description
- **WHEN** the user asks to generate a restaurant BOQ, compare quotations and prepare purchase orders with issuance approval
- **THEN** the request reaches the multi-agent requirements-first planner with its budget, constraints and approval instructions intact

### Requirement: Honest procurement evidence
Requirements-first plans SHALL distinguish estimates and simulated quotations from verified supplier evidence and SHALL preserve approval requirements before external issuance.

#### Scenario: Live suppliers unavailable
- **WHEN** a user permits simulated quotations and live evidence is unavailable
- **THEN** the planner is instructed to label simulated evidence and prepare drafts without claiming supplier contact or order issuance

### Requirement: Reuse existing source context
Source-backed procurement SHALL consider bounded server-supplied workspace source references in addition to explicit links, retaining discovery/access validation and clear errors when no usable source exists.

#### Scenario: Saved source
- **WHEN** a procurement ingestion request has an authorized saved spreadsheet reference
- **THEN** the source is discovered without requiring its URL to be repeated in the prompt
