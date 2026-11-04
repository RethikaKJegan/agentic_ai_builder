# Design

The existing scoped coverage preflight becomes SharedBusinessPreparation. The old InvestigationCoverage.preflight delegates to it. Existing resolver and coverage contracts provide deterministic task dependencies and preserve mandatory gaps. Results retain immutable source observations, request references, metadata stamps, ontology/mapping/provider hashes and scope. Registry candidates are discovery only, never executable grants.

General planning invokes the same service through the authenticated workflow service. Server-generated compact context is passed to the existing planner and a scoped preparation reference is pinned in draft metadata. Persistence verifies reference ownership/integrity. Backend task adapters reload preparation, reauthorize, verify pins and invoke existing validated retrieval/scenario adapters; no arbitrary queries. Existing runtime/delegation is unchanged.
