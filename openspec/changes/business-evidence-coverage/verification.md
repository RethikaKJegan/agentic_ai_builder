# Implementation verification — 4 November 2026

Implemented locally; ready for repository handoff, not downstream acceptance. No deployment, service restart, live knowledge/environment import, company writes or new paid-model calls occurred. The live website does not yet contain these changes.

## 1. Files changed

New backend modules: `workflow_api/business_coverage.py`, `business_environments.py`, `investigation_coverage.py`, and `schemas/business-evidence-record-v1.json`. Integrated through `business_investigations.py`, `business_ontology_routes.py`, `investigation_jobs.py`, `scripts/simpson_investigation.py`; added `scripts/business_evidence_environment.py`.

Frontend: `src/api/client.ts`, `src/api/investigations.ts`, `src/screens/app.index.tsx`, `features/investigations/InvestigationContext.tsx`, `InvestigationWorkspace.tsx`, `InvestigationPanels.tsx`. Tests: new `tests/test_business_coverage.py`, `test_business_environments.py`, `frontend/e2e/evidence-coverage.spec.ts`; updated investigation jobs/unit tests. Documentation: this OpenSpec change, `docs/simpson-business-ontology/evidence-coverage.md`, Phase 3 link and contributor handoffs.

## 2. Existing components reused

Five-layer ontology and stable concepts; versioned mappings/policies; Phase 2 authorized retrieval/native reference resolution; existing task requirement registry; durable Phase 3 graphs/jobs; current planner and specialist CrewAI implementations; report citations; permissions; existing scenario and independent source-checking infrastructure. Shared workflow/agent/tool contracts remain unchanged. Existing history/recurrence capabilities are preserved.

## 3. Evidence providers

Added deterministic typed-record providers for physical-identity certificate, invoice selection/profile, scoped policy applicability, required exclusions, technical disposition and commercial authorization. Existing complaint/inspection/reference/catalogue providers remain authoritative for original observations. Added complaint-observation requirements and required-vs-optional truncation classification. Providers reject invalid chronology, non-finite/negative hours, mismatched identity/linkage, conflicting evidence and inadequate recorded authority. A known rejection, expiry, revocation or confirmed exclusion is an outcome, not absent evidence. Scenario authority-role comparisons do not authenticate actual Simpson authorization.

## 4. Connected source cases

`A-2025-9-070` and `I-2026-3-068`, selected through bounded read-only source verification. No runtime complaint-ID branches. The CLI accepts other cases with supported anchors and usable source context. Stable source IDs/values/read times and native relationships remain intact.

## 5. Scenario records

24 connected cases: two source cases × 12 variants; 144 typed supplemental records across identity, invoice, policy, technical decision, authorization and exclusions. Missing business events and supplied associations are explicitly generated with source-qualified provenance. A combined invoice/sale profile is generated unless all required fields match one complete native source record. Genuine observed values are retained, never silently corrected. Policy month/hour parameters reuse the pinned application fallback profile, without asserting applicability to the company case. Scenario effective periods, exclusions and decisions are configured evidence, not official company policy or approval.

## 6. Supported task contracts

Comparison requires complaint observations plus supported inspection linkage/report/observations; optional engineer/catalogue detail cannot impose warranty requirements. Warranty depends on selected policy scope, required dates, assessment date, identity, hours and exclusions. Replacement review requires linked technical disposition, identity and separately recorded authorization. Eligibility, recommendation, readiness and official approval remain distinct; `official_approval` is false.

## 7. Coverage Validator

Pure deterministic evaluation over existing requirement results and typed case records. States: ready, ready_with_limitations, needs_input, insufficient_evidence, conflicting_evidence, unsupported. Mandatory/optional facts, source references, conflicts, outcomes and recovery information remain structured. Content-derived provider fingerprint pins executable provider code and contracts. Unsupported tasks remain unsupported rather than gaining synthesized facts.

## 8. Coverage manifest

Immutable content-addressed release with schema/contract versions, ontology ID/hash, mapping fingerprint, policy revisions, provider fingerprint, case IDs, supported tasks, expected/actual per-case validation, coverage status, provenance and known limitations. Installation reproduces validation and checks captured evidence against owned saved retrieval requests, source-qualified fields/edges and hashes. Secrets and forged source provenance are rejected. Scoped caching still compares current stored content; withdrawals live in a separate registry.

## 9. Pre-run validation

New HTTP planning, queued planning and CLI planning use `prepare_plan`: authorize, retrieve initial bounded evidence or select an explicit validated scenario, validate coverage, persist a signed scoped preflight receipt, then send compact verified context to the existing planner. Scenario/prompt/explicit identifiers must agree. Idempotent request keys bind preparation inputs. Missing assessment date or selected policy is actionable input, never silently inferred from the machine clock. The direct legacy service `plan` remains for historical/existing integrations.

## 10. Runtime revalidation

