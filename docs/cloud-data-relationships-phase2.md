# Cloud data relationships — Phase 2

Data Intelligence → Relationships builds a metadata graph from the latest owned
Phase 1 snapshots. Click Build relationships for existing connections. Every
successful subsequent metadata profile and disconnect automatically queues a
rebuild on the existing supervised DataSourceWorker.

Connection, dataset and field nodes retain source IDs and metadata revisions.
Parent IDs encode containment; relationship edges preserve foreign-key field
order, including composite keys. Undiscovered foreign-key targets produce a
coverage warning instead of an invented target.

Cross-connection proposals require matching normalized named identifiers ending
in `ID`, `Id`, `_id`, `-id` or ` id` (excluding generic `id`, nested paths
and arrays) and a compatible string or integer type per side. PostgreSQL text/character types normalize to string, integer widths
to integer and real/numeric types to number. Mixed observed types do not qualify.
Same-source guesses are excluded. Proposals make no assertion of value overlap,
uniqueness, direction or cardinality, and are never executable query authority.
There are no hardcoded Northwind edges or generated business descriptions.

Accept, reject or reset proposals; add manual descriptions to datasets/fields.
These are application metadata edits only. Review decisions survive rebuilds only
when the evidence fingerprint is unchanged. Sample-presence counts are excluded
from that fingerprint. Graph revisions advance on builds and edits; stale versions
receive 409. Metadata revision or generation changes make the previous graph
historical until rebuilt. Disconnected sources disappear immediately from reads.
MongoDB sample omissions do not prove that a field was deleted.

All graph routes reuse existing session/origin protection and no-store envelopes:
- GET `/data-relationships`: current owned graph, stale flag and build status.
- POST `/data-relationships/build`: coalesced durable build request.
- POST `/data-relationships/review/{id}`: `{revision, status}`.
- POST `/data-relationships/annotation/{id}`: `{revision, description}`.

Read requires `tools.read`; builds/edits require `tools.assign`. Source credentials
are never decrypted by graph building. The versioned response contract is
`shared/contracts/data-sources/relationships-v1.schema.json`; existing workflow,
Google and cloud metadata contracts are unchanged. No contributor signoff is inferred.

The existing application store holds graph state, jobs, reviews and annotations.
No separate graph database or external service is needed. Builds use leased claims,
three-attempt recovery, token-checked publication and source-fingerprint validation.
Graph computation runs outside the storage transaction. Last successful graph
survives failure; Build relationships retries a failed build. One latest graph is
retained per owner/workspace; Phase 1 source history remains available.

Limits: 12,000 nodes, 2,000 relationships, 20,000 candidate comparisons, 8 MB graph
output, 1,000 characters per manual description. Coverage warnings expose limits.
The interactive map displays 24 datasets and the list displays 100 matching edges;
all datasets remain available in the explorer and filters narrow the full edge set.

Phase 2 performs no additional cloud reads, writes, LLM calls or query execution.
LLM-written descriptions, value profiling, arbitrary inferred joins and natural
language query execution remain future work. The shared demo identity limitation
from Phase 1 still applies.

## Verification and deployment

Verified and deployed 2026-10-17 UTC using an isolated production build, then
restarted the existing frontend, API and worker services. All three are active.
The previous frontend build is retained at
`.local/ui-rollbacks/relationships-phase2-20261017-220959/.next`.

The real API through the frontend proxy returned 200 for session, build and graph
reads. The worker produced revision 1 from the two existing saved snapshots:
11 datasets, 101 nodes, five declared foreign keys and five unverified proposals.
This check performed no cloud reads or review mutations. Desktop and 390-pixel
mobile checks against the deployed API rendered the graph without browser errors
or page overflow. Screenshots are in
`frontend/test-results/relationships-live-{desktop,mobile}.png`.

Validation: 37 focused backend tests, eight focused frontend tests, two fixture
browser tests, TypeScript, lint on changed frontend modules, production build,
shared contract validation and strict OpenSpec validation passed. Backend coverage
includes composite keys, owner/workspace isolation, review persistence and evidence
changes, stale revisions, disconnects, leases, obsolete publication, failed builds,
limits, HTTP envelopes and automatic profile/disconnect rebuilds.

The broader frontend suite returned 233 passing and seven failing tests. A copy
with Phase 2 removed reproduced the same seven failures in automatic-sources,
phase3-actions, phase4-generation, phase4-journey and phase7-release. Its output is
retained at `.local/relationships-phase2-baseline-tests.log`; the full suite is
not green. Browser review/annotation tests use explicit fixtures; backend tests
separately verify durable storage. Actual saved proposals remain unreviewed.
