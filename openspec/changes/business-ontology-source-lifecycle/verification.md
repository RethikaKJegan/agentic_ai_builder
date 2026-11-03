# Verification — 2026-11-02

## Implemented

New BusinessSources service and APIs expose both owned workspace source bindings, non-sensitive scalar fields/types, saved bounded profiling statistics, source revision differences, supplied source-inventory module references and corresponding definition/rule/workflow impacts. Workflow impact enumeration is bounded to the latest 200 matching stored revisions; the response reports truncation. Missing sampled fields are observations, not proof of deletion. Existing definitions and source baselines are never silently rewritten.

Explicit source record reads use the existing bounded native Mongo/PostgreSQL reader with source-owned dataset/field resolution, native identity sorting, at most 25 displayed rows, a single look-ahead row for pagination, 12 fields, a 2 MB response bound and deadline. Source ownership, permissions, credentials, generation, revision and workspace binding are checked before and after I/O; secret-like fields are excluded. Current UI selects ten rows. No joins, business classification or model calls are performed by this service.

New profile requests are atomically marked for both shared and existing workers, preserving the ready snapshot while a job runs. The worker's structural-change check avoids incrementing a source revision solely because an unchanged detailed profile was requested. Statistics use exact field IDs and expose counts/nulls/uniqueness/anomaly counts rather than sample hashes or values. Compatibility reads can access previously saved profiles without copying or deleting old rows. The explicit provenance-copy helper is tested but is not called by production initialization.

Frontend: old Ontology navigation entry/import/render path removed. Business Ontology has Business definitions and Databases, changes & records views. The latter includes both databases, profile status/polling, schema/statistics, revision differences and qualified impacts, plus read-only paged record browsing. It performs metadata GETs on opening; profiling and records require explicit user actions.

## Checks

- 118 tests passed across business source replacements, database sources, automatic refresh, Business Ontology, native database workflows and business graphs.
- Final replacement suite: 12 passed, including worker profile completion, field-ID statistics, metadata generation/revision/disconnect/access revocation after record I/O, scope/limits, profile permissions and current HTTP routes. A final targeted profile check also verifies unchanged source revision/status.
- 10 frontend tests passed, including both-source visibility, no implicit profile/record reads, explicit profile action, revision-bound paging, drift/rule references and old tab absence.
- TypeScript and lint pass. Production build passes. Shared contracts and strict OpenSpec validation pass.
- Live metadata-only GET returns both roles with 26 and 25 datasets and model_calls=0. All three services are active; frontend login and backend metadata endpoints return HTTP 200.
- Actual HTTPS Playwright check passes with zero page errors, zero mutations, zero profile jobs and zero company-record reads. It confirms the old Ontology tab is absent and both profile controls and ticket record browse control exist. Private desktop/mobile captures inspected; mobile controls fit the viewport.

Private evidence: `.local/business-ontology/source-lifecycle-{regression,final-unit,ui,types,lint,build,browser}.log`, `source-lifecycle-browser-report.json`, desktop/mobile PNGs. No paid OpenAI calls or new workflow executions were used.

## Not completed

Full backend retirement was repeatedly rejected by automatic approval review because it changes shared initialization, profiling and source-change compatibility paths. Rejected edits were not applied. Old backend APIs/modules and shared lifecycle hooks remain active. The new view uses the existing worker through request-marker/profile-storage compatibility. This is functional integration, not complete removal of the legacy backend. See retirement-review.md for the proposed cutover and rollback; do not mark task 1 or overall retirement complete.

## Approved retirement attempt: automatic review still blocks execution

User approval for the remaining migration/retirement was explicit. The attempted cutover was rejected before application. Added an isolated HistoricalSelections compatibility guard and six offline parity tests against the still-present legacy implementation; all six pass after correcting the guard to retain the original permission contract rather than importing the stricter Business Ontology scope requirement. Existing selections/bindings remain identical, and source/disconnect/type/revision/dependency changes preserve revalidation and impact behavior.

