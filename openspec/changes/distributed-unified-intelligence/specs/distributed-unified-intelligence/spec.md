## ADDED Requirements

### Requirement: Bounded parallel execution
The service SHALL offer opt-in multiple active runtime and lifecycle dispatch
consumers using existing durable claims. Provider pollers and unqualified
background components SHALL retain singleton coordination. Server settings SHALL
bound queue admission, live account claims, specialist concurrency and configured
per-account provider windows. Retries SHALL preserve budgets and use bounded delay.

#### Scenario: Concurrent consumers claim the same run
- **WHEN** four active consumers encounter one approved tool invocation
- **THEN** only the live claim executes and checkpoints that invocation

#### Scenario: One account has a backlog
- **WHEN** multiple accounts have runnable jobs
- **THEN** bounded polling rotates accounts and waiting approvals do not hide runnable work

### Requirement: Permission preserving account knowledge
One logical account graph SHALL expose only the current owner's authorized
projections. Immutable revisions SHALL preserve source, mapping, ontology and
execution references. Entity identities SHALL include their source scope, and
conflicting observations SHALL remain explicit. Technical references SHALL NOT
be promoted to confirmed business predicates without existing semantic review.

#### Scenario: A source observation changes
- **WHEN** an authorized read synchronizes different evidence for the same source projection
- **THEN** a new immutable revision becomes current and the old pin is historical

#### Scenario: Current metadata differs from the pinned graph
- **WHEN** metadata is stale or has a different revision
- **THEN** current graph access is denied while historical references remain available

### Requirement: Bounded grounded context
Planning and execution SHALL consume bounded task relevant graph context under
current authorization. Traversal SHALL enforce direction, status, depth, result
and time bounds. Execution memories SHALL remain execution evidence and SHALL NOT
be represented as verified company facts. Graph context SHALL NOT grant tool access.

#### Scenario: Another owner supplies a valid graph pin
- **WHEN** an owner requests another owner's projection in the same account
- **THEN** access is denied without returning the projection

### Requirement: Reproducible controlled qualification
Verification SHALL distinguish successful PostgreSQL checks, process termination
checks, simulated provider benchmarks and unperformed production acceptance.
Unknown external outcomes SHALL remain blocked without blind repetition.

#### Scenario: Worker dies after provider acceptance
- **WHEN** a process is killed before its invocation outcome can be checkpointed
- **THEN** restart preserves the original intent and usage and blocks uncertain replay
