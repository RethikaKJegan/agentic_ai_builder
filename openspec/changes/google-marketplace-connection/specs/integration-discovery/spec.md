## ADDED Requirements

### Requirement: Discover and connect Google
Marketplace Tools and integrations SHALL show Google instead of Slack and HubSpot
and provide a Connect Google action linking to Integrations. Integrations SHALL
retain Google account/service authorization and omit generic technical provider
cards. Backend capabilities SHALL remain unchanged.

#### Scenario: Discover Google
- **WHEN** a user clicks Google or Connect Google in Marketplace
- **THEN** Integrations opens with Google account connection controls

#### Scenario: Authorize services
- **WHEN** a user selects Connect Google in Integrations
- **THEN** the existing service-selection and Google authorization flow is used
