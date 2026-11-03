# Business Ontology source lifecycle and legacy retirement

## Why
The Business Ontology must own source profiling, metadata-change impact and bounded record exploration. The separate legacy Ontology workspace duplicates business terminology and currently owns shared profiling hooks.

## What Changes
Move profiling provenance into a shared source-evidence service without activating legacy ontology definitions. Add owned Business Ontology source health/schema/drift/impact APIs and read-only record exploration scoped to both configured databases. Use metadata revisions/generations and exact source identifiers; do not infer joins, verify policy or run paid models. Retire the old public tab and API routes. Preserve inert historical audit data and immutable workflow history; reject creation of new legacy selections. Existing source-query workflow authority is unchanged.
