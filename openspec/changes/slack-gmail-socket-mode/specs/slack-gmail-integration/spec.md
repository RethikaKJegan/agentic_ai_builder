# Slack Gmail integration

## ADDED Requirements

### Requirement: Configured Socket Mode receipt handling
The receiver SHALL use operator-pinned team and DM conversation identifiers, accept only ordinary human DM messages, route to active matching bindings, persist receipt/jobs before acknowledging matching events, and suppress duplicates across restarts.

#### Scenario: Slack retries a DM
- **WHEN** Slack delivers the same event twice
- **THEN** only one durable dispatch job SHALL exist per binding

#### Scenario: Wrong source
- **WHEN** an event belongs to another team, conversation, sender or is bot-generated
- **THEN** it SHALL NOT create a workflow job

### Requirement: Authorized Gmail execution
Gmail sends SHALL use trusted Registry grants, opaque credential resolution, exact recipient allowlists and the existing approval gate. Setup SHALL NOT fabricate approval or publication.

#### Scenario: DM creates an email action
- **WHEN** a matching DM reaches an approved published workflow
- **THEN** runtime SHALL pause at the action approval and only submit email after an authorized approval

### Requirement: Operator setup preserves drafts
Setup SHALL prepare a deterministic mapped draft without overwriting an existing revision and SHALL report missing configuration without exposing secrets.

#### Scenario: Repeated setup
- **WHEN** the setup draft already exists
- **THEN** it SHALL remain unchanged
