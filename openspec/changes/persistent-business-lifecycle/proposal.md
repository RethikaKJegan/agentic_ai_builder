# Phase 4: persistent business lifecycle

Add owner/workspace-scoped, immutable process definitions and durable business
cases above the existing capability composition and runtime. No frontend changes.
Analytical completion is distinct from actual external activity verification.

Integration map (inspected before implementation):

| Concern | Existing integration |
|---|---|
| Storage / migrations | WorkflowStore.transaction; additive service-owned CREATE TABLE migrations; SQLite/Postgres adapter |
| Ontology / mapping versions | BusinessOntology, BusinessKnowledge, BusinessRetrieval and BusinessSources |
| Evidence / coverage | BusinessPreparation.checked, BusinessEvidenceAdapter, InvestigationCoverage |
| Capability contracts / planning | capability_contracts.catalogue; BusinessComposition.prepare; existing planner provider |
| Compiler / agents | BusinessComposition.workflow, compile_workflow, AgentConfigurationFactory |
| Execution / tools | GraphRunner; runtime.delegation; CrewExecutor; RegistryAdapter assignments and connectors |
| Persistence / memory / recovery | RuntimeService runtime_runs/events; task_checkpoints; WorkingMemory; ExperienceMemory; RecoveryService |
| Approval / effects | approved exact runtime revisions, Registry grants, runtime approvals and effect journal |
| HTTP / CLI | business_ontology_routes.install session transport; scripts/capability_composition.py isolated CLI |

Cases pin complete process snapshots; optimistic revision updates and durable command
receipts protect concurrent commands. Runtime execution happens outside case write
transactions, uses stable run keys, and reconciles interrupted stages against saved
runs. Unknown external effects never receive automatic replay. Event ingestion is
an authenticated explicit command; existing webhooks/pollers can call it using their
trusted current authority. No new orchestration engine, company writes, model mode,
or permission grants are introduced.
