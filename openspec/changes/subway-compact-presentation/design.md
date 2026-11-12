# Design

The hosted ontology list contains a valid Subway demonstration ontology at revision 0; the frontend currently rejects it with positive-only revision validation. Knowledge Map must consume an authorized pinned snapshot without making its availability depend on unrelated workspace list parsing. Missing pins must never be silently relabeled as the current version.

Presentation replaces verbose demonstration-source statements with a short Demo data label. Stored source definitions, dataset hashes, policy/rule provenance, receipts and prior executions are retained. Only newly prepared content is normalized before approval; reviewed external payloads are never rewritten at dispatch. UI presentation copies must not be submitted as execution contracts. Tests cover tenant scoping, numeric/currency preservation and each output type.
