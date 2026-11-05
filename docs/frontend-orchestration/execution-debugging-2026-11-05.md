# Workflow execution debugging and deployment — 5 November 2026

## Result and scope

Both supplied failures were recovered from the application database and their earliest failing validation was reproduced. Three separately authorized investigations then completed with the actual configured OpenAI planner/model, Registry, CrewAI, GraphRunner, mapped company-source reads and isolated persistence. Their saved reports were verified through the actual frontend/API on desktop and mobile. No real Gmail, Sheets or Calendar actions were performed.

The user explicitly requested deployment, superseding the attached brief's no-deployment instruction. The brief explicitly prohibited OpenSpec, superseding the repository's OpenSpec requirement; this conflict was reported before implementation. No OpenSpec workflow/artifact was created. Live model evidence transmission to `https://api.openai.com` and saved-login transmission to `https://praxi.bellcorpstudio.com` were separately approved in this conversation after automatic review initially rejected those checks. The live-model scope was limited to the three approved investigations; missing-record reproductions used controlled model responses.

## A. Verified root causes

| Diagnostic | Owned composition / run | Earliest failure |
| --- | --- | --- |
| `trace_84177da89daa463d879c3667b6b45fc8` | `composition_1fb9b938eb08ba719eab7635` / `run_616d4af192894eaa8e6cfe8d0d13ed96` | Complaint specialist `ca_56ee70a954d61489f50a66cf`, task_1, finished its successful read with an uncited `observation` about retrieval coverage. `validate_analysis` rejected it with `INVESTIGATION_AGENT_REFERENCE`. |
| `trace_ceb5b3a886ad45c3a948d6478b247cd0` | `composition_f8ef624acd9ec0264c363086` / `run_fe68a2541b9e4e4885005917b829bf7a` | Inspection specialist `ca_fad812fd5f349d6fbadaa9fd`, task_2, finished its successful read with an uncited `observation` about zero returned records. The same validator rejected it. |

The first original goal requested complaint C123, its linked inspection, comparison and an evidence-backed report. The second requested complaint C124, symptoms, operating hours/status, invalid/missing values and linked inspection availability. These fixture-style identifiers returned no matches in their configured-source preparations; they are not established live complaint records.

Both compositions belonged to `local-workspace` / `local-builder`, used model planning and resolved all four configured specialist IDs (complaints, inspection, comparison, report) plus their master. Both used ontology `bov_b573b6114fd3e5e361fe599692a20985`, knowledge digest `fc63dd0106b7a6ac6ed3629b28031650540bcea5226d5f805beafd2dfe7002d1`, mapping digest `250bbf7e570f3885568ad611ad290bd118e0bf4a8daf60163e76da88fd3e9b45`, and service source metadata revision 10. Preparation IDs were respectively `preflight_aa2373cc777a0cfaf0b0b8eb` and `preflight_69e2ec116cd174f6cbee4d1d`.

The actual tool inputs were the corresponding preparation ID plus `task: complaints` or `task: inspection`. The registered `business_retrieve_evidence` adapter enforced the prepared task, owner, current authority, ontology/provider pins and source stamps. Both tool invocations reached `node.completed` in each run, so missing Registry authorization, an unresolved agent ID and connector execution failure are not supported explanations for these traces. Inspection and complaint preparation evidence both contained zero records. The first run retained the successful inspection checkpoint; the second retained the successful complaint checkpoint. Dependent analysis could not proceed after the other specialist failed validation. Both original runs remained failed and were preserved.

The shared schema already restricted legal citation identifiers but still permitted an empty references array for `observation`, `agreement` and `discrepancy`. The runtime validator correctly prohibited that combination. This inconsistent model-generation contract was the execution defect. Retrieval coverage and evidence gaps must be qualified as limitations/unverified findings; they cannot become uncited source facts.

Two presentation defects compounded it: the recovery classifier fell back to `tool_execution_failure` / `retry_read`, and the UI mechanically expanded the code into “investigation agent reference,” suggesting an identity problem.

### Evidence limits

Original `node.failed` records retained `ApiFailure`, the stable code, stage `delegated_invocation`, invocation IDs and diagnostic correlation. No original Python stack trace was found in the inspected service journal. Failed tool output event snapshots were truncated before their record arrays; full completed-sibling receipts and both original preparations remain available. Replaying each original finish decision against the same empty legal citation catalog raises the exact exception: “An observation/comparison must cite supplied source observations.” This identifies the validator path without claiming an unavailable historical stack.

