## ADDED Requirements
### Requirement: Required review result join
When all explicitly required procurement reviews are scheduled and task capacity is exhausted, the runtime SHALL collect their actual results before invoking master synthesis.
#### Scenario: Continuation with pending reviews
- **WHEN** both required reviews are pending after a delegate decision with continuation
- **THEN** the next master turn sees both returned results without spawning duplicate reviews
### Requirement: Preserve independent concurrency
Other masters SHALL retain concurrent continuation behavior and the existing task limits.
#### Scenario: Independent master work
- **WHEN** a workflow has no explicit required-review barrier
- **THEN** its master may continue independent work while a child is pending
