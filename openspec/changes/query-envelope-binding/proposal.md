# Correct query-envelope bindings

## Why
Hosted population-count planning twice bound the complete data.plan_query response to the workflow_data_query query field. The response wraps the typed query, so validation rejected it before execution.

## What Changes
Normalize only the known automatic-planning data.plan_query to tool.workflow_data_query whole-output binding to its declared query child, with exact producer/consumer schema agreement. Keep strict validation for all other bindings and include type mismatch diagnostics in bounded correction feedback. Add controlled regression tests and deploy the backend using verified backups and application-only rollback.

## Impact
No shared contract, data schema, credentials, or provider effects change. No paid model calls or real email/Sheets writes during verification.
