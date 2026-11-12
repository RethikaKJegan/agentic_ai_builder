# Design

The Workflows screen retains InvestigationList and the existing New entry point. Only this screen suppresses the investigation heading and entry link; the Overview screen keeps its existing header. Lifecycle data and canonical workflows remain stored, while their redundant panels are removed from this page.

KnowledgeMap omits module-placeholder cards in This workflow mode. Full ontology retains its existing grouping and navigation.

ConnectedPlan mounts DurableAutomation inside Background. The API accepts an optional workflow_id and filters owned records before pagination, following explicit schedule, authorization, occurrence and case references. Metrics and jobs are scoped too; worker health remains service health. The existing case-specific automation panel is preserved.

The existing intent interpretation response returns a 3–4 word display_name before action planning. Direct model planning paths generate a display title before their planner. Offline, historical and unavailable-title cases use a deterministic short title. No model is invoked when listing historic workflows. Full objectives and manual renames remain separate. No extra title call is added to the standard Overview interpretation path.

Duplicate uses an idempotent owner-scoped POST. Copies have distinct workflow, composition, agent and action-plan identities and recomputed integrity hashes. Execution history, active releases, subscriptions and lifecycle continuation context stay with the original. Copies remain editable and require normal preparation/review before execution. Both connected action plans and legacy investigations are supported. The original prompt, steps and pinned source references are retained.

No shared contract files, live data, credentials, deployment configuration or external integrations are changed by this work.
