# Verification — 12 November 2026

This change makes dataset resolution deterministic before model routing and preserves saved source contracts. The existing 192 production demonstration records and their ontology are reused; no second production dataset is generated.

## Implemented source resolution and lifecycle

The dedicated Subway configuration enables automatic defaults. An ordinary request resolves the active, validated registry entry, and persists dataset ID, numeric revision, immutable manifest hash, associated ontology/rule version, query namespace and registry generation in the Overview intent and workflow. Compilation and bounded planner corrections consume that same contract. Saved workflows and recurring consent do not follow later pointer changes. Adaptive run-local revisions copy the source context; worker recovery verifies the original receipts against their pinned source.

Explicit historical requests use the restored source; explicit retained demo versions remain supported. Requests requiring real current operations return a source limitation. Invalid, unavailable or inactive defaults are not substituted with fabricated or historical records. Future registration validates the compatible nested schema, native identity, relationships, finite arithmetic, invoice/item/payment consistency, ontology and typed rule compatibility. Activation is atomic and follows numeric revisions. The current runtime accepts the existing reviewed modeled policy/schema; materially different policy or schema requires a reviewed runtime change.

Lifecycle management uses the existing application store, original demo data tables and a scoped workspace setting. Append-only audit and verified archives are retained. Cleanup scans saved source dependencies and deletes only inactive, retired, unreferenced non-base demo operational rows after archiving. Restore validates the archive. Protected history, credentials, evidence, shared ontology and backups are never deleted by this cleanup.

## Inventory and cleanup outcome

Read-only production inventory found **one** published demonstration dataset, `subway-demonstration-v1`, revision 1, **192 records / 18 collections**, SHA-256 `e29d250b172a64701e3af577a8fa4c5db77d5662e68f3c1ddfd1bfeda128f80c`.

Retained: v1 (active/referenced and the base schema dependency), both genuine historical source registrations, all existing ontology/package versions, saved workflows/runs/receipts/schedules, earlier provider-rehearsal stores and backups. No obsolete published production version qualifies for retirement or deletion. **Production versions retired: zero. Production versions deleted: zero.** Test-only versions exercise upgrade, retirement, protected cleanup, verified archival and restore; they are not installed into production. Historical runs, audit and backup files were not treated as disposable datasets.

## Automated verification

All commands use `PYTHONDONTWRITEBYTECODE=1`, the repository `.venv-integrations/bin/python`, and `pytest -q -p no:cacheprovider`.

| Suite | Result | Execution boundary |
| --- | --- | --- |
| Lifecycle / recovery / Knowledge Map | **45 passed, 0 failed, 0 skipped** | Exact isolated candidate |
| Wider affected acceptance | **80 passed, 0 failed, 0 skipped** | Checkout with the final scoped implementation; not claimed as a separate exact-artifact 80-test run |
| Existing Simpson regressions | **46 passed, 0 failed, 0 skipped** | Exact candidate; test stores only |
| Calendar / Gmail / Subway authentication | **22 passed, 0 failed, 0 skipped** | Exact candidate; controlled external transports |
| Adaptive / evaluator / usage / autonomy | **80 passed, 0 failed, 0 skipped** | Exact candidate |
| Existing Knowledge Map frontend domain tests | **29 passed, 0 failed, 0 skipped** | Existing frontend, unchanged source/build |

The counts overlap and must not be added together. Canonical contracts, generated UI-contract comparison, strict scoped OpenSpec and whitespace checks passed.

Exact-candidate lifecycle command:

```bash
/home/raf/agentic-ai-builder/.venv-integrations/bin/python -m pytest -q -p no:cacheprovider \
  tests/test_subway_dataset_lifecycle.py tests/test_subway_dataset_runtime.py \
  tests/test_workflow_ontology_usage.py
```

The wider affected acceptance added `test_subway_persistent_demo`, `test_subway_persistent_demo_runtime`, `test_subway_procurement_runtime`, `test_subway_automations`, and `test_workflow_knowledge_isolation` to the lifecycle and runtime tests.

Separate Simpson command:

