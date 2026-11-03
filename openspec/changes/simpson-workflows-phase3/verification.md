# Phase 3 verification — 3 November 2026

## Implemented scope

Backend-only read-only investigations compose Phase 2 evidence retrieval into typed validated DAGs with a versioned capability catalogue, model graph proposals, deterministic three-valued conditions, bounded parallel frontiers, joins, durable scoped state, leases/checkpoints, input/resume/cancel, real CrewAI analytical tasks and source-backed reports. API and terminal operations use the same service. No frontend, canvas, company writes, external messaging, business approval or deployment was implemented.

Reusable components: BusinessKnowledge/BusinessOntology immutable saved versions; BusinessRetrieval preview/execute/inspect and exact mapping/reference authority; BusinessSources current-source ownership; WorkflowStore transactions; runtime ready-frontier scheduling; LeaseHeartbeat; CrewAdapter; BoundedLLM/OpenAIModelFactory; accepted agent schema and secret/injection guards. Generic production release/registry gates remain intact. The new investigation graph is a versioned domain specification with a read-only capability allowlist, not permission to execute unapproved general production workflows.

## Baseline and Milestone A

Baseline before Phase 3 edits:

```bash
PYTHONDONTWRITEBYTECODE=1 .venv-integrations/bin/python -m pytest -q -p no:cacheprovider tests/test_business_knowledge.py tests/test_business_retrieval.py tests/test_runtime.py
```

**144 passed, 18 subtests passed**, 30 existing warnings, 77.36 seconds. Log: `/tmp/simpson-phase3-baseline.log`.

Before execution implementation, graph/catalogue/predicate/shared-scheduler verification:

```bash
PYTHONDONTWRITEBYTECODE=1 .venv-integrations/bin/python -m pytest -q -p no:cacheprovider tests/test_investigation_graph.py tests/test_runtime.py
```

**77 passed, 18 subtests passed**, 22 existing warnings, 18.11 seconds. Log: `/tmp/simpson-phase3-milestone-a.log`.

## Backend execution acceptance

Expanded Phase 3 graph/execution plus Phase 2 suite:

```bash
PYTHONDONTWRITEBYTECODE=1 .venv-integrations/bin/python -m pytest -q -p no:cacheprovider tests/test_investigation_graph.py tests/test_business_investigations.py tests/test_business_retrieval.py
```

**95 passed**, 14 existing deprecation warnings, 83.80 seconds. Log: `/tmp/simpson-phase3-focused.log`. After final cancellation-before-dispatch, input/date, capability-retry and schema-export checks, the full affected Phase 3 suite was rerun: **51 passed**, 10 existing warnings, 70.82 seconds. Command: `.venv-integrations/bin/python -m pytest -q -p no:cacheprovider tests/test_investigation_graph.py tests/test_business_investigations.py`. Log: `/tmp/simpson-phase3-final-focused.log`.

Test expectations use independently defined fixture records and IDs, including correct/unrelated/orphan inspections. Real CrewAI Agent/Task/Crew objects execute against a bounded fixture provider; these tests are not remote model calls. The fixture output is explicitly not business evidence.

Coverage includes supported capability composition/paraphrases, exclusion of unrelated actions, model graph validation and one repair, cycle/reference/type/input/branch/join/unreachable-node rejection, true/false/unknown predicates, real parallel source-read overlap using a barrier, skipped-branch joins, missing complaint, no linked inspection, invalid hours, candidate serial identity, missing policy inputs, gap reporting, typed waiting/input/resume, unverified assertions, request idempotency, durable restart and lease fencing, completed-node preservation, retryable/nonretryable failures, source drift/revocation, late authorization loss, cancellation, node/run/evidence budgets, model-output reference validation, unsupported business claims, actual CrewAI injection rejection without calling its provider, HTTP session/origin/owner boundaries, and all existing Phase 2 cases.

## Real company-source acceptance with models disabled

```bash
PYTHONDONTWRITEBYTECODE=1 .venv-integrations/bin/python scripts/check_simpson_investigation.py \
  --database .local/workflows.sqlite3 \
  --directory /tmp/simpson-phase3-live-offline-20261103
```

Passed. The real complaint `A-2022-12-013` and its linked inspection were independently queried for expected IDs, then retrieved by the actual workflow executor through Phase 2. The graph validated, found/inspection branches selected true, report completed with gaps, and original knowledge compared unchanged. Zero model calls. Planning/analysis are explicitly labelled offline; no CrewAI reasoning success is claimed from this check.

## Explicitly authorized actual-model/CrewAI acceptance

Automatic approval review initially blocked the model/live-source command because it would disclose bounded company evidence externally without explicit payload/destination authorization. No rejected command was bypassed. A separate local-only live investigation ran while the user was asked about the concrete payload and configured destination. The user explicitly authorized sending bounded mapped complaint, linked inspection and warranty-readiness evidence for `A-2022-12-013` to configured `api.openai.com`, excluding credentials, arbitrary attachments and company writes, with response storage disabled.

The first authorized attempt failed before planning because the strict graph schema's version property lacked an explicit type. That schema was corrected and exported. The subsequent authorized check ran:

```bash
PYTHONDONTWRITEBYTECODE=1 .venv-integrations/bin/python scripts/check_simpson_investigation.py \
  --database .local/workflows.sqlite3 \
  --directory /tmp/simpson-phase3-live-model-fixed-20261103 --models
```

**Passed.** Evidence: `phase3-report.json`, `workflow-plan.json`, `workflow-run.json` and `final-report.json` in that private directory.

