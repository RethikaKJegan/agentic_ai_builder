# Original-plan Phase 4: controlled database CRUD

Add registered Atlas/PostgreSQL create/read/update/delete tools behind explicit
server-owned workspace/subject/dataset/operation/field policies. Provide owned,
encrypted prepared operations, exact-key previews, explicit human execution,
optimistic concurrency, durable no-replay claims, counts/audit/history and guarded
compensating recovery for known committed steps. Preserve existing read queries,
Google/procurement, graph contracts and all Praxi files.

Point writes target one record per step, up to four distinct keys per group.
Unsupported types, views/generated columns/user triggers/cascading delete paths
fail closed. Independent source transactions do not provide a cross-database
transaction. Lost acknowledgements/crashes are uncertain and cannot be replayed
or automatically compensated. Existing bounded query reads remain available.

Expose a Database operations UI and additive data-operations-v1 contract. Do not
enable live targets, modify credentials, deploy or perform cloud writes during
implementation. Verify actual CRUD/conflicts/rollback/recovery using disposable
PostgreSQL and MongoDB instances, plus HTTP, policy, Registry and UI regressions.
