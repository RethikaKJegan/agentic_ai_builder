# Immediate-work default verification — 10 November 2026

Saved Overview request `81bc8586-4623-42ee-a1c8-5f16bd4a2562` used one_time with
recurrence once, hour/date null and no missing requirements. This reached the
scheduler and asked “At what time should this run?” The user had asked only to
investigate overheating/power loss and email the findings. Three saved service-hour
report requests showed the same empty-once scheduling error.

The router and shared planning guidance now distinguish composed one-time work
from future scheduled execution. An otherwise empty once recurrence becomes none
when the objective contains no execution scheduling cue. Reporting periods remain
data filters. Explicit dates, hours and recurring schedules are preserved; genuine
future timing gaps still ask a question. The cue guard only protects this narrow
normalization and does not parse or authorize schedules. Existing review, account,
source and external-action approval boundaries remain.

- Broader regressions: 92 passed, 10 warnings (Overview routing/API/integration,
  composed intent, knowledge and short-prompt defaults).
- After the final cue refinement, immediate/composed focused tests: 28 passed,
  2 warnings, overlapping the broader suite. Cases include the exact reported
  prompt, “may cause” wording, named-month data reports, today/previous-month data
  windows, explicit future execution, recurring schedules and retained email review.
- The actual saved faulty route was replayed against copied Simpson metadata and
  account context with controlled interpretation and blocked network. It prepared
  intent with schedule null and recurrence none. This verifies the timing correction,
  not root-cause investigation accuracy or email delivery. No paid model, source
  record query, live workflow submission or provider write was used.
- Copied-store startup protected existing rows. Canonical contracts, generated
  contract drift, strict OpenSpec and patch formatting passed.

Private evidence: `.local/immediate-workflow-default-20261110/` and
`/tmp/immediate-workflow-tests.log`, `/tmp/immediate-workflow-final.log`.