Private originals, events, preparations, retrieval plans and replay receipt are under `.local/execution-debug-20261105/trace_*` and `original-failure-replay.json`. They are not committed because they contain configured business context.

## B. Fixes and regressions

- `runtime/capability_composition.py::analysis_schema`: source-backed finding kinds require at least one exact supplied citation pair; without source records, only limitation/unverified kinds are available. Unknown and cross-record references remain rejected. The schema guides generation; runtime never relabels a rejected model claim into success.
- `workflow_api/investigation_agents.py::InvestigationAgents.run`: standalone analysis uses that same evidence-bound schema, removing contract drift.
- `workflow_api/business_composition.py::AgentConfigurationFactory.create`: distinguishes source observations from retrieval coverage, zero matches and missing evidence in specialist instructions.
- `runtime/recovery.py` and `shared/llm_feedback.py`: classify citation/result validation as invalid model output and provide bounded, data-free correction hints.
- `workflow_api/composition_presentation.py`: citation failures get actionable recovery guidance; historical labels are reclassified only in read projections. A regression proves stored runs are unchanged. Citation failures do not offer automatic read replay.
- `frontend/src/api/compositions.ts` and `DynamicInvestigationWorkspace.tsx`: show unsupported/missing source citation or invalid result-format messages, with the existing diagnostic reference.
- Regression additions in `test_composition_presentation.py`, `test_business_composition.py` and frontend `composition.test.tsx` cover strict transport rejection, legitimate gap findings, both original empty-read scenarios through real CrewAI/runtime, historical-record preservation and distinct UI messages. Existing schema-inspection fixtures in `test_business_investigations.py` and `test_investigation_report_schema.py` were updated to inspect the new strict variants; all prior citation and output assertions remain.

No permission, evidence requirement, source mapping, credential, process definition or canonical shared contract was weakened or replaced. No complaint ID or business plan was hardcoded in product code.

## C. Actual configured workflow execution

Current mapped-source reads first verified complaint `A-2022-12-013`. Each goal then used the same HTTP composition/workflow APIs called by the frontend: compose → compile → save → validate → approve → execute → persisted view. Workers were disabled in this isolated app; its actual GraphRunner advanced the saved runs. Only the read-only business evidence connector was callable.

| Workflow | Planning | Tools | Agents/runtime | Persisted result and frontend | Status |
| --- | --- | --- | --- | --- | --- |
| A: complaint read and coverage | Actual configured model; 1 planning call | 1 native evidence read | CrewAI/Registry/GraphRunner; 6 runtime model calls | 1 complaint source record; saved report visible desktop/mobile | Completed |
| B: complaint + inspection comparison | Actual configured model; 1 planning call | 2 native evidence reads | Same runtime; 10 runtime model calls | 23 unique mapped records in comparison/report; saved report visible desktop/mobile | Completed |
| C: authorized evidence-backed summary | Actual configured model; 1 planning call | 1 native evidence read | Same runtime; 6 runtime model calls | 1 complaint source record; saved report visible desktop/mobile | Completed |

Actual diagnostic references:

- A: `trace_0da6516ac0b9404a9c12445d8cb7f87d`, run `run_55c9d41ba2ac42d79fa4363672dfd232`.
- B: `trace_e778248150ab452ab2f9de05183ffd55`, run `run_5acf2a57b55449db848c293b0ea9bcbb`.
- C: `trace_3c3d3fa9628946abb7b6156969855ca1`, run `run_c892e65872954c83961798385849994c`.

Raw plans, events, complete run/checkpoint/receipt records, frontend views and screenshots are retained as `configured-{A,B,C}-*` in the private evidence directory. `configured-results.json` summarizes execution; `completed-ui-check.json` confirms all three reports/source records rendered with zero browser or failed asset/API errors and no additional executions. These are actual configured model/source results, not controlled-provider successes. They remain qualified interpretations, not authoritative warranty decisions or verified root-cause determinations.

The original C123/C124 missing-record pattern was reproduced separately with controlled source/model responses through actual CrewAI, Registry and GraphRunner. Both reads complete, limitations and missing evidence persist, dependent interpretation reports `needs_input`, and no citation failure or invented source record is accepted.

