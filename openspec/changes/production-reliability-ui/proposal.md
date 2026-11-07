# Production reliability and investigation UI integration

Reuse the existing durable runtime, Registry, ontology, account projections,
worker claims, approval/recovery services and investigation UI. Preserve all
prior changes, historical contracts, company data and concurrent Subway work.

Address demonstrated gaps with trusted shared-provider quotas and reserved runtime
capacity, bounded graph synchronization with stale-pin preservation, operational
alerts, investigation diagnostics and bounded graph views. Verify isolated
PostgreSQL failures, process recovery, sustained load and backup/restoration.
No production restart, migration, deployment, live model calls or provider effects.
Multi-host and live-provider acceptance require actual infrastructure and remain
explicitly unqualified when unavailable.
