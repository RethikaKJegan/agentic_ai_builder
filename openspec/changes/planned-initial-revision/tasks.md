- [x] Normalize initial planned draft revision and defensive first save.
- [x] Test generation/save recovery and validate contracts/specification.
- [x] Recover generated draft, deploy and verify services.

Backend, worker and frontend reloaded. Authenticated workflow GET confirms draft
v1, frontend workflow URL returns HTTP 200 and current RuntimeWorker is ready.
Previous frontend build retained under .local/ui-rollbacks/initial-revision-before/.

Evidence: successful planning job plan_e1dde61beb504d979a992070a1b1ca4e
contained new workflow planned_b92b9315f54dec2b version 2 with no saved revisions.
Repeated PUT version 2/base 0 conflicted; recovery GET then returned 404.
28 Python planner/provider-error tests and 4 subtests passed, plus 24 frontend
integration tests including version-2 initial-save normalization and genuine
concurrent-save recovery. Contracts, strict scoped OpenSpec, types, lint, production
build and diff checks passed. The existing successful job result was recovered
using normal authorized PUT base 0/version 1: response confirmed draft v1. No
generation, approval, publication or workflow execution was performed for recovery.
