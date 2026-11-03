# Verification — ontology foundation, Section 1.1–1.6

## Scope delivered

The user limited work to ontology construction/lifecycle and requested reuse of existing retrieval, planning and execution services. Selection resolves ontology concepts and dependencies only. Replay is impact tracking, eligibility and a thin adapter to existing authorized submission, including an explicitly selected reviewed replacement revision of the same workflow. No context/recovery engine, new agent runtime or execution contract was introduced. Ordinary graph cycles remain valid; explicit acyclic predicates and merge redirects alone prohibit cycles.

| User subsection | Implementation and evidence |
| --- | --- |
| 1.1 Connectivity/catalogue | Existing authenticated Atlas/Supabase adapters and leased worker; additive bounded profile requests; catalogue permissions/freshness/coverage; typed sample and composite-key evidence; incremental signature comparison, conservative rename hypotheses and disconnect/delete impact invalidation. Read-only Simpsons and real isolated PostgreSQL profiling checked. Unsupported connector capabilities and unavailable source ownership/grants remain explicit. |
| 1.2 Layered/selective ontology | Durable scoped concepts, attributes, mappings, constraints, typed relationships, stable identities, common/domain starter drafts and organization mappings; approved version publication and bounded ontology dependency selection. |
| 1.3 Explicit/inferred knowledge | Structural FK evidence, legacy semantic inference, definition-based mapping hypotheses and statistical value-overlap observations retain distinct evidence classes, original outputs and source revision lineage. Imports do not bulk-approve previous suggestions or reviews. |
| 1.4 Scoring/validation | Versioned per-signal assessments; applicable kind/domain calibration, source-family grouped held-out examples, precision/FPR and Wilson lower-bound gates; low-risk mapping policy checks current approved dependencies, contradictions and consumer impact. Synthetic positive/negative tests validate machinery only. |
| 1.5 Review/evolution | Layer/search review UI, correction reasons/history, compatible merges, typed constraint validation, actual dependent/consumer evidence, stale review rejection, immutable publication, affected selection/workflow/run impacts and existing-service replay integration. |
| 1.6 Controlled APIs | Additive `/ontology/v1` routes, source/entity/predicate lookups, publication/export/history/metrics, current source access checks and owner/workspace isolation. Existing API schemas and shared execution contracts preserved. |

## Automated evidence

- Backend/API/runtime compatibility regression command: `.venv-integrations/bin/python -m pytest tests/test_ontology_foundation.py tests/test_data_sources.py tests/test_data_ontology.py tests/test_semantic_kg.py tests/test_data_graph_v2.py tests/test_database_workflows.py tests/test_kg_retrieval.py tests/test_runtime.py tests/test_workflow_api.py -q -k 'not test_safe_planner_errors_and_missing_runtime' --disable-warnings --maxfail=1` — **208 passed**, 24 subtests passed, one known baseline failure deselected. Log: `/tmp/ontology-regressions-final.log`.
- Final standalone ontology acceptance after additional metrics/policy coverage — **31 passed**. Log: `/tmp/ontology-foundation-final.log`.
- Isolated real PostgreSQL ontology adapter suite — **25 passed**, including a real read-only source profile query. Log: `/tmp/ontology-postgres-final.log`. The temporary cluster uses a Unix socket and a UTF-8 database, leaving existing databases untouched.
- UI/reviewer/viewer/proxy compatibility — **13 passed** across the ontology, Data Intelligence and proxy test files. Log: `/tmp/ontology-ui-final.log`.
- Playwright review → publish → concept/dependency selection — **2 passed**, desktop and 390px mobile, with no page errors or horizontal overflow. Uses isolated test signing credentials and API fixtures, not company approval. Log: `/tmp/ontology-browser.log`; screenshots under `frontend/test-results/ontology-foundation-desktop.png` and `ontology-foundation-mobile.png`.
- TypeScript and changed-file ESLint — passed. Logs: `/tmp/ontology-types.log`, `/tmp/ontology-lint-final.log`.
- `python scripts/validate_contracts.py` — shared schemas/fixtures valid. `python scripts/generate_ui_contracts.py --check` — generated UI contracts match. No shared contract files changed.
- Strict OpenSpec validation — valid, zero issues. `git diff --check` — passed.

