# Verification — 10 November 2026

Actual failed Simpsons run: `run_829a408cae2146938fc96368b0ac074e`.
Its 30 projected fields included one duplicate and a customer-contact field belonging
to infantcares while the base source was jointinspectionreports. Against copied
metadata, the original and merely deduplicated plans both correctly fail with
DATA_QUERY_INVALID / unavailable field. Removing duplicates alone is insufficient.

The correction canonicalizes repeated model projection IDs, validates generated plans
against their actual supplied catalogue before source dispatch, and permits one
metadata-only correction within the new automatic draft's reviewed two-call budget.
Both attempts share its existing token/cost caps. Explicit saved/tool query payloads
are not silently repaired; foreign fields, scopes and relationships remain validated.
A second invalid output stops with AGENT_OUTPUT_INVALID and no query job/source call.
Existing approved budgets are not enlarged at runtime.

A returning worker clears only its own stopped run's lease. Running owners and
replacement owners remain fenced; effect/reconciliation state is preserved. Hosted
active-standby runtime pools now honor concurrency=2. Two slots let independent runs
progress concurrently; at full capacity work still queues, and no active invocation
is preempted or cancelled. This release does not implement unlimited capacity or
latest-request queue priority.

Evidence:

- Integration, query clarification, workers, recovery details and database reliability:
  **60 passed**.
- Focused final regression: **10 passed**, including two tests added after the larger
  run was collected; the groups overlap and must not be added as unique counts.
- Additional source-math, Sheets/email, Calendar authority, permission revocation,
  control-metadata and web-research safety checks: **7 passed**.
- Controlled parallelism test: a second queued run finishes while the first worker
  call remains blocked, with each selected run invoked once.
- A bad first model query receives exactly one feedback correction before creating
  a durable query job; both invalid attempts create no job or provider action.
- Canonical schema validation, generated UI contracts, strict OpenSpec and diff checks
  passed. The frontend artifact is unchanged, so no new frontend build is claimed.
- Copied actual Simpson account startup passed protected-history checks. Actual saved
  query still rejects its foreign field. A controlled corrected model response with
  28 valid source fields passes normal validation while retaining original source,
  filters, joins and limit. The constructed active-standby runtime pool has two slots.
  Networking and workers were disabled during rehearsal.

Tests use controlled models/providers. No live paid model, source execution, email,
spreadsheet or Calendar write was performed for verification. Arbitrary future model
outputs are not guaranteed to be valid. Failures stop safely within reviewed limits.
