## ADDED Requirements

### Requirement: Unscheduled work defaults to immediate execution readiness
The system SHALL interpret an ordinary request without execution scheduling instructions as immediate work, without creating a timer or asking for a run time. A one_time workflow SHALL use recurrence none unless future execution was requested. Existing workflow review and external-action approvals SHALL remain required.

#### Scenario: Investigation and email without a time
- **WHEN** a user asks to investigate overheating and power loss and email the findings without a schedule
- **THEN** planning prepares an unscheduled workflow without a run-time clarification

#### Scenario: Empty once proposal
- **WHEN** the interpreter returns once with no hour, date, weekday or month day and the objective has no scheduling cue
- **THEN** the system normalizes only that recurrence to none, preserving analysis and delivery

#### Scenario: Future or repeated work
- **WHEN** a user explicitly requests tomorrow, a future execution time or recurrence
- **THEN** the requested schedule is preserved and genuinely missing timing remains a clarification

#### Scenario: Reporting window is not execution time
- **WHEN** a user requests today's or the previous month's data without asking for delayed execution
- **THEN** the data window is preserved and the workflow remains unscheduled
