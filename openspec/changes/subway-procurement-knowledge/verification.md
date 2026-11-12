# Verification — 12 November 2026

The final deployed source is the isolated Subway `r2` artifact recorded in `deployment.md`. Tests use controlled model/external transports unless explicitly identified as real-source read-only rehearsals. No successful arbitrary live OpenAI procurement prompt or actual Google delivery is inferred from these results.

## Final results

- Final exact-artifact acceptance: **74 passed**. Includes the complete query-planner → registered deterministic assessment → report chain, RAG, identity/status/date/rule checks, Calendar routing, ontology usage, demo-profile compatibility and evidence-resolution regressions.
- Explicit evaluator/usage/conditional/paginated evidence regression suite: **57 passed**, run from the isolated Subway release. The final r2 changes add trusted enum bindings and guidance; evaluator and usage code is unchanged between these artifacts.
- Existing Knowledge Map frontend domain suite: **24 passed**; no frontend files/build were changed.
- Broad runtime/domain/integration suite: **309 passed, one failure**. The failure was the newly introduced empty-selection Calendar context expansion. It was corrected, and the exact failing test plus the complete Calendar file passed in the final 74-test acceptance. There is no remaining known failing test from that run. This is not reported as a fresh all-green 310-test run.
- Earlier source-stable 37-test and exact-artifact 75-test runs also passed. Counts overlap and must not be added together.
- Final modeled-scenario unit run: **36 passed**, including 16 deterministic scenarios / 226 records, scoped native identity, explicit modeled cross-source correspondences, orphan parents, missing evidence and large-decimal precision.
- Canonical contract validation, generated UI-contract comparison, strict scoped OpenSpec validation and whitespace checks passed.
- Final exact-candidate real-source rehearsal: **six assessments passed** using genuine restored Subway data and a consistent isolated application-store copy. Workers/model/external actions/company writes/production application writes were zero.

The first broad attempt encountered an exhausted host filesystem and temporary-store errors; it is not passing evidence. Only task-owned disposable copies and temporary stores were removed. Subsequent tests used memory-backed temporary directories. An independent filesystem cleanup later released additional space; it is not attributed to this change.

## Exact final acceptance command

Run from the final source directory recorded in deployment.md, using the repository's Python environment:

```bash
PYTHONDONTWRITEBYTECODE=1 /home/raf/agentic-ai-builder/.venv-integrations/bin/python -m pytest -q -p no:cacheprovider \
  tests/test_subway_procurement_knowledge.py \
  tests/test_subway_procurement_runtime.py \
  tests/test_calendar_action_routing.py \
  tests/test_workflow_ontology_usage.py \
  tests/test_subway_demo_definitions.py \
  tests/test_subway_evidence_resolution.py
```

The executed command additionally used a unique memory-backed TMPDIR/--basetemp. Full output: `.local/subway-procurement-20261112/r2-acceptance.log`.

Explicit adaptive-fix suite:

```bash
python -m pytest -q -p no:cacheprovider \
  tests/test_investigation_evaluator_protocol.py \
  tests/test_live_evaluator_wrapper.py \
  tests/test_conditional_investigation_evidence.py \
  tests/test_paginated_query_evidence.py \
  tests/test_automation_usage_settlement.py
```

Full output: `.local/subway-procurement-20261112/adaptive-fix-regressions.log`.

The broad suite additionally covered `test_subway_autonomy`, `test_subway_automations`, `test_workflow_knowledge_isolation`, `test_business_knowledge`, `test_business_identity`, `test_business_rule_execution`, `test_business_rules`, `test_simpsons_client_isolation`, `test_subway_client_auth`, `test_slack_gmail`, `test_adaptive_orchestration`, and `test_live_providers`. Full output: `regressions-final.log` in the same private directory.

## Required acceptance matrix