## Existing failures and build gate

`WorkflowApiTests.test_safe_planner_errors_and_missing_runtime` expects an empty tools list, but existing database tool registration returns four tools. The same failure was reproduced against an isolated archive of unchanged HEAD. Log: `/tmp/ontology-baseline.log`. The ontology change does not alter that registration policy.

`npm run build` compiled the frontend, passed TypeScript and generated all routes. Its final command exited nonzero because the installed Next.js version's security-advisory gate raised `SecurityFatalError`. This is a build blocker, not a successful final production build. No dependency upgrade was included in this scoped change. Log: `/tmp/ontology-build.log`. Browser checks used the compiled local output successfully.

## Simpsons read-only acceptance

Used a SQLite backup of `.local/workflows.sqlite3` under `.local/ontology-foundation/simpsons-check.sqlite3`; existing application data, credentials, source schemas and workflows were not modified. Only bounded company-source reads were made. No live model call, workflow activation, email or company write was issued.

| Connection | Discovered datasets | Datasets with profile fields | Profiled fields |
| --- | ---: | ---: | ---: |
| Simpsons db2 | 25 | 20 | 405 |
| Simpsons db1 | 26 | 26 | 1,759 |
| Total | 51 | 46 | 2,164 |

After adding starter drafts and constructing candidates from saved evidence, the isolated copy contains **2,227 draft records**, including five common/domain definitions and one definition-based mapping candidate. No value-only statistical relationship satisfied the conservative candidate gates on these samples; no relationships were invented to fill that gap. No ontology version was published for Simpsons and no SME decision was fabricated.

Machine-readable report: `.local/ontology-foundation/simpsons-report.json`. The database/report are ignored local artifacts; the database file is owner-readable only.

## Current completion gates

Owner-approved descriptive publication and UI deployment are now live: 409 approved records, seven unresolved drafts. See the final deployment section below. Independent business-rule validation and representative calibration remain incomplete; task 7.3 retains those explicit acceptance boundaries. The earlier production-build blocker was cleared by a successful ordinary retry; its emitted security-upgrade notice remains recorded, with no dependency remediation claimed. The unchanged tools-list baseline assertion remains separate.

The change remains unarchived. Loaded owner-approved descriptions do not imply complete production business validation.

## Supplied application-behaviour review evidence

The user supplied two code-derived review documents and explicitly classified all answers as documented current application behaviour, not business-confirmed policy. Originals, provenance hashes, interpretation boundaries and unresolved business definitions are recorded in [the Simpsons review notes](../../../docs/ontology-review/simpsons/review-status.md). The cross-database clarification supersedes the earlier blanket claim that references cannot be resolved. No ontology records were approved or published by this documentation update; task 7.3 remains pending.


## Simpsons descriptive draft construction — 2026-10-30

Built the [readable Simpsons draft](../../../docs/ontology-review/simpsons/draft/README.md) from the two preserved review documents and saved metadata only. It is a separate company-specific draft, not a replacement for the earlier 2,227 automatically generated candidates. All source assertions remain documented application behaviour, with no inferred business sign-off.

