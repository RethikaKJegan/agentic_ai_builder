# Phase 2 verification — 3 November 2026

## Scope and current status

Implemented backend-only saved-ontology prompt resolution, scoped concept indexing, deterministic/optional constrained-model interpretation, fact providers, fixed-point dependency closure, exact mapping selection, owner-scoped server plans, typed read execution, evidence, authenticated HTTP routes, terminal operations and existing planner/metadata integration. Phase 1 authoring artifacts and historical versions remain intact. No frontend, CrewAI orchestration, operational actions or deployment is included.

The request vocabulary is bounded and documented in `docs/simpson-business-ontology/phase2-retrieval.md`. This is not arbitrary natural-language-to-SQL or complete business-decision intelligence. Missing policy applicability, physical-engine identity, activity completion, authorization, incorporation and exposure evidence remain explicit.

## Baseline and executable backend acceptance

Phase 1 baseline before implementation: **43 passed**, 10 existing deprecation warnings, 25.89 seconds. Log: `/tmp/simpson-phase2-baseline.log`.

Final targeted Phase 2 and metadata-index acceptance:

```bash
PYTHONDONTWRITEBYTECODE=1 .venv-integrations/bin/python -m pytest -q -p no:cacheprovider tests/test_business_retrieval.py tests/test_kg_retrieval.py
```

**74 passed**, 14 existing deprecation warnings, 46.02 seconds. Log: `/tmp/simpson-phase2-final-acceptance.log`. This includes 46 Phase 2 cases and 28 existing/new KG cases. Earlier complete relevant regression snapshot: **574 passed**, 74 warnings, 390.57 seconds, `/tmp/simpson-phase2-broad.log`. **Final complete relevant regression: 579 passed**, 74 existing deprecation warnings, no failures or skips, 387.63 seconds. Log: `/tmp/simpson-phase2-backend-final.log`. This final run includes the finished implementation and all 46 Phase 2 cases plus the new KG required-source case.

Tests use independently specified source records in isolated stores. Coverage includes aliases/paraphrases, correct/unrelated/orphan records, exact complaint/report references, native ObjectId/string distinctions, bounded numeric filtering, invalid versus zero hours, nested dependencies, cycles, registered/unknown conditions, context limits, unavailable model/build fields, replacement and recurrence evidence, unknown policy revisions, model-output tampering and fallback, state/activity distinctions, server plan tampering, owner isolation, request idempotency, historical versions, preview expiry, stale metadata/credentials/ownership, late permission revocation, deadlines, byte/result limits, authenticated HTTP operations and foreign-origin rejection. The real source-reader dotted projection implementation is tested with a native Mongo cursor fixture, rather than only mocking the service layer.

Existing query, ontology, graph, policy, identity, compiler, rule, metadata, planning and workflow tests are included in the broader command:

```bash
PYTHONDONTWRITEBYTECODE=1 .venv-integrations/bin/python -m pytest -q -p no:cacheprovider tests/test_business*.py tests/test_kg_retrieval.py tests/test_database_workflows.py tests/test_database_budgets.py tests/test_data_queries.py tests/test_simpson_business_sources.py
```

## Contracts and static checks

```bash
PYTHONDONTWRITEBYTECODE=1 .venv-integrations/bin/python scripts/validate_contracts.py
PYTHONDONTWRITEBYTECODE=1 .venv-integrations/bin/python scripts/generate_ui_contracts.py --check
/home/raf/.nvm/versions/node/v22.23.3/bin/node /home/raf/.nvm/versions/node/v22.23.3/lib/node_modules/@fission-ai/openspec/bin/openspec.js validate simpson-knowledge-phase2 --type change --strict --json
git diff --check
```

All passed. New Python source parsed successfully. No shared contract file or generated UI model changed.

## Real Simpson read-only verification

Executed the final implementation with:

```bash
PYTHONDONTWRITEBYTECODE=1 .venv-integrations/bin/python scripts/check_business_retrieval.py \
  --database .local/workflows.sqlite3 \
  --directory /tmp/simpson-phase2-verified-20261103 --live-sources
```

Passed. Fresh isolated ontology version: `bov_b578217f868fb99066d7f73074460559`. Phase 1 saved revision 6 was imported as isolated revision 7; its 79 concepts, 45 relationships, 23 parent links, 36 mappings and four pinned policy revisions were preserved. Existing Phase 1 integration storage was not overwritten.

Expected native IDs were queried independently from the real sources before executing resolver plans. Exact comparison results:

| Check | Independently expected | Resolver returned | Evidence completeness |
| --- | --- | --- | --- |
| Linked inspection | 1 ticket, 1 linked report | Same exact source IDs | Incomplete: actual inspection activity completion unavailable |
| Reported serial complaints | 2 tickets | Same exact source IDs | Complete for the exact scoped source read |
| Two-database history | 0 tickets, 1 invoice, 1 QA record | Same exact source IDs | Incomplete: cross-source identity remains a candidate |