| # | Requested capability | Evidence and boundary |
|---|---|---|
| 1 | Identity resolution | Native scoped identity/direct-reference tests, duplicates, foreign namespace and missing relationships. |
| 2 | Approvals in progress | Source enum/observed-status definitions, discovery and exact PO→approval native references tested. Snapshot audit confirms 390 in-progress approval records. Arbitrary live model interpretation remains unverified. |
| 3 | Previous reporting month | Configured-timezone, half-open month/quarter tests; existing query/automation temporal regressions. No invented fiscal calendar. |
| 4 | PO rule checks | Deterministic supplier/amount/item/approval/requisition checks and actual registered-tool execution. |
| 5 | Budget readiness | Exact line allocation, consistent budget reference, existing native location, period and currency prerequisites; overrun fixture; genuine missing-currency outcome. |
| 6 | Invoice reconciliation | PO/receipt line quantities and header-grain checks; duplicates and currency conflicts. Real invoice item/currency/full-order evidence remains insufficient. |
| 7 | Approval investigation | Known source state distinct from granted decision; explicit delay parameters, cycle/stage date semantics, inconsistent history. |
| 8 | Missing evidence | Absent requisitions/approvals/reservations/parent approvals retain supported independent results and explicit gaps. |
| 9 | Generated scenarios | Stable source-shaped analytical fixtures and modeled correspondences; production connector rejects record/scenario injection. No scenario import in production. |
| 10 | Readiness outcomes | PASS, FAIL, INSUFFICIENT_EVIDENCE and NOT_APPLICABLE tested, with optional gaps separated from required prerequisites. |
| 11 | Autonomous investigation | Actual Overview, metadata/ontology context, registered query planner, Registry, CrewAI/GraphRunner, deterministic tool, adaptive receipt assessment and report; controlled models. Existing retrieve_more/replan regressions preserve completed receipts. |
| 12 | Adaptive execution fixes | Strict evaluator transport, malformed/invalid decisions, provider-wrapper failures and provider-managed usage settlement regressions pass. |
| 13 | Scheduled automations | Existing recurring/event/revocation/recovery/occurrence tests pass with ordinary query contracts unchanged. New assessments require exact reviewed consent; no live schedule is edited. |
| 14 | Gmail/Calendar | Existing fake-transport integration and exact authorization/approval tests; corrected Calendar-only source-free routing passes. No real communication. |
| 15 | Simpson regression | Existing identity/knowledge/rule/client-isolation tests; production shared source hashes and unrelated PIDs unchanged. No Simpson account/source/workflow mutations. |
| 16 | Tenant isolation | Cross-tenant tool rejection, source/context/map isolation tests and live Subway GET rejection of a genuine Simpson source ID. |
| 17 | Historical freshness | Historical source attestations survive all six actual-source rehearsals; temporal assessment inputs cannot bypass reviewed bounds. No current-source coverage is asserted. |
| 18 | Complete workflow | Exact runtime chain includes model query planning, trusted assessment selection, authorized evidence traversal, typed outcomes, adaptive evidence, report and recorded Knowledge Map field/rule/version usage. Full live-provider business-quality acceptance remains unverified. |

## Genuine source rehearsal results

Each assessment selected two base records. Query counts scanned complete base sources, while deterministic comparisons cover only those selected records and bounded supporting evidence.

| Assessment | Base matched count | Related records | Deterministic results | Readiness |
|---|---:|---:|---:|---|
| PO validation | 43,439 | 111 | 50 | PASS; optional requisition gap retained |
| PO reconciliation | 43,439 | 111 | 350 | PASS for required receipt checks; optional invoice gaps retained |
| Budget comparison | 43,439 | 111 | 50 | INSUFFICIENT_EVIDENCE |
| Approval assessment | 94,452 | 6 | 12 | PASS for assessing the recognized state, not granting approval |
| Invoice investigation | 42,533 | 16 | 70 | INSUFFICIENT_EVIDENCE |
| Receipt verification | 41,457 | 26 | 60 | PASS |

The final planning knowledge was 69,321 canonical bytes, inside the 70 KB allowance. All sources attested historical_snapshot. The authoring source audit separately enumerated complete observed status counts and missing-field presence, without returning operational records.

## Deployment verification

Authenticated public HTTPS checks passed for Subway session, tools, worker health, data-query availability and the existing investigation page. The `subway_assess`, `subway_query` and `subway_documents` tools are registered. Anonymous login/app/API boundaries remain 200/307/401. A genuine foreign source ID returns 404 to Subway.

Consistent backup, current source credentials, Google records, ontology/package records, schedules and history counts were verified. Only Subway restarted; original shared source hashes and other service PIDs remain unchanged. No live workflow, paid model call, source write or external action was submitted by smoke checks.

Private evidence: `.local/subway-procurement-20261112/`, including `source-audit.json`, `candidate-source-rehearsal.json`, `release-manifest.json`, `deployment-before.json`, `deployment.json`, `https-smoke.json`, logs and the private compressed Subway backup.
