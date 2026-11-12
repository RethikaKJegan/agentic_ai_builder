## ADDED Requirements
### Requirement: Public research scope is reviewed before recurrence
The system SHALL propose bounded public-only search queries during recurring intent preparation and bind them as reviewed context. Exact operation consent SHALL still constrain every occurrence. Source results SHALL NOT alter the approved public search payload. One-time search behavior SHALL remain unchanged.

#### Scenario: Business summary and public research recur together
- **WHEN** a recurring request combines internal analysis and general public guidance
- **THEN** public queries are proposed before review and bound independently of internal results
- **AND** each occurrence uses the exact reviewed search payload

### Requirement: Dynamic recurring read drafts are corrected before review
The system SHALL reject dynamic non-query read bindings during action-plan validation and use the existing bounded draft-correction process. It SHALL NOT widen recurring resource permission or silently omit explicitly required work.

#### Scenario: Runtime-generated web search or discovered URL
- **WHEN** a proposed recurring read depends on a generated search query or runtime-discovered resource
- **THEN** planning must bind an available reviewed scope or retain a genuine unresolved requirement before scheduling
