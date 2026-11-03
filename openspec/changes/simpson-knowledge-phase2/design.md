# Design

## Existing flow and integration points
`service.plan_workflow.resolve_context` loads `business_planning.retrieve` lexical business references, then `DatabaseWorkflows.enrich` calls `KnowledgeRetrieval.retrieve` to supply metadata to the planner. `DataQueries` plans schema-constrained reads; `QueryReader.objects` implements bounded projections. `BusinessSources` provides current authority, ownership and metadata checks. Phase 1 `BusinessKnowledge` snapshots pin mappings, dependencies, policy revisions and hashes.

Add a pure resolver shared by preview and planner context. Its output augments current planning without changing business-planning-v1 or execution permissions. Metadata selection uses resolved dataset IDs through a server-side argument, never client authority. Execution uses BusinessSources authorization/bound source checks and QueryReader.objects; reference steps preserve native types and only use saved direct bindings. Cross-source serial matches are separate candidates.

## Authority and limits
A request persists its original version, hash, intent and plan in a scoped table. Only a request ID can execute. Verify plan hash, knowledge, current permissions, metadata and credential stamp before and after reads. Preview reads metadata only. Required closure overflow blocks execution. Exact filters push down; text/numeric predicates apply after bounded reads and disclose population limits. Never infer diagnosis, physical identity, coverage or approval from retrieval success.

## AI
Optional bounded model interpretation sees candidate definitions and redacted identifier placeholders, never retrieved company rows. Strict output validates concept IDs/task vocabulary; deterministic interpretation remains available without any provider. Unknown predicates and unsupported requests remain explicit.
