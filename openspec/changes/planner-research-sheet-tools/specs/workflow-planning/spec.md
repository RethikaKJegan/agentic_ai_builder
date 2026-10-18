## ADDED Requirements
### Requirement: Complete trusted integration context
DB-backed planning SHALL include enabled runtime-registered web search/page read
and Sheets creation/setup tools alongside existing Calendar/mail tools. Availability
SHALL NOT grant execution authority or bypass immediate external-write approvals.
#### Scenario: Registered research and spreadsheet creation
- **WHEN** the tools are enabled and have runtime connectors
- **THEN** the planner receives their exact Registry schemas and capabilities
#### Scenario: Missing tools or forged context
- **WHEN** a tool is disabled, unregistered or browser-injected
- **THEN** it is not advertised as an available workflow tool
