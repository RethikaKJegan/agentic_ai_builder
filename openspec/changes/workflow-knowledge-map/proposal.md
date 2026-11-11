# Tenant-scoped workflow knowledge map and unified workflow UI

Reuse authorized ontology/version/knowledge, action-plan, composition and run
evidence APIs in a generic frontend adapter. No new ontology, execution semantics,
backend persistence or backend changes. Exact recorded references establish planned
associations; verified completed execution with exact concept/mapping evidence can
establish usage. Relevance, source names and labels never establish execution.
Unavailable historical associations and snapshots remain explicitly qualified.

Integrate Workflow, Steps, Reports, Knowledge Map and Background tabs; one Details
drawer and Validate/blue Run controls. Run retains explicit workflow approval and
exact-payload review using current APIs, roles and idempotent command handling.
Reset all loaded UI state on authenticated scope/workflow/run changes and ignore
stale responses. Do not fetch cross-tenant catalogues or persist graph payloads.
