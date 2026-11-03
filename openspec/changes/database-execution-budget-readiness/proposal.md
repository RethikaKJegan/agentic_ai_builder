# Database execution budget readiness

## Why
The published investigation failed before any database read: each dynamic database reader had max_tool_calls=1 while the registered query connector reserves four tool units. Planning validation did not check this contradiction. Repeated full schema metadata also consumes a large share of finite model-turn budgets.

## What Changes
Normalize proposed database-reader budgets against actual connector reservation units and bound model input metadata by agent responsibility. Reject undersized published/manual configurations in database workflow validation. Preserve finite Registry/workflow ceilings, source authorization, approval requirements and run history. Repair the existing workflow as a new unpublished revision; an actual bounded read-only execution requires the separately requested approval.

## Impact
Generic proposal budget sizing and database validation, task metadata, finite revised workflow budgets and regression tests. No budget-enforcement disabling, failed-run replay, company-data writes or automatic external messages.

The approved execution also reproduced a separate contract ambiguity: agents put operating notes in clarification, which means do not execute in the query engine. Constrain the executable tool contract to an empty clarification string so schema validation can correct the decision before dispatch. Genuine unresolved queries remain unexecuted.

The second approved execution reproduced a flat-field-only query restriction against advertised nested MongoDB scalar fields and mixed integer/number observations. Add safe catalog-backed object-path extraction, keep operator/array paths rejected, narrow delegated projected-field schemas to advertised executable IDs, and bound delegated query output to ten rows with explicit sampled coverage. Reduce repeated per-agent field-reference packing to 8 KB; full catalog/schema authority is preserved. No failed plan is silently edited or granted broader access.
