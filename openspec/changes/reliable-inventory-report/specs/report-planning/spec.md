## ADDED Requirements

### Requirement: Assemble executable inventory reports
The system SHALL compile fresh inventory-restocking report proposals with available registered tools into canonical read, rank, format, approved spreadsheet creation and approved delivery steps, using current owned KG sources without inventing database identities or records.

#### Scenario: Rank real evidence
- **WHEN** validated normalized inventory records are supplied
- **THEN** a bounded deterministic tool ranks shortages after subtracting stock and units already on order, excludes discontinued products, discloses when fewer than five shortages exist and labels any zero-shortage candidates as watchlist only

#### Scenario: Create and deliver a report
- **WHEN** spreadsheet creation succeeds after approval
- **THEN** only its verified URL is passed to subsequent email/calendar preparation, and each write requires a separate action approval

#### Scenario: Reject a write
- **WHEN** an action approval is rejected
- **THEN** no subsequent write is invoked and rejection outputs never reference unexecuted actions

#### Scenario: Invalid source assignment
- **WHEN** a model proposes an unavailable or malformed source assignment
- **THEN** the correction pass receives a safe specific source-binding error and never accepts an invented source
