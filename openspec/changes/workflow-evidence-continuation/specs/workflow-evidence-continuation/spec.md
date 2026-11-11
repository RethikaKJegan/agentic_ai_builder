## ADDED Requirements

### Requirement: Calendar event time is independent of workflow execution time
The system SHALL resolve explicit today/tomorrow event dates using the planning
clock and stated timezone. An event's timestamp SHALL NOT schedule the workflow
unless a separate execution time is requested. External writes SHALL retain review.

#### Scenario: Investigation followed by calendar review
- **WHEN** a user requests an investigation and a thirty-minute review in my calendar today at a specified India time
- **THEN** the investigation is ready immediately and the event retains the specified timestamp and duration

### Requirement: Recoverable planning gaps produce a useful report
Question-free generation SHALL prepare a content-only report from available scoped
ontology evidence when required execution information cannot be resolved. It SHALL
list the specific limitations and deferred operations without invented facts or
claims of original-request completion. Authorization failures SHALL remain denied.

#### Scenario: Missing recipient
- **WHEN** the destination cannot be resolved
- **THEN** a report can be reviewed without sending or substituting a recipient

#### Scenario: Missing evidence
- **WHEN** no relevant evidence exists
- **THEN** the report states this absence without inventing records or statistics
