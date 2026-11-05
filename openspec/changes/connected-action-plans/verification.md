# Phase 1 verification — 5 November 2026

Repository: `/home/raf/agentic-ai-builder`; branch `agentic_ai_builder`; starting commit `13e3e37`. Initial worktree clean. Backend only; no frontend, deployment, service restart, live provider/model call or live external write.

## Baseline and defects

The preceding read-only audit passed 230 existing tests plus four subtests. Before implementation edits, the additional focused baseline was:

```sh
PYTHONDONTWRITEBYTECODE=1 .venv-integrations/bin/python -B -m pytest -q -p no:cacheprovider \
 tests/test_inventory_report_runtime.py tests/test_business_cases.py tests/test_business_case_runtime.py \
 --basetemp /tmp/connected-action-baseline
```

**59 passed, 4 failed, 138 warnings, 203.31 s.** All four failures were the reported research-handoff fixture variants. The fixture bypassed `DelegationSession.__init__` and lacked its composition guard. It now invokes the real constructor. Existing valid/invalid/failed/cancelled assertions are unchanged. Focused corrected run: **4 passed, 8 deselected, 2 warnings, 0.60 s** (`/tmp/connected-research-fixed.log`).

A separate actual research integration defect was exposed by the new action path: anonymous public-research tools legitimately receive a null Registry credential, but the connector base required `cred_extension_ddgs`. Anonymous tools now accept the null reference; authenticated tools retain their exact credential check. Registry assignment/authorization/schema checks remain mandatory. The new search→fetch test and existing SSRF/provider regressions cover the integration.

The first broad regression also found a stale Sheets fixture: it expected five tools, although `extension_sheets_create_report` already existed at HEAD. The fixture now asserts the exact six tool IDs and excludes all three creation operations from its default-enabled assertion. No tool was removed or enabled to satisfy it.

A Phase 1 compatibility regression in the first broad run made unconfigured Simpson preparation return `command_rejected` instead of its existing driver budget stop. Mixed-goal preparation is now opt-in to stages explicitly requiring `content.prepare`. The original assertion is unchanged and passed in the targeted correction run. Initial broad results (**147 passed/1 failed** core, **127 passed/1 failed** connectors) are superseded by final runs below, never counted as successful qualification.

Initial new-test runs also caught isolated test directory/policy setup errors, the registered read timeout floor, canonical Sheets `/edit` URLs, URL comparison quoting, and optional skips incorrectly compiled as final outputs. These were corrected before final acceptance. Research and safe-read retry fixtures use actual connector bind/constructor interfaces; assertions were not weakened.

## Final commands and exact results

### New action-plan acceptance

```sh
PYTHONDONTWRITEBYTECODE=1 .venv-integrations/bin/python -B -m pytest -q -p no:cacheprovider \
 tests/test_connected_action_plans.py --basetemp /tmp/connected-phase1-final-evidence
```

**33 passed, 10 warnings, 107.25 s.** Log: `/tmp/connected-phase1-final-evidence.log`.

A final optional-dependency guard follow-up passed **11 overlapping tests**, 22 deselected, 2 warnings, 20.91 s (`/tmp/connected-final-guards.log`). It is not added to the distinct total.

### Existing platform

```sh
PYTHONDONTWRITEBYTECODE=1 .venv-integrations/bin/python -B -m pytest -q -p no:cacheprovider \
 tests/test_runtime.py tests/test_registry.py tests/test_planner.py tests/test_planner_provider_errors.py \
 tests/test_dynamic_delegation.py tests/test_delegated_tools.py \
 tests/test_business_preparation.py tests/test_business_planning.py \
 --basetemp /tmp/connected-final-platform
```

**184 passed, 32 subtests passed, 22 warnings, 139.68 s.** Log: `/tmp/connected-final-platform.log`.

### Existing Google and research connectors

```sh
PYTHONDONTWRITEBYTECODE=1 .venv-integrations/bin/python -B -m pytest -q -p no:cacheprovider \
 tests/test_google_tools.py tests/test_inventory_report_runtime.py tests/test_supplier_discovery.py \
 connector_extension/tests/test_connectors.py connector_extension/tests/test_sheet_report.py \
 connector_extension/tests/test_sheet_creation.py connector_extension/tests/test_generalized_sheets.py \
 connector_extension/tests/test_generalized_features.py connector_extension/tests/test_application.py \
 --basetemp /tmp/connected-final-connectors
```

**128 passed, 6 subtests passed, 218 warnings, 372.64 s.** Log: `/tmp/connected-final-connectors.log`.

### Existing cases, Simpson, retail, composition and memory

```sh
PYTHONDONTWRITEBYTECODE=1 .venv-integrations/bin/python -B -m pytest -q -p no:cacheprovider \
 tests/test_business_cases.py tests/test_business_case_runtime.py tests/test_simpson_lifecycle.py \
 tests/test_generic_lifecycle_phase6.py tests/test_business_composition.py tests/test_agent_memory_recovery.py \
 --basetemp /tmp/connected-final-core
```

