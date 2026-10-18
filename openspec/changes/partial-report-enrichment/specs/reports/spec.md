## ADDED Requirements
### Requirement: Optional enrichment does not block a report
Reports SHALL continue using verified core inventory evidence when optional category or supplier relationships are unreviewed, missing or ambiguous. They SHALL omit those joins, label unavailable enrichment and disclose limitations in delivered reports. They SHALL retain existing core evidence and external action approval checks.

#### Scenario: Proposed category link
- **WHEN** stock and supplier evidence are usable but the category link needs review
- **THEN** generation continues without querying that category source
- **AND** category details are marked unavailable pending relationship review
- **AND** spreadsheet, email and meeting retain separate approvals

#### Scenario: Missing core quantities
- **WHEN** required stock quantities or product identities are unavailable
- **THEN** the report does not invent them or publish an unsupported ranking
