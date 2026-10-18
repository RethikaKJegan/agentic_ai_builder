# Validated inventory research handoff

The latest inventory report failed with MODEL_OUTPUT_SCHEMA_INVALID on its
coordinator's second model call while its sole research specialist was pending.
The specialist completed with valid findings, but pool shutdown could not recover
the failed coordinator. Inventory compiler v1 intentionally delegates only public
risk research and uses the identical business output schema on both agents.

For that narrowly identified compiled workflow, wait for the sole delegated task,
validate its result against both schemas and return it directly to the graph.
Preserve recorded specialist/tool traces, current authorization, cancellation,
deadlines and all three Google-action approvals. Do not change generic multi-agent
synthesis or accept malformed provider output. Existing compiled revisions work
without editing approved documents. Validate offline before deployment.
