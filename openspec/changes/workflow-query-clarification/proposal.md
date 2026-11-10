# Workflow query clarification

## Why
Saved Simpson run run_018cdc5a65a24d44b3acfbfe1682f251 contains an explicit unresolved operating-hours definition in the typed query. The adapter stops safely before any read, but the runtime marks it failed, the task UI hides the question, and recovery treats a read-only node as an external write merely because a later email exists.

## What Changes
Persist deliberate query clarification as a blocked run/needs-input action, expose the original question through existing task result fields, classify per-node side effects using pinned contracts, and allow explicit generation of a new reviewed workflow with the supplied definition and same selected Google account. Project old runs without rewriting history. No inferred field meaning, casts, automatic replay or external writes.

## Impact
Existing query adapter, durable graph, recovery projection and investigation UI. No shared contract, database schema or new orchestration pipeline.
