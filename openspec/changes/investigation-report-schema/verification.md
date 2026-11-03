# Report schema reliability — 3 November 2026

## Observed failure

Actual saved run `investigation_run_b404047c8941baced0bb42c5` failed at `summary` with `MODEL_OUTPUT_SCHEMA_INVALID`. Complaint retrieval, linked inspection and comparison succeeded. The previous I-2026-3-068 comparison run completed. The failing objective included “Do not assess warranty” but selected and executed warranty nodes because task detection matched the word without handling the exclusion.

The original rejected model payload and schema path were not retained. The precise invalid field is therefore unknown; no claim is made that the failure was caused by a particular citation or length. The inspected provider bridge used JSON object mode, which enforces JSON syntax but not the investigation result schema.

## Implemented

- `runtime/model.py`: opt-in strict schema transport, independent of existing control protocols; schema overhead included in token reservations.
- `workflow_api/investigation_agents.py`: opts in with the exact request-specific schema and allowed citation pairs; communicates existing size limits. One bounded model call, no hidden replay or relaxed validation.
- `workflow_api/investigation_graph.py`: excluded clauses do not create required tasks; later positive clauses remain selected. Existing graph validation rejects unrelated capabilities.
- `workflow_api/business_investigations.py`: future schema failures persist a character-allowlisted schema path, without invalid payload/source values.
- `tests/test_investigation_report_schema.py`: actual CrewAI/OpenAI adapter with a local provider verifies strict format, citation constraints, token accounting, refusal of invalid output and no extra calls; exclusion regressions.
- `tests/test_business_investigations.py`: safe diagnostic persistence and nonretryable rejection.

## Verification

Additional safe diagnostic persistence checks: **2 passed**, 31 deselected, 2 warnings in 4.73 seconds (`/tmp/investigation-report-schema-diagnostics.log`).

Affected schema/model-protocol/graph/investigation/jobs suite: **82 passed, 10 subtests passed**, 10 warnings, 74.81 seconds. Log: `/tmp/investigation-report-schema-tests.log`. Shared contracts, strict OpenSpec and diff checks passed. Additional diagnostic persistence checks are recorded separately. All model tests used local fixture providers: zero paid calls or external company evidence transfers. A future real-model response can still fail for refusal, truncation, transport or semantic errors; these continue to fail visibly.

## Rollout status

A consistent private live-database backup was created at `.local/report-schema-rollout-20261103/before.sqlite3`. Idle background queues were confirmed. Importing the 47-mapping package into that restored database passed as revision 8.

Automatic approval review initially rejected the combined live service stop/restart and knowledge import. The command did not execute. The user then explicitly authorized: “Yes, deploy the tested fix and ontology update.” After that approval, the compatible backend/worker were restarted and live revision 8 was imported: `bov_b573b6114fd3e5e361fe599692a20985`. Frontend remained running and unchanged. Original ontology versions and run documents compared byte-identical using stored hashes. Company writes and deployment model calls were zero.

Normal authenticated public HTTPS sign-in, session, worker health and updated requirement registry passed; unauthenticated session returned 401. Backend, worker and frontend are active. Receipts: `.local/report-schema-rollout-20261103/public-check.json`, `preservation-after.json`, `import-live.json`; source recovery archive and consistent database backup are in the same private directory. A real-model replay of this complaint was not performed; local fixture-provider checks verified strict adapter behavior. The user can now generate and run the same objective in the UI.

After deployment, regenerate from the same objective. Prior runs remain preserved. Existing plans use the old capability fingerprint and cannot silently adopt the local evidence-refinement catalogue. Recommended objective:

> Compare complaint I-2026-3-068 with its linked inspection. Explain the recorded symptom, compare the complaint and inspection observations, and prepare a source-backed report showing differences and missing evidence. Do not assess warranty.

The fresh graph should contain comparison and report tasks, with no warranty retrieval/analysis. The live updated mapping version should resolve UC22 to “Alternator Bracket Broken.” Real missing evidence must remain visible.
