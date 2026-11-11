# Additive Overview automation design

The existing Overview remains the only prompt entry point. Its automatic mode uses
`overview_routing_available` advertised by the authenticated backend. Explicit legacy
modes and disabled-flag dispatch retain their existing handlers.

The current planning-job queue carries a versioned internal
`praxi_overview_request_v1` context marker in its existing canonical planning envelope.
The worker rechecks feature availability, owner, objective and retry identity before
calling the Overview adapter. Existing normal planning jobs retain their old dispatch.
No additional queue, scheduler, store, ontology, executor or model framework exists.

## Interpretation and preparation

The configured OpenAI planner transport produces a bounded `overview-intent-v1`
interpretation. It distinguishes knowledge, investigation, population, one-time,
recurring, event, unsupported and ambiguous requests. Entity scope is independent
of recurrence, so an identified case can retain its existing reader while population
requests use generic queries. No new customer-name branch or source-field dictionary
is introduced. Existing relevant metadata and source-backed business retrieval feed
the model; existing RAG prompts/retrieval algorithms are unchanged.

The route grants no authority. Read-only routes exclude write capabilities. Explicit
negative-action checks reject contradictory interpretations. Registered contracts,
connector availability, selected-account validation, binding validation, budgets and
approvals remain authoritative in action-plan preparation. Unknown write operations
are excluded until a provider adapter has reviewed operation semantics.

Recurring population queries use the existing QueryPlanner to prepare one exact
metadata-validated query. The existing action planner binds that reviewed query from
server context, rather than inviting another model to change it each day. CrewAI still
executes selected analysis/content agents; the existing graph and connectors perform
fresh reads and approved effects. One-time workflows can retain their existing CrewAI
query-planning task. Identified recurring cases retain existing evidence readers.
Multiple case-read tasks authorize a finite set of complete input payloads.

Preparation stages and final replies use the existing scoped mutation ledger. A
crash after composition commit reuses the persisted interpretation, query, logical
preparation time and immutable composition. Unique insert/conflict checks preserve
one stored result. Unknown submissions retain the same client retry identity.
Cancellation uses the existing planning-job mechanism: discard the result, preserve
history, and deny schedule activation even if an inert preparation stage committed.

## Semantic time consent

Existing unannotated consent continues requiring `properties.query.const`.
`x-praxi-relative-query-v1` is a versioned internal annotation on that exact schema,
not a change to shared contracts. It identifies only the reviewed timestamp field,
period, timezone, bounded day count and two filter positions (`gte` and `lt`).
The schema validator alone does not implement the extension: backend code validates
it explicitly and requires an identical immutable workflow pin before materializing
consent for an occurrence. Dataset, joins, fields, all other filters, metrics,
destinations and limits remain unchanged.

Each run carries the persisted occurrence due time. Authorization rechecks it against
the occurrence record. Delayed execution and retries therefore resolve the reporting
window from the scheduled day, not wall-clock dispatch time. Day/week/month boundaries
use ZoneInfo local calendar arithmetic and UTC half-open bounds. Weeks begin Monday.
`last_n_days` means N calendar days including the occurrence day, with N limited to
1–90. Timestamp fields without an established timezone require clarification.

Existing CronSchedule validates generated daily, weekday, weekly and dated one-time
schedules. A one-time schedule has one permitted occurrence and a short expiry; an
expired proposal cannot roll into an annual cron execution. Default recurring review
is bounded to 90 occurrences/90 days. Missed runs coalesce; overlaps are forbidden.
Existing revocation, pause/resume/cancel, leases, receipts and reconciliation remain.

## Query execution and UI

MongoDB datetime/null fields gain native validated UTC filtering, with exact BSON
millisecond precision. Full-source type checks, one-million-row database cap, snapshot
reads and numeric guards remain. The 5,000-row application fallback and 120 KB query
catalogue bound are unchanged. Unsupported/date-string/coercion cases do not gain
implicit conversion or partial population statistics.

The Overview reuses ConnectedPlan, account selection, SavedDetails, ApiFeedback,
existing workflow approval/run controls and automation-control APIs. It shows the
proposed time, scope, destinations, limits and explicit recurring acknowledgement.
Acknowledgement resets for a new proposal. The backend requires the reviewed workflow
before saving authorization/schedule. Scoped request IDs restore pending generation,
review and schedule state after refresh. No prompts, credentials or payloads are
persisted in browser storage. Legacy query navigation remains intact.

## Limits

A new complaint-created event source is not installed by this change. Event intent
returns an explicit unsupported-source result; existing event/subscription APIs are
unchanged. A tenant must supply actual mappings, reviewed meanings, credentials and
resource destinations. Legacy domain-specific adapters remain available; this project
does not rewrite them into a new ontology. Actual OpenAI interpretation breadth and
live provider outcomes need an authorized pilot; controlled tests are not that pilot.

## Deployment acceptance addition

The supplied deployment examples include first-day-of-month recurrence. Extend
the internal structured recurrence with a bounded month_day and compile it through
the existing cron scheduler. Daily/weekday/weekly/once handling stays compatible.
No new scheduler or shared canonical schema is required.
