# Design

Use the existing dedicated Subway application store and HMAC audience boundary.
Restore selected collections into two databases in a separate authenticated,
loopback-only MongoDB process. Grant the application only read access to those
collections, independently of application ownership checks. A trusted manifest pins
source IDs, databases and exact URI fingerprints; arbitrary cloud-loopback access
remains forbidden by the standard adapter.

Reuse the existing metadata, business ontology, compiler, package preparation,
Registry and runtime interfaces. Server configuration selects the Subway package
for normal chat action planning. Runtime reads require a matching immutable package,
current authenticated owner, source binding, metadata revision and generation.
All source projections are bounded. Preserve native BSON identity types and qualify
reference probes rather than generating join permissions.

Build a draft from observed schemas and explicit modelling conventions, with exact
quotations and hashed evidence. Preserve unresolved policy/acronym semantics. Do
not reuse Simpsons definitions or invent operational templates or policy thresholds.
Source records, source instance validation and approved business policy are distinct.

Keep original archives, private extraction/restore evidence and rollback inputs.
Deploy the staged store only after local source reads, compilation and workflow
execution checks. Verify both public logins, cross-client denial, desktop/mobile
pages and unchanged Simpsons ontology/source metadata snapshots and service process.
No live model calls are part of acceptance; the user chose to test chat themselves.
