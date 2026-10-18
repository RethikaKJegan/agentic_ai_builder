## ADDED Requirements

### Requirement: Initial draft version is application-owned
New planned workflows SHALL return draft/version 1. After confirming no saved
workflow exists, the frontend SHALL save its initial draft as version 1 with base
0 even when a cached planning result proposes a higher version. Existing saved
revisions SHALL remain unchanged, and genuine concurrent saves SHALL still load
the server's saved revision.

#### Scenario: Model proposes version 2
- **WHEN** a new planning result proposes version 2 without a saved workflow
- **THEN** initial saving succeeds as draft version 1
