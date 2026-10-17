# Automatic source selection

## Why
Users should describe their requirement once. A manual/automatic dropdown exposes an implementation choice and the planner currently lacks persisted workspace knowledge/source context.

## What Changes
- Remove the overview input-source selector and submit prompt-only automatic setup.
- Enrich planning on the server with bounded, workspace-scoped saved knowledge and published source descriptions; inspect supported explicit and saved spreadsheet references using existing discovery.
- Give accepted data-reading agents fresh bounded workspace knowledge as separate untrusted task data, without modifying agent contracts, schemas, credentials or assignments.
- Retain specific unresolved requirements for missing/ambiguous/unsupported sources and all existing release/action authorization.

## Impact
Overview, planning service/provider, CrewAI context, focused API/unit/browser regressions. No schema or database migration. No new source ingestion or arbitrary URL fetcher.