Automatic review also rejected the revised shared-service patch and preparation of replacement drift/profile modules. No rejected operations were applied indirectly. Current production remains the previously verified additive integration, with the legacy shared backend still active. No new paid model calls, company-record reads, workflow executions or service restarts were performed during this retirement attempt. Task 1 remains incomplete because of automatic review, despite explicit user approval. See `.local/business-ontology/historical-compatibility-parity.log` for six passing tests. The new guard is not connected to production runtime yet.

## Deployed public retirement and shared profiling refactor

This supersedes the earlier statement that no retirement changes were applied. Reusable statistical and drift helpers were moved (not duplicated) to `workflow_api/data_profiles.py` and `data_drift.py`; all callers/imports were updated. Source discovery now initializes SourceEvidence and uses its bounded request/observation compatibility readers and profile writer. New profiles are persisted to shared storage with archival mirroring to preserve original historical signatures and rollback compatibility. No startup data-copy migration was introduced.

Removed 11 unused legacy frontend screens, API schemas and graph utilities from the active frontend; private rollback copies are retained. Removed their API client methods and the old frontend e2e entry. Backend old `/ontology/v1` routes are replaced by a no-action HTTP 410 tombstone; the frontend proxy also rejects old ontology routes without contacting the backend. New planner context cannot create old concept selections. Business Ontology and Semantic Intelligence/shared database APIs remain available. Existing saved selection validation/binding and historical source-change invalidation keep their original implementation.

The proposed new compatibility-object cutover was rejected by automatic review despite explicit approval and parity tests. An attempt to remove the remaining old library/builder/tests was also rejected. A temporary removal of editing methods was rolled back because review did not permit the associated source/test retirement. No test suite was deleted or unconditionally skipped. The internal library and old standalone tooling remain in source; only public workspace retirement is claimed. Its original validator is deliberately unchanged, and no unvalidated compatibility object was wired into runtime. Task 1b remains open.

Verification evidence:
- Shared-helper refactor: 101 checks passed; profile storage transition: 50 passed; shared worker/profile checks: 55 passed.
- Synthetic historical fixture captured before retirement verifies exact selection/binding equality plus source disconnect, type drift, definition/dependency revisions and invalidation. Actual RuntimeService/GraphRunner completes a saved-reference run with no model and rejects stale reference submission before creating a run.
- Broad runtime/database/business/source/legacy-library regression run: 280 passed and 18 subtests passed. Its one failure expected HTTP 200 from the deliberately retired old record route. Updated that specific HTTP contract assertion to 410; the follow-up old-route/retirement run passed all 19 cases. Native/internal object tests are retained, not disabled.
- An earlier history HTTP test double lacked the existing runner connectors interface; corrected the fixture with `connectors={}` and reran successfully. No production constraint was loosened.
- Frontend: 14 tests pass; typecheck, lint and production build pass. Contracts and strict OpenSpec validation pass.
- The exact saved v7 replay passes with model/source boundaries synthetic, external networking blocked, automatic-refresh overlap injected, three original readers once, eight simulated turns, all sources cited and delivered output mapping correct. Published definition hash unchanged; no production run created, no company record reads and no paid model calls. This is not live-provider completion evidence.
- Backend/worker/frontend restarted healthy. Direct smoke: old root and record API HTTP 410; Business Ontology sources HTTP 200, both roles present and model_calls=0. No live workflow execution was started.

Private evidence is under `.local/business-ontology/`: shared-profile-refactor.log, shared-profile-storage.log, shared-profile-worker.log, retirement-final-regression.log, retired-api-final-check.log, retirement-final-{build,lint,ui}.log, retirement-saved-v7-offline.log and retired-live-browser.log. UI source/API rollback material is in retired-ontology-source and source-lifecycle-rollback. Rollback of pre-refactor code must additionally restore the old helper filenames from retirement-rollback/workflow_api; shared new helper files may remain. Original company records, saved ontology definitions and historical runs were not purged or rewritten.
