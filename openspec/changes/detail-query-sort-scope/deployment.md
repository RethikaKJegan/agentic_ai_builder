# Detail query sorting — deployed 12 November 2026

Release `detail-sort-20261112-39a1504efca0` is deployed to Subway at https://praxi.bellcorpstudio.com/.

The reported run `run_bc7d6879e219459fa210e8a77f4ae478` failed at plan_comparison before any source read or Calendar creation. Its saved safe diagnostic is AGENT_OUTPUT_INVALID, field query, validation rule SUBWAY_QUERY_INVALID: Sort columns must be selected output columns. The approved workflow retained tool.extension_calendar_create; that action was pending. The rejected raw query was not persisted, so its exact field list and sort ID are unknown.

Detail queries may now sort by an authorized base-source field independently of displayed columns. Sort fields pass the same source-scope checks and are included in read/provenance requirements; returned columns remain exactly the requested projection. Sorting still happens before pagination across the full matching source. Unknown/out-of-scope fields and joined-field detail sorts remain rejected; aggregate sorts must still reference returned group IDs or metric labels.

The model response schema constrains detail sort identifiers to supplied catalogue field IDs, preventing invented sort labels. Model guidance explains the distinct detail/aggregate sorting rules. No prompt-specific field IDs, amounts, vendors or business rules are hardcoded; no approval, source authorization or currency checks were removed.

Verification: 40 tests passed directly from `.local/workflow-ui-release-20261112/app`, covering real CrewAI planning-to-executor execution, model-boundary validation, complete-scan ordering/pagination, unchanged result columns, left joins/unmatched coverage, aggregate behavior and rejected sort scopes. Canonical contracts, generated UI contracts, strict OpenSpec and whitespace checks passed. Hosted authentication, worker health, account isolation, protected source/Google credentials, ontology, knowledge packages, automation and history preservation checks passed. Only Subway restarted; other backend PIDs and frontend build were unchanged. No real source investigation or Calendar/email action was triggered for verification.

Private evidence, source rollback and database snapshot: `.local/detail-query-sort-20261112/`. Generate a fresh workflow with a future Calendar time; the failed historical run remains preserved. This verifies the observed sort-validation failure class, not a replay of the unrecorded rejected query or a completed live Calendar event.