- Actual configured model generated an **18-node DAG on its first proposal**, passing deterministic validation with no repair.
- Actual CrewAI performed **three bounded analytical model calls**: warranty evidence analysis, complaint/inspection comparison, report writing. No agent had tools, code execution, delegation or company-write authority.
- Workflow source reads used **three Phase 2 retrieval capabilities**, not new per-workflow queries.
- The independently queried expected complaint and linked inspection IDs matched exactly.
- Selected conditions: `found=true`, `has_inspection=true`; irrelevant branches were skipped and joins completed.
- Final status: **completed with gaps**. The report retained four source observations across two unique records because independent retrievals observe the complaint separately. Source IDs and observation times remain qualified by evidence request.
- The three analyses returned **25 findings**, all with validated supplied record/mapping references (5, 13 and 7 respectively). Their kinds were observations, agreements and limitations. They remain agent interpretations, not newly verified database facts.
- Two configured readiness-rule outcomes and 34 missing-information entries were retained; entries can overlap across source requests and agent descriptions and are not 34 distinct business facts.
- Physical identity remained unresolved and warranty approval was not performed.
- Analytical provider usage: **13,625 tokens**, three reserved/confirmed calls and **$0.008536 estimated cost** using existing configured rates; this estimate excludes planning cost. Active workflow execution was approximately **62.61 seconds**.
- Original live ontology rows compared unchanged. **Zero company writes, zero live application writes, zero copied credentials.** Source credentials were borrowed in memory from an owner-scoped read-only application database connection.

The one schema-rejected provider request, successful model proposal and three analytical calls are separately distinguished. Provider success in this single bounded investigation is not a guarantee for every prompt, dataset or business conclusion. Stored findings are source-reference validated, not semantically proven by the backend.

## Terminal operations

Executed `scripts/simpson_investigation.py` as separate processes against the completed actual-model store for `graph`, `validate`, `inspect` and `report`; all passed with no new model calls or company-record reads. Private files: `terminal-graph.json`, `terminal-validate.json`, `terminal-inspect.json`, `terminal-report.json` in the model acceptance directory.

Also exercised terminal `plan`, `run`, `execute` and `report` as separate processes against real read-only linked complaint data using explicitly offline planning/analysis. These use the same executor and source boundaries as the API/model run and make zero additional model calls. Outputs are `terminal-offline-*.json` in the same private directory. Exact concrete command sequences, including typed missing-input/resume, are in `docs/simpson-business-ontology/phase3-investigations.md`.

## Regression and contract commands

Complete relevant regression:

```bash
PYTHONDONTWRITEBYTECODE=1 .venv-integrations/bin/python -m pytest -q -p no:cacheprovider \
  tests/test_business*.py tests/test_investigation_graph.py tests/test_runtime.py \
  tests/test_kg_retrieval.py tests/test_database_workflows.py tests/test_database_budgets.py \
  tests/test_data_queries.py tests/test_simpson_business_sources.py
```

**683 passed, 18 subtests passed**, 94 existing deprecation warnings, no failures or skips, 475.07 seconds. Log: `/tmp/simpson-phase3-backend-final.log`. The final capability-retry/schema-export additions were subsequently covered by the complete affected Phase 3 suite: **51 passed**, 10 warnings, `/tmp/simpson-phase3-final-focused.log`. The broad run and final focused run cover the final code; these totals are overlapping and must not be added as distinct cases. Existing generic runtime branch/retry/approval tests remain included because the pure DAG frontier is now shared. Phase 2's source execution lock is now per scoped request, permitting independent reads while keeping duplicate request execution single-flight.

Executed and passed:

```bash
PYTHONDONTWRITEBYTECODE=1 .venv-integrations/bin/python scripts/validate_contracts.py
PYTHONDONTWRITEBYTECODE=1 .venv-integrations/bin/python scripts/generate_ui_contracts.py --check
/home/raf/.nvm/versions/node/v22.23.3/bin/node /home/raf/.nvm/versions/node/v22.23.3/lib/node_modules/@fission-ai/openspec/bin/openspec.js validate simpson-workflows-phase3 --type change --strict --json
git diff --check
```

New Python modules parsed successfully. Shared contracts and generated UI models did not change. Existing Phase 2 uncommitted work was preserved rather than overwritten or reverted. Live source evidence remains in private temporary directories, not checked into the repository.

## Handoff limitations

Backend scope only; no production activation/import, worker restart, canvas or deployment. Source mapping gaps `enginedetails.buildDate` and `enginedetails.engineModel` remain explicit. Policy applicability, physical identity, actual inspection completion, authorization and incorporation/exposure cannot be fabricated from the current data. Readiness is not eligibility approval.

Execution is synchronous bounded frontier parallelism, not a distributed/streaming task fleet. Input currently supports an initial exact lookup context and acknowledgment/notes for final gaps; it cannot certify missing business evidence. Interrupted/failed model calls are not automatically retried, and reserved budgets are not refunded. Already in-flight read/provider calls cannot be forcibly rolled back on cancellation, but later dispatch and persisted late results are fenced. Larger/arbitrary queries, loops, business writes and external notifications remain unavailable.

All output narrative is classified as interpretation. Reference validation does not prove semantic entailment or establish diagnosis/identity/approval. Retention/export policy for persisted evidence and the hosting model for a future background worker should be chosen before frontend integration. Complete file inventory, capability/schema details, concrete graph/report and exact commands are in the Phase 3 guide.