Scenario execution checks the pinned release/current provider and withdrawals. Real-source execution performs new bounded reads before dependent analysis and final reporting. Changed source observations are retained and earlier interpretations qualified. Missing mandatory decision evidence suppresses the dependent expensive analysis, while unrelated reads/comparison/reporting can continue. Current authorizations remain enforced. Withdrawn evidence is marked in its source trace. Prior saved runs and original source records are preserved.

## 11. Missing-information improvements

Reports separate technical execution, decision readiness, mandatory decision blockers and optional limitations. Only requested tasks impose requirements; normalized gaps remain scoped/deduplicated with recovery and source context. Negative determinations are known outcomes. Invalid/conflicting/absent real evidence is not hidden. Original source gaps remain inspectable even when a selected scenario supplies separately identified supplemental evidence.

## 12. UI

Workflow options offer company sources or an explicit validated scenario/case, assessment date, policy and Check evidence. Pre-run coverage is shown before execution. Existing canvas/node/results layout remains. Reports distinguish execution state from decision readiness and optional evidence limitations. Scenario provenance is visible; full original fields/references and pinned environment information are available in technical evidence. Registry/list actions are preserved.

## 13. Exact backend commands

See [the complete terminal guide](../../../docs/simpson-business-ontology/evidence-coverage.md#exact-backend-commands): fresh isolated prepare, cases/tasks, coverage/records/mappings/manifest, preflight, plan/requirements/graph, run/execute/report and withdrawal. `--planning-mode offline --analysis-mode offline` is diagnostic execution, not a claim of paid-model/CrewAI quality. Company-source mode omits scenario context and uses authorized credential references, without copying secrets.

## 14. Automated verification

- Broad relevant backend regression: **742 passed**, 78 warnings, 619.59 s. Includes business/investigation, existing scenarios, knowledge retrieval, source mapping, queries and database budgets. This preceded final contract/source tightening; subsequent affected checks are listed separately and overlap, so counts are not summed.
- Subsequent scoped Phase 3/runtime checks: **69 passed**, 10 warnings, 141.65 s.
- Final current provider/environment checks: **28 passed**, 2 warnings, 32.20 s. Covers the 12-variant matrix, schema/provenance, invalid hours/dates, source association, scoping, forgery, withdrawal/runtime changes, storage mutation and secret rejection.
- Full frontend suite: **456 passed**, 70 files.
- Browser checks against isolated staged build: **8 passed**, 36.6 s; desktop/mobile evidence context/preflight/report plus existing canvas/execution/recovery/list-action flows. Screenshots inspected for report and mobile context layout.
- TypeScript, ESLint, production staged Next build, shared contract validation, generated UI contract drift, scoped strict OpenSpec validation and `git diff --check` passed.

Logs are private `/tmp/business-coverage-{regression,final-scoped,providers-final,frontend-full,browser,build-verified,contracts-delivery}.log`. Only an isolated staged `.local/business-coverage-build/frontend` build was used; live `.next` was not replaced. Deprecation warnings are recorded, not counted as failures. No whole-repository all-suite claim.

## 15. Real-source integration

Eight independent bounded checks passed: inspection, warranty, replacement and recurrence for each of the two source cases. Actual complaint/report references, controlled/engineer resolution, observed dates and invoice candidates were cross-checked against original records. These checks establish retrieval behavior, not missing business events or eligibility. Baseline records zero company/live-application writes, model calls and copied credentials; source ontology unchanged. Evidence is private in `/tmp/simpson-evidence-coverage-20261104-01/refinement-report.json` and task artifacts.

## 16. Scenario acceptance

The final release `dataset_9b54fb86a77d96de3bd547ed` and acceptance receipt are in the same private directory (`environment.json`, `acceptance.json`); their dataset IDs match and acceptance passed. The final CLI smoke check executed eight actual commands (preflight, plan, requirements, graph, validate, run creation, execution, report) on that release; `terminal-delivery.json` records completed status and zero mandatory gaps. Earlier terminal inspection also exercised all report sections and case/manifest/records/mapping commands. Each case is evaluated against all three declared contracts, then passed through the actual preparation, planner, run creation, executor and report services in explicit offline diagnostic mode. Complete cases have zero mandatory gaps; optional source limitations can remain. Known negative technical, rejected-authorization, expired-policy and confirmed-exclusion cases produce outcomes. Missing inspection/exclusions/authorization, invalid dates and ambiguous/conflicting evidence retain their expected blockers. Runtime readiness must match released readiness for all tasks. This is separate from independent real-source checks and does not establish live model reasoning quality.

## 17. Remaining boundaries

This release does not make all arbitrary company data complete. Real records missing identity, policy applicability, exclusions or authorizations remain honestly incomplete. QA/CAPA, corrective-action incorporation, full recurrence completeness, external operational approvals, dispatch/reverse-logistics and arbitrary new business tasks need additional contracts/providers/evidence. Scenario identity certificates and role checks are supplied test evidence, not real company proof. Captured scenario observations remain snapshots; new observations require a new immutable release. Existing permission, record/byte and workflow call/time controls remain; no new model token or cost ceiling was added. Live rollout and model-backed acceptance were deliberately not performed.
