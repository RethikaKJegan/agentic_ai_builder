## ADDED Requirements

### Requirement: Explicitly configured tenant public research
When tenant public research is explicitly enabled, the system SHALL register
enabled keyless search and public-page tool copies matching the installed connector
definitions. Reusable unconfigured templates and tenants without the opt-in SHALL
remain unchanged.

#### Scenario: Enabled tenant searches public sources
- **WHEN** a tenant enables public research
- **THEN** eligible search and public-page tools SHALL be available to planning
- **AND** existing permission, quota, private-query and public-HTTPS checks SHALL apply

#### Scenario: Tenant without public research opt-in
- **WHEN** a tenant has not enabled public research
- **THEN** public research SHALL NOT be registered by that tenant configuration
