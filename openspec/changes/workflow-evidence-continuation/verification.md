# Verification — 11 November 2026

Related backend regressions: 194 passed, one stale assertion failed because earlier
percentage support adds guidance after the shared defaults. Updated that assertion
to verify both shared defaults and aggregate guidance; its focused rerun passed.
No production code was changed to satisfy the stale assertion. All 195 selected
cases therefore passed across the broad run and focused recheck.

Coverage includes the exact overheating/calendar prompt, today/tomorrow and India
local-date rollover, distinct execution schedules, recurring workflows, exact
Calendar approval, missing recipient, no ontology matches, scoped citations,
idempotency, authorization denial, email, Sheets, empty reports and percentages.
The fallback content workflow completed through the actual Registry/CrewAI graph
with controlled model responses, with and without scoped ontology evidence, and
without executing delivery or creating a schedule.

Replayed the actual saved failed Simpsons request from an isolated online SQLite
copy. Calendar start/end resolve to 11 November 2026 12:45–13:15 Asia/Kolkata,
calendar_id=primary, without a workflow timer. This validates interpretation and
input binding only; no live query, model request or Calendar event was executed.

Contracts, Python syntax, diff formatting and strict OpenSpec validation passed.
An initial broad test run was interrupted after SQLite reported a full disk.
Removed this session's temporary test files and two obsolete release npm download
caches, then completed verification in isolated memory-backed test directories.
No production history, credential, installed dependency or backup was removed.

The new fallback is a report-only workflow that identifies deferred operations.
It does not fulfill an unavailable query or external action, substitute sampled
metrics for complete results, invent evidence, bypass access or remove existing
approval requirements. Existing blocked drafts retain their immutable history;
the corrected behavior applies to newly generated requests. Runtime/provider
failures remain possible and are not hidden as successful execution.
