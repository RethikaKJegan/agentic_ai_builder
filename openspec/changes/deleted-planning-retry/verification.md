# Deleted planning-result retry verification

Verified 2026-10-17 18:37 IST on https://praxi.bellcorpstudio.com.

## Confirmed cause

The user deleted `planned_591e401bfc1c532e` successfully. The browser retained its original durable planning retry key. Submitting that key returned completed job `plan_e8470c2b700e4df79c7eaae278c28afb`, which retained the deleted generic draft. The latest-workflow read also returned its historical saved revision, causing the generation helper's existing-workflow popup. The earlier source-routing verification did not cover this completed-job retry path.

## Correction

Planning submissions now follow a deterministic replacement-job key when a completed result belongs to a workflow deleted in the same workspace. Its effective queued planner key is also fresh, avoiding the original in-process planner cache. Repeated submissions converge on one replacement job. Original jobs, results, workflow revisions and tombstones are unchanged. Historical job reads alone never trigger generation.

Latest-workflow lookup returns not found for deleted workflows. Authorized explicit revision lookup remains available. Existing non-deleted workflow preservation behavior remains intact. The fix changes only `workflow_api/planning_jobs.py` and `workflow_api/service.py`; no frontend build, credentials, contracts or provider permissions change.

## Evidence

- 74 regression tests plus six subtests passed, covering repeated deletion, concurrent submissions, durable retry identity, workspace isolation, payload mismatch, history preservation, security, existing API behavior and both procurement routing paths.
- Canonical contract validation, strict OpenSpec validation and whitespace checks passed.
- API and planning worker were restarted with no active planning job interrupted. Final source hashes match the reviewed patch.
- Public verification reused the exact affected original prompt, context and durable retry key after confirming its fingerprint privately. The retry key was not logged or exposed.
- That original submission resolved to replacement job `plan_5e0b5c5d6ffc42c4aad6d536fc1ddb6a`. A repeated submission returned the same replacement job, which succeeded with native procurement setup and no unresolved requirements.
- Deleted latest lookup: 404. Explicit historical revision lookup: 200. The original job result remained identical.
- Fresh result `planned_2233c2783b970796` had no saved revision (latest lookup 404), so generation's existing-saved-workflow branch cannot mistakenly reopen the old deleted revision for this result.

Private evidence: `.local/deleted-planning-retry/regressions.log`, `source-checkpoint.json`, `live-summary.json`, `live-result.json` and `live-generation.log`. Exact production diff: `implementation-review.patch`.

## Scope and user retry

The public check generated a draft only; it did not save, approve, publish, activate or execute a workflow, create a tracking workbook, or contact suppliers. Existing background automation was not changed.

Refresh Overview and submit the same prompt. No rename, browser-storage clearing or additional deletion is required. The same browser retry key now resolves to the verified fresh result, which the ordinary generation flow can save as a new draft.
