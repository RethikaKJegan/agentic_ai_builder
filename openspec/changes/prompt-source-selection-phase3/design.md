# Design

Include only confirmed mappings for supported catalog IDs in planner context.
Verify detailed graph revision against the v1 query context; existing whole-graph
freshness rechecks fence concurrent edits. Never provide rows or credentials.

Add optional selection_preview to queries-v1 planned responses. Include selected
datasets, required fields and usage roles, confirmed relevant mappings, ordered
execution join pairs, original review status, and metadata coverage warnings.
Reasons describe validated plan usage, not fabricated model reasoning. Empty
clarification plans expose no sources. Saved plans/jobs preserve the same preview.

Show source cards and an accessible interactive SVG subset in Questions. Display
full linking pairs and runtime caveats. The logical plan is inspectable structured
intent, not executable SQL or actual database traces. Retain legacy compatibility.
Successful execution returns an optional executed_plan snapshot, identifying the
logical query actually used for that completed result. It is displayed separately
from the preview and is not labelled as native SQL/Mongo pipeline text.