- **416 records:** 72 concepts (9 common, 17 domain, 46 organization), 228 typed attributes, 46 provisional domain mappings, 37 relationships and 33 documented constraints. Both saved connections and all 51 collections are accounted for as business concepts or operational metadata. Eleven code-reported field bindings remain explicitly unobserved in the saved sample, with no invented field identifiers or types.
- Native record and graph validation passed. The invoice-to-billed-company reference remains distinct from ticket serial-text candidates, physical-engine identity and current ownership. Documented enforcement defects are not asserted as invariants; warranty boundary operators remain unknown and the reported warranty table is not executable approved policy. Per-record provenance retains the exact review hashes and distinguishes ID references from text associations.
- Reused the existing bounded ontology dependency selection in a pure helper. Three **unpublished previews** select 181 records for engine service history, 88 for company replacement/dispatch review and 91 for model/bulletin cut-in coverage. They select definitions/dependencies only: no company rows, actual query answers, authorized runtime manifests, workflow planning or execution. Explicit domain queries still include organization mappings; organization queries no longer pull unrelated sibling concepts solely because they share a domain ancestor. Existing approved/version/access/staleness guards remain in the production API.
- New isolated database: `.local/ontology-foundation/simpsons-domain-draft.sqlite3`, owner-only permissions, 416 persisted draft records, zero approvals or published versions and no copied connector secrets. The builder reads `.local/ontology-foundation/simpsons-check.sqlite3` through a read-only SQLite connection. Its before/after SHA-256 values match. The live application database is not opened by the final builder; its byte-for-byte stability is not asserted because the running application can independently update it. No company system is contacted. A fixture test guards against opening the live database and raises on connector I/O.
- Native APIs reject publication of the draft-only graph and selection through a nonexistent published version. No reviewer identities, calibration examples, production approvals or new replay submissions were created. No existing app process was restarted or deployed.
- New automated evidence: `.venv-integrations/bin/python -m pytest tests/test_simpsons_ontology.py tests/test_ontology_foundation.py tests/test_kg_retrieval.py -q --disable-warnings --maxfail=1` — **58 passed**, including isolated construction, input preservation, absent bindings, company/account separation, non-invariant enforcement, bounded previews and approved-version regressions. Log: `/tmp/simpsons-draft-tests.log`.
- Shared contract validation, generated UI contract drift check and strict scoped OpenSpec validation passed. `git diff --check` passed. No frontend/dependency changes were added by this construction step; the earlier final-build gate remains unresolved.

Reproducible construction: `scripts/build_simpsons_ontology.py` with the project's Python environment. It refuses to overwrite an existing database or artifact directory; use new `--database` and `--output` paths for a subsequent build. Native definitions are under `ontology/simpsons/`; exported records, provenance, source coverage, unresolved bindings and previews are under `docs/ontology-review/simpsons/draft/`.

Tasks 8.1–8.3 are verified. Task 7.3 (actual reviewed publication) and the existing task 7.4 completion gates remain open. This draft is not loaded into the running application's database or graph UI.


## Targeted technical field verification — 2026-10-30

With the expert unavailable, verified the eleven open bindings technically through existing scoped connector configurations and bounded read-only MongoDB commands. The [technical review](../../../docs/ontology-review/simpsons/technical-verification.md) links per-field machine evidence and the [revised unpublished draft](../../../docs/ontology-review/simpsons/draft-v2/README.md).

- Four fields were observed as BSON strings: `tickets.engineReplacementStatus`, `tickets.cutInNumber`, `advaced-engine-replacements.oem` and `courseschedules.requestedBy`.
- Six fields belong to three currently empty collections without database schema declarations: `failedpartanalyses.partNumber/approvedBy`, `icacapas.defect` and `workshopmanualrevisions.manual/version/approvedBy`. `claimsftps.status` was not observed in the completed targeted existence query against a nonempty collection. These seven remain unresolved; no field absence, approved business meaning or reference target is invented. Authoritative application model/schema evidence can resolve technical questions without an SME policy decision.
- Queries return only field presence and server-side BSON type groups over at most 25 matching documents, with a three-second per-operation maximum, sixty-second connector deadline and bounded collection enumeration. No source documents, reference values, credentials or raw error messages were exported. The initial multi-name metadata filter was rejected; the supported bounded listing completed all eleven final checks. Initial and final evidence are retained separately.
- The four observations enrich cloned metadata only, using the existing connector stable-ID function. Local copied snapshot revisions advance; previous value profiles do not masquerade as evidence for the newly observed fields. Each affected attribute retains the technical report hash, method, timestamp and bounded sample count, while business semantics and actual reference integrity remain unverified. Original native records and isolated draft database are preserved.
- Revised database `.local/ontology-foundation/simpsons-domain-draft-v2.sqlite3` has owner-only permissions, 416 native draft records, no copied connector secrets, no approved records and no published versions. Seven bindings remain unresolved. The three previews still select 181, 88 and 91 ontology records; approved APIs continue rejecting draft consumption/publication. Input SQLite SHA-256 values match before/after offline construction.
- `.venv-integrations/bin/python -m pytest tests/test_simpsons_field_verification.py tests/test_simpsons_ontology.py tests/test_ontology_foundation.py tests/test_kg_retrieval.py -q --disable-warnings --maxfail=1` — **68 passed**. Covers bounded read-only projection/grouping, null types, empty versus undeclared schemas, safe error reporting, rejected invalid enrichment, source immutability, persisted technical provenance/revisions, draft guards and existing ontology/retrieval regressions. Log: `/tmp/simpsons-field-verification-tests.log`.
- Shared schemas/fixtures, UI contract drift checks, strict OpenSpec validation and diff checks passed. No frontend or deployed processes were changed. Tasks 7.3 and 7.4 remain pending; this verification does not fabricate expert labels, approve policies or publish Simpsons knowledge.

