# Foundation verification and fault-tolerant execution

Qualify the existing execution engine with offline providers and disposable stores.
Preserve approved revisions, shared contracts, tenant authority and consumed budgets.
Investigate late-result fencing, cancellation before dispatch, delegated failure
commits and recovery visibility. Add deterministic regressions for demonstrated
defects, retain the existing reconciliation mechanisms, and document provider-specific
limits. Repair SQL inventory drift after source changes. No deployment, production
migration, live effects, new engine or multi-active worker implementation.

PostgreSQL tests must use the existing isolated-test DSN mechanism; missing test
infrastructure is an explicit blocker, never a passing qualification.