The first live check exposed a pre-existing `QueryReader.objects` byte-accounting defect for Mongo dotted scalar projections: the driver returns a nested document and the scalar packer rejected the nested structure. The source reader now budgets exactly the selected scalar paths while retaining native rows for reference matching. Independent driver/fixture tests and the repeated live check verify this change.

Both existing company connections were read-only. Original live ontology rows compared unchanged. Zero company writes, zero live application writes, zero copied credentials and zero model calls in these checks. Credentials were borrowed only in memory from an owner-scoped read-only application database connection. Source values and identifiers are retained only inside the private selected evidence directory, not in this report.

Reports: `/tmp/simpson-phase2-verified-20261103/phase2-report.json`, `linked_inspection-preview.json`, `linked_inspection-evidence.json`, `serial_complaints-evidence.json`, `two_source_history-evidence.json`. Sampling and per-request limits prevent claims of complete company-database coverage.

`enginedetails.buildDate` and `enginedetails.engineModel` remain unavailable in the saved metadata. They were not fabricated, aliased or projected. Equal serials did not merge physical engines.

## Actual terminal interface

Ran `scripts/ontology_retrieval.py` as separate processes for preview, execute and inspect using a real linked complaint in an isolated store. Preview was ready, execution returned the correct two linked records, and inspection returned the saved evidence and original pinned version. No browser, frontend or agent framework was used. Repeated this separate-process terminal check successfully on the final implementation and final isolated version `bov_b578217f868fb99066d7f73074460559`: preview ready with zero company reads, execute returned the two expected linked records, and inspect returned exactly the persisted evidence. Final private outputs: `/tmp/simpson-phase2-verified-20261103/terminal-preview.json`, `terminal-execute.json`, `terminal-inspect.json`. Exact reproducible commands are in the Phase 2 backend guide; the guide discovers a real existing sample instead of claiming illustrative E123/C123 values exist in Simpson.

## Configured-model interpretation evaluation

Mocked-provider tests verify strict output schema, candidate-ID constraints, rejected invented fields/concepts, identifier placeholder handling and deterministic fallback. Model evaluations are separate from deterministic record correctness.

Three initial configured-model calls exposed two overly cautious ambiguity outputs and one safe deterministic fallback. None queried company records or created an executable operational action. The interpreter instructions were corrected to distinguish retrieval intent from inherent unknown identity, and to supply locally parsed identifier roles/task/filter context.

Three final configured-model calls all passed:

| Prompt | Task | Model result | Preview |
| --- | --- | --- | --- |
| Find service issues for motor E123. | complaints | Validated | Ready |
| Show inspection findings for complaint C123. | inspection | Validated | Ready |
| Find previous cooling-related breakdown reports. | complaints | Validated | Ready |

Final calls took approximately 5.15, 3.05 and 3.61 seconds. Each used one configured-model call, bounded saved concept metadata and example-question identifiers replaced by placeholders. Zero company-record queries; zero retrieved company records sent. Responses storage and automatic retries were disabled. These three cases are a small evaluation, not a universal prompt-understanding guarantee. Six total real interpretation calls were made across initial/final evaluations; no model-generated source query was executed.

Private evidence: `/tmp/simpson-phase2-final-20261103/model-evaluation.json` (initial), `model-final-evaluation.json` and `model-final-preview-0.json` through `model-final-preview-2.json` (final).

## Handoff and remaining boundaries

The existing planner consumes grounded context and required owned dataset IDs without altering its business-planning-v1 contract or widening execution permissions. Preview does not read company records. Only a saved owner-scoped request ID can execute, with current authority/source stamps and immutable knowledge/hash checks. Model outputs cannot supply fields, joins, sources or permissions.

The live application's latest saved knowledge remains unchanged; the Phase 1 extended version used here exists in isolated integration storage. Production activation/import is not claimed. No backend/worker was restarted and no workflow was approved, published, activated or executed.

Current limitations are explicit: bounded first-page text/numeric searches; no pagination continuation; no arbitrary date/OEM/model/priority predicates, aggregates or rates; no unsupported joins; no verified physical-engine merges; no automatic warranty decisions; no completeness claim for missing incorporation/exposure/mechanism facts. Candidate company/model context remains unverified when suitable exact mappings are absent. Versioned schema changes need new previews; mappings are not silently rewritten under existing requests.

Phase 3 remains workflow construction/orchestration and controlled operational actions, with frontend integration and deployment separate. See the backend guide for changed files, editable registries/rules/mappings, supported request types and exact commands.