**148 passed, 26 warnings, 581.55 s.** Log: `/tmp/connected-final-core.log`.

The four disjoint final suites total **493 tests and 38 subtests passed; zero final failures**. Focused follow-ups overlap those counts and are not added.

### Contract, OpenSpec and source gates

```sh
PYTHONDONTWRITEBYTECODE=1 .venv-integrations/bin/python -B scripts/validate_contracts.py
/home/raf/.nvm/versions/node/v22.23.3/bin/node \
 /home/raf/.nvm/versions/node/v22.23.3/lib/node_modules/@fission-ai/openspec/bin/openspec.js \
 validate connected-action-plans --type change --strict
git diff --check
```

Shared schemas/fixtures (including the executed orchestration-plan example) and strict OpenSpec passed. Changed backend Python modules compile. Warnings are the repository's existing JSON Schema RefResolver and FastAPI lifespan deprecations. No all-repository or production readiness claim.

## Executed acceptance and artifacts

The main acceptance uses real SharedBusinessPreparation, BusinessComposition, AgentConfigurationFactory, Registry assignment/approval, GraphRunner, CrewExecutor/CrewAI, Sheets report creation, MailConnector, effect journals and disposable persistence. Only model/source/Google HTTP transports are controlled. No domain workflow template is installed in the planner; test proposals are provider fixtures over a registered capability catalogue.

Executed order: complaint read → structured CrewAI findings/report tabs → exact-payload Sheet approval → registered Sheet creation/read verification → actual URL binding → CrewAI subject/body → exact-payload Gmail approval → registered Gmail send → persisted verified receipt. Reconstructing runtime/composition before the send preserves the Sheet result and does not duplicate it. Re-advancing the completed run does not resend. Repeated Gmail actions have independent IDs, inputs, approvals and RFC message/effect identities. Calendar creation, search/fetch provenance and persistent-case attachment execute separately through the same stack.

Repository artifacts:

- `shared/contracts/orchestration-plan-v1.json`: additive contract; no frozen process/case/workflow contract replacement.
- `shared/contracts/examples/orchestration-plan-v1.json`: actual controlled plan example.
- `docs/connected-action-plans/execution-trace.json`: complete plan, persisted run and runtime events.
- `docs/connected-action-plans/case-trace.json`: separate complete case, composition and persisted execution, plus explicit qualification.
- `docs/connected-action-plans/README.md`: API/contract/binding/authority/tool/recovery guide.

Raw temporary sources:

```
/tmp/connected-phase1-final-evidence/test_prompt_to_actual_crewai_s0/connected-action-trace.json
/tmp/connected-phase1-final-evidence/test_action_plan_case_attachme0/connected-case-trace.json
```

SHA-256:

- Execution trace/raw source: `47a734ca518b095a919dd4b8cc0b97ac59357b7cc720e069725599dbe7ad75dd`.
- Case raw source: `ad9c6ebe41a19268730e52ddb5c3e7ae96f8d0c439470c51e42fa27ad58287df`.
- Case repository artifact (adds the controlled-execution qualification): `0a4fe1a525cd137fa35f2d3a7fddf2fa376088ab41a95873a342a47fdffe64ca`.

These fixtures prove local execution/binding/persistence behavior, not live provider access, a real engineer assignment, live model quality, a completed physical investigation or commercial authorization. The recipient is explicitly supplied and allowlisted; absent authoritative engineer contact data remains an input requirement.

## Files and boundaries

New helpers: `workflow_api/action_plans.py`, `workflow_api/action_bindings.py`, `runtime/action_plans.py`; new shared schema/example, `tests/test_connected_action_plans.py`, guide/traces and this OpenSpec change.

Existing integration edits: `planner/provider.py`, `workflow_api/business_composition.py`, `business_cases.py`, `business_ontology_routes.py`, `capability_contracts.py`, `composition_presentation.py`, `service.py`, `runtime/graph.py`, `runtime/recovery.py`, `connector_extension/app.py`, `connector_extension/common.py`, `scripts/validate_contracts.py`. Existing fixtures corrected: `tests/test_inventory_report_runtime.py` and `connector_extension/tests/test_generalized_sheets.py`.

No frontend or service/configuration/deployment files changed. Existing frozen contracts, Simpson process definitions, retail packages, source mappings and credentials are unchanged. No provider consent or Registry permission is granted by model content. There is no schema migration, separate executor, separate case store or new scheduler.

Phase 2 adaptive plan revision/replanning, Phase 3 scheduled/recurring execution and Gmail reply workers, and frontend integration remain excluded. Authorized live connection/model-quality validation and production qualification remain unperformed. Current Calendar adapter guest invitations remain unsupported. Missing real identities/times/permissions still block; uncertain effects still require operator/connector reconciliation.
