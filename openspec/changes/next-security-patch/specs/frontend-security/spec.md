## ADDED Requirements

### Requirement: Patched Next.js dependency
The frontend SHALL use a patched Next.js version on its current 16.4 release line.

#### Scenario: Production build
- **WHEN** the production build runs after dependency installation
- **THEN** it SHALL complete without the Next.js vulnerability reminder
- **AND** existing ontology and business-foundation navigation SHALL continue working

#### Scenario: Dependency audit
- **WHEN** the dependency audit completes
- **THEN** Next.js SHALL not be listed as a vulnerable installed package
- **AND** unrelated findings SHALL be reported without claiming a clean dependency tree
