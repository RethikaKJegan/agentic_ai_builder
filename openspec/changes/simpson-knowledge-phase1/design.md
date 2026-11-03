# Design

Keep legacy concepts/relationships/rules and their strict extraction shape compatible. Add a versioned `knowledge` extension for richer semantics and a digest over it. An explicit importer merges by stable ID into populated modules and creates a new snapshot using expected-revision CAS and owner-scoped idempotency. Saved policy heads are copied as immutable references with hashes. Read paths never initialize or import. Regeneration preserves protected definitions and extension content or fails on conflict.

Use existing reference source documents for exact citations; configured conditions identify their configuration origin and are never represented as official policy. Metadata coverage is reported as observed, missing, type mismatch or unavailable, never inferred from source examples. Direct-reference bindings remain distinct from conceptual relationships and serial candidate associations. New backend routes and a read-only CLI expose saved versions without UI work.
