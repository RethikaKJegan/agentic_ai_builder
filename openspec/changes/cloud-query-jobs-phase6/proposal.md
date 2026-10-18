# Phase 6: durable query jobs

Replace the Questions UI synchronous execution path with owned durable jobs, truthful stage progress, cancellation, lease fencing/recovery and encrypted expiring result retrieval. Reuse the configured store and worker supervisor. Preserve reviewed logical plans, authorization, metadata freshness, strict joins, exact arithmetic and row/byte limits. Keep the legacy synchronous API compatible with its original 45-second bound.

Results are newly retained encrypted for 15 minutes; job/plan metadata is retained for 24 hours, with bounded admission. No credentials or authority snapshots are persisted in jobs. This is an explicit data-query contract extension, not a workflow/agent/tool contract change or contributor acceptance.