```bash
python -m pytest -q -p no:cacheprovider \
  tests/test_simpsons_client_isolation.py tests/test_simpsons_ontology.py \
  tests/test_simpsons_field_verification.py tests/test_simpson_business_sources.py \
  tests/test_simpson_lifecycle.py
```

Separate external-integration command:

```bash
python -m pytest -q -p no:cacheprovider \
  tests/test_calendar_action_routing.py tests/test_slack_gmail.py tests/test_subway_client_auth.py
```

Separate adaptive command:

```bash
python -m pytest -q -p no:cacheprovider \
  tests/test_investigation_evaluator_protocol.py tests/test_live_evaluator_wrapper.py \
  tests/test_conditional_investigation_evidence.py tests/test_paginated_query_evidence.py \
  tests/test_automation_usage_settlement.py tests/test_subway_autonomy.py
```

Frontend command: `frontend/node_modules/.bin/vitest run src/domain/workflow-knowledge.test.ts src/domain/knowledge-context.test.ts`, run from `frontend`.

### Targeted safety evidence

- Ordinary investigation, summary and assessment prompts resolve automatically before models.
- Numeric version 10 wins over 2 through explicit activation; invalid/inactive versions never become defaults.
- Activation between Overview routing and compilation retains the first saved source contract.
- A workflow waits after a verified assessment, v2 activates, the worker/Registry caches are recreated, the original workflow resumes and replans, and the completed assessment receipt remains byte-for-byte unchanged on v1.
- A schedule approved before v2 activation executes a later durable occurrence using v1, while new requests resolve v2.
- Legacy historical workflows without demo pins keep historical sources; legacy explicit v1 workflows retain their original descriptor and query namespace.
- Cross-tenant access, missing approval authority, invalid financial/reference/nested-schema data, source/ontology/manifest tampering and foreign source pins are rejected.
- Cleanup retains active/base/referenced versions, archives only unreferenced retired test versions, restores from verified archives and retains ontology/audit/history.
- Knowledge Map actual usage includes selected dataset ID/revision, fields, typed rule outcomes and receipt references. Existing frontend renders these evidence descriptions.

Initial test attempts combining recovery with a newly reconstructed original schedule exposed a test-fixture Registry definition mismatch. The final test correctly creates the approved schedule before the source upgrade, then verifies recovery and the existing schedule separately against their immutable reviewed definitions. No Registry or approval rule was relaxed. An initial genuine ordinary prompt requested an unnecessary policy clarification; demo-only routing guidance now makes the supplied modeled policy explicit. These exploratory attempts are not counted as passing acceptance.

## Genuine configured-provider application acceptance

These journeys used the actual configured OpenAI transports, normal Overview API, canonical save/validate/approve/execute APIs, existing Registry, CrewAI/GraphRunner, deterministic query/assessment engines, adaptive evaluator and report actions. The store is a consistent isolated Subway application copy with the persisted demo data. No provider/model factory or source response was replaced. No real external action or company-source write was submitted.

| Ordinary user prompt | Actual result |
| --- | --- |
| `Investigate purchase-order discrepancies and prepare an evidence-backed report.` | Completed `run_a65a6859364948aa9b983b8761e9b262`; eight modeled POs, related records, 470 deterministic outcomes and labeled report |
| `Summarize purchase-order counts and values by status and currency.` | Completed `run_94afe95d23674de2bd280fb1d998ba3f`; five complete aggregate groups, eight records and exact source-grain monetary sums |
| `Check purchase orders for approval issues, budget problems and invoice discrepancies.` | Completed `run_c3f60804ece04c2181ad2197fb33788d` through registered deterministic assessment and report |
| Daily procurement investigation with explicit UTC recurrence, no dataset phrase | Completed actual clock-due occurrence `run_d1f23faf459b4824b21206deb8985641`; recurring consent and source pin persisted at creation |

The summary returned status/currency-code groups exactly: approved/1: count 4, value 11800; approval_in_progress/1: 1, 3540; rejected/1: 1, 3776; approved/2: 1, 4012; approval_in_progress/2: 1, 4248. The report retained codes 1 and 2, did not invent their currency meanings and did not combine currencies.

