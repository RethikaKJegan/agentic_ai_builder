# Investigation workflow UI and authorized website rollout

## Why
Phase 1–3 work through backend/CLI, while users need prompt-to-graph generation, real execution state, reports and optional business evidence in the existing builder website.

## What changes
Integrate supported investigation prompts from Overview and Workflows into a dedicated read-only investigation canvas using the existing graph/UI patterns. Add persistent server job submission/polling/listing for model planning and execution, source-backed node/report panels, typed input/resume/cancel and an optional ontology evidence drawer. Preserve existing general automation editing and production release flows. Activate the tested saved knowledge as a new live revision and deploy to the existing builder services behind praxi.bellcorpstudio.com, with backups/rollback and authenticated browser verification.

## Impact
Additive backend routes/jobs and frontend screens/client validation. Existing auth, source ownership, model budgets and shared contracts remain authoritative. Company records are read-only. No general connectors or operational business actions are added.
