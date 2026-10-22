## ADDED Requirements
### Requirement: MESH browser and sidebar branding
The application SHALL use the existing MESH mark as its favicon, enlarge sidebar branding and display Powered by PraxilonAI legibly while retaining responsive/collapsed navigation. Only the sidebar Create workflow shortcut SHALL be removed.
#### Scenario: Sidebar
- **WHEN** a user opens the expanded workspace sidebar
- **THEN** the larger MESH branding and attribution are visible without the blue Create workflow shortcut
### Requirement: Targeted informational notice removal
Google accounts SHALL omit the shared-identity informational banner and callback-file warning while preserving account cards, permissions, connect/manage/verify/disconnect controls and actionable errors.
#### Scenario: Connected accounts
- **WHEN** existing connected Google accounts load
- **THEN** their cards and controls remain visible beneath the header without the two marked banners
