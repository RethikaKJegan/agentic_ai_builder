## ADDED Requirements
### Requirement: Reviewed scheduled adaptive investigations
Subway Overview SHALL create reviewed recurring or delayed investigations using
the existing durable scheduler, queue and run-owned adaptive GraphRunner path.
Each occurrence SHALL retain independent checkpoints, evidence and budgets.

#### Scenario: A delayed weekly occurrence executes
- **WHEN** a reviewed Subway schedule is due
- **THEN** exactly one logical occurrence runs with date bounds computed from its
  logical due time and IANA timezone, using only authorized Subway capabilities

### Requirement: Authenticated workflow event subscriptions
Existing automation subscriptions SHALL support case-independent workflow events
only through configured authenticated source adapters. Events SHALL be tenant
scoped, schema checked, deduplicated and durably linked to workflow occurrences.

#### Scenario: A source repeats an invoice event
- **WHEN** an authorized source delivers the same event twice
- **THEN** one logical occurrence is retained and duplicate business actions are
  prevented through the existing occurrence/run/effect identities

### Requirement: Freshness and authorization remain evidence prerequisites
Automated investigations SHALL disclose historical or unknown source freshness;
successful queries SHALL NOT establish current-period business evidence without
appropriate source freshness. External effects SHALL retain normal credentials,
destination restrictions, consent and approval enforcement.

#### Scenario: Current-week reporting uses a historical snapshot
- **WHEN** an occurrence requests current-period conclusions from historical data
- **THEN** evidence assessment records the stale-source limitation and cannot
  silently qualify historical records as current operations

### Requirement: Compatible observable lifecycle and recovery
Existing automation controls and history SHALL preserve prior occurrences when
definitions change. Concurrency, restart, resource exhaustion and revoked access
SHALL remain fenced, bounded and observable without changing Simpsons behavior.

#### Scenario: Scheduler restarts after dispatch
- **WHEN** a fresh scheduler observes an already dispatched due time
- **THEN** durable occurrence deduplication prevents a second logical execution
