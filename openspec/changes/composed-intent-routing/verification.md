# Composed intent routing verification — 10 November 2026

Hosted jobs `plan_6961dd421e4b49d5a21ca3b3a8896403` and
`plan_824c1839e9434d2b970a83c1f0857c9a` failed before composition with
OVERVIEW_INTENT_INVALID, “A read-only route cannot request external actions.”
The reported prompt was “Count tickets by status, show their average hmr, and
email me the summary.” This is composed analysis and delivery.

After schema and secret validation, population/investigation routes that contain
external actions are now canonicalized to one_time for none/once recurrence or
recurring for repeating recurrence. Only the category changes. Business scope,
side effects, missing requirements and recurrence remain intact. Explicit negative
instructions, scoped accounts, capability filtering, Registry and exact-payload
approval checks remain. Transport guidance also explains this category distinction.

- 77 tests passed, 10 warnings: category correction, unchanged source proposals,
  exact reported prompt preparation, no-external-write/email restrictions,
  read-only routing, Overview API/integration, knowledge and short-request defaults.
- The exact prompt prepared and validated a workflow against actual copied Simpson
  metadata/account with the deliberately contradictory population/email route.
  A status-grouped count/average-HMR query separately passed actual metadata
  validation. Route/action/model responses were controlled; no live-model accuracy,
  source query execution or email delivery is claimed by this replay.
- The generated email still requires exact-payload approval and the workflow stays
  draft pending review. No provider write or paid model call was made in checks.
- Contract validation, generated-contract drift, strict OpenSpec and patch
  formatting checks passed.

Private evidence: `.local/composed-intent-fix-20261110/` and
`/tmp/composed-intent-tests.log`.
