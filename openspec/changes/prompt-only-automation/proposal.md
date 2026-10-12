# Prompt-only automation

Users describe the process once. Generated workflows must save known settings in existing node configuration and map changing inputs from their triggers, rather than asking for resource IDs, ranges and instructions on every run. Keep existing v1 contracts and published revisions unchanged.

The creation screen will accept one process prompt. Automatic drafts use existing constant mappings, connector reads and event mappings. Validation rejects automatic drafts with inputs that have no event source. Resource ambiguity remains a setup requirement; the model must not invent access, identifiers or business facts. Manual automatic workflows execute with empty inputs; event workflows wait for their configured event.
