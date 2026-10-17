## ADDED Requirements

### Requirement: Existing source instructions take routing precedence
Procurement planning SHALL use its source-backed setup path when the user explicitly requests reading requirements or using Requirements/Vendors tables, even if the prompt also asks to prepare a BOQ.

#### Scenario: Workshop source prompt
- **WHEN** a user requests discovery of Requirements and Vendors tabs and preparation of a BOQ
- **THEN** the planner discovers authorized source references and generates native procurement setup rather than requiring generic connector setup

#### Scenario: Saved source
- **WHEN** a source-backed procurement request uses an authorized saved source instead of repeating its link
- **THEN** source discovery still occurs before procurement setup generation

### Requirement: New BOQ generation remains available
Description-based BOQ creation SHALL continue to use requirements-first planning without an existing requirements spreadsheet.

#### Scenario: Supplementary knowledge
- **WHEN** a new BOQ request includes a supplementary knowledge link without instructions to ingest requirements tables
- **THEN** the link alone does not force existing-BOQ ingestion

### Requirement: Routing does not grant execution authority
Routing SHALL preserve source discovery errors, Registry requirements and approval policy, and SHALL NOT alter existing workflow revisions or issue procurement actions.

#### Scenario: Inaccessible source
- **WHEN** a source-backed request references an inaccessible explicit spreadsheet
- **THEN** generation returns the source-access error without silently switching paths or granting access