## D. Frontend architecture

The original runs used dynamic capability compositions, not an unresolved-agent fallback and not the oldest `BusinessInvestigations` graph engine. The main Business Investigation prompt currently submits `kind: compose` when `dynamic_composition_available` is advertised (`screens/app.index.tsx`). This is an intentional retained route.

“New connected investigation” explicitly opens `?connected=1`, which uses the Phase 1–4 action-plan API and existing canonical runtime. A saved action-plan composition opened in the dynamic inspector is redirected to that connected inspector. Case links open the lifecycle/adaptive route. The oldest graph route remains compatibility behavior when no dynamic/connected/case reference is selected. No routing defect was demonstrated by these traces, so no existing workflow was silently moved between execution architectures.

Seven actual frontend→backend browser journeys verify the connected path, adaptive revisions and preserved completed reads, typed missing-input wait, desktop/mobile reply continuation, two fresh scheduled occurrences, uncertain-send restart protection and revoked-account blocking. Their Google/model transports are controlled; actual Registry, CrewAI, GraphRunner, LifecycleDriver, persistence and automation code execute.

## E. Regression evidence and exact commands

Run from `/home/raf/agentic-ai-builder`; logs are in `.local/execution-debug-20261105/`. Warnings are existing JSON Schema/FastAPI deprecations and test-only startup notices.

```sh
.venv-integrations/bin/python -m pytest -q tests/test_business_retrieval.py tests/test_business_preparation.py tests/test_business_composition.py tests/test_composition_presentation.py tests/test_investigation_report_schema.py tests/test_business_investigations.py tests/test_registry.py tests/test_runtime.py tests/test_dynamic_delegation.py tests/test_delegated_tools.py tests/test_business_planning.py tests/test_planner.py tests/test_planner_provider_errors.py tests/test_agent_memory_recovery.py
```

Initial broad run: **369 passed, 1 failed, 32 subtests passed** (`platform.log`). The sole failure was an existing controlled model fixture assuming the previous schema tree; its citation assertions were preserved while changing the schema lookup. This intermediate run is not labelled an all-pass result.

```sh
.venv-integrations/bin/python -m pytest -q tests/test_business_investigations.py tests/test_investigation_report_schema.py tests/test_composition_presentation.py tests/test_business_composition.py
```

Final affected suites: **92 passed** (`final-focused.log`). Final historical-presentation follow-up: **21 passed** (`presentation-final.log`), including the added preservation test. Empty-read reproduction follow-up: **2 passed, 27 deselected** (`empty-read-regressions.log`). These suites overlap; their counts are not added together or to the initial broad run.

```sh
.venv-integrations/bin/python -m pytest -q tests/test_connected_action_plans.py tests/test_adaptive_orchestration.py tests/test_durable_automation.py tests/test_orchestration_frontend_api.py
.venv-integrations/bin/python -m pytest -q tests/test_business_cases.py tests/test_business_case_runtime.py tests/test_simpson_lifecycle.py tests/test_generic_lifecycle_phase6.py tests/test_business_lifecycle_ui.py tests/test_lifecycle.py
.venv-integrations/bin/python -m pytest -q tests/test_business_evidence.py tests/test_business_coverage.py tests/test_business_compiler.py tests/test_business_rule_execution.py
```

Respectively **87 passed**, **93 passed plus 5 subtests**, and **101 passed** (`phases.log`, `cases.log`, `evidence.log`).

```sh
python3 .local/execution-debug-20261105/postgres_tests.py
```

Creates a disposable UTF-8 PostgreSQL 16 cluster on loopback port 55489 and a restricted application role, exports its private `BUILDER_TEST_POSTGRES_DSN`, then runs:

```sh
.venv-integrations/bin/python -m pytest -q tests/test_durable_automation_postgres.py tests/test_postgres_backend.py tests/test_generic_lifecycle_postgres.py --basetemp /tmp/execution-debug-postgres-20261105
```

**116 passed plus 23 subtests; zero skips** (`postgres-tests.log`). The disposable cluster was stopped. No live database migrated to PostgreSQL.