This follow-up contacted company sources through read-only operations, unlike the earlier offline-only construction. No company records or schemas were modified, and no company workflow was executed. The read-only current-credential diagnostic did not modify application records or connector configuration.


## Owner-approved publication and live UI deployment — 2026-10-30

[Deployment report](../../../docs/ontology-review/simpsons/deployment.md) and [owner approval](../../../docs/ontology-review/simpsons/owner-approval.json) record the explicit authorization, scope, live URL, source preservation and verification. Native review/publication services produced the approved versions; no separate context/recovery engine or source/tool execution grant was introduced.

- Live frontend build `tWVmsTzo3PodyiFlIgA72`; current ontology `ov_d633a24f73d20898769885f779fe39c4fb929723`, **409 approved records**, seven unresolved attributes retained as drafts. Common/domain/organization layers, evidence, review history, version export and approved dependency selection are loaded and verified.
- Found and corrected missing import provenance in authorized record history. A real sampled refresh also exposed loss of previously targeted ticket fields. Added `ontology_source_observations` and bounded sample reconciliation, preserving the existing public field contract. Scoped credential fingerprints prevent evidence reuse after credential replacement. Sample omission retains prior observations with warnings; current type changes, explicit schema prohibitions, missing collections and metadata bounds remain explicit. Revalidated 58 unchanged definitions and published a new version, retaining the first stale version and original outputs.
- Real scheduled-worker refresh completed after deployment: **zero stale records**; public metadata contracts validate for both connections. Live desktop/mobile checks passed owner history, targeted evidence, unresolved draft inspection, published version export and 42-record Service ticket selection. No page errors, horizontal overflow or unexpected API mutations.
- Final checks: backend regression **227 passed**/24 subtests/one known baseline excluded; history suite **32 passed**; final observation/construction/source/ontology checks **86 passed**; source/workflow/retrieval/runtime checks **131 passed**/18 subtests; final isolated PostgreSQL **27 passed**; frontend compatibility **13 passed**; isolated lifecycle browsers **2 passed** and both live viewports passed. TypeScript, changed-file lint, shared schema/fixture checks, generated contract drift, strict OpenSpec and diff checks passed. Exact commands/logs are listed in the deployment report.
- Isolated production build succeeded on the ordinary retry and was activated with prior assets retained. The initial installed Next.js security-upgrade notice was not treated as authority for an unsolicited dependency upgrade, and security remediation is not claimed. Backend, frontend and worker services are active. The earlier 'not restarted/deployed' statements describe historical stages only.
- A full owner-only application backup and prior frontend/backend sources are retained. Connector identities/encrypted credentials, legacy reviews, workflow revisions and runtime runs compared unchanged. No company record/schema writes or workflow executions were performed. Local catalogue/ontology/audit/version/selection state changed as authorized.

Tasks 10.1–10.3 and final verification task 7.4 are satisfied. Task 7.3 remains open for complete business acceptance: owner-approved descriptive publication is verified, while the seven unresolved bindings, intended business rules and independent production calibration are not fabricated. No archive was performed.


