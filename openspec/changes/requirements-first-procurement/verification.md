# Requirements-first procurement verification

Verified 2026-10-17 18:09 IST against https://praxi.bellcorpstudio.com.

## Cause and correction

The procurement adapter treated a request to create a new BOQ as an instruction to ingest an existing spreadsheet. Explicit BOQ creation now reaches the general multi-agent planner with the original requirements and trusted workspace context. Existing source-backed procurement still validates access, now considering bounded saved references as well as prompt links.

Requirements-first guidance preserves budget, simulated-evidence labels and issuance approval. It includes a valid trigger-to-output graph and adequate bounded delegation turns. Automatic procurement planning explicitly disables customer-email automation context; it never grants supplier contact authority.

## Live evidence

Generation-only job `plan_236bced180d0439e98570b6f23cab4af` succeeded for the exact supplied 60-seat restaurant prompt, producing **60-Seat Restaurant Procurement Planning**:

- Six agents: procurement master, BOQ specialist, supplier research specialist, quotation comparison specialist, budget/delivery analyst and procurement document specialist.
- Trigger → dynamic master → review approval → output; no manual workflow input fields.
- Saved setup values: 60 seats, INR 2,500,000 ceiling, simulation permitted, approval required before issuance.
- Outputs: BOQ, supplier research, quotation comparison, procurement report, RFQ drafts, PO drafts and review status.
- External writes disabled; no tools proposed or tool assignments granted; no customer-email automation metadata.
- Outstanding information disclosed: menu/concept, premises/utilities, tax/freight/installation/contingency scope and opening date. Live supplier destinations/tools remain prerequisites for actual issuance.

An initial deployment check hit an old worker and exposed the separate-process reload requirement. A subsequent model check failed graph validation. Private, bounded diagnostic generation identified missing trigger nodes and unrelated customer-email metadata. Both were corrected and regression-tested. Final API and worker processes were restarted with the complete change. The frontend build was unchanged.

The successful live job preceded the final explicit customer-email context guard. Its complete draft also passed the final guarded provider validation offline with no additional model call. The guard has dedicated regression coverage.

Private evidence: `.local/requirements-first-procurement/live-summary.json`, `live-result.json`, `source-checkpoint.json`, and test logs. Exact original-to-final production diff: `implementation-review.patch`.

## Verification

- Broad procurement, automatic-source, live-provider, planner, API and security suite: **118 passed** before final graph/automation guidance changes.
- Final focused requirements-first, live-provider and planner regressions: **60 passed**, including missing-trigger correction and procurement/customer-email separation. These overlap the broad suite; counts are not additive.
- Canonical contract validation and generated UI contract checks passed.
- OpenSpec strict validation and whitespace checks passed.

Only planning was exercised against the public application. No workflow was saved, published, activated or executed by this verification; no RFQ, purchase order or supplier communication was issued. Runtime procurement results and live supplier connectivity were not tested.
