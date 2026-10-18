# Phase 5: bounded federated aggregation

Implement trusted fragmentation of reviewed aggregate plans: a PostgreSQL fact prefix with same-connection joins, followed by bounded PostgreSQL/MongoDB dimensions. Validate complete join domains before filters, transfer exact partial states, merge weighted aggregates and apply global sorting/limits. Add native average through sum/count finalization. Unsupported shapes retain explicit bounded fallback.

Preserve ownership, permissions, expiry, freshness, read-only snapshots, strict joins and numeric bounds. Do not change relationship reviews or credentials. Add optional fragment evidence to data-query contracts only; no workflow/agent/tool changes or inferred contributor signoff. No asynchronous jobs, result storage or shared cross-database snapshot.
