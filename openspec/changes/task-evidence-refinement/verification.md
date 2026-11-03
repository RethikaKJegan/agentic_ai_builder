# Evidence refinement verification — 3 November 2026

Subsequent rollout: the user explicitly approved deployment with the report-schema fix. Live revision 8 and compatible backend/worker are now deployed; original runs/versions are preserved. See [rollout verification](../investigation-report-schema/verification.md). Statements below describe the original backend-only implementation and testing stage.

Implemented and tested locally. No frontend edits, deployment, restart, live ontology import, company writes, paid model calls or external evidence transfers.

## 1. Files modified

- Authoring: `scripts/build_business_knowledge_pack.py`, `ontology/business-reference/knowledge-pack.json`; new `retrieval-contract.json` and `retrieval-mappings.json` in that directory.
- Retrieval: `workflow_api/business_knowledge.py`, `business_knowledge_model.py`, `business_resolution.py`, `business_retrieval.py`, `schemas/business-knowledge-v1.json`.
- Evidence/reporting: new `workflow_api/business_evidence.py`; updated `business_investigations.py`, `investigation_graph.py`, `investigation_agents.py`, `schemas/simpson-investigation-v1.json`.
- Terminal/acceptance: `scripts/simpson_investigation.py`; new `scripts/check_evidence_refinement.py`, `scripts/check_evidence_scenarios.py`.
- Tests: `tests/test_business_knowledge.py`, `test_business_retrieval.py`, `test_business_investigations.py`; new `test_business_evidence.py`, `test_evidence_scenarios.py`.
- Documentation: evidence-refinement guide, Phase 3 cross-reference, contributor handoffs and this OpenSpec change.

Shared contracts, existing graph inventory and original source-mappings file are unchanged. Supplemental retrieval projections have their own hashed import catalogue.

## 2. Retrieval improvements

Authoring revision 2 has 47 mappings, up from 36. An isolated revision-8 snapshot compiled with 79 concepts, 48 relationships and 23 parent links. Forty-five mappings were observed in sampled metadata; two unavailable fields remain explicit. Lookup execution uses saved mappings/native IDs, not complaint-specific branching.

## 3. Verified controlled codes

Independent source checks resolved UC22 / “Alternator Bracket Broken” for I-2026-3-068. A separate history workflow for engine SJV43509849CACFC000328 resolved the reported UUID to UC32 / “Engine RPM fluctuation.” Original references remain unchanged; unmatched references remain unresolved.

## 4. Date formats

Failure-date mapping accepts declared DD-MM-YYYY, ISO calendar dates and native dates. Inspection-date mapping accepts ISO timestamp calendar components without inventing a timezone. Invalid dates remain invalid; unsupported slash dates are ambiguous. Original values, precision and conversion meaning remain available; no creation-date substitution.

## 5. New relationships

Native references support complaint-to-code, complaint-to-engineer and ticket-to-timeline reads. Serial invoice lookup is explicitly a candidate association, never physical identity. Company/list observations and candidate multiplicity are retained. No unsupported work-order join was introduced.

## 6. Task evidence definitions

Registry covers complaint retrieval, comparison, warranty readiness, replacement evidence, history and effectiveness evidence readiness. Each fact has provider, validation, level and registered recovery. Selected policy is distinct from applicability. Comparison does not require downstream authorization or inspection completion.

## 7. Gap normalization

Stable gaps distinguish not retrieved/found, invalid, ambiguous, unsupported mapping and not established. Permission denial remains the existing denied API response. Deduplication preserves task/record distinctions and merges provenance. Agent suggestions cannot add mandatory requirements; original outputs remain inspectable.

## 8. Recovery actions

Advisory recovery identifies allowed source/knowledge inspection or fresh typed plan inputs, including assessment date/policy selection. Actions do not certify facts or update company records. Reports expose grouped gaps, resolutions, associations and recovery without repeated agent-generated missing-information lists.

## 9. Isolated scenarios

Twelve complete/incomplete/ambiguous scenarios cover comparison, warranty, replacement and effectiveness. Generated sign-off, authorization, return receipt, QA, incorporation and exposure require explicit case context and valid chronology. Scenario facts cannot establish live business conclusions. Private output: `/tmp/simpson-evidence-scenarios-final-20261103`.

## 10. Exact terminal commands

See [backend testing commands](../../../docs/simpson-business-ontology/evidence-refinement.md#exact-backend-testing-commands) for fresh private-store setup, question, requirements, Phase 2 preview, run/execute and every report section. The real CLI interfaces were exercised using offline diagnostic planning/analysis.

## 11. Automated results

- Broad Phase 1–3/retrieval/database regression: **689 passed**, 78 warnings, 513.20 seconds (`/tmp/evidence-refinement-regression.log`).
- Follow-up retrieval/report checks: **159 passed**; schema/knowledge/graph: **70 passed**; Phase 3/jobs/graph after registry fingerprinting: **60 passed**.
- Supplemental-catalogue isolation checks: **90 passed**.
- Final packet/scenario/report checks: **80 passed**, 10 warnings, 67.42 seconds (`/tmp/evidence-refinement-packet-final.log`).

Counts overlap and must not be added. Warnings are dependency/FastAPI deprecations.

Final shared contract validation, generated UI contract drift check, strict scoped OpenSpec validation and `git diff --check` all passed.

Nine local fixture-provider turns through the actual CrewAI adapter passed with the configured tokenizer and existing 14,000-token budget. Largest input reservation was 10,300 tokens, leaving 3,700 completion tokens. Compatible records retain all references; conflicts and required evidence remain intact. Only optional timeline model context is sampled, with disclosure; full retrieval persists. This is adapter/context verification, not actual-model reasoning evaluation. Artifact: `/tmp/simpson-evidence-refinement-final-20261103/context-budget-check.json`.

## 12. Read-only real-source results

**12 checks passed**: comparison, warranty, replacement and effectiveness evidence readiness for I-2026-3-068, A-2025-9-070 and A-2022-12-013. Independently queried bounded expected ticket/report/code/user/invoice/timeline IDs and dates matched. Current package digest matches the tested snapshot.

Comparison had no current-task gaps for I-2026-3-068 and A-2025-9-070. A-2022-12-013 retained two optional gaps: unresolved symptom reference and invalid failure date. Warranty retained six/six/seven relevant gaps respectively; replacement two, effectiveness six. No identity, approval or effectiveness was fabricated.

Additional real history run completed and every terminal report section passed. Private artifacts: `/tmp/simpson-evidence-refinement-final-20261103/refinement-report.json` and sibling files. Existing Phase 2 source acceptance also passed in `/tmp/simpson-evidence-refinement-live-20261103-a`.

Checks used isolated application stores and credentials borrowed in memory: zero copied credentials, company writes or model calls. Bounded observations do not establish database-wide completeness.

## 13. Remaining unavailable evidence

Authoritative policy applicability, physical identity, exclusions, activity sign-off, confirmed diagnosis, commercial authorization, incorporation, complete population and exposure require supported providers. Sampled metadata lacks `enginedetails.buildDate` and `enginedetails.engineModel`; this is not proof of company-wide absence. Work-order typed linkage remains unverified.

## 14. Deferred features

Frontend/deployment, live knowledge import, additional agents, company writes, operational notifications/scheduling, unrestricted prompts, full effectiveness monitoring, knowledge-graph materialization and reinforcement learning. Existing runs are not rewritten. Future deployment requires fresh plans and an explicit versioned knowledge import. Current website is unchanged by this task.
