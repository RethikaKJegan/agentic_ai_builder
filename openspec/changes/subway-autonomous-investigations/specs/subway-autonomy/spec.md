## ADDED Requirements
### Requirement: Workflow-owned adaptive investigation
Eligible read-only Subway Overview investigations SHALL use bounded run-owned
adaptive control without requiring a business case. GraphRunner SHALL remain the
only executor and existing Registry authority SHALL remain mandatory.

#### Scenario: Additional evidence is needed
- **WHEN** successful actions leave a business requirement unsatisfied
- **THEN** the controller validates a bounded unfinished-plan revision or persists
  a typed input wait or explicit blocker, preserving completed execution history

### Requirement: Evidence-qualified completion
The controller SHALL separate execution success from objective satisfaction,
validate receipt scope and completeness, retain stable requirement/evidence IDs,
and reject completion with unsupported requirements or blocking source gaps.

#### Scenario: All tools succeeded but the goal remains unsatisfied
- **WHEN** the assessment cites incomplete evidence or an unresolved requirement
- **THEN** the run cannot complete as a satisfied objective

### Requirement: Durable isolated continuation
Evaluation claims, revisions, budgets and waits SHALL persist in scoped runtime
state; concurrent workers SHALL NOT commit conflicting decisions or replay
completed actions. Existing non-adaptive and Simpsons workflows SHALL retain
their behavior.

#### Scenario: Worker restarts after a completed action
- **WHEN** a fresh worker resumes an eligible run
- **THEN** existing checkpoints and evidence are reused without executing that
  completed action again
