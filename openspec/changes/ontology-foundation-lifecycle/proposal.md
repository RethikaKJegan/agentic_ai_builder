# Proposal

## Why

The connected Simpsons data needs a versioned, evidence-backed business ontology before agents can reliably interpret tasks. Existing metadata discovery, semantic suggestions and owner reviews provide useful infrastructure but do not implement the user's six-part ontology construction and lifecycle specification.

## What Changes

- Extend authenticated source discovery with bounded value profiling, catalogue lineage, permissions, freshness and incremental change handling. Report unsupported connector capabilities explicitly.
- Introduce stable, typed, connected common, domain and organization concepts, attributes, constraints, source mappings and relationships, with selective dependency resolution.
- Classify observed facts, model inferences, statistical findings and hypotheses separately; retain evidence packages and contradictory signals.
- Introduce evidence scoring, reviewed evaluation examples, calibration versions and risk-based acceptance policies. Uncalibrated candidates remain reviewable; scores never substitute for correctness.
- Extend human review with corrections, merges, impact views, immutable original proposals and labelled evaluation data.
- Add approved ontology publication, immutable versions, dependency invalidation, workflow revalidation and eligible replay through existing execution authorization.
- Provide authenticated versioned lookups, exports and task subsets with current access checks and decision lineage.
- Verify the full lifecycle against isolated fixtures, then the existing Simpsons connection through bounded read-only acceptance checks. Never fabricate business definitions or SME approvals.

## Capabilities

### New Capabilities

- `enterprise-catalogue`: Source capability declarations, value profiles, metadata lineage and incremental drift handling.
- `layered-business-ontology`: Typed business graph, layer composition, stable identities and evidence classification.
- `ontology-validation`: Evidence scoring, calibration, risk policies, review, correction and merge semantics.
- `ontology-lifecycle`: Approved publication, versioned access, selective resolution, dependencies, invalidation, revalidation and replay eligibility.

### Modified Capabilities

None. Existing execution, tool, workflow and authorization contracts remain authoritative. Any necessary shared-contract change requires its existing joint review process before adoption.

## Impact

Backend: `workflow_api/data_source_adapters.py`, `data_sources.py`, `data_refresh.py`, `data_relationships.py`, `data_graph_v2.py`, `data_ontology.py`, `semantic_kg.py`, `kg_retrieval.py`, `database_workflows.py`, route and persistence modules. Frontend: existing Data Intelligence, source review, relationship review and API schemas. Add additive persistence migrations and relevant tests. No new graph database is assumed: first extend existing durable storage and indexed graph projections. Existing connections and reviewed evidence must be preserved. Current metadata heuristics are candidate generators, not automatically approved knowledge.
