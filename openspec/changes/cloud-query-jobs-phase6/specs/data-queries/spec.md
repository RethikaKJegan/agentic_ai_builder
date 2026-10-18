## ADDED Requirements
### Requirement: Durable owned query lifecycle
The service SHALL execute owned reviewed query plans as durable bounded jobs with current authorization, idempotent admission, lease fencing and encrypted temporary results.

#### Scenario: Worker loss
- **WHEN** an attempt loses its lease and retry/deadline/plan validity allow recovery
- **THEN** another worker starts fresh source reads and only the currently owned attempt may publish a complete result

#### Scenario: Cancellation publication race
- **WHEN** cancellation commits before result publication
- **THEN** the worker cannot publish success or expose result rows

#### Scenario: Expired result
- **WHEN** a successful job result reaches its retention deadline
- **THEN** retrieval returns an explicit expiry error and result ciphertext is removed while success metadata remains

### Requirement: Observable refresh recovery
The Questions screen SHALL display observed job stages, support cancellation and restore owned job status after page refresh without browser-stored result rows.

#### Scenario: Page refresh
- **WHEN** a user refreshes during a query job
- **THEN** the screen recovers the server-owned job and displays progress or retrieves its complete unexpired result
