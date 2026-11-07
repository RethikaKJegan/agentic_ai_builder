# Tool-result visibility — 7 November 2026

**Implemented, tested and published to the existing Builder preview and dedicated
Simpsons backend. No workflow/tool was rerun to repair the display.**

## Cause and correction

Connected database-read tasks entered a generic external-write receipt branch.
That branch discarded source records, retained only draft/event/spreadsheet/status
fields, and read a nonexistent task.selected_tool_id instead of the persisted
selected_tools mapping. Hence the completed inspector showed `tool_id:null` and
`receipt:{}` even though the saved read contained records.

The existing owner-scoped composition projection now retains mapped source records
and rule results, derives the actual tool identity from the selected tool/workflow
node, and reports actual record counts and collections. Tool metadata also retains
recorded message/thread IDs, spreadsheet URLs, bounded read counts and relevant
request/version references. Unknown result shapes expose field names only, not
arbitrary provider payload values. Completed run documents/pins remain unchanged.

The existing inspector renders a readable tool name (including **Database read**),
actual read counts and source collections before technical details. Existing report
source-record views remain available. A real zero-row read says **No matching
records**. A pending tool says **Tool has not returned a result yet**; historical
missing receipt details remain explicitly unavailable, not invented. Reports now
label their tool-execution section accurately rather than describing every read
as an external action.

## Exact tests and gates

- Before-fix backend regressions: **2 failed**, 22 deselected, 4.11s;
  `/tmp/tool-visibility-before.log`. Both reproduce the bad projection/receipt.
- Final complete affected backend modules `tests/test_composition_presentation.py`
  and `tests/test_connected_action_plans.py`: **59 passed, 0 failed, 0 skipped**,
  6 warnings, 157.18s; `/tmp/tool-visibility-qualified.log`. Actual controlled
  database reads verify tool identity, counts, source preservation and no extra
  reads while projecting. Existing approval, tenant, history and action checks pass.
- Final frontend composition/orchestration modules: **34 passed in 2 files**,
  0 failed/skipped, 3.97s; `/tmp/tool-visibility-ui-final.log`. Includes readable
  database metadata, true zero matches, legacy missing receipt and pending states.
  Earlier overlapping 33-test run is not added.
- Typecheck, lint and isolated production build pass:
  `/tmp/tool-visibility-{types,lint,build}.log`. The built chunk was checked for the
  final pending-state text before publication. Active build was not rebuilt in place.
- Contract, SQL inventory drift, whitespace and strict scoped OpenSpec pass.
  Inventory remains 1,193 calls /123 literal tables; only source-line references
  shifted. No canonical workflow/agent/tool schema or database migration changed.

Pytest uses existing `.venv-integrations/bin/python -B -m pytest -q -p
no:cacheprovider`, `PYTHONDONTWRITEBYTECODE=1`, and private basetemp paths. Frontend
uses Node22.23.3 and the isolated `.local/release-blocker-remediation/frontend-v4`
copy with existing dependencies, excluding environment files and active build.

## Scoped publication and real browser verification

Isolated tenant startup against a read-only backup copied to a private directory
required zero new/changed/removed schema objects, zero network calls and no workers.
The audit hook rejects database connections outside that copy. Evidence:
`evidence/startup-check.json`. This is not a production backup/RPO rehearsal.

The first publication attempt was rejected by automatic review under the earlier
deployment hold; that command did not run. The user's later explicit website
publication instruction was documented in `evidence/authorization-scope.md`.
Read-only checks proved zero queued/running tenant work. A safer credential-free
publication procedure was subsequently approved and executed: only the existing
Simpsons/frontend preview services restarted, with prior frontend build retained
for rollback. No credential/configuration/reverse-proxy changes, source writes,
paid calls, provider effects or migrations. See `evidence/preview-publication.json`.
Unauthenticated tenant sessions remain HTTP401; public login remains HTTP200.

A real desktop Chromium check opened the user's existing saved composition on the
public HTTPS preview with an existing scoped Simpsons identity. All non-read API
requests were blocked by the browser harness. The inspector displayed **Database
read** and **2 record(s) retrieved** for the original complaints read. These are
two source records, not a claim of two complaints. No rerun/provider read occurred.
Evidence: `evidence/browser-verification.json`; private screenshot:
`.local/tool-result-visibility/inspector.png`. The diagnostic collector initially
matched hidden technical JSON as well as visible labels; its reviewable artifact
was sanitized and the collector narrowed to visible paragraph labels. No source
record values remain in that artifact.

The fix reconstructs existing display from recorded outputs and applies to future
views. It cannot fabricate historically absent receipts or turn zero matches into
business evidence. Earlier production-readiness, audit, external-provider and
separate procurement-suite limitations remain outside this presentation fix.
