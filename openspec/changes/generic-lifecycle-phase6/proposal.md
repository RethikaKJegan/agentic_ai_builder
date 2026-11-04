# Phase 6 generic lifecycle, memory and reassessment

Reuse BusinessCases, EvidenceCompletion, LifecycleDriver, BusinessComposition,
ClientPackages, WorkingMemory, ExperienceMemory and RecoveryService. Keep Simpson
version 1 immutable. No frontend, production migration, deployment or live writes.

Audit: Phase 4/5 already provide scoped SQLite/Postgres transactions, case CAS,
durable command receipts, event deduplication, source/version pins, bounded driving,
dynamic Registry-controlled composition, CrewAI task checkpoints and guarded recovery.
Phase 3 runtime/memory.py provides bounded working views and provenance-backed,
human-validated recovery strategies; runtime/recovery.py provides failure taxonomy,
dependency closure, source revalidation and uncertain-write barriers. ClientPackages
already provides scoped immutable ontology/mapping/capability data and trusted source
adapters, but cannot declare executable processes or memory boundaries.

Missing: package process installation, lifecycle-specific bounded working views,
deterministic execution feedback and advisory planning ranks, and reviewed late-event
reassessment that preserves original completed executions. Extend these existing
components; add an orchestration helper around case commands, not an execution engine.
Use additive service-owned tables for archived case revisions and immutable feedback;
extend the existing experience table for verified operational strategy records.

Reassessment explicitly selects an authenticated saved event and schema-checked
input bindings. Archive original state, compute dependency closure, reset eligible
analytical stages with new reviewed compositions; retain write stages/receipts and
block uncertain effects. Never rewrite source data or grant approval. Expose current
and archived conclusions through existing authenticated case inspection routes.

A clearly labelled retail complaint fixture package exercises eight different stages,
mapped order/purchase evidence, retail capabilities, conditional fulfillment analysis,
quality feedback and monitoring on this same runtime. Test controlled transports,
restart, concurrency and disposable PostgreSQL where available. Production readiness
claims require measured verification and explicit live-provider/deployment limits.