## Business graph presentation correction — 2026-10-30

Owner feedback identified the technical JSON/record-management screen as the wrong default presentation. The [business graph release](../../../docs/ontology-review/simpsons/graph-ui.md) now opens directly to a connected, labelled SVG concept diagram backed by the same foundation API. Default overview: six concepts and nine actual stored relationships; all layers: 72 concepts. Readable inspectors show meanings, fields, constraints, source names and explicit unresolved states. Candidate links remain distinguished; no row instances, invented relationships or confidence values were introduced. Review/publication controls remain accessible in a separate management mode, with JSON restricted to optional advanced editing/exports.

Validation: **19 UI tests**, TypeScript, scoped lint, production build, **two isolated management lifecycle browsers**, captured-real-ontology desktop/mobile graph checks and live authenticated desktop/mobile graph checks passed. Live checks additionally exercised dragging, zoom/fit, search, pending-field explanation, readable node/edge inspection and layer switching. No page errors, page overflow or unintended API mutations occurred. Existing shared contract validation/drift and strict OpenSpec/diff checks passed.

Frontend-only activation: `zCmmvYM2O8OO6XuTavX-9`; retained 85 prior assets and rollback. Backend/worker PIDs unchanged. Before/after and post-browser hashes confirm unchanged ontology records, approval events, versions, selections, evidence observations, connector credentials, workflow revisions and runtime runs. Current ontology version and 409-approved/seven-draft boundary are unchanged. Source company data was not modified. Logs: `/tmp/ontology-graph-tests-final.log`, `/tmp/ontology-graph-types-final.log`, `/tmp/ontology-graph-lint-final.log`, `/tmp/ontology-graph-build-responsive-final.log`, `/tmp/ontology-graph-management-browser-final.log`, `/tmp/ontology-graph-browser-final.log`, `/tmp/ontology-graph-live-browser-final.log`. Private machine evidence, screenshots and rollback: `.local/ontology-foundation/graph-release/`.

Tasks 11.1–11.2 are verified. Full business acceptance/calibration gate 7.3 remains explicitly separate; no archive or business-data mutation was performed.
# Source-backed record explorer extension — 31 October 2026

Owner explicitly authorized the architecture design implementation and subsequently approved the live service pause/restart and technical republication. See [release evidence](../../../docs/ontology-review/simpsons/object-explorer.md). Native object identity, permission-filtered scalar projection, bounded exact search/pagination, detail and one-hop bidirectional reference/candidate expansion reuse the existing query reader and connector boundary. No new context, query-planning, execution or recovery engine; existing shared execution contracts and concept/dependency-only task selection remain authoritative.

117 backend regression checks passed, followed by 51 reader/query checks including the final BSON decimal filter case; 41 workflow/retrieval regressions passed and 27 PostgreSQL fixture cases skipped for absent independent configuration. 18 frontend/proxy tests, TypeScript, scoped ESLint, isolated production build, shared contract fixtures/drift and strict OpenSpec/diff checks passed. Desktop/mobile record-browser checks against captured real projections and the live application passed, alongside the two existing management lifecycle browsers. Browser checks block all non-GET backend requests except the two explicitly read-only object endpoints; no writes/workflow submissions were attempted.

Loaded frontend `Luy8ChhV-XPO0tJlhuS7D`, ontology version `ov_3c9e855088f5ac678e11127661eae182b5189707`. Stale evidence was not bypassed: 150 existing approved records were technically revalidated through native correction/publication methods after proving stable collection/key/constraint/field bindings. All business descriptions/properties remain unchanged; 409 approved and seven draft records remain. `tickets.hmr` retains datatype unknown and mixed numeric observations, so it is excluded from scalar browsing. No SME identity, business policy, calibration or physical-engine ownership was fabricated. Source schemas and records were read only. Existing selections/impacts follow native invalidation, while workflows, credentials and run records were preserved during paused activation. Normal existing scheduled processing resumes afterward. Previous application database/build/source and verification artifacts remain private for rollback. Overall business acceptance task 7.3 is still open.

