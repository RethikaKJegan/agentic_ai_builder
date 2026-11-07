# Complaint retrieval readiness — 7 November 2026

**Confirmed defect fixed and activated in the dedicated Simpsons backend.**
This does not add complete newest-first/joined complaint listing to the case reader.

Read-only inspection of the reported tenant's saved composition found the exact
list objective compiled with state `ready` and no gaps. Its saved retrieval
questions were `Show complaints for complaint.` and `Show inspection findings for
complaint.`, with empty identifiers and `no_supported_anchored_path` gaps. No
complaint records were read for diagnosis. The model-selected connected-plan
compiler had not enforced the case identifier requirement already present in the
older composition path. This was a planning/readiness defect, not evidence that
permissions should be relaxed or records fabricated.

`workflow_api/action_plans.py` now requests an exact complaint ID before compiling
selected case-retrieval actions without an anchor. It returns the existing
`ACTION_INPUT_REQUIRED` metadata understood by the input UI. Explicit user-supplied
complaint/serial inputs can create a fresh preparation for the same pinned version;
existing preparations are preserved. This does not change completed/failed runs,
remove immutable pins, replay actions or bypass source/Registry checks.

Two added regressions in `tests/test_connected_action_plans.py` both failed before
the implementation fix. Final narrow run `/tmp/complaint-readiness-fixed.log`:
**2 passed, 0 failed, 33 deselected**, 11.93 seconds. Deselected tests were not
executed or counted as passes. A temporary misplaced guard caused diagnostic
failures during editing; it was corrected before this passing run and rollout.
The complete affected run (`tests/test_connected_action_plans.py`,
`tests/test_business_cases.py`, `tests/test_business_composition.py`) is
`/tmp/complaint-readiness-final.log`: **101 passed, 0 failed, 0 skipped**,
10 warnings, 367.91 seconds. This includes both new regressions; overlapping
focused counts are not added to the total.

An online read-only backup of only the dedicated Simpsons application store was
copied into `.local/complaint-readiness/startup`. An audit hook prohibited SQLite
connections outside that clone and prohibited network calls. Current configured
application construction completed with **zero new/changed/removed schema objects**,
zero network calls and no worker startup. No production schema migration was run.
Evidence: `evidence/startup-check.json`. This is not a production backup/RPO proof.

Read-only active-state inspection found no queued/running tenant work before
restarting only `agentic-builder-simpsons.service`. The service became healthy;
an authenticated session GET returned HTTP200 and `client-isolated` mode. No
credentials, reverse proxy, operator/Subway service or source records changed.
No paid model test or real external action was executed. The prior source file
is retained privately under `.local/complaint-readiness/rollback`.

A live request used the existing unanchored preparation and an explicit read-only
action proposal, bypassing model generation entirely. It returned HTTP422,
`ACTION_INPUT_REQUIRED`, and typed `complaint_id` clarification metadata before
workflow compilation. **Zero model calls, source reads or external actions** were
performed by that smoke check. Evidence: `evidence/live-guard.json` and
`evidence/rollout.json`.

Contracts, whitespace and scoped strict OpenSpec validation pass. The user should
refresh and prepare a new workflow; the existing failed run remains immutable.
Use a concrete complaint ID for case investigation. Multi-record sorted/linked
listing needs a separately supported query plan; no complete-list guarantee is
made by this fix, and source/authentication failures can still correctly block work.

Earlier release-remediation backend runs predate this follow-up change and are not
universal qualification of the current action-plan implementation. Production
readiness, incident-audit and external staging/provider/operational blockers remain.
