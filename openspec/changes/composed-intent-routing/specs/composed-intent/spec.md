## ADDED Requirements

### Requirement: Analysis and external actions form a composed intent
The system SHALL canonicalize schema-valid population or investigation routes containing external actions to one_time for none/once recurrence, or recurring for repeating recurrence. It SHALL preserve the scope, business goal, declared side effects, missing requirements and schedule fields. This correction SHALL NOT add actions or execution authority, and explicit negative instructions SHALL still be validated.

#### Scenario: Group tickets and email me
- **WHEN** the interpreter labels status grouping and email delivery as population with email_send
- **THEN** the system prepares a one-time composed workflow through existing scoped planning and approval checks

#### Scenario: Repeated analysis and delivery
- **WHEN** the same contradiction includes a repeating recurrence
- **THEN** the system preserves that recurrence and uses the recurring route

#### Scenario: Read-only restriction
- **WHEN** an interpreter proposes delivery despite an explicit no-external-writes instruction
- **THEN** validation rejects the contradiction without enabling delivery