```sh
PATH=/home/raf/.nvm/versions/node/v22.23.3/bin:$PATH npm --prefix frontend run test
PATH=/home/raf/.nvm/versions/node/v22.23.3/bin:$PATH npm --prefix frontend run typecheck
PATH=/home/raf/.nvm/versions/node/v22.23.3/bin:$PATH npm --prefix frontend run lint
PATH=/home/raf/.nvm/versions/node/v22.23.3/bin:$PATH npm --prefix .local/execution-debug-20261105/frontend run build
PATH=/home/raf/.nvm/versions/node/v22.23.3/bin:$PATH frontend/node_modules/.bin/playwright test --config .local/execution-debug-20261105/playwright.config.ts
.venv-integrations/bin/python scripts/validate_contracts.py
git diff --check
```

**500 frontend tests in 74 files passed; typecheck, lint, production build, contracts and diff checks passed. Seven browser journeys passed.** The copied browser config points at the latest staged build and installed browser cache. A config-module-path startup error was corrected before that successful run. The configured acceptance harness also initially retained transport-envelope fields in a strict workflow body; it was corrected to match the existing frontend parser and reused the already generated plan. Neither setup failure changed product assertions or was counted as successful execution.

## F. Remaining boundaries

- C123/C124 are repository fixture identifiers, not verified configured-source complaints. A valid live identifier such as the source-verified example below is required to retrieve actual records. A missing identifier/record must produce a qualified evidence gap.
- Three read-only live model/source investigations passed. This does not establish success for arbitrary prompts, complete business evidence, external Google writes, email delivery or unattended business consent.
- Gmail/Sheets/Calendar effects remain controlled acceptance results. No live external-write authorization was requested or used.
- Existing domain process/stage compatibility and production operational prerequisites in `live-provider-checklist.md` still apply. This change does not install domain processes or replace the existing sign-in model.
- The original Python stack was not retained, and failed tool event snapshots were bounded. Original agent decisions, preparation data, successful tool events, sibling receipts and exact validator replay support the diagnosis.

## G. Reproduce a successful investigation

1. Sign in at `https://praxi.bellcorpstudio.com/app` using the existing workspace login and refresh after deployment.
2. Select Business Investigation from the main workflow prompt.
3. Submit: “Retrieve complaint and inspection evidence for complaint A-2022-12-013, compare their findings and identify missing information. Do not perform external writes.”
4. Review the generated source/task context, save the draft, validate and approve the workflow, then run the investigation.
5. Open View report. Inspect actual source records/citations and retained limitations; completed execution does not establish warranty approval or a confirmed technical cause.
6. For connected-action/adaptive/recurring controls, use Workflow → New connected investigation or a compatible prepared case. Review real destinations and exact payload approvals before authorizing any external write.

These UI steps create a new user-initiated run with normal model charges. The three acceptance runs were deliberately stored in isolated test persistence; they were not imported into the live workflow database.

## Deployment verification

Deployment receipt and public verification are recorded below after activation. Private rollback evidence is in `.local/execution-debug-20261105/`, including source archive/patch and source hashes, four database snapshots, previous frontend build, preservation fingerprints and final public browser checks. No push or Git commit is made automatically.

Deployed build **`AqbO7mh4NSGG2GRPCPVtz`** to https://praxi.bellcorpstudio.com/app from the reviewed working-tree fixes on base commit `6edc6babde37739011b7a51593bcfc57f0ee13bf`. No Git commit/push was made. API, worker and frontend services are active with zero automatic restarts. Four database snapshots passed integrity quick checks. **170,645 existing rows across 32 business tables matched before/after fingerprints.** Existing failed runs were retained.

Approved normal public sign-in, unauthenticated API rejection, active worker heartbeat, automation reads, connected-investigation goal/recipient controls, automation panel and desktop/mobile rendering passed with **zero browser errors, missing assets or failed API reads**. Both original failed runs were reopened publicly; each retains its failed status and shows the correct citation explanation/model-output classification with no retry-read control. See `public-check.json` and `public-originals-check.json`. Public checks submitted no model execution or live connector action.

The actual configured-run mobile report screenshot was visually inspected. Disposable PostgreSQL, completed-run API and staged frontend servers were stopped. Deployment services remain running. To roll back frontend assets, stop only the Builder frontend, preserve the current build, restore `previous-next` to `frontend/.next`, then restart. Backend rollback requires the prior reviewed source archive; never overwrite later database writes or automatically replay uncertain external effects.
