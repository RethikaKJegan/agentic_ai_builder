# Simpson Business Ontology

## Why
The owner supplied an enterprise ontology blueprint and Simpson backend source and approved a separate Business Ontology subsystem. The existing source-backed Ontology tab is an independent implementation and must be preserved. Delivery proceeds in reviewable chunks.

## What Changes
- Chunk 1: bounded read-only source verification, source-code mapping inventory, and explicit evidence gaps.
- Chunk 2: isolated Business Ontology storage/API/UI foundation and versioned artifacts.
- Later chunks: five ontology layers and twelve business modules; existing OpenAI-assisted extraction; deterministic JSON-to-OWL/RDF and SHACL compilation; automated semantic validation; rule catalogue; mapped knowledge graph; intelligence and monitoring.
- No Bedrock dependency or SME ontology validation interface/approval gate. Operational business approvals remain modeled.

## Impact
Chunk 1 adds documentation, a standalone diagnostic script, fixture tests, and aggregate-only evidence. It does not instantiate the application, modify existing ontology records, change shared contracts, call a model, run workflows, or write to company databases. Future application changes require their own chunk verification.
