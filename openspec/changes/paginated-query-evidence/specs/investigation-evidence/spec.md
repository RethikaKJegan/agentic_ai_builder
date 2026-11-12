## ADDED Requirements
### Requirement: Paginated detail retains scoped evidentiary validity
The system SHALL accept authenticated, complete-scan query receipts whose detail rows are paginated, while preserving pagination limitations separately. It SHALL NOT infer exhaustive detail analysis from a page. Receipt tampering, revoked source authority, incomplete scans and query warnings SHALL retain their existing rejection behavior.

#### Scenario: Response-byte pagination during an automation
- **WHEN** a verified complete scan returns fewer detail rows than the matched population because of response-size bounds
- **THEN** the investigation can cite returned records and executed coverage facts
- **AND** report preparation receives explicit page coverage and instructions against exhaustive conclusions from the page

#### Scenario: Invalid receipt with pagination
- **WHEN** a paginated receipt fails scope, integrity or scan validation
- **THEN** pagination does not override that failure
