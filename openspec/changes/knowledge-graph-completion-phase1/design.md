# Design

GET /data-relationships/v2 projects the current persisted graph with matching
historical snapshots, adding database/schema/entity nodes and metadata details.
POST /data-relationships/v2/mapping/{node_id} saves an owned evidence-bound
entity mapping with exact revision and suggested/confirmed/rejected status.
Mapping edits increment the existing graph revision, invalidating old plans.
The strict v1 response remains unchanged. An additive v2 contract is explicit.

Existing cross-source suggestion IDs/evidence remain unchanged. Extend the
worker's v1 graph builder with conservative same-connection Mongo suggestions:
specific matching scalar identifiers and collection-qualified references to a
target _id. Exclude generic-id pairing, arrays/mixed types and declared duplicates.
Neither user acceptance nor entity confirmation proves value overlap/cardinality.
V2 qualifications separate database declarations, metadata uniqueness, user review
and unknown facts. No confidence percentages or business assertions are invented.

Business suggestions derive from dataset names and specific identifier stems,
not hardcoded Northwind names. Users can correct the entity and role. Fingerprints
exclude sample-presence counts but include structural evidence and relevant keys.
Historical/stale views disable edits. Same transaction checks revision/ownership;
disconnect immediately hides dependent graph content. UI preserves the existing
relationship map/review screen and adds a focused v2 technical/business explorer.
