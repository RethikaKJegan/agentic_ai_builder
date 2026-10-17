# Source-backed procurement routing verification

Verified 2026-10-17 18:29 IST on https://praxi.bellcorpstudio.com.

## Correction

The previous BOQ-creation matcher captured "prepare the BOQ" in the workshop source-ingestion prompt. Explicit requirements-reading and source-table instructions now take precedence. New BOQ generation from a description still reaches the general planner, including when supplementary knowledge links are present. Source discovery, Registry checks, provider authorization and approval policy remain enforced.

The production change is confined to `workflow_api/procurement.py`; `implementation-review.patch` records its exact before/after diff. No contracts or frontend assets changed.

## Verification evidence

- 90 tests passed across source-routing regressions, requirements-first planning, integrated procurement, live providers, automatic sources and security.
- Coverage includes the exact operator-guide prompt, saved sources, description-based restaurant planning, supplementary knowledge, missing sources, inaccessible sources and canonical native setup generation without procurement execution.
- Canonical contracts and generated UI contract checks passed; strict OpenSpec validation and whitespace checks passed.
- Both `agentic-builder-backend.service` and `agentic-builder-worker.service` were restarted after tests, with no active planning jobs interrupted. Both returned active. The reviewed source hash matches the deployed file.
- Public generation-only job `plan_8d006329dcf2419d8147fb15bf09ae5f` succeeded for the exact **Workshop Automatic Procurement Full Test 6** prompt.
- The result is a canonical draft with `metadata.procurement_plan`, no unresolved requirements, no manual input fields and no executable agent tool assignments.
- Extracted setup retains automatic action mode, a 100000 INR purchasing limit, quotation/award/PO monitoring and fulfilment settings.

Private evidence is retained in `.local/procurement-source-routing/`: `regressions.log`, `deploy.log`, `source-checkpoint.json`, `live-result.json` and `live-summary.json`.

## Scope and retry

Verification generated a draft and inspected sources only. It did not save, validate for publication, approve, publish, activate or execute a workflow; it created no tracking workbook and sent no RFQs, POs or supplier messages. Full procurement runtime remains for the user's staged test.

Existing drafts retain their prior generated metadata. Regenerate from Overview using the workshop prompt and a fresh test name, then review **Procurement setup & status**. Refreshing an old generic draft does not convert it into native procurement setup. No existing draft or published revision was rewritten and no Registry blockers were manually removed.