The procurement assessment outcomes remain **448 PASS, 15 FAIL, one INSUFFICIENT_EVIDENCE and six NOT_APPLICABLE**. Failing checks and missing approval-stage evidence are deliberate modeled findings, not execution failures or business approvals. All reports identify modeled records and illustrative policies.

A separate genuine-source audit confirmed automatic demo count **8**, explicit restored historical count **43,439** with historical-snapshot attestations, registered RAG retrieval of the modeled policy source, and dependency inventory. It performed no company-source writes. Rehearsal schedules are confined to the isolated application copy; live schedules were not edited.

## Files and evidence

Runtime/API changes: `workflow_api/subway_dataset_lifecycle.py`, `subway_demonstration.py`, `subway_queries.py`, `overview_automation.py`, `action_plans.py`, `live_providers.py`, `workflow_adaptive.py`, `workflow_knowledge.py`.

Tests: `tests/test_subway_dataset_lifecycle.py`, `tests/test_subway_dataset_runtime.py`. Documentation: `docs/subway-dataset-lifecycle.md`, updated `docs/subway-demonstration-data.md`, and this OpenSpec change. Shared contracts, frontend source, Simpson code and historical ontology/data files are unchanged.

Private evidence: `.local/subway-dataset-lifecycle-20261112/`, including inventory, test logs, genuine Overview/workflow/run/receipt artifacts, release manifest, consistent backup, source audit, deployment/preservation checks and hosted acceptance. Credentials and operational payloads are not reproduced here.


## Actual deployment and public HTTPS acceptance

The user authorized rollout after verification. Only `agentic-builder-subway` restarted, at **19:14 IST on 12 November 2026**. Its effective systemd WorkingDirectory and `/proc/<MainPID>/cwd` identify the exact immutable release recorded in `deployment.md`. The original 192 records, their immutable dataset header and the full existing ontology versions are byte-for-byte retained. The new lifecycle metadata selects v1; no second production dataset was created and no production version was retired or deleted.

At **19:16 IST**, the public website completed the exact ordinary prompt `Investigate purchase-order discrepancies and prepare an evidence-backed report.` No dataset name/version or special phrase was present. The normal HTTPS Overview, workflow compilation, draft save, validation, approval and execution APIs all returned 200, and the deployed background workers completed the run. Source authority records `selection: automatic`, dataset v1/hash, ontology `bov_subway_demonstration_v1` and rule version `subway-demo-procurement-v1`.

Completed run: `run_2f9d1d61cb2e42c1897529e8eb2b0533`. [Open the report](https://praxi.bellcorpstudio.com/app/workflows/investigate?connected=1&composition=composition_71e6729c7487d089f03f3e05&run=run_2f9d1d61cb2e42c1897529e8eb2b0533) after signing in as Subway. The verified assessment selected eight orders and 184 related records, emitted 470 deterministic rule results, and persisted 181 mapped field/concept usage entries. Reporting carried those usages forward and labeled the data/policy as modeled. No source write, email, Calendar mutation or other external action was submitted.

Authenticated public session, tools, worker-health, query availability and lifecycle inventory checks passed. Anonymous login/app/session boundaries remain 200/307/401. A public request for real current Subway operations returns 409 `SUBWAY_CURRENT_SOURCE_UNVERIFIED` before a model call.

After hosted acceptance, a fresh comparison to the consistent pre-deployment backup verified every existing protected row across revisions, runs, events, compositions, source/Google connections, snapshots, ontology/package versions, demo records/manifest, query/assessment receipts, schedules, workspace settings and ontology workspace/document/event tables. Only routine source-profile timestamps are normalized. Added workflow/run/composition/history belongs solely to this authorized Subway acceptance. Source-key hash, active/previous/shared code hashes and unrelated service PIDs—including Simpson—remain unchanged. See private `final-preservation.json` and `hosted-acceptance.json`.

Remaining boundaries: the default is modeled demonstration evidence, never current actual operations. No live external delivery was tested. New materially different schemas/policies require a reviewed runtime change; existing workflows/schedules remain pinned and require normal revalidation/approval to change source. Test-only cleanup/version/recovery exercises were not applied to production history. No follow-active source updates are inferred for approved schedules.
