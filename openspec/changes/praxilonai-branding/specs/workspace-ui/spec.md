## ADDED Requirements
### Requirement: PraxilonAI product identity
Product copy, accessible labels and browser page titles SHALL use PraxilonAI instead of MESH. Powered by attribution SHALL be removed. The existing icon and stable internal/storage identifiers SHALL remain unchanged.
#### Scenario: Product entry points
- **WHEN** a user opens the landing page, login or application
- **THEN** the product is named PraxilonAI without Powered by text
### Requirement: Targeted Knowledge navigation removal
Only the Knowledge shell navigation entry SHALL be removed, including its shared mobile menu representation. The Knowledge page and existing backend functionality SHALL remain intact.
#### Scenario: Sidebar
- **WHEN** navigation is expanded
- **THEN** Knowledge is absent and the remaining destinations remain available
