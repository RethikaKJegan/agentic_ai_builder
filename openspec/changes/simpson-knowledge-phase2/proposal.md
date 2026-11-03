# Simpson Phase 2: grounded ontology retrieval

## Why
Phase 1 saves connected definitions but callers must supply mapping IDs. Natural-language questions need a read-only, evidence-producing resolver before agent orchestration.

## What changes
Add scoped concept indexing, constrained interpretation, fact/dependency closure, mapping-grounded read plans, owner-scoped plan persistence, authorized execution, API/CLI inspection and planner context. Reuse Phase 1 immutable snapshots/conversions/identities and existing source authorization/read adapters. No frontend, business writes or workflow execution.

## Impact
Backend services, isolated tests and documentation. Existing shared contracts remain unchanged.
