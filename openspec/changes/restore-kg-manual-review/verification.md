# Manual relationship review verification — 18 October 2026

Restored the original business-label/direction review form in Inspect only. Uses
the existing semantic review API with the selected relationship ID and exact KG
revision. Poll results cannot overwrite an in-flight save. Stale/read-only guards
remain. Technical join permissions and backend/planner behavior are unchanged.

Evidence in `.local/kg-manual-review/`:
- `tests.log`: 11 focused tests passed, including ambiguous/needs-review correction,
  current revision, stale/read-only disabling, existing inspector and filters.
- `types.log`, `lint.log`, `build.log`: typecheck, lint and isolated build passed.
- `browser.log`: 4 desktop tests passed, including ambiguous correction through
  intercepted review API and existing PostgreSQL/MongoDB/combined-source previews.
  The synthetic overlapping self-link is selected using its keyboard-accessible
  button; the earlier pointer-only test timed out on the SVG overlap. Existing
  graph layout was not changed as part of this narrowly scoped correction.
- `activation-verified/result.json`: frontend EleW6dZe9YkaYwp8yE9N- deployed,
  448 previous assets retained; backend/worker PIDs and configuration unchanged.
- `live-browser.log`: live desktop label edit and enabled confirmation verified;
  the test did not submit the label. External/mutation requests were blocked.

No real relationship review was overwritten by acceptance checks. No cloud write,
email/Calendar action or semantic extraction request was initiated by these checks.
Record exploration, technical permission editing and extra mode controls stay hidden.
