## ADDED Requirements
### Requirement: Readable approved briefings
Email and calendar briefings SHALL separate urgent products, watchlist items, market context and coverage notes while retaining source quantities and the verified spreadsheet URL. Gmail SHALL include an escaped HTML alternative and readable plain text. Calendar descriptions SHALL include the exact IST schedule and review agenda. Formatting SHALL NOT add external actions or bypass approvals.

#### Scenario: Inventory report delivery
- **WHEN** a ranked report is prepared for delivery
- **THEN** shortages and watchlist products appear in separate readable sections
- **AND** incomplete enrichment is explained without repeating technical errors for every product

#### Scenario: Untrusted product text
- **WHEN** a product or body contains HTML markup
- **THEN** the HTML email escapes it instead of interpreting it as markup
