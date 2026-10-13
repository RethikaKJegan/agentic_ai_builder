# Procurement persistence

## Why
Procurement definitions and connector calls currently lack a durable case store. Restart-safe state is required before agents can coordinate procurement.

## What Changes
Add an extension-only SQLite repository with schema validation, scoped references, immutable history, optimistic revisions, transaction idempotency, provider-resource links and synchronization intents. Enforce ordinary lifecycle edges, quote arithmetic/scope and evidence-backed order closure. Trusted approval/evidence validation is injected by a future application adapter; caller-supplied authority labels never grant permission.

## Impact
Only new extension and scoped OpenSpec files change. No original database, API, worker, credentials or workflow is modified. No provider writes or automatic synchronization are enabled.
