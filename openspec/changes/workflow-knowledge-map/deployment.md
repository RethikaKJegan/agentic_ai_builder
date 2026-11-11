# Hosted Knowledge Map UI — 11 November 2026

Live at https://praxi.bellcorpstudio.com/ with build
`LwjiQ6zW7R_v9SiWeofP8`, activated at **2:44 PM India time** after explicit user
approval. Workflow, Steps, Reports, Knowledge Map and Background tabs, consolidated
Details and Validate/blue Run controls now use the existing workflow interface.

The generic graph uses authorized existing ontology and workflow APIs. It supports
workflow/full views, business module groups, search, step filtering, pan/zoom,
concept definitions, source mappings and conservative evidence states. Older
workflows with insufficient recorded links remain explicitly qualified.

Verification: 581 frontend tests, 139 backend authorization/workflow tests, six
production-artifact browser journeys, four actual hosted account/browser journeys,
types/lint/build/contracts/specification checks and live cross-account denial.
See [full implementation and verification report](verification.md).

Only the frontend restarted. Backend/runtime/planner/Registry/shared-contract file
hashes and backend/worker process IDs remained unchanged; configuration hashes were
preserved. No backend persistence, database migration, model call, provider write,
workflow submission or approval was introduced by verification. Rollback artifact
and prior static chunks are retained privately under
`.local/knowledge-map-ui-20261111/`.
